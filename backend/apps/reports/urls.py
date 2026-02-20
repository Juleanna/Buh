from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('asset-summary/', views.AssetSummaryReportView.as_view(), name='asset-summary'),
    path('turnover-statement/', views.TurnoverStatementView.as_view(), name='turnover-statement'),
    path('backup/', views.DatabaseBackupView.as_view(), name='backup'),
    path('backup/gdrive-status/', views.GDriveStatusView.as_view(), name='gdrive-status'),
    path('backup/cloud/', views.CloudBackupView.as_view(), name='cloud-backup'),
    path('backup/history/', views.BackupHistoryView.as_view(), name='backup-history'),
    path('backup/gdrive-auth/', views.GDriveAuthView.as_view(), name='gdrive-auth'),
    path('backup/gdrive-callback/', views.GDriveCallbackView.as_view(), name='gdrive-callback'),
    path('backup/schedule/', views.BackupScheduleView.as_view(), name='backup-schedule'),
]
