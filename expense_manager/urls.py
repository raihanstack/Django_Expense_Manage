from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page

    # User authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_loginout, name='logout'),
    path('register/', views.user_register, name='register'),

    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset_done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset_confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset_complete/', views.password_reset_complete, name='password_reset_complete'),

    # Expense management
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/update/<int:id>/', views.expense_update, name='expense_update'),
    path('expense/delete/', views.expense_delete, name='expense_delete')
]
