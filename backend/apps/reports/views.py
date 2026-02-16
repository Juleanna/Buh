from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from decimal import Decimal

from apps.assets.models import Asset, AssetGroup, DepreciationRecord


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
