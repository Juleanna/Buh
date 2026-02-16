from django.urls import path
from . import views

urlpatterns = [
    path('asset/<int:pk>/card/', views.AssetCardPDFView.as_view(), name='asset-card-pdf'),
    path('depreciation-report/', views.DepreciationReportPDFView.as_view(), name='depreciation-report-pdf'),
    path('inventory/<int:pk>/report/', views.InventoryReportPDFView.as_view(), name='inventory-report-pdf'),
    path('receipt/<int:pk>/act/', views.AssetReceiptActPDFView.as_view(), name='receipt-act-pdf'),
    path('disposal/<int:pk>/act/', views.AssetDisposalActPDFView.as_view(), name='disposal-act-pdf'),
    path('disposal/<int:pk>/vehicle-act/', views.VehicleDisposalActPDFView.as_view(), name='vehicle-disposal-act-pdf'),
    path('entries-report/', views.AccountEntriesReportPDFView.as_view(), name='entries-report-pdf'),
]
