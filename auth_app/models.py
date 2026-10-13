from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        BUYER = 'BUYER', 'Buyer'
        SELLER = 'SELLER', 'Seller'
        VERIFIER = 'VERIFIER', 'Verifier'
        ADMIN = 'ADMIN', 'Administrator'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BUYER,
        help_text='Primary access role in the system.'
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_buyer(self):
        return self.role == self.Role.BUYER

    def is_seller(self):
        return self.role == self.Role.SELLER

    def is_verifier(self):
        return self.role == self.Role.VERIFIER

    def is_admin_user(self):
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN] or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"