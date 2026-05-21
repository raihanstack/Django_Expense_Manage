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
        self.assertIsNull = self.assertIsNone(expense)
        
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
