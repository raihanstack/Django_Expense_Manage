from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expense_manager.urls'))
]

handler400 = 'expense_manager.views.handler400'
handler403 = 'expense_manager.views.handler403'
handler404 = 'expense_manager.views.handler404'
handler500 = 'expense_manager.views.handler500'

