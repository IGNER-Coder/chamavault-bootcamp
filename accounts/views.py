from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import CustomUser

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        nid = request.POST.get('national_id')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        # 1. Basic Validation
        if password != confirm:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('register')

        # --- NEW VALIDATION BLOCK ---
        
        # 1. Validate National ID (Must be numbers, 7-8 digits)
        if not nid.isdigit():
            messages.error(request, "National ID must contain numbers only.")
            return redirect('register')
        if len(nid) < 7 or len(nid) > 8:
            messages.error(request, "Invalid National ID length (should be 7-8 digits).")
            return redirect('register')

        # 2. Validate Phone (Must start with 07 or 254)
        if not (phone.startswith('07') or phone.startswith('01') or phone.startswith('254')):
            messages.error(request, "Invalid Phone Number format.")
            return redirect('register')
        
        # 3. Check for duplicates manually (Double safety)
        if CustomUser.objects.filter(national_id=nid).exists():
            messages.error(request, "This National ID is already registered.")
            return redirect('register')
            
        # ... continue to create user ...

        # 2. Create the User
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                phone_number=phone,
                national_id=nid
            )
            
            # 3. Log them in immediately
            login(request, user)
            messages.success(request, f"Welcome to ChamaVault, {username}!")
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('register')

    return render(request, 'accounts/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have logged out.")
    return redirect('login')