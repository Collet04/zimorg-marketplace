from django.db import models
from auth_app.models import User

class SellerProfile(models.Model):
    class SellerType(models.TextChoices):
        INDIVIDUAL_FARMER = 'INDIVIDUAL_FARMER', 'Individual Farmer'
        COOPERATIVE = 'COOPERATIVE', 'Cooperative'
        COMMERCIAL_FARM = 'COMMERCIAL_FARM', 'Commercial Farm'
        PROCESSOR = 'PROCESSOR', 'Processor / Producer'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=255)
    seller_type = models.CharField(max_length=30, choices=SellerType.choices, default=SellerType.INDIVIDUAL_FARMER)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, help_text="e.g., Goromonzi, Mashonaland East")
    farm_size_hectares = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    years_operating = models.PositiveIntegerField(default=1)
    
    # Workflow status tracking
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        ADDITIONAL_EVIDENCE_REQUIRED = 'ADDITIONAL_EVIDENCE_REQUIRED', 'Additional Evidence Required'
        VERIFIED = 'VERIFIED', 'Verified'
        CONDITIONALLY_VERIFIED = 'CONDITIONALLY_VERIFIED', 'Conditionally Verified'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        EXPIRED = 'EXPIRED', 'Expired'

    verification_status = models.CharField(
        max_length=40,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} ({self.get_verification_status_display()})"