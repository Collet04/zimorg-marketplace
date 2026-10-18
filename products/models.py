from django.db import models
from sellers.models import SellerProfile


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    class UnitType(models.TextChoices):
        KG = 'KG', 'Kilograms (kg)'
        GRAM = 'GRAM', 'Grams (g)'
        BUNCH = 'BUNCH', 'Bunch'
        CRATE = 'CRATE', 'Crate'
        LITRE = 'LITRE', 'Litre (l)'
        PIECE = 'PIECE', 'Piece / Item'
        PACK = 'PACK', 'Pack'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in USD")
    unit = models.CharField(max_length=20, choices=UnitType.choices, default=UnitType.KG)
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Available inventory quantity")
    
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='product_images/%Y/%m/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.seller.business_name}"