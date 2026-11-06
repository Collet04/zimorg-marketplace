from django.contrib import admin
from django.utils.html import format_html
from .models import EvidenceDocument


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'seller',
        'document_type',
        'status',
        'screening_status',
        'screening_recommendation',
        'uploaded_file',
        'created_at',
    ]
    list_filter = ['document_type', 'status']
    search_fields = [
        'title',
        'seller__business_name',
        'seller__user__username',
        'seller__user__email',
        'extracted_text',
        'review_notes',
    ]
    list_select_related = ('seller', 'seller__user', 'reviewed_by')
    readonly_fields = ('created_at', 'updated_at', 'uploaded_file')
    fields = (
        'seller',
        'document_type',
        'title',
        'file',
        'uploaded_file',
        'status',
        'screening_status',
        'screening_recommendation',
        'screening_findings',
        'screened_at',
        'issue_date',
        'expiry_date',
        'extracted_text',
        'review_notes',
        'reviewed_by',
        'created_at',
        'updated_at',
    )

    @admin.display(description='Document')
    def uploaded_file(self, obj):
        if not obj.file:
            return 'No file uploaded'
        return format_html('<a href="{}" target="_blank" rel="noopener">View document</a>', obj.file.url)