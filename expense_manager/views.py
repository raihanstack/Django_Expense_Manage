from django.shortcuts import render, get_object_or_404, redirect
from .models import Expense
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

def user_login(request):
    # যদি user আগে থেকেই logged-in থাকে
    if request.user.is_authenticated:
        return redirect("home")  # already logged-in হলে home page এ redirect

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        # Email support
        username = username_or_email
        if "@" in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, "Login Successful!")
            return redirect("home")
        else:
            messages.error(request, "Invalid Username or Password!")

    return render(request, "login.html")



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
    return render(request, 'password_reset.html')

def password_reset_confirm(request):
    return render(request, 'password_reset_confirm.html')

def password_reset_done(request):
    return render(request, 'password_reset_done.html')

def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')



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


def expense_list(request):
    return render(request, 'expense_list.html')

def expense_create(request):
    return render(request, 'expense_form.html')

def expense_update(request):
    return render(request, 'expense_form.html')

def expense_delete(request, id):
    expense = get_object_or_404(Expense, id=id)
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list')
    return render(request, 'expense_confirm_delete.html', {'expense': expense})