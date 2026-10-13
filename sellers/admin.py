from django.contrib import admin
from .models import SellerProfile


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'seller_type', 'location', 'verification_status', 'created_at']
    list_filter = ['verification_status', 'seller_type']
    search_fields = ['business_name', 'user__username', 'location']