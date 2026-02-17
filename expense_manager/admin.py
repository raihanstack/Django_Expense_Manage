from django.contrib import admin
from .models import Expense, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_category_name", "amount", "date")
    list_filter = ('category', 'date')
    search_fields = ('user__username', 'category__name', "description")
    ordering = ("-date",)

    def get_category_name(self, obj):
        return obj.category.name
    get_category_name.short_description = "Category"
