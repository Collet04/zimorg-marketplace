from django import forms
from .models import EvidenceDocument


class EvidenceUploadForm(forms.ModelForm):
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