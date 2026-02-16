from django.shortcuts import render

def user_login(request):
    return render(request, 'login.html')

def user_loginout(request):
    pass

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
    return render(request, 'home.html')

def expense_create(request):
    return render(request, 'expense_form.html')

def expense_update(request):
    return render(request, 'expense_form.html')

def expense_delete(request):
    pass