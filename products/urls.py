from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_catalog_view, name='catalog'),
    path('my-products/', views.seller_product_list_view, name='seller_products'),
    path('add/', views.add_product_view, name='add_product'),
]