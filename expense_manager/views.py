from django.shortcuts import render, get_object_or_404, redirect
from .models import Expense

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
    return render(request, 'home.html')

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