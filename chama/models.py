from django.db import models
from django.conf import settings
import random
import string

# --- 1. Helper Function ---
def generate_unique_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"{letters}-{numbers}"

# --- 2. The Chama Group Model ---
class ChamaGroup(models.Model):
    CHAMA_TYPES = (
        ('savings', 'Savings Group'),
        ('lending', 'Lending Group'),
        ('merry', 'Merry-Go-Round'),
    )
    
    name = models.CharField(max_length=100)
    chama_code = models.CharField(max_length=10, default=generate_unique_code, unique=True, editable=False)
    chama_type = models.CharField(max_length=20, choices=CHAMA_TYPES, default='savings')
    
    # NEW: The Rule (e.g., Everyone must contribute 1000)
    contribution_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # NEW: Track the Merry-Go-Round Pot
    pot_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Membership')

    def __str__(self):
        return f"{self.name} ({self.chama_code})"

# --- 3. The Membership Model ---
class Membership(models.Model):
    ROLES = (
        ('admin', 'Admin/Treasurer'),
        ('member', 'Member'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.ForeignKey(ChamaGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    savings_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # NEW: For Merry-Go-Round tracking
    has_eaten = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"

# --- 4. The Transaction Model (The Receipt) ---
class Transaction(models.Model):
    TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('loan_request', 'Loan Request'),
        ('loan_repayment', 'Loan Repayment'),
    )
    
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    reference = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

# --- 5. The Loan Model (The Borrowing Contract) ---
class Loan(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved (Disbursed)'),
        ('rejected', 'Rejected'),
        ('paid', 'Fully Paid'),
    )
    
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # We add a default interest rate of 10%
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    date_requested = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Loan {self.amount} - {self.membership.user.username}"