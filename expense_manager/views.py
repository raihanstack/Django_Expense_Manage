from django.shortcuts import render, get_object_or_404, redirect 
from .models import Expense 
from django.utils import timezone 
from datetime import timedelta 
from django.contrib import messages 
from django.contrib.auth.models import User 
from django.contrib.auth import authenticate, login, logout 
from django.contrib.auth.decorators import login_required 
from django.contrib.auth.tokens import default_token_generator 
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode 
from django.utils.encoding import force_bytes 
from django.contrib.sites.shortcuts import get_current_site 
from django.template.loader import render_to_string 
from django.core.mail import send_mail

def user_login(request):
    if request.user.is_authenticated:
        return redirect("home")  

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = None
        if email:
            try:
                user_obj = User.objects.get(email=email) 
            
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            messages.success(request, "Login Successful!")
            return redirect("home")
        else:
            messages.error(request, "Invalid Email or Password!")

    return render(request, "login.html")

@login_required(login_url='/login/')
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")

def user_register(request):
    
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
        else:
            User.objects.create_user(username=username, email=email, password=password1)
            messages.success(request, "Account created successfully!")
            return redirect("login")

    return render(request, "register.html")


def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if user:
            # token & uid generate
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            domain = get_current_site(request).domain
            reset_link = f'http://{domain}/password-reset/confirm/{uid}/{token}/'

            # email content
            message = render_to_string("password_reset_email.html", {"reset_link": reset_link})

            # send mail
            send_mail(
                subject="Password Reset",
                message=message,
                from_email='raihan.invite@gmail.com',
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, f"Password Reset Link has been sent to {email}")
            return redirect("password_reset_done")
        else:
            messages.error(request, "User not found!")

    return render(request, 'password_reset.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid Reset Link.")
        return redirect("password_reset_request")
    
    if not default_token_generator.check_token(user, token):
        messages.error(request, "Invalid or expired reset link.")
        return redirect("password_reset_request")
    
    if request.method == "POST":
        new_password = request.POST.get("new_password1")
        confirm_password = request.POST.get("new_password2")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
        else:
            user.set_password(new_password)
            user.save() 
            messages.success(request, "Password Reset Successfully")
            return redirect("password_reset_complete")

    return render(request, 'password_reset_confirm.html')


def password_reset_done(request):
    return render(request, 'password_reset_done.html')


def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')


@login_required(login_url='/login/')
def home(request):
    recent_expenses = Expense.objects.all().order_by('-date')[:5]

    total_expenses = sum(exp.amount for exp in Expense.objects.all())

    today = timezone.now().date()
    month_expenses = sum(exp.amount for exp in Expense.objects.filter(date__month=today.month))
    week_expenses = sum(exp.amount for exp in Expense.objects.filter(date__gte=today - timedelta(days=7)))

    context = {
        'recent_expenses': recent_expenses,
        'total_expenses': total_expenses,
        'month_expenses': month_expenses,
        'week_expenses': week_expenses,
    }
    return render(request, 'home.html', context)

@login_required(login_url='/login/')
def expense_list(request):
    return render(request, 'expense_list.html')

@login_required(login_url='/login/')
def expense_create(request):
    return render(request, 'expense_form.html')

@login_required(login_url='/login/')
def expense_update(request):
    return render(request, 'expense_form.html')

@login_required(login_url='/login/')
def expense_delete(request, id):
    expense = get_object_or_404(Expense, id=id)
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list')
    return render(request, 'expense_confirm_delete.html', {'expense': expense})