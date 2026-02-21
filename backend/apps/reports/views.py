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

from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from apps.accounts.permissions import IsAdmin
from apps.assets.models import (
    Asset, AssetGroup, AssetReceipt, AssetDisposal,
    DepreciationRecord, AssetImprovement,
)
from .models import BackupRecord
from .serializers import BackupRecordSerializer
from . import gdrive


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
                exclude=[
                    'contenttypes', 'auth.Permission', 'sessions',
                    'admin.logentry', 'django_celery_beat',
                ],
                stdout=buf,
            )
        except Exception as e:
            return Response({'error': f'dumpdata помилка: {str(e)}'}, status=500)

        content = buf.getvalue().encode('utf-8')
        if not content or content == b'[]':
            return Response({'error': 'Дані для бекапу відсутні.'}, status=500)

        filename = f'backup_{db_name}_{timestamp}.json'

        from django.http import HttpResponse
        response = HttpResponse(
            content,
            content_type='application/octet-stream',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Backup-Filename'] = filename
        return response


class GDriveStatusView(APIView):
    """Статус підключення Google Drive."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        configured = gdrive.is_configured()
        has_credentials = gdrive.has_credentials_file()
        has_token = gdrive.has_token()
        last_backup = BackupRecord.objects.filter(
            status=BackupRecord.Status.SUCCESS,
        ).first()

        # Розклад автобекапу
        schedule_info = {'enabled': False, 'hour': 2, 'minute': 0}
        try:
            from django_celery_beat.models import PeriodicTask
            task = PeriodicTask.objects.filter(name='daily-backup-to-gdrive').first()
            if task and task.crontab:
                schedule_info = {
                    'enabled': task.enabled,
                    'hour': int(task.crontab.hour),
                    'minute': int(task.crontab.minute),
                }
        except Exception:
            pass

        return Response({
            'is_configured': configured,
            'has_credentials': has_credentials,
            'has_token': has_token,
            'folder_id': getattr(settings, 'GDRIVE_FOLDER_ID', ''),
            'retention_days': getattr(settings, 'GDRIVE_BACKUP_RETENTION_DAYS', 30),
            'last_backup': BackupRecordSerializer(last_backup).data if last_backup else None,
            'schedule': schedule_info,
        })


class GDriveAuthView(APIView):
    """Початок OAuth2 авторизації Google Drive."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        """Повертає URL для авторизації Google."""
        creds_path = getattr(settings, 'GDRIVE_CREDENTIALS_PATH', '')
        if not creds_path or not os.path.isfile(creds_path):
            return Response(
                {'error': 'Файл OAuth credentials не знайдено. Покладіть його в backend/ та вкажіть GDRIVE_CREDENTIALS_PATH в .env'},
                status=400,
            )

        from google_auth_oauthlib.flow import Flow

        callback_url = request.build_absolute_uri('/api/reports/backup/gdrive-callback/')

        flow = Flow.from_client_secrets_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive.file'],
            redirect_uri=callback_url,
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )

        # Зберегти state в сесії
        request.session['gdrive_oauth_state'] = state

        return Response({'auth_url': auth_url})


class GDriveCallbackView(APIView):
    """Callback OAuth2 від Google — зберігає токен."""
    permission_classes = []  # Google redirects тут без JWT

    def get(self, request):
        from django.http import HttpResponseRedirect
        from google_auth_oauthlib.flow import Flow

        code = request.query_params.get('code')
        if not code:
            error = request.query_params.get('error', 'Невідома помилка')
            return HttpResponseRedirect(f'/?gdrive_error={error}')

        creds_path = getattr(settings, 'GDRIVE_CREDENTIALS_PATH', '')
        callback_url = request.build_absolute_uri('/api/reports/backup/gdrive-callback/')

        try:
            flow = Flow.from_client_secrets_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.file'],
                redirect_uri=callback_url,
            )
            flow.fetch_token(code=code)
            creds = flow.credentials

            token_path = gdrive._token_path()
            with open(token_path, 'w') as f:
                f.write(creds.to_json())

            # Перенаправити на сторінку бекапу з повідомленням про успіх
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:5173'
            return HttpResponseRedirect(f'{frontend_url}/backup?gdrive_auth=success')
        except Exception as e:
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:5173'
            return HttpResponseRedirect(f'{frontend_url}/backup?gdrive_auth=error&message={str(e)[:100]}')


class CloudBackupView(APIView):
    """Ручний запуск бекапу на Google Drive."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        if not gdrive.is_configured():
            return Response(
                {'error': 'Google Drive не налаштовано. Перевірте GDRIVE_CREDENTIALS_PATH та GDRIVE_FOLDER_ID в .env'},
                status=400,
            )

        # Перевірити чи немає бекапу в процесі
        pending = BackupRecord.objects.filter(status=BackupRecord.Status.PENDING).exists()
        if pending:
            return Response(
                {'error': 'Бекап вже виконується. Зачекайте завершення.'},
                status=409,
            )

        from .backup import create_full_backup, upload_and_record

        try:
            zip_path = create_full_backup()
            record = upload_and_record(zip_path, is_auto=False)

            if record.status == BackupRecord.Status.FAILED:
                return Response(
                    {'error': record.error_message or 'Помилка завантаження на Google Drive'},
                    status=500,
                )

            from .serializers import BackupRecordSerializer
            return Response({
                'message': 'Бекап успішно створено та завантажено на Google Drive',
                'record': BackupRecordSerializer(record).data,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class BackupHistoryPagination(PageNumberPagination):
    page_size = 20


class BackupHistoryView(generics.ListAPIView):
    """Історія хмарних бекапів."""
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = BackupRecordSerializer
    pagination_class = BackupHistoryPagination
    queryset = BackupRecord.objects.all()


class DatabaseRestoreView(APIView):
    """Відновлення бази даних з завантаженого файлу (.sql / .json)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error': 'Файл не надано.'}, status=400)

        filename = uploaded.name.lower()
        if not filename.endswith(('.sql', '.json')):
            return Response(
                {'error': 'Підтримуються тільки формати .sql та .json'},
                status=400,
            )

        # Зберегти у тимчасовий файл
        tmp_dir = tempfile.mkdtemp(prefix='buh_restore_')
        tmp_path = os.path.join(tmp_dir, uploaded.name)

        try:
            with open(tmp_path, 'wb') as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)

            from .backup import restore_from_sql, restore_from_json

            if filename.endswith('.sql'):
                result = restore_from_sql(tmp_path)
            else:
                result = restore_from_json(tmp_path)

            if result['success']:
                return Response({'message': result['message']})
            return Response({'error': result['message']}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class CloudRestoreView(APIView):
    """Відновлення бази з хмарного бекапу Google Drive."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        record_id = request.data.get('record_id')
        if not record_id:
            return Response({'error': 'record_id не вказано.'}, status=400)

        try:
            record = BackupRecord.objects.get(id=record_id)
        except BackupRecord.DoesNotExist:
            return Response({'error': 'Запис бекапу не знайдено.'}, status=404)

        if not record.gdrive_file_id:
            return Response(
                {'error': 'У цього бекапу відсутній Google Drive file ID.'},
                status=400,
            )

        if record.status != BackupRecord.Status.SUCCESS:
            return Response(
                {'error': 'Можна відновити тільки успішний бекап.'},
                status=400,
            )

        tmp_dir = tempfile.mkdtemp(prefix='buh_cloud_restore_')
        zip_path = os.path.join(tmp_dir, record.filename)

        try:
            # Завантажити ZIP з Google Drive
            gdrive.download_file(record.gdrive_file_id, zip_path)

            from .backup import restore_from_zip
            result = restore_from_zip(zip_path)

            if result['success']:
                return Response({'message': result['message']})
            return Response({'error': result['message']}, status=500)
        except Exception as e:
            return Response({'error': f'Помилка завантаження з GDrive: {str(e)}'}, status=500)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


BACKUP_TASK_NAME = 'apps.reports.tasks.auto_backup_to_gdrive'


class BackupScheduleView(APIView):
    """Управління розкладом автоматичного бекапу через django-celery-beat."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_periodic_task(self):
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        try:
            return PeriodicTask.objects.get(name='daily-backup-to-gdrive')
        except PeriodicTask.DoesNotExist:
            return None

    def get(self, request):
        task = self._get_periodic_task()
        if task and task.crontab:
            return Response({
                'enabled': task.enabled,
                'hour': int(task.crontab.hour),
                'minute': int(task.crontab.minute),
            })
        return Response({
            'enabled': False,
            'hour': 2,
            'minute': 0,
        })

    def put(self, request):
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json

        enabled = request.data.get('enabled', True)
        hour = int(request.data.get('hour', 2))
        minute = int(request.data.get('minute', 0))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return Response({'error': 'Невірний час'}, status=400)

        schedule, _ = CrontabSchedule.objects.get_or_create(
            hour=hour,
            minute=minute,
            timezone=settings.CELERY_TIMEZONE,
        )

        task = self._get_periodic_task()
        if task:
            task.crontab = schedule
            task.enabled = enabled
            task.save()
        else:
            PeriodicTask.objects.create(
                name='daily-backup-to-gdrive',
                task=BACKUP_TASK_NAME,
                crontab=schedule,
                enabled=enabled,
                kwargs=json.dumps({}),
            )

        return Response({
            'enabled': enabled,
            'hour': hour,
            'minute': minute,
            'message': 'Розклад оновлено',
        })
