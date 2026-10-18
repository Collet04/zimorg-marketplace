from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'seller', 'category', 'price', 'unit', 'stock_quantity', 'is_available', 'created_at']
    list_filter = ['category', 'is_available', 'unit']
    search_fields = ['name', 'seller__business_name', 'description']