from django.contrib import admin
from .models import (
    AssetGroup, Asset, AssetReceipt, AssetDisposal,
    DepreciationRecord, Inventory, InventoryItem,
)


@admin.register(AssetGroup)
class AssetGroupAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'min_useful_life_months', 'account_number']
    search_fields = ['name', 'code']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'inventory_number', 'name', 'group', 'status',
        'initial_cost', 'current_book_value', 'commissioning_date',
    ]
    list_filter = ['status', 'group', 'depreciation_method']
    search_fields = ['inventory_number', 'name']
    date_hierarchy = 'commissioning_date'


@admin.register(AssetReceipt)
class AssetReceiptAdmin(admin.ModelAdmin):
    list_display = ['document_number', 'asset', 'receipt_type', 'amount', 'document_date']
    list_filter = ['receipt_type']
    date_hierarchy = 'document_date'


@admin.register(AssetDisposal)
class AssetDisposalAdmin(admin.ModelAdmin):
    list_display = ['document_number', 'asset', 'disposal_type', 'document_date']
    list_filter = ['disposal_type']
    date_hierarchy = 'document_date'


@admin.register(DepreciationRecord)
class DepreciationRecordAdmin(admin.ModelAdmin):
    list_display = ['asset', 'period_year', 'period_month', 'amount', 'is_posted']
    list_filter = ['period_year', 'period_month', 'is_posted', 'depreciation_method']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'status', 'commission_head']
    list_filter = ['status']
    date_hierarchy = 'date'


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['inventory', 'asset', 'is_found', 'condition', 'book_value', 'difference']
    list_filter = ['is_found', 'condition']
