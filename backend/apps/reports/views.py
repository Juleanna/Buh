from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import date, datetime

from apps.assets.models import (
    Asset, AssetGroup, AssetReceipt, AssetDisposal,
    DepreciationRecord, AssetImprovement,
)


class DashboardView(APIView):
    """Зведена інформація для головної сторінки."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_assets = Asset.objects.filter(status=Asset.Status.ACTIVE)

        return Response({
            'assets': {
                'total': Asset.objects.count(),
                'active': active_assets.count(),
                'disposed': Asset.objects.filter(status=Asset.Status.DISPOSED).count(),
                'conserved': Asset.objects.filter(status=Asset.Status.CONSERVED).count(),
            },
            'financials': {
                'total_initial_cost': active_assets.aggregate(
                    s=Sum('initial_cost'))['s'] or Decimal('0.00'),
                'total_book_value': active_assets.aggregate(
                    s=Sum('current_book_value'))['s'] or Decimal('0.00'),
                'total_depreciation': active_assets.aggregate(
                    s=Sum('accumulated_depreciation'))['s'] or Decimal('0.00'),
            },
            'by_group': list(
                active_assets.values('group__code', 'group__name')
                .annotate(
                    count=Count('id'),
                    total_initial=Sum('initial_cost'),
                    total_book=Sum('current_book_value'),
                )
                .order_by('group__code')
            ),
            'depreciation_by_method': list(
                active_assets.values('depreciation_method')
                .annotate(count=Count('id'))
                .order_by('depreciation_method')
            ),
        })


class AssetSummaryReportView(APIView):
    """Зведений звіт по ОЗ за групами."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        groups = AssetGroup.objects.annotate(
            active_count=Count('assets', filter=Q(assets__status='active')),
            total_initial=Sum('assets__initial_cost', filter=Q(assets__status='active')),
            total_book=Sum('assets__current_book_value', filter=Q(assets__status='active')),
            total_depreciation=Sum(
                'assets__accumulated_depreciation', filter=Q(assets__status='active')
            ),
        ).order_by('code')

        data = []
        for g in groups:
            data.append({
                'code': g.code,
                'name': g.name,
                'active_count': g.active_count,
                'total_initial': g.total_initial or Decimal('0.00'),
                'total_book': g.total_book or Decimal('0.00'),
                'total_depreciation': g.total_depreciation or Decimal('0.00'),
                'wear_percentage': (
                    round(float(g.total_depreciation / g.total_initial * 100), 1)
                    if g.total_initial else 0
                ),
            })

        return Response(data)


class TurnoverStatementView(APIView):
    """Оборотна відомість по основних засобах за період."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')

        if not date_from_str or not date_to_str:
            return Response(
                {'error': 'Параметри date_from та date_to є обов\'язковими (формат YYYY-MM-DD).'},
                status=400,
            )

        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Невірний формат дати. Використовуйте YYYY-MM-DD.'},
                status=400,
            )

        # Get all assets: active ones + any that had operations in the period
        assets_with_receipts = AssetReceipt.objects.filter(
            document_date__range=(date_from, date_to)
        ).values_list('asset_id', flat=True)

        assets_with_disposals = AssetDisposal.objects.filter(
            document_date__range=(date_from, date_to)
        ).values_list('asset_id', flat=True)

        assets_with_depreciation = DepreciationRecord.objects.filter(
            self._period_range_q(date_from, date_to)
        ).values_list('asset_id', flat=True)

        assets_with_improvements = AssetImprovement.objects.filter(
            date__range=(date_from, date_to),
            increases_value=True,
        ).values_list('asset_id', flat=True)

        relevant_asset_ids = set(
            Asset.objects.filter(status=Asset.Status.ACTIVE).values_list('id', flat=True)
        ) | set(assets_with_receipts) | set(assets_with_disposals) \
          | set(assets_with_depreciation) | set(assets_with_improvements)

        assets = Asset.objects.filter(
            id__in=relevant_asset_ids
        ).select_related('group', 'responsible_person').order_by('inventory_number')

        data = []
        for asset in assets:
            # --- Opening balance ---
            # Asset exists before date_from if commissioning_date < date_from
            if asset.commissioning_date < date_from:
                opening_qty = asset.quantity
                opening_amount = asset.initial_cost
            else:
                opening_qty = 0
                opening_amount = Decimal('0.00')

            # --- Debit turnover (receipts + value-increasing improvements) ---
            debit_receipts = AssetReceipt.objects.filter(
                asset=asset,
                document_date__range=(date_from, date_to),
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            debit_improvements = AssetImprovement.objects.filter(
                asset=asset,
                date__range=(date_from, date_to),
                increases_value=True,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            debit_amount = debit_receipts + debit_improvements
            debit_qty = AssetReceipt.objects.filter(
                asset=asset,
                document_date__range=(date_from, date_to),
            ).count()

            # --- Credit turnover (disposals + depreciation) ---
            credit_disposals = AssetDisposal.objects.filter(
                asset=asset,
                document_date__range=(date_from, date_to),
            ).aggregate(total=Sum('sale_amount'))['total'] or Decimal('0.00')

            credit_depreciation = DepreciationRecord.objects.filter(
                asset=asset,
            ).filter(
                self._period_range_q(date_from, date_to)
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            credit_amount = credit_disposals + credit_depreciation
            credit_qty = AssetDisposal.objects.filter(
                asset=asset,
                document_date__range=(date_from, date_to),
            ).count()

            # --- Closing balance ---
            closing_amount = opening_amount + debit_amount - credit_amount
            closing_qty = opening_qty + debit_qty - credit_qty

            data.append({
                'responsible_person_name': (
                    asset.responsible_person.full_name
                    if asset.responsible_person else ''
                ),
                'account_number': asset.group.account_number,
                'name': asset.name,
                'inventory_number': asset.inventory_number,
                'unit_of_measure': asset.unit_of_measure,
                'cost': str(asset.initial_cost),
                'opening_qty': opening_qty,
                'opening_amount': opening_amount,
                'debit_qty': debit_qty,
                'debit_amount': debit_amount,
                'credit_qty': credit_qty,
                'credit_amount': credit_amount,
                'closing_qty': closing_qty,
                'closing_amount': closing_amount,
            })

        return Response(data)

    @staticmethod
    def _period_range_q(date_from, date_to):
        """Build a Q filter for DepreciationRecord by period_year/period_month range."""
        # DepreciationRecord stores period as separate year and month fields.
        # Build a Q expression that covers all year/month combos in the range.
        if date_from.year == date_to.year:
            return Q(
                period_year=date_from.year,
                period_month__gte=date_from.month,
                period_month__lte=date_to.month,
            )
        # Spans multiple years
        q = Q(
            period_year=date_from.year,
            period_month__gte=date_from.month,
        ) | Q(
            period_year=date_to.year,
            period_month__lte=date_to.month,
        )
        # Full years in between (if any)
        if date_to.year - date_from.year > 1:
            q = q | Q(
                period_year__gt=date_from.year,
                period_year__lt=date_to.year,
            )
        return q
