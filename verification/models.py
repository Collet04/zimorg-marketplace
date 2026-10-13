from django.db import models

# Create your models here.
from django.db import models
from sellers.models import SellerProfile
from auth_app.models import User


class EvidenceDocument(models.Model):
    class DocumentType(models.TextChoices):
        CERTIFICATE = 'CERTIFICATE', 'Official Organic Certificate'
        PGS_RECORD = 'PGS_RECORD', 'Participatory Guarantee System Record'
        INSPECTION_RECORD = 'INSPECTION_RECORD', 'Farm Inspection Record'
        FARM_RECORD = 'FARM_RECORD', 'Farm / Production Log'
        INPUT_RECORD = 'INPUT_RECORD', 'Soil / Input Purchase Record'
        PRODUCT_LABEL = 'PRODUCT_LABEL', 'Product Packaging / Label'
        BUSINESS_DOCUMENT = 'BUSINESS_DOCUMENT', 'Business Registration Document'
        OTHER = 'OTHER', 'Other Supporting Evidence'

    class Status(models.TextChoices):
        UPLOADED = 'UPLOADED', 'Uploaded'
        PROCESSING = 'PROCESSING', 'Processing (AI Analysis)'
        PROCESSED = 'PROCESSED', 'Processed'
        REQUIRES_REVIEW = 'REQUIRES_REVIEW', 'Requires Verifier Review'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        EXPIRED = 'EXPIRED', 'Expired'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='evidence_documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=255, help_text="e.g., Organic Soil Certificate 2026")
    file = models.FileField(upload_to='evidence_documents/%Y/%m/')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    review_notes = models.TextField(blank=True, help_text="Feedback or notes from verifiers")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_evidence')
    
    # OCR / AI Extracted text summary (to be populated in Sprint 6)
    extracted_text = models.TextField(blank=True)
    
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.seller.business_name}"