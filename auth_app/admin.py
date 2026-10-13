from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'is_verified_email', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_verified_email']
    
    fieldsets = UserAdmin.fieldsets + (
        ('ZOM Custom Profile', {'fields': ('role', 'phone_number', 'is_verified_email')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ZOM Custom Profile', {'fields': ('role', 'phone_number', 'is_verified_email')}),
    )