from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    path('evidence/', views.evidence_list_view, name='evidence_list'),
    path('evidence/upload/', views.upload_evidence_view, name='upload_evidence'),
]