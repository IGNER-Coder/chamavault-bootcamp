from django.contrib import admin
from .models import ChamaGroup, Membership, Transaction, Loan

# 1. Transactions (The Receipts)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('membership', 'transaction_type', 'amount', 'status', 'reference', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('reference', 'membership__user__username')
    readonly_fields = ('created_at',)

# 2. Loans (The Debts)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('membership', 'amount', 'status', 'date_requested')
    list_filter = ('status',)
    search_fields = ('membership__user__username',)

# 3. Chama Groups & Memberships
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1

class ChamaGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'chama_code', 'chama_type', 'created_at')
    inlines = [MembershipInline]

# Register everything
admin.site.register(ChamaGroup, ChamaGroupAdmin)
admin.site.register(Membership)
admin.site.register(Transaction, TransactionAdmin) # <--- This was missing!
admin.site.register(Loan, LoanAdmin)               # <--- This was missing!