import json
import logging
import time
import random
import os

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from django_daraja.mpesa.core import MpesaClient

# Import Models and Forms
from .models import Membership, Transaction, Loan, ChamaGroup
from .forms import ChamaCreationForm
from .utils import render_to_pdf # Ensure you have utils.py created from previous steps

logger = logging.getLogger('chama')

# --- HELPER: Format Phone ---
def format_phone_number(phone):
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone

# --- 1. PUBLIC PAGES ---
def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'chama/index.html')

def pricing(request):
    return render(request, 'chama/pricing.html')

def about(request):
    return render(request, 'chama/about.html')

# --- 2. CORE DASHBOARD (THE MISSING FUNCTION) ---
@login_required
def dashboard(request):
    membership = Membership.objects.filter(user=request.user).first()
    
    # Redirect if they haven't joined a group yet
    if not membership:
        return redirect('join_chama')

    group = membership.group

    # 1. Standard Context
    context = {
        'membership': membership,
        'loan_limit': membership.savings_balance * 3,
        'active_loan': Loan.objects.filter(membership=membership, status__in=['approved', 'pending']).first(),
        'recent_transactions': Transaction.objects.filter(membership=membership).order_by('-created_at')[:5],
    }

    # 2. MERRY-GO-ROUND: Get Rotation
    if group.chama_type == 'merry':
        context['rotation_members'] = Membership.objects.filter(group=group).order_by('joined_at')

    # 3. SAVINGS: Calculate Goal Progress
    if group.chama_type == 'savings' and group.target_amount > 0:
        total_group_savings = sum([m.savings_balance for m in Membership.objects.filter(group=group)])
        percentage = (total_group_savings / group.target_amount) * 100
        context['percentage_complete'] = min(percentage, 100)
        context['total_group_savings'] = total_group_savings

    return render(request, 'chama/dashboard.html', context)

# --- 3. ONBOARDING (Create/Join) ---
@login_required
def join_chama(request):
    if request.method == 'POST':
        code = request.POST.get('code').strip()
        try:
            group = ChamaGroup.objects.get(chama_code=code)
        except ChamaGroup.DoesNotExist:
            messages.error(request, "Invalid Chama Code.")
            return redirect('join_chama')
            
        if Membership.objects.filter(user=request.user, group=group).exists():
            messages.info(request, "You are already a member!")
            return redirect('dashboard')

        Membership.objects.create(user=request.user, group=group, role='member')
        messages.success(request, f"Joined {group.name}!")
        return redirect('dashboard')

    return render(request, 'chama/join.html')

@login_required
def create_group(request):
    if request.method == 'POST':
        form = ChamaCreationForm(request.POST)
        if form.is_valid():
            group = form.save()
            Membership.objects.create(user=request.user, group=group, role='admin')
            messages.success(request, f"Group '{group.name}' created! Code: {group.chama_code}")
            return redirect('dashboard')
    else:
        form = ChamaCreationForm()
    return render(request, 'chama/create_group.html', {'form': form})

# --- 4. FINANCIALS (Deposit/Loan) ---
@login_required
def deposit(request):
    if request.method == 'POST':
        try:
            amount = int(request.POST.get('amount'))
            phone_number = request.user.phone_number 
            account_ref = format_phone_number(phone_number)
            
            cl = MpesaClient()
            callback_url = f"{os.getenv('NGROK_URL')}/api/v1/c2b/callback"
            
            response = cl.stk_push(account_ref, amount, "ChamaVault", "Deposit", callback_url)
            
            if response.response_code == "0":
                checkout_id = response.checkout_request_id
                membership = Membership.objects.filter(user=request.user).first()
                
                Transaction.objects.create(
                    membership=membership,
                    amount=amount,
                    transaction_type='deposit',
                    reference=checkout_id,
                    status='pending'
                )
                messages.success(request, "STK Push Sent! Enter PIN on your phone.")
            else:
                messages.error(request, f"M-Pesa Error: {response.error_message}")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
        return redirect('dashboard')
    return render(request, 'chama/deposit.html')

@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            stk_callback = body.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_id = stk_callback.get('CheckoutRequestID')

            logger.info(f"Callback: {result_code} ID: {checkout_id}")

            if result_code == 0:
                transaction = Transaction.objects.get(reference=checkout_id)
                membership = transaction.membership
                group = membership.group
                
                # Get Receipt
                meta_data = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                mpesa_receipt = next((item['Value'] for item in meta_data if item['Name'] == 'MpesaReceiptNumber'), None)
                
                # Penalty Logic
                amount_to_credit = transaction.amount
                today = timezone.now().day
                if today > group.contribution_day:
                    penalty = group.late_penalty_fee
                    if amount_to_credit > penalty:
                        amount_to_credit -= penalty
                    else:
                        amount_to_credit = 0

                transaction.reference = mpesa_receipt
                transaction.status = 'completed'
                transaction.save()

                if group.chama_type == 'savings':
                    membership.savings_balance += amount_to_credit
                elif group.chama_type == 'merry':
                    group.pot_balance += amount_to_credit
                    group.save()
                    # Add rotation winner logic here if desired
                
                membership.save()
            else:
                try:
                    t = Transaction.objects.get(reference=checkout_id)
                    t.status = 'failed'
                    t.save()
                except Transaction.DoesNotExist:
                    pass

        except Exception as e:
            logger.error(f"Callback Error: {e}")
            
    return JsonResponse({"Result": "OK"})

@login_required
def request_loan(request):
    membership = Membership.objects.filter(user=request.user).first()
    if not membership:
        return redirect('dashboard')
    group = membership.group
    max_loan = membership.savings_balance * 3
    
    if request.method == 'POST':
        amount = int(request.POST.get('amount'))
        
        if amount > max_loan:
             messages.error(request, f"Limit exceeded. Max: {max_loan}")
             return redirect('request_loan')

        # TABLE BANKING LIQUIDITY CHECK
        if group.chama_type == 'lending':
            total_savings = sum([m.savings_balance for m in Membership.objects.filter(group=group)])
            total_loans = sum([l.amount for l in Loan.objects.filter(membership__group=group, status='approved')])
            liquid_cash = total_savings - total_loans
            
            if amount > liquid_cash:
                messages.error(request, f"Group only has KES {liquid_cash} available.")
                return redirect('request_loan')

        Loan.objects.create(membership=membership, amount=amount, status='pending')
        messages.success(request, "Loan Requested!")
        return redirect('dashboard')

    return render(request, 'chama/loan_request.html', {'max_loan': max_loan})

@login_required
def repay_loan(request):
    membership = Membership.objects.filter(user=request.user).first()
    active_loan = Loan.objects.filter(membership=membership, status='approved').first()
    
    if request.method == 'POST':
        amount = int(request.POST.get('amount'))
        # Simulate payment for MVP (In production, use STK Push here too)
        time.sleep(1)
        active_loan.amount -= amount
        if active_loan.amount <= 0:
            active_loan.status = 'paid'
            active_loan.amount = 0
            messages.success(request, "Loan Repaid!")
        else:
            messages.success(request, f"Paid {amount}. Balance: {active_loan.amount}")
        active_loan.save()
        return redirect('dashboard')

    return render(request, 'chama/repay_loan.html', {'loan': active_loan})

# --- 5. ADMIN & UTILS ---
@login_required
def admin_dashboard(request):
    membership = Membership.objects.filter(user=request.user).first()
    if not membership or (membership.role != 'admin' and not request.user.is_staff):
        return redirect('dashboard')
    
    group = membership.group
    members = Membership.objects.filter(group=group)
    pending_loans = Loan.objects.filter(membership__group=group, status='pending')
    total_savings = sum([m.savings_balance for m in members])
    
    # Recent Logs
    recent_deposits = Transaction.objects.filter(membership__group=group, transaction_type='deposit').order_by('-created_at')[:20]

    context = {
        'group': group,
        'pending_loans': pending_loans,
        'total_savings': total_savings,
        'recent_deposits': recent_deposits,
        'member_labels': [m.user.username for m in members],
        'member_data': [float(m.savings_balance) for m in members],
    }

    if group.chama_type == 'lending':
        total_loans_out = sum([l.amount for l in Loan.objects.filter(membership__group=group, status='approved')])
        context['liquid_cash'] = total_savings - total_loans_out
        context['total_loans_out'] = total_loans_out

    return render(request, 'chama/admin_dashboard.html', context)

@login_required
def process_loan(request, loan_id, action):
    if not request.user.is_staff: # Add membership admin check here in prod
        # For MVP we allow is_staff
        pass
        
    loan = Loan.objects.get(id=loan_id)
    if action == 'approve':
        loan.status = 'approved'
        messages.success(request, "Loan Approved")
    elif action == 'reject':
        loan.status = 'rejected'
        messages.error(request, "Loan Rejected")
    loan.save()
    return redirect('admin_dashboard')

@login_required
def group_settings(request):
    membership = Membership.objects.filter(user=request.user).first()
    if not membership or membership.role != 'admin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        membership.group.contribution_day = int(request.POST.get('deadline_day'))
        membership.group.late_penalty_fee = int(request.POST.get('penalty_fee'))
        membership.group.contribution_amount = int(request.POST.get('contribution_amount'))
        membership.group.save()
        messages.success(request, "Rules Updated!")
        return redirect('admin_dashboard')

    return render(request, 'chama/settings.html', {'group': membership.group})

@login_required
def download_statement(request):
    membership = Membership.objects.filter(user=request.user).first()
    transactions = Transaction.objects.filter(membership=membership).order_by('-created_at')
    context = {
        'membership': membership,
        'transactions': transactions,
        'user': request.user,
        'date': timezone.now(),
        'group': membership.group
    }
    return render_to_pdf('chama/pdf_statement.html', context)