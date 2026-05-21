from django.contrib import admin
from .models import Expense, Category, Wallet

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "balance")
    search_fields = ("user__username", "name")
    list_filter = ("user",)
    ordering = ("name",)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "wallet", "get_category_name", "amount", "date")
    list_filter = ('wallet', 'category', 'date')
    search_fields = ('user__username', 'category__name', "description", "wallet__name")
    ordering = ("-date",)

    def get_category_name(self, obj):
        return obj.category.name if obj.category else "-"
    get_category_name.short_description = "Category"

