from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('asset-summary/', views.AssetSummaryReportView.as_view(), name='asset-summary'),
    path('turnover-statement/', views.TurnoverStatementView.as_view(), name='turnover-statement'),
]
