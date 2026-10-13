from django import forms
from .models import SellerProfile


class SellerProfileForm(forms.ModelForm):
    class Meta:
        model = SellerProfile
        fields = [
            'business_name', 
            'seller_type', 
            'description', 
            'location', 
            'farm_size_hectares', 
            'years_operating'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Ruwa Organic Farms'}),
            'seller_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your farming or natural production practices...'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Goromonzi, Mashonaland East'}),
            'farm_size_hectares': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 5.5'}),
            'years_operating': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2'}),
        }