from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'unit', 'stock_quantity', 'image', 'is_available']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Organic Red Tomatoes'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe farming practices or details about this batch...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 2.50'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g., 50'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }