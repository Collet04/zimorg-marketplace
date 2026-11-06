from django import forms
from .models import EvidenceDocument

MAX_EVIDENCE_FILE_SIZE = 20 * 1024 * 1024
SUPPORTED_EVIDENCE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'}


class EvidenceUploadForm(forms.ModelForm):
    def __init__(self, *args, seller=None, **kwargs):
        self.seller = seller
        super().__init__(*args, **kwargs)

    class Meta:
        model = EvidenceDocument
        fields = ['document_type', 'title', 'file', 'issue_date', 'expiry_date']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Annual Organic Farm Certification 2026'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_document_type(self):
        document_type = self.cleaned_data['document_type']
        if self.seller and EvidenceDocument.objects.filter(
            seller=self.seller,
            document_type=document_type,
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                'You already have this document type uploaded. Update the existing document instead.'
            )
        return document_type

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file is None:
            return uploaded_file

        extension = uploaded_file.name.rpartition('.')[2].lower()
        suffix = f'.{extension}' if extension else ''
        if suffix not in SUPPORTED_EVIDENCE_EXTENSIONS:
            raise forms.ValidationError('Upload a PDF or image file (PNG, JPG, or TIFF).')
        if uploaded_file.size > MAX_EVIDENCE_FILE_SIZE:
            raise forms.ValidationError('The document must be no larger than 20 MB.')
        return uploaded_file