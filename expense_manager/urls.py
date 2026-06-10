from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.home, name='home'),

    # User authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('register/verify/', views.user_register_verify, name='register_verify'),
    path('register/resend/', views.user_register_resend, name='register_resend'),
    path('register/details/', views.user_register_details, name='register_details'),

    # Password reset flow
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),

    # Expense management
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/update/<int:expense_id>/', views.expense_update, name='expense_update'),
    path('expenses/delete/<int:expense_id>/', views.expense_delete, name='expense_delete'),

    # User Account
    path('account/', views.account_details, name='account_details'),
    path('account/delete/', views.account_delete, name='account_delete'),
    path('account/delete/resend/', views.account_delete_resend, name='account_delete_resend'),

    # Wallet Management
    path('wallets/', views.wallet_list, name='wallet_list'),
    path('wallets/create/', views.wallet_create, name='wallet_create'),
    path('wallets/update/<int:wallet_id>/', views.wallet_update, name='wallet_update'),
    path('wallets/delete/<int:wallet_id>/', views.wallet_delete, name='wallet_delete'),
    path('wallets/deposit/', views.wallet_deposit, name='wallet_deposit'),
    path('wallets/transfer/', views.wallet_transfer, name='wallet_transfer'),

]
