from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name=models.CharField(max_length=100,unique=True)

class Expense(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    category=models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200, blank=True)
    amount=models.DecimalField(max_digits=10, decimal_places=2)
    description=models.TextField(blank=True, null=True)
    date=models.DateField(auto_now_add=True)
