from django import forms

from sellers.models import SellerProfile
from verification.models import EvidenceDocument, unapproved_mandatory_documents


class SellerVerificationForm(forms.ModelForm):
    class Meta:
        model = SellerProfile
        fields = ['verification_status', 'rejection_reason']
        widgets = {
            'verification_status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why this application was rejected.',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('verification_status') == SellerProfile.VerificationStatus.REJECTED
            and not cleaned_data.get('rejection_reason', '').strip()
        ):
            self.add_error('rejection_reason', 'A rejection reason is required.')
        if cleaned_data.get('verification_status') == SellerProfile.VerificationStatus.VERIFIED:
            missing_approvals = unapproved_mandatory_documents(self.instance)
            if missing_approvals:
                self.add_error(
                    'verification_status',
                    'Seller cannot be verified until all mandatory documents are approved: '
                    + '; '.join(missing_approvals),
                )
        return cleaned_data


class EvidenceReviewForm(forms.ModelForm):
    class Meta:
        model = EvidenceDocument
        fields = ['status', 'review_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add review feedback for this document.',
            }),
        }


class CustomerAccountForm(forms.Form):
    is_active = forms.BooleanField(
        required=False,
        label='Account active',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
