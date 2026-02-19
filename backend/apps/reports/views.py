import io
import os
import subprocess
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.assets.models import (
    Asset, AssetGroup, AssetReceipt, AssetDisposal,
    DepreciationRecord, AssetImprovement,
)


class DashboardView(APIView):
    """Зведена інформація для головної сторінки."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_assets = Asset.objects.filter(status=Asset.Status.ACTIVE)

        # ОЗ з високим зносом (>80%)
        high_wear = list(
            active_assets.filter(
                initial_cost__gt=0,
            ).annotate(
                wear_pct=ExpressionWrapper(
                    F('accumulated_depreciation') * 100 / F('initial_cost'),
                    output_field=DecimalField(),
                ),
            ).filter(
                wear_pct__gte=80,
            ).order_by('-wear_pct').values(
                'id', 'inventory_number', 'name', 'initial_cost',
                'current_book_value', 'accumulated_depreciation', 'wear_pct',
            )[:10]
        )

        # ОЗ, що скоро будуть повністю амортизовані (залишок < 10% від початкової)
        near_full = list(
            active_assets.filter(
                initial_cost__gt=0,
                current_book_value__gt=F('residual_value'),
            ).annotate(
                remaining_pct=ExpressionWrapper(
                    (F('current_book_value') - F('residual_value')) * 100 / F('initial_cost'),
                    output_field=DecimalField(),
                ),
            ).filter(
                remaining_pct__lte=10,
            ).order_by('remaining_pct').values(
                'id', 'inventory_number', 'name', 'initial_cost',
                'current_book_value', 'residual_value', 'remaining_pct',
            )[:10]
        )

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
            'high_wear_assets': high_wear,
            'near_full_depreciation': near_full,
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


class DatabaseBackupView(APIView):
    """Інформація про БД та створення бекапу — один endpoint."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # GET — інформація про БД
        db_conf = settings.DATABASES['default']
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = cursor.fetchone()[0]
            cursor.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            tables_count = cursor.fetchone()[0]

        return Response({
            'database_name': db_conf['NAME'],
            'database_host': db_conf['HOST'],
            'database_size': db_size,
            'tables_count': tables_count,
            'assets_count': Asset.objects.count(),
        })

    def post(self, request):
        """POST — створити та завантажити бекап."""
        backup_format = request.data.get('format', request.query_params.get('format', 'sql'))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_name = settings.DATABASES['default']['NAME']

        if backup_format == 'json':
            return self._backup_json(timestamp, db_name)
        return self._backup_sql(timestamp, db_name)

    def _backup_sql(self, timestamp, db_name):
        """Бекап через pg_dump (SQL формат) — вивід прямо в пам'ять."""
        from django.http import HttpResponse

        db_conf = settings.DATABASES['default']

        pg_dump = shutil.which('pg_dump')
        if not pg_dump:
            for ver in range(20, 12, -1):
                candidate = f'C:/Program Files/PostgreSQL/{ver}/bin/pg_dump.exe'
                if os.path.isfile(candidate):
                    pg_dump = candidate
                    break

        if not pg_dump:
            return Response(
                {'error': 'pg_dump не знайдено. Встановіть PostgreSQL або додайте pg_dump до PATH.'},
                status=500,
            )

        env = {**os.environ, 'PGPASSWORD': db_conf['PASSWORD']}
        cmd = [
            pg_dump,
            '-h', db_conf['HOST'],
            '-p', str(db_conf['PORT']),
            '-U', db_conf['USER'],
            '-F', 'p',
            '--no-owner',
            '--no-privileges',
            db_conf['NAME'],
        ]

        try:
            result = subprocess.run(
                cmd, env=env, capture_output=True, timeout=300,
            )
            if result.returncode != 0:
                err = result.stderr.decode('utf-8', errors='replace')[:500]
                return Response(
                    {'error': f'pg_dump помилка: {err}'},
                    status=500,
                )
        except subprocess.TimeoutExpired:
            return Response({'error': 'Бекап перевищив ліміт часу (5 хв).'}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        filename = f'backup_{db_name}_{timestamp}.sql'
        response = HttpResponse(
            result.stdout,
            content_type='application/octet-stream',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Backup-Filename'] = filename
        return response

    def _backup_json(self, timestamp, db_name):
        """Бекап через Django dumpdata (JSON формат)."""
        buf = io.StringIO()
        try:
            call_command(
                'dumpdata',
                '--natural-foreign',
                '--natural-primary',
                '--indent', '2',
                exclude=['contenttypes', 'auth.Permission', 'sessions', 'admin.logentry'],
                stdout=buf,
            )
        except Exception as e:
            return Response({'error': f'dumpdata помилка: {str(e)}'}, status=500)

        content = buf.getvalue().encode('utf-8')
        filename = f'backup_{db_name}_{timestamp}.json'

        response = FileResponse(
            io.BytesIO(content),
            content_type='application/json',
            as_attachment=True,
            filename=filename,
        )
        response['X-Backup-Filename'] = filename
        return response
