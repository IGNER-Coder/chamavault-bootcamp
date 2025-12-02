from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Add our new fields to the admin display
    model = CustomUser
    
    # Control what shows up in the list view
    list_display = ['username', 'email', 'phone_number', 'national_id', 'is_staff']
    
    # Control what allows us to edit in the "User Info" page
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'national_id')}),
    )
    
    # Control what allows us to edit in the "Add User" page
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone_number', 'national_id')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)