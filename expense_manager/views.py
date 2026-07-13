from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotFound 
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
from datetime import timedelta, datetime
from django.utils import timezone
from django.conf import settings

# Maximum allowed expense amount
MAX_EXPENSE_AMOUNT = Decimal('1000000')

def user_login(request):
    if request.user.is_authenticated:
        return redirect("home")  

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = None
        if email:
            user_obj = User.objects.filter(email=email).first() 
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

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
        email = request.POST.get("email", "").strip()

        errors = False

        if not email:
            messages.error(request, "Email is required!")
            errors = True
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            errors = True

        if not errors:
            import random
            otp = str(random.randint(100000, 999999))
            request.session['registration_email'] = email
            request.session['registration_otp'] = otp
            request.session['registration_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()
            request.session['email_verified'] = False

            try:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
                send_mail(
                    subject="TakaSave Registration OTP",
                    message=f"Your verification OTP code is: {otp}. It is valid for 5 minutes. Do not share this OTP with anyone.",
                    from_email=from_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, f"An OTP has been sent to {email}. Please verify.")
                return redirect("register_verify")
            except Exception as e:
                print(f"Error sending verification email: {e}")
                messages.error(request, "Failed to send email. Please check your SMTP settings or try again.")

    return render(request, "register.html")


def user_register_verify(request):
    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get('registration_email')
    if not email:
        messages.error(request, "Please start the registration process first.")
        return redirect("register")

    if request.method == "POST":
        user_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get('registration_otp')
        expiry = request.session.get('registration_otp_expiry', 0)

        if not user_otp:
            messages.error(request, "OTP is required!")
        elif timezone.now().timestamp() > expiry:
            messages.error(request, "OTP has expired! Please click resend.")
        elif user_otp != session_otp:
            messages.error(request, "Invalid OTP. Please try again.")
        else:
            request.session['email_verified'] = True
            messages.success(request, "Email verified successfully! Complete your account details.")
            return redirect("register_details")

    expiry_time = request.session.get('registration_otp_expiry', 0)
    remaining = int(expiry_time - timezone.now().timestamp())
    if remaining < 0:
        remaining = 0

    return render(request, "register_verify.html", {
        "email": email,
        "remaining_seconds": remaining
    })


def user_register_resend(request):
    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get('registration_email')
    if not email:
        messages.error(request, "No registration session found. Please enter your email.")
        return redirect("register")

    import random
    otp = str(random.randint(100000, 999999))
    request.session['registration_otp'] = otp
    request.session['registration_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()

    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
        send_mail(
            subject="TakaSave Registration OTP",
            message=f"Your verification OTP code is: {otp}. It is valid for 5 minutes. Do not share this OTP with anyone.",
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        messages.success(request, f"OTP has been resent to {email}.")
    except Exception as e:
        messages.error(request, "Failed to send email. Please check your SMTP settings.")

    return redirect("register_verify")


def user_register_details(request):
    if request.user.is_authenticated:
        return redirect("home")

    email = request.session.get('registration_email')
    verified = request.session.get('email_verified', False)

    if not email or not verified:
        messages.error(request, "Please verify your email address first.")
        return redirect("register")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        errors = False

        if not username:
            messages.error(request, "Username is required!")
            errors = True
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            errors = True

        if not password1:
            messages.error(request, "Password is required!")
            errors = True
        elif password1 != password2:
            messages.error(request, "Passwords do not match!")
            errors = True

        if not errors:
            try:
                User.objects.create_user(username=username, email=email, password=password1)
                # Clear session
                request.session.pop('registration_email', None)
                request.session.pop('registration_otp', None)
                request.session.pop('registration_otp_expiry', None)
                request.session.pop('email_verified', None)

                messages.success(request, "Account created successfully! Please login.")
                return redirect("login")
            except Exception as e:
                messages.error(request, f"Failed to create account: {str(e)}")

    return render(request, "register_details.html", {"email": email})




def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email=email).first()

        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            domain = get_current_site(request).domain
            scheme = 'https' if request.is_secure() else 'http'
            reset_link = f'{scheme}://{domain}/password-reset/confirm/{uid}/{token}/'

            message = render_to_string("password_reset_email.html", {"reset_link": reset_link, "user": user})

            try:
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
                send_mail(
                    subject="Password Reset",
                    message=message,
                    from_email=from_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, f"Password Reset Link has been sent to {email}")
                return redirect("password_reset_done")
            except Exception as e:
                print(f"Error sending password reset email: {e}")
                messages.error(request, "Failed to send password reset email. Please try again later or verify email settings.")
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

    # Ensure categories exist
    if not Category.objects.exists():
        for cat_name in ["Food", "Travel", "Rent", "Utilities", "Entertainment", "Others"]:
            Category.objects.get_or_create(name=cat_name)

    # Ensure default 'Cash' wallet exists
    wallets = Wallet.objects.filter(user=user)
    if not wallets.exists():
        Wallet.objects.create(user=user, name="Cash", balance=Decimal('0.00'))
        wallets = Wallet.objects.filter(user=user)

    total_expenses = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    month_expenses = Expense.objects.filter(user=user, date__gte=start_month).aggregate(total=Sum('amount'))['total'] or 0
    week_expenses = Expense.objects.filter(user=user, date__gte=start_week).aggregate(total=Sum('amount'))['total'] or 0

    category_data = Expense.objects.filter(user=user).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    # Wallet summary
    wallets = wallets.order_by('name')
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
    # Ensure default categories exist
    if not Category.objects.exists():
        for cat_name in ["Food", "Travel", "Rent", "Utilities", "Entertainment", "Others"]:
            Category.objects.get_or_create(name=cat_name)

    categories = Category.objects.all().order_by('name')
    
    # Check if user has wallets. If not, auto-create a default 'Cash' wallet.
    wallets = Wallet.objects.filter(user=request.user)
    if not wallets.exists():
        Wallet.objects.create(user=request.user, name="Cash", balance=Decimal('0.00'))
        wallets = Wallet.objects.filter(user=request.user)
        messages.info(request, "Default 'Cash' wallet has been automatically created for you.")

    today_date = timezone.now().date().strftime('%Y-%m-%d')

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        amount = request.POST.get("amount", "").strip()
        category_id = request.POST.get("category")
        wallet_id = request.POST.get("wallet")
        date_str = request.POST.get("date", "").strip()
        description = request.POST.get("description", "").strip()

        errors = False

        if not title:
            messages.error(request, "Title is required!")
            errors = True

        try:
            amount_dec = Decimal(amount)
            if amount_dec <= 0:
                messages.error(request, "Amount must be greater than zero.")
                errors = True
            elif amount_dec > MAX_EXPENSE_AMOUNT:
                messages.error(request, f"Amount exceeds the allowed limit of {MAX_EXPENSE_AMOUNT}.")
                errors = True
        except (ValueError, TypeError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid amount.")
            errors = True
            amount_dec = Decimal('0.00')

        category = None
        if not category_id:
            messages.error(request, "Category is required!")
            errors = True
        else:
            try:
                category = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                messages.error(request, "Selected category does not exist.")
                errors = True

        wallet = None
        if wallet_id:
            try:
                wallet = Wallet.objects.get(user=request.user, id=wallet_id)
            except (Wallet.DoesNotExist, ValueError):
                messages.error(request, "Selected wallet does not exist.")
                errors = True

        parsed_date = timezone.now().date()
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format. Use YYYY-MM-DD.")
                errors = True

        if wallet and not errors:
            if wallet.balance < amount_dec:
                messages.error(request, f"Insufficient balance in '{wallet.name}'. Cannot create expense!")
                errors = True

        if errors:
            dummy_expense = Expense(
                title=title,
                amount=amount_dec,
                category=category,
                wallet=wallet,
                date=parsed_date,
                description=description
            )
            return render(request, 'expense_form.html', {
                "expense": dummy_expense,
                "categories": categories,
                "wallets": wallets,
                "today_date": today_date,
            })

        try:
            with transaction.atomic():
                Expense.objects.create(
                    user=request.user,
                    title=title,
                    amount=amount_dec,
                    category=category,
                    wallet=wallet,
                    date=parsed_date,
                    description=description
                )
                if wallet:
                    wallet.balance -= amount_dec
                    wallet.save()
            messages.success(request, "Expense added successfully!")
            return redirect("expense_list")
        except Exception as e:
            messages.error(request, f"Failed to save expense: {str(e)}")
            dummy_expense = Expense(
                title=title,
                amount=amount_dec,
                category=category,
                wallet=wallet,
                date=parsed_date,
                description=description
            )
            return render(request, 'expense_form.html', {
                "expense": dummy_expense,
                "categories": categories,
                "wallets": wallets,
                "today_date": today_date,
            })

    return render(request, 'expense_form.html', {
        "categories": categories,
        "wallets": wallets,
        "today_date": today_date,
    })


@login_required(login_url='/login/')
def expense_update(request, expense_id):
    expense = get_object_or_404(Expense, user=request.user, id=expense_id)
    categories = Category.objects.all().order_by('name')
    wallets = Wallet.objects.filter(user=request.user)
    if not wallets.exists():
        Wallet.objects.create(user=request.user, name="Cash", balance=Decimal('0.00'))
        wallets = Wallet.objects.filter(user=request.user)

    if request.method == "POST":
        old_wallet = expense.wallet
        old_amount = expense.amount

        title = request.POST.get("title", "").strip()
        amount = request.POST.get("amount", "").strip()
        category_id = request.POST.get("category")
        wallet_id = request.POST.get("wallet")
        date_str = request.POST.get("date", "").strip()
        description = request.POST.get("description", "").strip()

        errors = False

        if not title:
            messages.error(request, "Title is required!")
            errors = True

        try:
            new_amount = Decimal(amount)
            if new_amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                errors = True
            elif new_amount > MAX_EXPENSE_AMOUNT:
                messages.error(request, f"Amount exceeds the allowed limit of {MAX_EXPENSE_AMOUNT}.")
                errors = True
        except (ValueError, TypeError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid amount.")
            errors = True
            new_amount = Decimal('0.00')

        category = None
        if not category_id:
            messages.error(request, "Category is required!")
            errors = True
        else:
            try:
                category = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError):
                messages.error(request, "Selected category does not exist.")
                errors = True

        new_wallet = None
        if wallet_id:
            try:
                new_wallet = Wallet.objects.get(user=request.user, id=wallet_id)
            except (Wallet.DoesNotExist, ValueError):
                messages.error(request, "Selected wallet does not exist.")
                errors = True

        parsed_date = expense.date
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format. Use YYYY-MM-DD.")
                errors = True

        if not errors:
            # Validate wallet balances before updating expense
            if new_wallet:
                if old_wallet == new_wallet:
                    prospective_balance = new_wallet.balance + old_amount - new_amount
                    if prospective_balance < 0:
                        messages.error(request, f"Insufficient balance in '{new_wallet.name}' for this update.")
                        errors = True
                else:
                    if new_wallet.balance < new_amount:
                        messages.error(request, f"Insufficient balance in '{new_wallet.name}' for this update.")
                        errors = True

        if errors:
            # Preserving user inputs on the existing object
            expense.title = title
            expense.amount = new_amount
            expense.category = category
            expense.wallet = new_wallet
            expense.date = parsed_date
            expense.description = description
            return render(request, 'expense_form.html', {
                "expense": expense,
                "categories": categories,
                "wallets": wallets,
            })

        try:
            with transaction.atomic():
                expense.title = title
                expense.amount = new_amount
                expense.category = category
                expense.wallet = new_wallet
                expense.date = parsed_date
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
        except Exception as e:
            messages.error(request, f"Failed to update expense: {str(e)}")
            return render(request, 'expense_form.html', {
                "expense": expense,
                "categories": categories,
                "wallets": wallets,
            })

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
        try:
            with transaction.atomic():
                expense.delete()
                if wallet:
                    wallet.balance += amount
                    wallet.save()
            messages.success(request, "Expense Deleted Successfully!")
        except Exception as e:
            messages.error(request, f"Failed to delete expense: {str(e)}")
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

# =========================
# Profile Edit Views
# =========================

@login_required(login_url='/login/')
def profile_edit(request):
    """Render profile edit form. Handles email change with OTP verification."""
    user = request.user
    if request.method == "POST":
        new_username = request.POST.get('username', '').strip()
        new_email = request.POST.get('email', '').strip()
        new_password1 = request.POST.get('password1', '')
        new_password2 = request.POST.get('password2', '')
        errors = False

        # Username validation
        if not new_username:
            messages.error(request, "Username is required!")
            errors = True
        elif new_username != user.username and User.objects.filter(username=new_username).exists():
            messages.error(request, "Username already taken!")
            errors = True

        # Email validation (optional but if provided must be unique)
        if not new_email:
            messages.error(request, "Email is required!")
            errors = True
        elif new_email != user.email and User.objects.filter(email=new_email).exists():
            messages.error(request, "Email already registered by another user!")
            errors = True

        # Password validation (optional)
        if new_password1 or new_password2:
            if new_password1 != new_password2:
                messages.error(request, "Passwords do not match!")
                errors = True
            elif len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                errors = True

        if errors:
            return render(request, 'profile_edit.html', {
                'user': user,
                'form_username': new_username,
                'form_email': new_email
            })

        # Collect pending changes (username, email, password)
        pending_changes = {
            'username': new_username,
            'email': new_email,
            'password': new_password1,
        }
        # Determine what fields are actually changing
        email_changed = new_email and new_email != user.email
        username_changed = new_username != user.username
        password_changed = new_password1 != ''

        # Validate that at least one field is being changed
        if not any([email_changed, username_changed, password_changed]):
            messages.error(request, "No changes detected.")
            return render(request, 'profile_edit.html', {
                'user': user,
                'form_username': new_username,
                'form_email': new_email
            })

        # If only username/password are changing (no email change), apply directly without OTP
        if not email_changed:
            try:
                if username_changed:
                    user.username = new_username
                if password_changed:
                    user.set_password(new_password1)
                user.save()
                if password_changed:
                    # Preserve login after password change
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                messages.success(request, "Profile updated successfully.")
                return redirect('account_details')
            except Exception as e:
                messages.error(request, f"Failed to update profile: {str(e)}")
                return render(request, 'profile_edit.html', {
                    'user': user,
                    'form_username': new_username,
                    'form_email': new_email
                })

        # Otherwise, require OTP (email change or both email and other fields)
        # Store pending changes in session for OTP verification
        request.session['profile_edit_pending'] = pending_changes
        # Generate OTP
        import random
        otp = str(random.randint(100000, 999999))
        request.session['profile_edit_otp'] = otp
        request.session['profile_edit_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()
        
        # Send OTP email to the new email
        target_email = new_email
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
            send_mail(
                subject="TakaSave Profile Change OTP",
                message=f"Your OTP for confirming profile changes is {otp}. It is valid for 5 minutes.",
                from_email=from_email,
                recipient_list=[target_email],
                fail_silently=False,
            )
            messages.success(request, f"OTP sent to {target_email}. Verify to apply changes.")
            return redirect('profile_edit_verify')
        except Exception as e:
            messages.error(request, f"Failed to send OTP email: {str(e)}")
            return render(request, 'profile_edit.html', {
                'user': user,
                'form_username': new_username,
                'form_email': new_email
            })
    # GET request – prefill form
    return render(request, 'profile_edit.html', {
        'user': user,
        'form_username': user.username,
        'form_email': user.email
    })

@login_required(login_url='/login/')
def profile_edit_verify(request):
    """Verify OTP for email change and apply pending profile updates."""
    pending = request.session.get('profile_edit_pending')
    if not pending:
        messages.error(request, "No pending profile changes.")
        return redirect('profile_edit')
    if request.method == "POST":
        user_otp = request.POST.get('otp', '').strip()
        session_otp = request.session.get('profile_edit_otp')
        expiry = request.session.get('profile_edit_otp_expiry', 0)
        if not user_otp:
            messages.error(request, "OTP is required!")
        elif timezone.now().timestamp() > expiry:
            messages.error(request, "OTP expired! Please resend.")
        elif user_otp != session_otp:
            messages.error(request, "Invalid OTP.")
        else:
            # OTP valid – apply changes
            user = request.user
            new_username = pending.get('username')
            new_email = pending.get('email')
            new_password = pending.get('password')
            if new_username and new_username != user.username:
                user.username = new_username
            if new_email and new_email != user.email:
                user.email = new_email
            if new_password:
                user.set_password(new_password)
                # Preserve login after password change
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
            user.save()
            # Cleanup session
            for key in ['profile_edit_pending', 'profile_edit_otp', 'profile_edit_otp_expiry']:
                request.session.pop(key, None)
            messages.success(request, "Profile updated successfully.")
            return redirect('account_details')
    return render(request, 'profile_edit_verify.html')

@login_required(login_url='/login/')
def profile_edit_resend(request):
    """Resend OTP for email change."""
    pending = request.session.get('profile_edit_pending')
    if not pending:
        messages.error(request, "No pending profile changes.")
        return redirect('profile_edit')
    new_email = pending.get('email')
    if not new_email:
        messages.error(request, "Email not changed.")
        return redirect('profile_edit')
    import random
    otp = str(random.randint(100000, 999999))
    request.session['profile_edit_otp'] = otp
    request.session['profile_edit_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
        send_mail(
            subject="TakaSave Email Change OTP (Resend)",
            message=f"Your OTP for email change is {otp}. It is valid for 5 minutes.",
            from_email=from_email,
            recipient_list=[new_email],
            fail_silently=False,
        )
        messages.success(request, f"OTP resent to {new_email}.")
    except Exception as e:
        messages.error(request, "Failed to send OTP email.")
    return redirect('profile_edit_verify')

@login_required(login_url='/login/')

def account_delete(request):
    """Handle account deletion with OTP verification."""
    user = request.user
    if request.method == "POST":
        user_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get('delete_account_otp')
        expiry = request.session.get('delete_account_otp_expiry', 0)
        if not user_otp:
            messages.error(request, "OTP is required!")
        elif timezone.now().timestamp() > expiry:
            messages.error(request, "OTP has expired! Please click resend.")
        elif user_otp != session_otp:
            messages.error(request, "Invalid OTP. Please try again.")
        else:
            # OTP is valid, proceed with deletion
            request.session.pop('delete_account_otp', None)
            request.session.pop('delete_account_otp_expiry', None)
            user.delete()
            messages.success(request, "Your account has been deleted successfully.")
            return redirect('login')
    else:
        # GET request - generate new OTP
        import random
        otp = str(random.randint(100000, 999999))
        request.session['delete_account_otp'] = otp
        request.session['delete_account_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
            send_mail(
                subject="TakaSave Account Deletion OTP",
                message=f"Your verification OTP code for account deletion is: {otp}. It is valid for 5 minutes. Do not share this OTP with anyone.",
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.info(request, f"A verification OTP has been sent to {user.email}.")
        except Exception as e:
            print(f"Error sending deletion OTP email: {e}")
            messages.error(request, "Failed to send verification email. Please check your SMTP settings or try again.")
    expiry_time = request.session.get('delete_account_otp_expiry', 0)
    remaining = int(expiry_time - timezone.now().timestamp())
    if remaining < 0:
        remaining = 0
    return render(request, 'account_confirm_delete.html', {
        'remaining_seconds': remaining,
        'email': user.email
    })


@login_required(login_url='/login/')
def account_delete_resend(request):
    user = request.user
    import random
    otp = str(random.randint(100000, 999999))
    request.session['delete_account_otp'] = otp
    request.session['delete_account_otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()

    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'raihan.invite@gmail.com')
        send_mail(
            subject="TakaSave Account Deletion OTP",
            message=f"Your verification OTP code for account deletion is: {otp}. It is valid for 5 minutes. Do not share this OTP with anyone.",
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
            )
        messages.success(request, f"OTP has been resent to {user.email}.")
    except Exception as e:
        messages.error(request, "Failed to send verification email. Please check your SMTP settings.")

    return redirect('account_delete')

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
        balance = request.POST.get("balance", "0.00").strip()
        if not name:
            messages.error(request, "Wallet name is required!")
            return redirect('wallet_list')
        
        try:
            balance_dec = Decimal(balance)
            if balance_dec < 0:
                messages.error(request, "Initial balance cannot be negative!")
                return redirect('wallet_list')
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
        balance_str = request.POST.get("balance", "").strip()
        
        if not name:
            messages.error(request, "Wallet name is required!")
            return redirect('wallet_list')
            
        if Wallet.objects.filter(user=request.user, name__iexact=name).exclude(id=wallet_id).exists():
            messages.error(request, f"Another wallet named '{name}' already exists!")
            return redirect('wallet_list')
            
        wallet.name = name
        if balance_str != "":
            try:
                balance_dec = Decimal(balance_str)
                if balance_dec < 0:
                    messages.error(request, "Wallet balance cannot be negative!")
                    return redirect('wallet_list')
                wallet.balance = balance_dec
            except (ValueError, TypeError, decimal.InvalidOperation):
                messages.error(request, "Invalid balance amount entered!")
                return redirect('wallet_list')
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
        amount = request.POST.get("amount", "").strip()
        
        try:
            wallet = Wallet.objects.get(user=request.user, id=wallet_id)
        except (Wallet.DoesNotExist, ValueError):
            messages.error(request, "Invalid wallet selected.")
            return redirect('wallet_list')
        
        try:
            amount_dec = Decimal(amount)
            if amount_dec <= 0:
                raise ValueError
        except (ValueError, TypeError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid positive amount!")
            return redirect('wallet_list')
            
        try:
            with transaction.atomic():
                wallet.balance += amount_dec
                wallet.save()
            messages.success(request, f"Deposited ৳ {amount_dec:.2f} into '{wallet.name}'!")
        except Exception as e:
            messages.error(request, f"Failed to deposit amount: {str(e)}")
    return redirect('wallet_list')

@login_required(login_url='/login/')
def wallet_transfer(request):
    if request.method == "POST":
        from_wallet_id = request.POST.get("from_wallet")
        to_wallet_id = request.POST.get("to_wallet")
        amount = request.POST.get("amount", "").strip()
        
        if from_wallet_id == to_wallet_id:
            messages.error(request, "Cannot transfer to the same wallet!")
            return redirect('wallet_list')
            
        try:
            from_wallet = Wallet.objects.get(user=request.user, id=from_wallet_id)
            to_wallet = Wallet.objects.get(user=request.user, id=to_wallet_id)
        except (Wallet.DoesNotExist, ValueError):
            messages.error(request, "Invalid wallet selected.")
            return redirect('wallet_list')
        
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
            
        try:
            with transaction.atomic():
                from_wallet.balance -= amount_dec
                to_wallet.balance += amount_dec
                from_wallet.save()
                to_wallet.save()
            messages.success(request, f"Transferred ৳ {amount_dec:.2f} from '{from_wallet.name}' to '{to_wallet.name}'!")
        except Exception as e:
            messages.error(request, f"Failed to transfer amount: {str(e)}")
    return redirect('wallet_list')


def handler400(request, exception=None):
    return render(request, '400.html', status=400)

def handler403(request, exception=None):
    return render(request, '403.html', status=403)

def handler404(request, exception=None):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)