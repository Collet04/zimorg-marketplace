from django.core.validators import MaxValueValidator, MinValueValidator
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

    class ScreeningStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    class ScreeningRecommendation(models.TextChoices):
        REVIEW = 'REVIEW', 'Manual review required'
        LIKELY_RELEVANT = 'LIKELY_RELEVANT', 'Likely relevant'
        EXPIRED = 'EXPIRED', 'Possible expiry'
        IRRELEVANT = 'IRRELEVANT', 'Possibly unrelated'

    class AIRecommendation(models.TextChoices):
        APPROVED = 'APPROVED', 'Recommend approval'
        REJECTED = 'REJECTED', 'Recommend rejection'
        REQUIRES_REVIEW = 'REQUIRES_REVIEW', 'Requires manual review'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='evidence_documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=255, help_text="e.g., Organic Soil Certificate 2026")
    file = models.FileField(upload_to='evidence_documents/%Y/%m/')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    review_notes = models.TextField(blank=True, help_text="Feedback or notes from verifiers")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_evidence')
    
    # Text extracted by the local document-screening pipeline.
    extracted_text = models.TextField(blank=True)
    screening_status = models.CharField(
        max_length=12,
        choices=ScreeningStatus.choices,
        default=ScreeningStatus.PENDING,
    )
    screening_recommendation = models.CharField(
        max_length=20,
        choices=ScreeningRecommendation.choices,
        default=ScreeningRecommendation.REVIEW,
    )
    screening_findings = models.JSONField(default=list, blank=True)
    screened_at = models.DateTimeField(null=True, blank=True)
    confidence_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    ai_recommendation = models.CharField(
        max_length=20,
        choices=AIRecommendation.choices,
        default=AIRecommendation.REQUIRES_REVIEW,
    )
    audit_reasons = models.JSONField(default=list, blank=True)
    
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['seller', 'document_type'],
                name='unique_evidence_type_per_seller',
            ),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.seller.business_name}"


MANDATORY_DOCUMENT_GROUPS = (
    (
        'Official Organic Certificate or Participatory Guarantee System Record',
        (EvidenceDocument.DocumentType.CERTIFICATE, EvidenceDocument.DocumentType.PGS_RECORD),
    ),
    (
        'Business Registration Document',
        (EvidenceDocument.DocumentType.BUSINESS_DOCUMENT,),
    ),
    (
        'Farm Inspection Record',
        (EvidenceDocument.DocumentType.INSPECTION_RECORD,),
    ),
)


def mandatory_document_checklist(seller):
    documents = list(seller.evidence_documents.all())
    checklist = []
    for label, document_types in MANDATORY_DOCUMENT_GROUPS:
        group_documents = [
            document for document in documents
            if document.document_type in document_types and document.file
        ]
        checklist.append({
            'label': label,
            'documents': group_documents,
            'submitted': bool(group_documents),
            'approved': any(
                document.status == EvidenceDocument.Status.ACCEPTED
                for document in group_documents
            ),
        })
    return checklist


def missing_mandatory_documents(seller):
    return [
        item['label']
        for item in mandatory_document_checklist(seller)
        if not item['submitted']
    ]


def unapproved_mandatory_documents(seller):
    return [
        item['label']
        for item in mandatory_document_checklist(seller)
        if not item['approved']
    ]