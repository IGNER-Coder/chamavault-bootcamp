from django.contrib import admin
from .models import ChamaGroup, Membership

# This allows us to see Members INSIDE the Chama Group page
class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1

class ChamaGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'chama_code', 'chama_type', 'created_at')
    inlines = [MembershipInline]

# Register the models so they appear in the Admin Panel
admin.site.register(ChamaGroup, ChamaGroupAdmin)
admin.site.register(Membership)