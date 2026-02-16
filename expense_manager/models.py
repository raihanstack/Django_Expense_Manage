from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name=models.CharField(max_length=100,unique=True)

class Expense(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    Category=models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    amount=models.DecimalField(max_digits=10, decimal_places=2)
    description=models.TextField(blank=True, null=True)
    date=models.DateField(auto_now_add=True)
