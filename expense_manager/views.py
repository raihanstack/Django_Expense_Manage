from django.shortcuts import render, get_object_or_404, redirect 
from .models import Expense, Category, Wallet
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
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
import decimal
from datetime import timedelta
from django.utils import timezone



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
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            domain = get_current_site(request).domain
            reset_link = f'https://{domain}/password-reset/confirm/{uid}/{token}/'

            message = render_to_string("password_reset_email.html", {"reset_link": reset_link})

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
    user = request.user
    today = timezone.now().date()
    start_week = today - timedelta(days=7)
    start_month = today.replace(day=1)

    total_expenses = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    month_expenses = Expense.objects.filter(user=user, date__gte=start_month).aggregate(total=Sum('amount'))['total'] or 0
    week_expenses = Expense.objects.filter(user=user, date__gte=start_week).aggregate(total=Sum('amount'))['total'] or 0

    category_data = Expense.objects.filter(user=user).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    # Wallet summary
    wallets = Wallet.objects.filter(user=user).order_by('name')
    total_balance = wallets.aggregate(total=Sum('balance'))['total'] or 0

    context = {
        'total_expenses': total_expenses,
        'month_expenses': month_expenses,
        'week_expenses': week_expenses,
        'category_data': category_data,
        'wallets': wallets,
        'total_balance': total_balance,
    }
    return render(request, 'home.html', context)

@login_required(login_url='/login/')
def expense_list(request):
    result = Expense.objects.filter(user=request.user).select_related('category', 'wallet').order_by('-date')
    total_expenses = result.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'expense_list.html', {
        "result": result,
        "total_expenses": total_expenses
    })

@login_required(login_url='/login/')
def expense_create(request):
    categories = Category.objects.all()
    # Check if user has wallets. If not, auto-create a default 'Cash' wallet.
    wallets = Wallet.objects.filter(user=request.user)
    if not wallets.exists():
        Wallet.objects.create(user=request.user, name="Cash", balance=0.00)
        wallets = Wallet.objects.filter(user=request.user)
        messages.info(request, "Default 'Cash' wallet has been automatically created for you.")

    if request.method == "POST":
        title = request.POST.get("title")
        amount = request.POST.get("amount")
        category_id = request.POST.get("category")
        wallet_id = request.POST.get("wallet")
        date = request.POST.get("date")
        description = request.POST.get("description")

        category = get_object_or_404(Category, id=category_id)
        wallet = get_object_or_404(Wallet, user=request.user, id=wallet_id) if wallet_id else None
        
        try:
            amount_dec = Decimal(amount)
        except (ValueError, TypeError, decimal.InvalidOperation):
            amount_dec = Decimal('0.00')

        with transaction.atomic():
            Expense.objects.create(
                user=request.user,
                title=title,
                amount=amount_dec,
                category=category,
                wallet=wallet,
                date=date,
                description=description
            )
            if wallet:
                wallet.balance -= amount_dec
                wallet.save()

        messages.success(request, "Expense added successfully!")
        return redirect("expense_list")

    return render(request, 'expense_form.html', {
        "categories": categories,
        "wallets": wallets
    })


@login_required(login_url='/login/')
def expense_update(request, expense_id):
    expense = get_object_or_404(Expense, user=request.user, id=expense_id)
    categories = Category.objects.all()
    wallets = Wallet.objects.filter(user=request.user)
    if not wallets.exists():
        Wallet.objects.create(user=request.user, name="Cash", balance=0.00)
        wallets = Wallet.objects.filter(user=request.user)

    if request.method == "POST":
        old_wallet = expense.wallet
        old_amount = expense.amount

        title = request.POST.get("title")
        amount = request.POST.get("amount")
        category_id = request.POST.get("category")
        wallet_id = request.POST.get("wallet")
        date = request.POST.get("date")
        description = request.POST.get("description")

        category = get_object_or_404(Category, id=category_id)
        new_wallet = get_object_or_404(Wallet, user=request.user, id=wallet_id) if wallet_id else None

        try:
            new_amount = Decimal(amount)
        except (ValueError, TypeError, decimal.InvalidOperation):
            new_amount = Decimal('0.00')

        with transaction.atomic():
            expense.title = title
            expense.amount = new_amount
            expense.category = category
            expense.wallet = new_wallet
            expense.date = date
            expense.description = description
            expense.save()

            # Adjust wallet balances
            if old_wallet == new_wallet:
                if old_wallet:
                    old_wallet.balance += old_amount - new_amount
                    old_wallet.save()
            else:
                if old_wallet:
                    old_wallet.balance += old_amount
                    old_wallet.save()
                if new_wallet:
                    new_wallet.balance -= new_amount
                    new_wallet.save()

        messages.success(request, "Expense updated successfully!")
        return redirect("expense_list")

    return render(request, 'expense_form.html', {
        "expense": expense,
        "categories": categories,
        "wallets": wallets
    })

@login_required(login_url='/login/')
def expense_delete(request, expense_id):
    expense = get_object_or_404(Expense, user=request.user, id=expense_id)

    if request.method == "POST":
        wallet = expense.wallet
        amount = expense.amount
        with transaction.atomic():
            expense.delete()
            if wallet:
                wallet.balance += amount
                wallet.save()
        messages.success(request, "Expense Deleted Successfully!")
        return redirect('expense_list')

    return render(request, 'expense_confirm_delete.html', {
        "expense": expense
    })

@login_required(login_url='/login/')
def account_details(request):
    user = request.user
    total_expenses = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'account_details.html', {
        'user': user,
        'total_expenses': total_expenses
    })

@login_required(login_url='/login/')
def account_delete(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('login')
        
    return render(request, 'account_confirm_delete.html')

# =========================
# Wallet Management Views
# =========================

@login_required(login_url='/login/')
def wallet_list(request):
    user = request.user
    wallets = Wallet.objects.filter(user=user).order_by('name')
    total_balance = wallets.aggregate(total=Sum('balance'))['total'] or 0
    return render(request, 'wallet_list.html', {
        'wallets': wallets,
        'total_balance': total_balance,
    })

@login_required(login_url='/login/')
def wallet_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        balance = request.POST.get("balance", "0.00")
        if not name:
            messages.error(request, "Wallet name is required!")
            return redirect('wallet_list')
        
        try:
            balance_dec = Decimal(balance)
        except (ValueError, TypeError, decimal.InvalidOperation):
            balance_dec = Decimal('0.00')

        if Wallet.objects.filter(user=request.user, name__iexact=name).exists():
            messages.error(request, f"Wallet '{name}' already exists!")
        else:
            Wallet.objects.create(user=request.user, name=name, balance=balance_dec)
            messages.success(request, f"Wallet '{name}' created successfully!")
            
    return redirect('wallet_list')

@login_required(login_url='/login/')
def wallet_update(request, wallet_id):
    wallet = get_object_or_404(Wallet, user=request.user, id=wallet_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        balance_str = request.POST.get("balance", "")
        
        if not name:
            messages.error(request, "Wallet name is required!")
            return redirect('wallet_list')
            
        if Wallet.objects.filter(user=request.user, name__iexact=name).exclude(id=wallet_id).exists():
            messages.error(request, f"Another wallet named '{name}' already exists!")
            return redirect('wallet_list')
            
        wallet.name = name
        if balance_str != "":
            try:
                wallet.balance = Decimal(balance_str)
            except (ValueError, TypeError, decimal.InvalidOperation):
                pass
        wallet.save()
        messages.success(request, f"Wallet '{name}' updated successfully!")
    return redirect('wallet_list')

@login_required(login_url='/login/')
def wallet_delete(request, wallet_id):
    wallet = get_object_or_404(Wallet, user=request.user, id=wallet_id)
    if request.method == "POST":
        wallet_name = wallet.name
        wallet.delete()
        messages.success(request, f"Wallet '{wallet_name}' deleted successfully!")
    return redirect('wallet_list')

@login_required(login_url='/login/')
def wallet_deposit(request):
    if request.method == "POST":
        wallet_id = request.POST.get("wallet")
        amount = request.POST.get("amount")
        wallet = get_object_or_404(Wallet, user=request.user, id=wallet_id)
        
        try:
            amount_dec = Decimal(amount)
            if amount_dec <= 0:
                raise ValueError
        except (ValueError, TypeError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid positive amount!")
            return redirect('wallet_list')
            
        with transaction.atomic():
            wallet.balance += amount_dec
            wallet.save()
            
        messages.success(request, f"Deposited ৳ {amount_dec:.2f} into '{wallet.name}'!")
    return redirect('wallet_list')

@login_required(login_url='/login/')
def wallet_transfer(request):
    if request.method == "POST":
        from_wallet_id = request.POST.get("from_wallet")
        to_wallet_id = request.POST.get("to_wallet")
        amount = request.POST.get("amount")
        
        if from_wallet_id == to_wallet_id:
            messages.error(request, "Cannot transfer to the same wallet!")
            return redirect('wallet_list')
            
        from_wallet = get_object_or_404(Wallet, user=request.user, id=from_wallet_id)
        to_wallet = get_object_or_404(Wallet, user=request.user, id=to_wallet_id)
        
        try:
            amount_dec = Decimal(amount)
            if amount_dec <= 0:
                raise ValueError
        except (ValueError, TypeError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid positive amount!")
            return redirect('wallet_list')
            
        if from_wallet.balance < amount_dec:
            messages.error(request, f"Insufficient balance in '{from_wallet.name}'!")
            return redirect('wallet_list')
            
        with transaction.atomic():
            from_wallet.balance -= amount_dec
            to_wallet.balance += amount_dec
            from_wallet.save()
            to_wallet.save()
            
        messages.success(request, f"Transferred ৳ {amount_dec:.2f} from '{from_wallet.name}' to '{to_wallet.name}'!")
    return redirect('wallet_list')