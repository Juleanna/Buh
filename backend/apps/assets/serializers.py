from rest_framework import serializers
from .models import (
    AssetGroup, Asset, AssetReceipt, AssetDisposal,
    DepreciationRecord, Inventory, InventoryItem,
    Organization, AccountEntry, AssetRevaluation,
    AssetImprovement, AssetAttachment, AuditLog, Notification,
    Location, ResponsiblePerson,
)


class LocationSerializer(serializers.ModelSerializer):
    assets_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Location
        fields = '__all__'


class ResponsiblePersonSerializer(serializers.ModelSerializer):
    assets_count = serializers.IntegerField(read_only=True, default=0)
    location_name = serializers.CharField(
        source='location.name', read_only=True, default=''
    )

    class Meta:
        model = ResponsiblePerson
        fields = '__all__'


class AssetGroupSerializer(serializers.ModelSerializer):
    assets_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AssetGroup
        fields = '__all__'


class AssetListSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    responsible_person_name = serializers.CharField(
        source='responsible_person.full_name', read_only=True, default=''
    )
    location_name = serializers.CharField(
        source='location.name', read_only=True, default=''
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    depreciation_method_display = serializers.CharField(
        source='get_depreciation_method_display', read_only=True
    )

    class Meta:
        model = Asset
        fields = [
            'id', 'inventory_number', 'name', 'group', 'group_name',
            'status', 'status_display', 'initial_cost', 'current_book_value',
            'accumulated_depreciation', 'depreciation_method',
            'depreciation_method_display', 'commissioning_date',
            'responsible_person', 'responsible_person_name',
            'location', 'location_name', 'quantity',
        ]


class AssetDetailSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    responsible_person_name = serializers.CharField(
        source='responsible_person.full_name', read_only=True, default=''
    )
    location_name = serializers.CharField(
        source='location.name', read_only=True, default=''
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    depreciation_method_display = serializers.CharField(
        source='get_depreciation_method_display', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = [
            'current_book_value', 'accumulated_depreciation',
            'created_by', 'created_at', 'updated_at',
        ]


class AssetReceiptSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    receipt_type_display = serializers.CharField(
        source='get_receipt_type_display', read_only=True
    )

    class Meta:
        model = AssetReceipt
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class AssetDisposalSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    disposal_type_display = serializers.CharField(
        source='get_disposal_type_display', read_only=True
    )

    class Meta:
        model = AssetDisposal
        fields = '__all__'
        read_only_fields = [
            'book_value_at_disposal', 'accumulated_depreciation_at_disposal',
            'created_by', 'created_at',
        ]


class DepreciationRecordSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    method_display = serializers.CharField(
        source='get_depreciation_method_display', read_only=True
    )
    account_number = serializers.CharField(
        source='asset.group.account_number', read_only=True, default=''
    )
    expense_account = serializers.CharField(
        source='asset.group.depreciation_account', read_only=True, default='131'
    )
    asset_initial_cost = serializers.DecimalField(
        source='asset.initial_cost', read_only=True,
        max_digits=15, decimal_places=2
    )
    asset_residual_value = serializers.DecimalField(
        source='asset.residual_value', read_only=True,
        max_digits=15, decimal_places=2
    )
    asset_depreciation_rate = serializers.DecimalField(
        source='asset.depreciation_rate', read_only=True,
        max_digits=8, decimal_places=4, default=None
    )
    asset_useful_life_months = serializers.IntegerField(
        source='asset.useful_life_months', read_only=True
    )

    class Meta:
        model = DepreciationRecord
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    condition_display = serializers.CharField(
        source='get_condition_display', read_only=True
    )

    class Meta:
        model = InventoryItem
        fields = '__all__'
        read_only_fields = ['difference']


class InventoryListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    commission_head_name = serializers.CharField(
        source='commission_head.get_full_name', read_only=True, default=''
    )
    location_name = serializers.CharField(
        source='location.name', read_only=True, default=''
    )
    items_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Inventory
        fields = [
            'id', 'number', 'date', 'order_number', 'order_date',
            'status', 'status_display', 'location', 'location_name',
            'commission_head', 'commission_head_name', 'items_count',
        ]


class InventoryDetailSerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    commission_head_name = serializers.CharField(
        source='commission_head.get_full_name', read_only=True, default=''
    )
    location_name = serializers.CharField(
        source='location.name', read_only=True, default=''
    )

    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class AccountEntrySerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    entry_type_display = serializers.CharField(
        source='get_entry_type_display', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = AccountEntry
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class AssetRevaluationSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    revaluation_type_display = serializers.CharField(
        source='get_revaluation_type_display', read_only=True
    )

    class Meta:
        model = AssetRevaluation
        fields = '__all__'
        read_only_fields = [
            'revaluation_type',
            'old_initial_cost', 'old_depreciation', 'old_book_value',
            'new_initial_cost', 'new_depreciation', 'new_book_value',
            'revaluation_amount', 'created_by', 'created_at',
        ]


class AssetImprovementSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    improvement_type_display = serializers.CharField(
        source='get_improvement_type_display', read_only=True
    )

    class Meta:
        model = AssetImprovement
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']


class AssetAttachmentSerializer(serializers.ModelSerializer):
    file_type_display = serializers.CharField(
        source='get_file_type_display', read_only=True
    )
    uploaded_by_name = serializers.CharField(
        source='uploaded_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = AssetAttachment
        fields = '__all__'
        read_only_fields = ['file_size', 'uploaded_by', 'uploaded_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.get_full_name', read_only=True, default=''
    )
    action_display = serializers.CharField(
        source='get_action_display', read_only=True
    )
    content_type_name = serializers.CharField(
        source='content_type.model', read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_name', 'action', 'action_display',
            'content_type', 'content_type_name', 'object_id', 'object_repr',
            'changes', 'ip_address', 'timestamp',
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', read_only=True
    )

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['recipient', 'created_at']


class DepreciationCalcRequestSerializer(serializers.Serializer):
    """Запит на нарахування амортизації за період."""
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    asset_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Якщо порожній — для всіх активних ОЗ',
    )
    production_volumes = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2),
        required=False,
        help_text='Обсяги продукції: {asset_id: volume}',
    )
