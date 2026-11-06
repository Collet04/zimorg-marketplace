from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_dashboard_home, name='home'),
    path('manage/sellers/', views.sellers_view, name='sellers'),
    path('sellers/<int:seller_id>/', views.seller_detail_view, name='seller_detail'),
    path('sellers/<int:seller_id>/verify/', views.admin_verify_action, name='verify_seller'),
    path('evidence/<int:evidence_id>/verify/', views.admin_verify_action, name='verify_evidence'),
    path('manage/customers/', views.customers_view, name='customers'),
    path('customers/<int:customer_id>/', views.customer_detail_view, name='customer_detail'),
    path('manage/evidence/', views.evidence_view, name='evidence'),
    path('manage/evidence/<int:evidence_id>/', views.evidence_detail_view, name='evidence_detail'),
    path('manage/evidence/<int:evidence_id>/rescreen/', views.rescreen_evidence_view, name='rescreen_evidence'),
]