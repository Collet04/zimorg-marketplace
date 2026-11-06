from django.urls import path

from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('analysis/<int:evidence_id>/', views.analysis_report_view, name='analysis_report'),
]
