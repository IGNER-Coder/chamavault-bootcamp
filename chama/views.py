from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # <--- You might be missing this
import time                          # <--- You were missing this!
import random                        # <--- You might be missing this too!
from .models import Membership, Transaction
from .models import Membership, Transaction, Loan
from .models import Membership, Transaction, Loan, ChamaGroup

def index(request):
    # If they are already logged in, send them to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'chama/index.html')
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
        amount = int(request.POST.get('amount'))
        
        # 1. Simulation
        time.sleep(2)
        ref_code = f"QKH{random.randint(1000000, 9999999)}"
        
        # 2. Get Data
        membership = Membership.objects.filter(user=request.user).first()
        group = membership.group
        
        if not membership:
            messages.error(request, "No group found.")
            return redirect('dashboard')

        # 3. Create Receipt (Happens for both types)
        Transaction.objects.create(
            membership=membership,
            amount=amount,
            transaction_type='deposit',
            reference=ref_code
        )

        # --- THE FORK IN THE ROAD ---
        
        if group.chama_type == 'savings':
            # SCENARIO A: Standard Savings
            membership.savings_balance += amount
            membership.save()
            messages.success(request, f"Deposit Confirmed! New Balance: {membership.savings_balance}")

        elif group.chama_type == 'merry':
            # SCENARIO B: Merry-Go-Round
            
            # A. Update Group Pot
            group.pot_balance += amount
            
            # B. Track that THIS member contributed (for records)
            membership.savings_balance += amount 
            membership.save()
            
            # C. Calculate Target Pot (e.g. 5 members * 1000 = 5000)
            member_count = Membership.objects.filter(group=group).count()
            target_pot = group.contribution_amount * member_count
            
            messages.success(request, f"Contribution Received! Pot: {group.pot_balance} / {target_pot}")

            # D. CHECK FOR WINNER (The Automation)
            if group.pot_balance >= target_pot and target_pot > 0:
                # 1. Find someone who hasn't eaten yet
                winner = Membership.objects.filter(group=group, has_eaten=False).first()
                
                if winner:
                    # 2. PAYOUT!
                    Transaction.objects.create(
                        membership=winner,
                        amount=group.pot_balance, # They take the whole pot
                        transaction_type='withdrawal', # It leaves the system
                        reference=f"WIN-{random.randint(1000,9999)}"
                    )
                    
                    # 3. Reset the Cycle
                    payout_amount = group.pot_balance
                    group.pot_balance = 0 # Empty the pot
                    winner.has_eaten = True
                    winner.save()
                    
                    messages.success(request, f"🎉 MERRY-GO-ROUND ROUND COMPLETE! {winner.user.username} has been paid KES {payout_amount}!")
                else:
                    messages.info(request, "Round complete, but everyone has eaten! Admin needs to reset the cycle.")
            
            group.save()

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
    # 1. Security Check
    if not request.user.is_staff:
        messages.error(request, "Access Denied: Admins Only.")
        return redirect('dashboard')

    # 2. Get Pending Loans
    pending_loans = Loan.objects.filter(status='pending').order_by('-date_requested')
    
    # --- THIS WAS THE MISSING PART CAUSING THE CRASH ---
    members = Membership.objects.all()  # <--- You need to define 'members' here!
    # ---------------------------------------------------

    # 3. Calculate Total Savings & Prepare Chart Data
    total_savings = 0
    member_labels = []
    member_data = []
    
    for member in members:
        total_savings += member.savings_balance
        member_labels.append(member.user.username)
        member_data.append(float(member.savings_balance))

    context = {
        'pending_loans': pending_loans,
        'total_savings': total_savings,
        'member_labels': member_labels,
        'member_data': member_data,
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

@login_required
def repay_loan(request):
    # 1. Get the active loan
    membership = Membership.objects.get(user=request.user)
    active_loan = Loan.objects.filter(membership=membership, status='approved').first()
    
    if not active_loan:
        messages.info(request, "You have no active loans to repay!")
        return redirect('dashboard')

    if request.method == 'POST':
        amount = int(request.POST.get('amount'))
        
        # 2. Validation: Don't overpay
        if amount > active_loan.amount:
            messages.error(request, f"You only owe KES {active_loan.amount}. Do not overpay.")
            return redirect('repay_loan')

        # 3. Simulate Payment
        time.sleep(2)
        ref_code = f"PAY{random.randint(1000000, 9999999)}"
        
        # 4. Create Transaction Receipt
        Transaction.objects.create(
            membership=membership,
            amount=amount,
            transaction_type='loan_repayment',
            reference=ref_code
        )
        
        # 5. DEDUCT from Loan Amount (The Logic)
        active_loan.amount -= amount
        
        # 6. Check if fully paid
        if active_loan.amount <= 0:
            active_loan.status = 'paid'
            active_loan.amount = 0 # Ensure no negative numbers
            messages.success(request, "Congratulations! Loan fully repaid.")
        else:
            messages.success(request, f"Payment Received. Remaining Balance: KES {active_loan.amount}")
            
        active_loan.save()
        return redirect('dashboard')

    return render(request, 'chama/repay_loan.html', {'loan': active_loan})

@login_required
def repay_loan(request):
    # 1. Find the User's Membership
    membership = Membership.objects.filter(user=request.user).first()
    
    # 2. Find their ACTIVE loan (Approved or Pending Repayment)
    # We filter for 'approved' because that's the status when they have money.
    active_loan = Loan.objects.filter(membership=membership, status='approved').first()
    
    # Safety Check: Do they even have a loan?
    if not active_loan:
        messages.info(request, "You have no active loans to repay!")
        return redirect('dashboard')

    if request.method == 'POST':
        amount = int(request.POST.get('amount'))
        
        # 3. Validation: Don't let them overpay!
        if amount > active_loan.amount:
            messages.error(request, f"REJECTED: You only owe KES {active_loan.amount}. Do not overpay.")
            return redirect('repay_loan')

        # 4. Simulate Payment Processing
        time.sleep(2)
        ref_code = f"PAY{random.randint(1000000, 9999999)}"
        
        # 5. Create the Receipt (Transaction)
        Transaction.objects.create(
            membership=membership,
            amount=amount,
            transaction_type='loan_repayment',
            reference=ref_code
        )
        
        # 6. THE CORE LOGIC: Reduce the Debt
        active_loan.amount -= amount
        
        # 7. Check if fully paid
        if active_loan.amount <= 0:
            active_loan.status = 'paid'
            active_loan.amount = 0 # Clean up just in case
            messages.success(request, "CONGRATULATIONS! Your loan is fully repaid.")
        else:
            messages.success(request, f"Payment Received. Remaining Balance: KES {active_loan.amount}")
            
        active_loan.save()
        return redirect('dashboard')

    return render(request, 'chama/repay_loan.html', {'loan': active_loan})