from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # <--- You might be missing this
import time                          # <--- You were missing this!
import random                        # <--- You might be missing this too!
from .models import Membership, Transaction
from .models import Membership, Transaction, Loan
from .models import Membership, Transaction, Loan, ChamaGroup
@login_required
def dashboard(request):
    try:
        membership = Membership.objects.filter(user=request.user).first()
        
        if not membership:
            return render(request, 'base.html', {'message': 'You have not joined a Chama yet.'})

        loan_limit = membership.savings_balance * 3
        
        context = {
            'membership': membership,
            'loan_limit': loan_limit,
        }
        return render(request, 'chama/dashboard.html', context)
        
    except Exception as e:
        print(f"Error: {e}")
        return render(request, 'base.html')

@login_required
def deposit(request):
    if request.method == 'POST':
        # Get the amount from the form
        amount = int(request.POST.get('amount'))
        
        # 1. SIMULATION: Pause for 2 seconds
        time.sleep(2)  # <--- This is what caused the crash!
        
        # 2. SIMULATION: Generate fake M-Pesa Code
        ref_code = f"QKH{random.randint(1000000, 9999999)}"
        
        # 3. Get membership
        membership = Membership.objects.get(user=request.user)
        
        # 4. Create Receipt
        Transaction.objects.create(
            membership=membership,
            amount=amount,
            transaction_type='deposit',
            reference=ref_code
        )
        
        # 5. Update Balance
        membership.savings_balance += amount
        membership.save()
        
        # 6. Success Message
        messages.success(request, f"Confirmed! Received KES {amount}. Ref: {ref_code}")
        return redirect('dashboard')

    return render(request, 'chama/deposit.html')

@login_required
def request_loan(request):
    # 1. Get the user's membership
    membership = Membership.objects.filter(user=request.user).first()
    if not membership:
        messages.error(request, "You are not a member of any Chama.")
        return redirect('dashboard')

    # 2. Calculate the Limit
    max_loan = membership.savings_balance * 3
    
    if request.method == 'POST':
        amount = int(request.POST.get('amount'))
        
        # 3. THE RULE ENFORCER: Check if amount is too high
        if amount > max_loan:
            messages.error(request, f"REJECTED: You can only borrow up to KES {max_loan}")
            return redirect('request_loan')
        
        # 4. Check if they already have an active loan (Optional but good for MVP)
        active_loan = Loan.objects.filter(membership=membership, status='approved').exists()
        if active_loan:
             messages.error(request, "REJECTED: You must repay your current loan first.")
             return redirect('request_loan')

        # 5. Create the Loan Request
        Loan.objects.create(
            membership=membership,
            amount=amount,
            status='pending' # It waits for Admin approval
        )
        
        messages.success(request, "Loan Application Submitted! Waiting for Admin approval.")
        return redirect('dashboard')

    # If GET request, show the form
    return render(request, 'chama/loan_request.html', {'max_loan': max_loan})
# --- ADD AT THE BOTTOM OF chama/views.py ---

@login_required
def admin_dashboard(request):
    # 1. Security Check: Only allow 'staff' (Superusers)
    if not request.user.is_staff:
        messages.error(request, "Access Denied: Admins Only.")
        return redirect('dashboard')

    # 2. Get all Pending Loans
    pending_loans = Loan.objects.filter(status='pending').order_by('-date_requested')
    
    # 3. Get Total Group Savings (For the "Vault" display)
    # We sum up the savings_balance of all memberships
    total_savings = 0
    members = Membership.objects.all()
    for member in members:
        total_savings += member.savings_balance

    context = {
        'pending_loans': pending_loans,
        'total_savings': total_savings,
    }
    return render(request, 'chama/admin_dashboard.html', context)

@login_required
def process_loan(request, loan_id, action):
    # 1. Security Check
    if not request.user.is_staff:
        return redirect('dashboard')
        
    # 2. Find the specific loan
    loan = Loan.objects.get(id=loan_id)
    
    # 3. Decision Logic
    if action == 'approve':
        loan.status = 'approved'
        messages.success(request, f"Loan of KES {loan.amount} APPROVED for {loan.membership.user.username}.")
    elif action == 'reject':
        loan.status = 'rejected'
        messages.error(request, f"Loan of KES {loan.amount} REJECTED.")
        
    loan.save()
    return redirect('admin_dashboard')

# Make sure you have Loan and Transaction imported at the top!
# from .models import Membership, Transaction, Loan

@login_required
def dashboard(request):
    try:
        membership = Membership.objects.filter(user=request.user).first()
        
        if not membership:
            return redirect('join_chama')
        loan_limit = membership.savings_balance * 3
        
        # --- NEW PART 1: Get Active Loan ---
        # We look for a loan that is either 'approved' or 'pending'
        active_loan = Loan.objects.filter(
            membership=membership, 
            status__in=['approved', 'pending']
        ).first()

        # --- NEW PART 2: Get Recent Transactions (Last 5) ---
        recent_transactions = Transaction.objects.filter(
            membership=membership
        ).order_by('-created_at')[:5]
        
        context = {
            'membership': membership,
            'loan_limit': loan_limit,
            'active_loan': active_loan,          # <--- Sending this to HTML
            'recent_transactions': recent_transactions, # <--- Sending this to HTML
        }
        return render(request, 'chama/dashboard.html', context)
        
    except Exception as e:
        print(f"Error: {e}")
        return render(request, 'base.html')
    
    # --- Add this function at the bottom ---
@login_required
def join_chama(request):
    if request.method == 'POST':
        code = request.POST.get('code').strip() # Remove spaces
        
        # 1. Check if group exists
        try:
            group = ChamaGroup.objects.get(chama_code=code)
        except ChamaGroup.DoesNotExist:
            messages.error(request, "Invalid Chama Code. Please ask your Chairperson.")
            return redirect('join_chama')
            
        # 2. Check if already a member
        if Membership.objects.filter(user=request.user, group=group).exists():
            messages.info(request, "You are already a member of this group!")
            return redirect('dashboard')

        # 3. Create Membership (Default role is 'member')
        Membership.objects.create(
            user=request.user,
            group=group,
            role='member',
            savings_balance=0.00
        )
        
        messages.success(request, f"Successfully joined {group.name}!")
        return redirect('dashboard')

    return render(request, 'chama/join.html')