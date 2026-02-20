"""Логіка створення повного бекапу та вивантаження на Google Drive."""
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from . import gdrive
from .models import BackupRecord

logger = logging.getLogger(__name__)


def _find_pg_dump():
    """Знайти pg_dump на системі."""
    pg_dump = shutil.which('pg_dump')
    if pg_dump:
        return pg_dump
    for ver in range(20, 12, -1):
        candidate = f'C:/Program Files/PostgreSQL/{ver}/bin/pg_dump.exe'
        if os.path.isfile(candidate):
            return candidate
    return None


def _dump_database(output_path):
    """Створити SQL дамп бази даних."""
    pg_dump = _find_pg_dump()
    if not pg_dump:
        raise RuntimeError('pg_dump не знайдено')

    db_conf = settings.DATABASES['default']
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

    with open(output_path, 'wb') as f:
        result = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE, timeout=600)

    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace')[:500]
        raise RuntimeError(f'pg_dump помилка: {err}')


def create_full_backup():
    """
    Створити повний бекап: БД + media + .env → ZIP архів.

    Returns:
        str: шлях до створеного ZIP файлу.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{timestamp}.zip'

    tmp_dir = tempfile.mkdtemp(prefix='buh_backup_')
    zip_path = os.path.join(tempfile.gettempdir(), filename)

    try:
        # 1. Дамп бази даних
        db_dump_path = os.path.join(tmp_dir, 'database.sql')
        _dump_database(db_dump_path)

        # 2. Створити ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Додати дамп бази
            zf.write(db_dump_path, 'database.sql')

            # Додати media файли
            media_root = settings.MEDIA_ROOT
            if os.path.isdir(media_root):
                for root, _dirs, files in os.walk(media_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(
                            'media',
                            os.path.relpath(file_path, media_root),
                        )
                        zf.write(file_path, arcname)

            # Додати .env
            env_path = os.path.join(settings.BASE_DIR, '.env')
            if os.path.isfile(env_path):
                zf.write(env_path, 'env_backup')

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return zip_path


def upload_and_record(zip_path, is_auto=False):
    """
    Завантажити бекап на Google Drive та зберегти запис в БД.

    Args:
        zip_path: шлях до ZIP файлу.
        is_auto: True якщо це автоматичний бекап.

    Returns:
        BackupRecord: створений запис.
    """
    filename = os.path.basename(zip_path)
    file_size = os.path.getsize(zip_path)

    record = BackupRecord.objects.create(
        filename=filename,
        file_size=file_size,
        is_auto=is_auto,
        status=BackupRecord.Status.PENDING,
    )

    try:
        file_id, web_link = gdrive.upload_file(zip_path, filename)
        record.gdrive_file_id = file_id
        record.gdrive_link = web_link
        record.status = BackupRecord.Status.SUCCESS
        record.save()
        logger.info('Бекап %s завантажено на GDrive', filename)
    except Exception as e:
        record.status = BackupRecord.Status.FAILED
        record.error_message = str(e)[:1000]
        record.save()
        logger.error('Помилка завантаження бекапу %s: %s', filename, e)
    finally:
        # Видалити тимчасовий файл
        try:
            os.remove(zip_path)
        except OSError:
            pass

    # Автоочистка старих бекапів
    _cleanup_old_backups()

    return record


def _cleanup_old_backups():
    """Видалити старі бекапи з GDrive, якщо вони старші за retention period."""
    retention_days = getattr(settings, 'GDRIVE_BACKUP_RETENTION_DAYS', 30)
    cutoff = timezone.now() - timedelta(days=retention_days)

    old_records = BackupRecord.objects.filter(
        created_at__lt=cutoff,
        status=BackupRecord.Status.SUCCESS,
        gdrive_file_id__gt='',
    )

    for record in old_records:
        try:
            gdrive.delete_file(record.gdrive_file_id)
        except Exception as e:
            logger.warning('Не вдалося видалити старий бекап %s: %s', record.filename, e)
        record.delete()

    if old_records.exists():
        logger.info('Видалено %d старих бекапів', old_records.count())
