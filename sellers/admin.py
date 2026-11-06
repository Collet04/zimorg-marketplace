from django.contrib import admin
from .models import SellerProfile
from verification.models import EvidenceDocument


class EvidenceDocumentInline(admin.TabularInline):
    model = EvidenceDocument
    extra = 0
    fields = (
        'title',
        'document_type',
        'file',
        'status',
        'issue_date',
        'expiry_date',
        'extracted_text',
        'review_notes',
        'reviewed_by',
    )
    readonly_fields = ('extracted_text',)


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'business_name',
        'user',
        'seller_type',
        'location',
        'verification_status',
        'created_at',
    ]
    list_filter = ['verification_status', 'seller_type']
    search_fields = [
        'business_name',
        'user__username',
        'user__email',
        'user__phone_number',
        'location',
        'description',
    ]
    readonly_fields = (
        'user_email',
        'user_phone_number',
        'user_role',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Account details', {
            'fields': ('user', 'user_email', 'user_phone_number', 'user_role'),
        }),
        ('Seller-submitted details', {
            'fields': (
                'business_name',
                'seller_type',
                'description',
                'location',
                'farm_size_hectares',
                'years_operating',
            ),
        }),
        ('Verification', {'fields': ('verification_status',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    inlines = [EvidenceDocumentInline]

    @admin.display(description='Email')
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description='Phone number')
    def user_phone_number(self, obj):
        return obj.user.phone_number or 'Not provided'

    @admin.display(description='Account role')
    def user_role(self, obj):
        return obj.user.get_role_display()