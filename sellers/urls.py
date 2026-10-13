from django.urls import path
from . import views

app_name = 'sellers'

urlpatterns = [
    path('onboarding/', views.seller_onboarding_view, name='onboarding'),
    path('dashboard/', views.seller_dashboard_view, name='dashboard'),
]