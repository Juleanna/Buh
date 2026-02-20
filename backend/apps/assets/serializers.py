from decimal import Decimal
from rest_framework import serializers
from .models import (
    AssetGroup, Asset, AssetReceipt, AssetDisposal,
    DepreciationRecord, Inventory, InventoryItem,
    Organization, AccountEntry, AssetRevaluation,
    AssetImprovement, AssetAttachment, AuditLog, Notification,
    Location, ResponsiblePerson, Position,
)


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'


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
    position_name = serializers.CharField(
        source='position.name', read_only=True, default=''
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

    def validate(self, data):
        incoming = data.get('incoming_depreciation', Decimal('0.00'))
        initial = data.get('initial_cost')
        if self.instance:
            if initial is None:
                initial = self.instance.initial_cost
            if 'incoming_depreciation' not in data:
                incoming = self.instance.incoming_depreciation
        if incoming and initial and incoming > initial:
            raise serializers.ValidationError({
                'incoming_depreciation':
                    'Вхідна амортизація не може перевищувати первісну вартість.'
            })
        return data


class AssetReceiptSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_inventory_number = serializers.CharField(
        source='asset.inventory_number', read_only=True
    )
    receipt_type_display = serializers.CharField(
        source='get_receipt_type_display', read_only=True
    )
    supplier_organization_name = serializers.CharField(
        source='supplier_organization.name', read_only=True, default=''
    )

    class Meta:
        model = AssetReceipt
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']

    def validate_asset(self, value):
        # При створенні — перевіряємо що на ОЗ ще немає приходу
        if not self.instance and AssetReceipt.objects.filter(asset=value).exists():
            raise serializers.ValidationError(
                'На цей основний засіб вже є прихід. Повторний прихід неможливий.'
            )
        return value


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

    def validate_asset(self, value):
        # При створенні — перевіряємо що на ОЗ ще немає вибуття
        if not self.instance and AssetDisposal.objects.filter(asset=value).exists():
            raise serializers.ValidationError(
                'На цей основний засіб вже є вибуття. Повторне вибуття неможливе.'
            )
        return value


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
    asset_incoming_depreciation = serializers.DecimalField(
        source='asset.incoming_depreciation', read_only=True,
        max_digits=15, decimal_places=2
    )
    wear_before = serializers.SerializerMethodField()
    wear_after = serializers.SerializerMethodField()

    class Meta:
        model = DepreciationRecord
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']

    def get_wear_before(self, obj):
        """Сума зносу на початок періоду = вхідна амортизація + сума всіх попередніх нарахувань."""
        from django.db.models import Sum, Q
        incoming = obj.asset.incoming_depreciation or Decimal('0.00')
        prior = DepreciationRecord.objects.filter(
            asset=obj.asset,
        ).filter(
            Q(period_year__lt=obj.period_year) |
            Q(period_year=obj.period_year, period_month__lt=obj.period_month) |
            Q(period_year=obj.period_year, period_month=obj.period_month, id__lt=obj.id)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return incoming + prior

    def get_wear_after(self, obj):
        """Сума зносу на кінець періоду = знос на початок + амортизація за період."""
        return self.get_wear_before(obj) + obj.amount


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
        source='commission_head.full_name', read_only=True, default=''
    )
    responsible_person_name = serializers.CharField(
        source='responsible_person.full_name', read_only=True, default=''
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
            'responsible_person', 'responsible_person_name',
            'commission_head', 'commission_head_name', 'items_count',
        ]


class InventoryDetailSerializer(serializers.ModelSerializer):
    items = InventoryItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    commission_head_name = serializers.CharField(
        source='commission_head.full_name', read_only=True, default=''
    )
    responsible_person_name = serializers.CharField(
        source='responsible_person.full_name', read_only=True, default=''
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
