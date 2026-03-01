from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .qr_excel import AssetQRCodeView, BulkQRCodesView, AssetExcelExportView, AssetExcelImportView

router = DefaultRouter()
router.register(r'positions', views.PositionViewSet, basename='positions')
router.register(r'locations', views.LocationViewSet, basename='locations')
router.register(r'responsible-persons', views.ResponsiblePersonViewSet, basename='responsible-persons')
router.register(r'groups', views.AssetGroupViewSet, basename='asset-groups')
router.register(r'items', views.AssetViewSet, basename='assets')
router.register(r'receipts', views.AssetReceiptViewSet, basename='receipts')
router.register(r'disposals', views.AssetDisposalViewSet, basename='disposals')
router.register(r'depreciation', views.DepreciationRecordViewSet, basename='depreciation')
router.register(r'inventories', views.InventoryViewSet, basename='inventories')
router.register(r'inventory-items', views.InventoryItemViewSet, basename='inventory-items')
router.register(r'organizations', views.OrganizationViewSet, basename='organizations')
router.register(r'entries', views.AccountEntryViewSet, basename='entries')
router.register(r'revaluations', views.AssetRevaluationViewSet, basename='revaluations')
router.register(r'improvements', views.AssetImprovementViewSet, basename='improvements')
router.register(r'transfers', views.AssetTransferViewSet, basename='transfers')
router.register(r'attachments', views.AssetAttachmentViewSet, basename='attachments')
router.register(r'audit-log', views.AuditLogViewSet, basename='audit-log')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')

urlpatterns = [
    path('', include(router.urls)),
    path('items/<int:pk>/qr/', AssetQRCodeView.as_view(), name='asset-qr'),
    path('qr/bulk/', BulkQRCodesView.as_view(), name='bulk-qr'),
    path('export/excel/', AssetExcelExportView.as_view(), name='asset-excel-export'),
    path('import/excel/', AssetExcelImportView.as_view(), name='asset-excel-import'),
]
