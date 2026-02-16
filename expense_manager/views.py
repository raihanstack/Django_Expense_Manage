from django.shortcuts import render, get_object_or_404, redirect
from .models import Expense
from django.utils import timezone
from datetime import timedelta

def user_login(request):
    return render(request, 'login.html')

def user_loginout(request):
    return redirect('login')

def user_register(request):
    return render(request, 'register.html')

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