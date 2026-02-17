from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Sum, Q
from django.db import transaction
from decimal import Decimal

from apps.accounts.permissions import IsAccountant, IsInventoryManager
from .models import (
    AssetGroup, Asset, AssetReceipt, AssetDisposal,
    DepreciationRecord, Inventory, InventoryItem,
    Organization, AccountEntry, AssetRevaluation,
    AssetImprovement, AssetAttachment, AuditLog, Notification,
    Location, ResponsiblePerson,
)
from .serializers import (
    AssetGroupSerializer, AssetListSerializer, AssetDetailSerializer,
    AssetReceiptSerializer, AssetDisposalSerializer,
    DepreciationRecordSerializer,
    InventoryListSerializer, InventoryDetailSerializer,
    InventoryItemSerializer, DepreciationCalcRequestSerializer,
    OrganizationSerializer, AccountEntrySerializer,
    AssetRevaluationSerializer, AssetImprovementSerializer,
    AssetAttachmentSerializer, AuditLogSerializer, NotificationSerializer,
    LocationSerializer, ResponsiblePersonSerializer,
)
from .depreciation import calculate_monthly_depreciation
from .entries import (
    create_receipt_entries, create_depreciation_entries,
    create_disposal_entries, create_revaluation_entries,
    create_improvement_entries,
)
from .audit import log_action, get_client_ip
from .notifications import (
    notify_receipt, notify_disposal, notify_depreciation,
    notify_revaluation, notify_inventory_complete,
    check_high_wear_inline, check_full_depreciation_inline,
)


class LocationViewSet(viewsets.ModelViewSet):
    """CRUD для місцезнаходжень."""
    queryset = Location.objects.annotate(
        assets_count=Count('assets')
    ).order_by('name')
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    filterset_fields = ['is_active']


class ResponsiblePersonViewSet(viewsets.ModelViewSet):
    """CRUD для матеріально відповідальних осіб."""
    queryset = ResponsiblePerson.objects.select_related('location').annotate(
        assets_count=Count('assets')
    ).order_by('full_name')
    serializer_class = ResponsiblePersonSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['full_name', 'ipn', 'position']
    filterset_fields = ['is_active']


class AssetGroupViewSet(viewsets.ModelViewSet):
    """CRUD для груп основних засобів."""
    queryset = AssetGroup.objects.annotate(assets_count=Count('assets')).order_by('code')
    serializer_class = AssetGroupSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'code']


class AssetViewSet(viewsets.ModelViewSet):
    """CRUD для основних засобів."""
    queryset = Asset.objects.select_related(
        'group', 'responsible_person', 'location', 'created_by'
    )
    permission_classes = [IsAccountant]
    filterset_fields = ['group', 'status', 'depreciation_method', 'responsible_person', 'location']
    search_fields = ['inventory_number', 'name', 'location__name', 'responsible_person__full_name']
    ordering_fields = ['inventory_number', 'name', 'initial_cost', 'commissioning_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        return AssetDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            current_book_value=serializer.validated_data['initial_cost'],
        )

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        """Пошук ОЗ за інвентарним номером (для QR-сканера)."""
        inv = request.query_params.get('inventory_number', '').strip()
        if not inv:
            return Response(
                {'detail': 'Параметр inventory_number обов\'язковий'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            asset = Asset.objects.select_related('group', 'responsible_person').get(
                inventory_number=inv
            )
        except Asset.DoesNotExist:
            return Response(
                {'detail': f'ОЗ з інв. номером "{inv}" не знайдено'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AssetDetailSerializer(asset).data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по ОЗ для дашборду."""
        qs = Asset.objects.all()
        active = qs.filter(status='active')
        stats = {
            'total_count': qs.count(),
            'active_count': active.count(),
            'disposed_count': qs.filter(status='disposed').count(),
            'total_initial_cost': active.aggregate(
                s=Sum('initial_cost'))['s'] or Decimal('0.00'),
            'total_book_value': active.aggregate(
                s=Sum('current_book_value'))['s'] or Decimal('0.00'),
            'total_depreciation': active.aggregate(
                s=Sum('accumulated_depreciation'))['s'] or Decimal('0.00'),
            'by_group': list(
                active.values('group__code', 'group__name')
                .annotate(
                    count=Count('id'),
                    total_cost=Sum('initial_cost'),
                )
                .order_by('group__code')
            ),
        }
        return Response(stats)


class AssetReceiptViewSet(viewsets.ModelViewSet):
    """CRUD для приходів ОЗ."""
    queryset = AssetReceipt.objects.select_related('asset', 'created_by')
    serializer_class = AssetReceiptSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'receipt_type']
    search_fields = ['document_number', 'supplier']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        create_receipt_entries(instance.asset, instance, user=self.request.user)
        log_action(
            self.request.user, AuditLog.Action.RECEIPT, instance,
            ip_address=get_client_ip(self.request),
        )
        notify_receipt(instance, self.request.user)


class AssetDisposalViewSet(viewsets.ModelViewSet):
    """CRUD для вибуття ОЗ."""
    queryset = AssetDisposal.objects.select_related('asset', 'created_by')
    serializer_class = AssetDisposalSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'disposal_type']

    @transaction.atomic
    def perform_create(self, serializer):
        asset = serializer.validated_data['asset']
        instance = serializer.save(
            created_by=self.request.user,
            book_value_at_disposal=asset.current_book_value,
            accumulated_depreciation_at_disposal=asset.accumulated_depreciation,
        )
        asset.status = Asset.Status.DISPOSED
        asset.disposal_date = serializer.validated_data['document_date']
        asset.save()
        create_disposal_entries(asset, instance, user=self.request.user)
        log_action(
            self.request.user, AuditLog.Action.DISPOSAL, instance,
            ip_address=get_client_ip(self.request),
        )
        notify_disposal(instance, self.request.user)


class DepreciationRecordViewSet(viewsets.ModelViewSet):
    """Записи нарахування амортизації."""
    queryset = DepreciationRecord.objects.select_related('asset__group', 'asset', 'created_by')
    serializer_class = DepreciationRecordSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'period_year', 'period_month', 'is_posted']

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Масове нарахування амортизації за період."""
        serializer = DepreciationCalcRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        asset_ids = serializer.validated_data.get('asset_ids', [])
        production_volumes = serializer.validated_data.get('production_volumes', {})

        # Вибираємо активні ОЗ
        qs = Asset.objects.filter(status=Asset.Status.ACTIVE)
        if asset_ids:
            qs = qs.filter(id__in=asset_ids)

        records_created = []
        errors = []

        for asset in qs:
            # Перевірка: чи не нараховано вже
            if DepreciationRecord.objects.filter(
                asset=asset, period_year=year, period_month=month
            ).exists():
                errors.append({
                    'asset_id': asset.id,
                    'error': f'Амортизація за {month:02d}.{year} вже нарахована',
                })
                continue

            # Розрахунок
            prod_vol = production_volumes.get(str(asset.id))
            amount = calculate_monthly_depreciation(
                asset,
                production_volume=Decimal(str(prod_vol)) if prod_vol else None,
            )

            if amount <= 0:
                continue

            with transaction.atomic():
                record = DepreciationRecord.objects.create(
                    asset=asset,
                    period_year=year,
                    period_month=month,
                    depreciation_method=asset.depreciation_method,
                    amount=amount,
                    book_value_before=asset.current_book_value,
                    book_value_after=asset.current_book_value - amount,
                    production_volume=prod_vol,
                    created_by=request.user,
                )
                asset.accumulated_depreciation += amount
                asset.current_book_value -= amount
                asset.save()
                create_depreciation_entries(asset, record, user=request.user)
                log_action(
                    request.user, AuditLog.Action.DEPRECIATION, record,
                    ip_address=get_client_ip(request),
                )

            records_created.append(DepreciationRecordSerializer(record).data)

        # Сповіщення після нарахування
        if records_created:
            total_amount = sum(Decimal(r['amount']) for r in records_created)
            notify_depreciation(year, month, len(records_created), total_amount, request.user)

            # Перевірка зносу та повної амортизації
            processed_assets = Asset.objects.filter(
                pk__in=[r['asset'] for r in records_created]
            )
            check_high_wear_inline(processed_assets, request.user)
            check_full_depreciation_inline(processed_assets, request.user)

        return Response({
            'created': len(records_created),
            'records': records_created,
            'errors': errors,
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Зведена відомість амортизації за період."""
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        if not year or not month:
            return Response(
                {'error': 'Параметри year та month обов\'язкові'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        records = DepreciationRecord.objects.filter(
            period_year=year, period_month=month,
        ).select_related('asset', 'asset__group')

        total = records.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return Response({
            'year': int(year),
            'month': int(month),
            'total_amount': total,
            'records_count': records.count(),
            'records': DepreciationRecordSerializer(records, many=True).data,
        })


class InventoryViewSet(viewsets.ModelViewSet):
    """CRUD для інвентаризацій."""
    queryset = Inventory.objects.annotate(items_count=Count('items')).order_by('-date')
    permission_classes = [IsInventoryManager]
    filterset_fields = ['status']
    search_fields = ['number', 'order_number']

    def get_serializer_class(self):
        if self.action == 'list':
            return InventoryListSerializer
        return InventoryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def populate(self, request, pk=None):
        """Заповнити інвентаризацію всіма активними ОЗ."""
        inventory = self.get_object()
        if inventory.status != Inventory.Status.DRAFT:
            return Response(
                {'error': 'Заповнення можливе тільки для чернетки'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assets = Asset.objects.filter(status=Asset.Status.ACTIVE)
        if inventory.location:
            assets = assets.filter(location__icontains=inventory.location)

        created = 0
        for asset in assets:
            _, was_created = InventoryItem.objects.get_or_create(
                inventory=inventory,
                asset=asset,
                defaults={
                    'book_value': asset.current_book_value,
                    'actual_value': asset.current_book_value,
                },
            )
            if was_created:
                created += 1

        inventory.status = Inventory.Status.IN_PROGRESS
        inventory.save()

        return Response({'created': created, 'total': inventory.items.count()})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Завершити інвентаризацію."""
        inventory = self.get_object()
        inventory.status = Inventory.Status.COMPLETED
        inventory.save()

        # Підсумки
        items = inventory.items.all()
        shortages = items.filter(is_found=False)
        with_difference = items.exclude(difference=Decimal('0.00'))

        results = {
            'total_items': items.count(),
            'found': items.filter(is_found=True).count(),
            'shortages': shortages.count(),
            'with_difference': with_difference.count(),
            'total_difference': with_difference.aggregate(
                s=Sum('difference'))['s'] or Decimal('0.00'),
        }

        notify_inventory_complete(inventory, results, request.user)

        return Response(results)


class InventoryItemViewSet(viewsets.ModelViewSet):
    """CRUD для рядків інвентаризації."""
    queryset = InventoryItem.objects.select_related('asset', 'inventory')
    serializer_class = InventoryItemSerializer
    permission_classes = [IsInventoryManager]
    filterset_fields = ['inventory', 'is_found', 'condition']


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD для організацій."""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'short_name', 'edrpou']


class AccountEntryViewSet(viewsets.ModelViewSet):
    """Бухгалтерські проводки (журнал операцій)."""
    queryset = AccountEntry.objects.select_related('asset', 'created_by')
    serializer_class = AccountEntrySerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'entry_type', 'is_posted', 'date']
    search_fields = ['description', 'document_number', 'debit_account', 'credit_account']
    ordering_fields = ['date', 'amount', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def journal(self, request):
        """Оборотно-сальдова відомість за період."""
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        qs = self.get_queryset().filter(is_posted=True)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        by_type = list(
            qs.values('entry_type').annotate(
                count=Count('id'), total_amount=Sum('amount')
            ).order_by('entry_type')
        )
        return Response({
            'total_amount': total,
            'count': qs.count(),
            'by_type': by_type,
            'entries': AccountEntrySerializer(qs[:100], many=True).data,
        })


class AssetRevaluationViewSet(viewsets.ModelViewSet):
    """CRUD для переоцінок ОЗ."""
    queryset = AssetRevaluation.objects.select_related('asset', 'created_by')
    serializer_class = AssetRevaluationSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'revaluation_type']

    @transaction.atomic
    def perform_create(self, serializer):
        asset = serializer.validated_data['asset']
        fair_value = serializer.validated_data['fair_value']
        reval_date = serializer.validated_data['date']

        old_initial = asset.initial_cost
        old_depr = asset.accumulated_depreciation
        old_book = asset.current_book_value

        # Коефіцієнт переоцінки
        if old_book > 0:
            index = fair_value / old_book
        else:
            index = Decimal('1')

        new_initial = (old_initial * index).quantize(Decimal('0.01'))
        new_depr = (old_depr * index).quantize(Decimal('0.01'))
        new_book = new_initial - new_depr

        reval_type = 'upward' if fair_value > old_book else 'downward'
        reval_amount = new_book - old_book

        instance = serializer.save(
            created_by=self.request.user,
            revaluation_type=reval_type,
            old_initial_cost=old_initial,
            old_depreciation=old_depr,
            old_book_value=old_book,
            new_initial_cost=new_initial,
            new_depreciation=new_depr,
            new_book_value=new_book,
            revaluation_amount=reval_amount,
        )

        # Оновлюємо актив
        asset.initial_cost = new_initial
        asset.accumulated_depreciation = new_depr
        asset.current_book_value = new_book
        asset.save()

        create_revaluation_entries(asset, instance, user=self.request.user)
        log_action(
            self.request.user, AuditLog.Action.REVALUATION, instance,
            changes={'old_book_value': str(old_book), 'new_book_value': str(new_book)},
            ip_address=get_client_ip(self.request),
        )
        notify_revaluation(instance, self.request.user)


class AssetImprovementViewSet(viewsets.ModelViewSet):
    """CRUD для поліпшень / ремонтів ОЗ."""
    queryset = AssetImprovement.objects.select_related('asset', 'created_by')
    serializer_class = AssetImprovementSerializer
    permission_classes = [IsAccountant]
    filterset_fields = ['asset', 'improvement_type', 'increases_value']
    search_fields = ['description', 'document_number', 'contractor']

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        asset = instance.asset

        if instance.increases_value:
            asset.initial_cost += instance.amount
            asset.current_book_value += instance.amount
            asset.save()

        create_improvement_entries(asset, instance, user=self.request.user)
        log_action(
            self.request.user, AuditLog.Action.IMPROVEMENT, instance,
            ip_address=get_client_ip(self.request),
        )


class AssetAttachmentViewSet(viewsets.ModelViewSet):
    """CRUD для вкладень (файлів) ОЗ."""
    queryset = AssetAttachment.objects.select_related('asset', 'uploaded_by')
    serializer_class = AssetAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ['asset', 'file_type']

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get('file')
        file_size = uploaded_file.size if uploaded_file else 0
        serializer.save(uploaded_by=self.request.user, file_size=file_size)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Журнал аудиту (тільки читання)."""
    queryset = AuditLog.objects.select_related('user', 'content_type')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['action', 'user']
    search_fields = ['object_repr']
    ordering_fields = ['timestamp']


class NotificationViewSet(viewsets.ModelViewSet):
    """Сповіщення поточного користувача."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'ok'})
