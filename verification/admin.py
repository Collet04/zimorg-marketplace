from django.contrib import admin
from .models import EvidenceDocument


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'document_type', 'status', 'created_at']
    list_filter = ['document_type', 'status']
    search_fields = ['title', 'seller__business_name']