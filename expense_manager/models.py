from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name=models.CharField(max_length=100,unique=True)

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} (৳ {self.balance})"

class Expense(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    category=models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    wallet=models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    title = models.CharField(max_length=200, blank=True)
    amount=models.DecimalField(max_digits=10, decimal_places=2)
    description=models.TextField(blank=True, null=True)
    date=models.DateField(auto_now_add=True)

