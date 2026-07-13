from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from expense_manager.models import Category, Wallet, Expense
from django.utils import timezone

class ExpenseManagerTests(TestCase):
    def setUp(self):
        # Create standard user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        
        # Ensure categories exist
        self.category = Category.objects.create(name="Food")
        
        # Create wallet with initial balance
        self.wallet = Wallet.objects.create(user=self.user, name="Cash", balance=Decimal("100.00"))

    def test_category_string_representation(self):
        self.assertEqual(str(self.category), "Food")

    def test_wallet_string_representation(self):
        self.assertEqual(str(self.wallet), "Cash (৳ 100.00)")

    def test_expense_creation_with_sufficient_balance(self):
        # Post a valid expense within balance limits
        response = self.client.post(reverse('expense_create'), {
            'title': 'Lunch',
            'amount': '45.50',
            'category': self.category.id,
            'wallet': self.wallet.id,
            'date': timezone.now().date().strftime('%Y-%m-%d'),
            'description': 'Tasty food'
        })
        
        # Check redirection after success
        self.assertRedirects(response, reverse('expense_list'))
        
        # Verify expense was created
        expense = Expense.objects.filter(user=self.user, title='Lunch').first()
        self.assertIsNotNone(expense)
        self.assertEqual(expense.amount, Decimal('45.50'))
        
        # Verify wallet balance was updated
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('54.50'))

    def test_expense_creation_blocked_with_insufficient_balance(self):
        # Post an expense that exceeds the wallet balance
        response = self.client.post(reverse('expense_create'), {
            'title': 'Expensive Dinner',
            'amount': '150.00',
            'category': self.category.id,
            'wallet': self.wallet.id,
            'date': timezone.now().date().strftime('%Y-%m-%d'),
            'description': 'Over limit'
        })
        
        # Check that we stay on the form page (not redirected)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'expense_form.html')
        
        # Verify no expense was created in database
        expense = Expense.objects.filter(user=self.user, title='Expensive Dinner').first()
        self.assertIsNone(expense)
        
        # Verify wallet balance remained unchanged
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100.00'))

    def test_expense_form_preserves_user_inputs_on_error(self):
        response = self.client.post(reverse('expense_create'), {
            'title': 'Keep Me',
            'amount': '150.00', # will fail due to insufficient balance
            'category': self.category.id,
            'wallet': self.wallet.id,
            'date': timezone.now().date().strftime('%Y-%m-%d'),
            'description': 'Retain this note'
        })
        
        self.assertEqual(response.status_code, 200)
        # Check that dummy expense values are passed back to preserve user inputs
        self.assertEqual(response.context['expense'].title, 'Keep Me')
        self.assertEqual(response.context['expense'].description, 'Retain this note')

    def test_wallet_transfer_insufficient_balance(self):
        target_wallet = Wallet.objects.create(user=self.user, name="Savings", balance=Decimal("10.00"))
        
        response = self.client.post(reverse('wallet_transfer'), {
            'from_wallet': self.wallet.id,
            'to_wallet': target_wallet.id,
            'amount': '150.00' # more than 100.00
        })
        
        self.assertRedirects(response, reverse('wallet_list'))
        
        # Verify balances are unchanged
        self.wallet.refresh_from_db()
        target_wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100.00'))
        self.assertEqual(target_wallet.balance, Decimal('10.00'))


class RegistrationOTPFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_step1_email_sent(self):
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com'
        })
        self.assertRedirects(response, reverse('register_verify'))
        
        session = self.client.session
        self.assertEqual(session.get('registration_email'), 'newuser@example.com')
        self.assertIsNotNone(session.get('registration_otp'))
        self.assertEqual(session.get('email_verified'), False)

    def test_registration_step1_email_exists(self):
        User.objects.create_user(username="existing", email="test@example.com", password="password")
        response = self.client.post(reverse('register'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        
        session = self.client.session
        self.assertIsNone(session.get('registration_email'))

    def test_registration_step2_verify_otp_success(self):
        session = self.client.session
        session['registration_email'] = 'newuser@example.com'
        session['registration_otp'] = '123456'
        session['registration_otp_expiry'] = timezone.now().timestamp() + 300
        session['email_verified'] = False
        session.save()

        response = self.client.post(reverse('register_verify'), {
            'otp': '123456'
        })
        self.assertRedirects(response, reverse('register_details'))
        
        session = self.client.session
        self.assertEqual(session.get('email_verified'), True)

    def test_registration_step2_verify_otp_failure(self):
        session = self.client.session
        session['registration_email'] = 'newuser@example.com'
        session['registration_otp'] = '123456'
        session['registration_otp_expiry'] = timezone.now().timestamp() + 300
        session['email_verified'] = False
        session.save()

        response = self.client.post(reverse('register_verify'), {
            'otp': '000000'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register_verify.html')
        
        session = self.client.session
        self.assertEqual(session.get('email_verified'), False)

    def test_registration_step3_details_success(self):
        session = self.client.session
        session['registration_email'] = 'newuser@example.com'
        session['registration_otp'] = '123456'
        session['registration_otp_expiry'] = timezone.now().timestamp() + 300
        session['email_verified'] = True
        session.save()

        response = self.client.post(reverse('register_details'), {
            'username': 'newverifieduser',
            'password1': 'securepass123',
            'password2': 'securepass123'
        })
        self.assertRedirects(response, reverse('login'))
        
        # Verify user was created with correct credentials
        user = User.objects.filter(username='newverifieduser', email='newuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('securepass123'))
        
        # Verify session is cleaned up
        session = self.client.session
        self.assertIsNone(session.get('registration_email'))
        self.assertIsNone(session.get('registration_otp'))
        self.assertIsNone(session.get('email_verified'))

    def test_registration_step3_details_unverified(self):
        response = self.client.get(reverse('register_details'))
        self.assertRedirects(response, reverse('register'))


class AccountDeletionOTPFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="todelete", email="delete@example.com", password="securepass123")
        self.client = Client()
        self.client.login(username="todelete", password="securepass123")

    def test_account_delete_get_sends_otp(self):
        response = self.client.get(reverse('account_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_confirm_delete.html')

        session = self.client.session
        self.assertIsNotNone(session.get('delete_account_otp'))
        self.assertIsNotNone(session.get('delete_account_otp_expiry'))
        self.assertEqual(response.context['email'], 'delete@example.com')

    def test_account_delete_post_success(self):
        session = self.client.session
        session['delete_account_otp'] = '654321'
        session['delete_account_otp_expiry'] = timezone.now().timestamp() + 300
        session.save()

        response = self.client.post(reverse('account_delete'), {
            'otp': '654321'
        })
        self.assertRedirects(response, reverse('login'))

        # Verify user no longer exists
        self.assertFalse(User.objects.filter(username="todelete").exists())

        # Verify session is cleared
        session = self.client.session
        self.assertIsNone(session.get('delete_account_otp'))

    def test_account_delete_post_incorrect_otp(self):
        session = self.client.session
        session['delete_account_otp'] = '654321'
        session['delete_account_otp_expiry'] = timezone.now().timestamp() + 300
        session.save()

        response = self.client.post(reverse('account_delete'), {
            'otp': '000000'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_confirm_delete.html')

        # Verify user still exists
        self.assertTrue(User.objects.filter(username="todelete").exists())

    def test_account_delete_post_expired_otp(self):
        session = self.client.session
        session['delete_account_otp'] = '654321'
        session['delete_account_otp_expiry'] = timezone.now().timestamp() - 10 # expired 10s ago
        session.save()

        response = self.client.post(reverse('account_delete'), {
            'otp': '654321'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_confirm_delete.html')

        # Verify user still exists
        self.assertTrue(User.objects.filter(username="todelete").exists())

    def test_account_delete_resend_otp(self):
        response = self.client.get(reverse('account_delete_resend'))
        self.assertRedirects(response, reverse('account_delete'))

        session = self.client.session
        self.assertIsNotNone(session.get('delete_account_otp'))
        self.assertIsNotNone(session.get('delete_account_otp_expiry'))


class ProfileEditFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="profileuser", email="profile@example.com", password="password123")
        self.client = Client()
        self.client.login(username="profileuser", password="password123")

    def test_profile_edit_no_changes(self):
        response = self.client.post(reverse('profile_edit'), {
            'username': 'profileuser',
            'email': 'profile@example.com',
            'password1': '',
            'password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile_edit.html')
        from django.contrib.messages import get_messages
        msg_list = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("No changes detected.", msg_list)

    def test_profile_edit_username_change_success(self):
        response = self.client.post(reverse('profile_edit'), {
            'username': 'newprofileuser',
            'email': 'profile@example.com',
            'password1': '',
            'password2': ''
        })
        self.assertRedirects(response, reverse('account_details'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newprofileuser')

    def test_profile_edit_username_taken(self):
        User.objects.create_user(username="takenuser", email="taken@example.com", password="password123")
        response = self.client.post(reverse('profile_edit'), {
            'username': 'takenuser',
            'email': 'profile@example.com',
            'password1': '',
            'password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile_edit.html')
        
        # Verify no changes made to our user
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'profileuser')

    def test_profile_edit_email_taken(self):
        User.objects.create_user(username="takenemailuser", email="takenemail@example.com", password="password123")
        response = self.client.post(reverse('profile_edit'), {
            'username': 'profileuser',
            'email': 'takenemail@example.com',
            'password1': '',
            'password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile_edit.html')
        
        from django.contrib.messages import get_messages
        msg_list = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Email already registered by another user!", msg_list)

    def test_profile_edit_password_mismatch(self):
        response = self.client.post(reverse('profile_edit'), {
            'username': 'profileuser',
            'email': 'profile@example.com',
            'password1': 'newpass123',
            'password2': 'differentpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile_edit.html')
        
        from django.contrib.messages import get_messages
        msg_list = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Passwords do not match!", msg_list)

    def test_profile_edit_password_too_short(self):
        response = self.client.post(reverse('profile_edit'), {
            'username': 'profileuser',
            'email': 'profile@example.com',
            'password1': 'short',
            'password2': 'short'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile_edit.html')

    def test_profile_edit_email_change_sends_otp(self):
        response = self.client.post(reverse('profile_edit'), {
            'username': 'profileuser',
            'email': 'newemail@example.com',
            'password1': '',
            'password2': ''
        })
        self.assertRedirects(response, reverse('profile_edit_verify'))
        
        session = self.client.session
        self.assertIsNotNone(session.get('profile_edit_pending'))
        self.assertEqual(session.get('profile_edit_pending').get('email'), 'newemail@example.com')
        self.assertIsNotNone(session.get('profile_edit_otp'))



