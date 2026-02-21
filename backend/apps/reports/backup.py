"""Логіка створення повного бекапу, вивантаження на Google Drive та відновлення."""
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import call_command
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


# ---------------------------------------------------------------------------
#  Відновлення з бекапу
# ---------------------------------------------------------------------------

def _find_psql():
    """Знайти psql на системі."""
    psql = shutil.which('psql')
    if psql:
        return psql
    for ver in range(20, 12, -1):
        candidate = f'C:/Program Files/PostgreSQL/{ver}/bin/psql.exe'
        if os.path.isfile(candidate):
            return candidate
    return None


def restore_from_sql(sql_file_path):
    """
    Відновити базу даних з SQL дампу через psql.

    Args:
        sql_file_path: шлях до .sql файлу.

    Returns:
        dict: результат з ключами 'success' та 'message'.
    """
    psql = _find_psql()
    if not psql:
        return {'success': False, 'message': 'psql не знайдено. Встановіть PostgreSQL або додайте psql до PATH.'}

    db_conf = settings.DATABASES['default']
    env = {**os.environ, 'PGPASSWORD': db_conf['PASSWORD']}

    # Крок 1: Очистити базу — видалити всі таблиці public schema
    drop_cmd = [
        psql,
        '-h', db_conf['HOST'],
        '-p', str(db_conf['PORT']),
        '-U', db_conf['USER'],
        '-d', db_conf['NAME'],
        '-c', (
            "DO $$ DECLARE r RECORD; BEGIN "
            "FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP "
            "EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE'; "
            "END LOOP; END $$;"
        ),
    ]

    try:
        result = subprocess.run(drop_cmd, env=env, capture_output=True, timeout=120)
        if result.returncode != 0:
            err = result.stderr.decode('utf-8', errors='replace')[:500]
            logger.warning('Помилка очищення БД: %s', err)
    except Exception as e:
        logger.warning('Помилка очищення БД: %s', e)

    # Крок 2: Відновити з SQL файлу
    restore_cmd = [
        psql,
        '-h', db_conf['HOST'],
        '-p', str(db_conf['PORT']),
        '-U', db_conf['USER'],
        '-d', db_conf['NAME'],
        '-f', sql_file_path,
    ]

    try:
        result = subprocess.run(restore_cmd, env=env, capture_output=True, timeout=600)
        if result.returncode != 0:
            err = result.stderr.decode('utf-8', errors='replace')[:500]
            # psql може повернути warnings які не є фатальними
            if 'ERROR' in err.upper():
                return {'success': False, 'message': f'Помилка psql: {err}'}
            logger.warning('psql warnings: %s', err)

        return {'success': True, 'message': 'Базу даних успішно відновлено з SQL бекапу.'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Відновлення перевищило ліміт часу (10 хв).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def restore_from_json(json_file_path):
    """
    Відновити дані з JSON дампу через Django loaddata.

    Args:
        json_file_path: шлях до .json файлу.

    Returns:
        dict: результат з ключами 'success' та 'message'.
    """
    try:
        # Очистити БД перед завантаженням
        call_command('flush', '--no-input')
        call_command('loaddata', json_file_path)
        return {'success': True, 'message': 'Дані успішно відновлено з JSON бекапу.'}
    except Exception as e:
        return {'success': False, 'message': f'Помилка loaddata: {str(e)[:500]}'}


def restore_from_zip(zip_path):
    """
    Повне відновлення з ZIP архіву (БД + media).

    Args:
        zip_path: шлях до .zip файлу.

    Returns:
        dict: результат з ключами 'success' та 'message'.
    """
    tmp_dir = tempfile.mkdtemp(prefix='buh_restore_')

    try:
        # Розпакувати ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)

        messages = []

        # 1. Відновити БД з database.sql
        sql_path = os.path.join(tmp_dir, 'database.sql')
        if os.path.isfile(sql_path):
            db_result = restore_from_sql(sql_path)
            messages.append(db_result['message'])
            if not db_result['success']:
                return {'success': False, 'message': ' | '.join(messages)}
        else:
            return {'success': False, 'message': 'Файл database.sql не знайдено в архіві.'}

        # 2. Відновити media файли
        media_src = os.path.join(tmp_dir, 'media')
        if os.path.isdir(media_src):
            media_dst = settings.MEDIA_ROOT
            # Очистити існуючі media файли
            if os.path.isdir(media_dst):
                shutil.rmtree(media_dst)
            shutil.copytree(media_src, media_dst)
            messages.append('Медіафайли відновлено.')

        return {'success': True, 'message': ' '.join(messages)}
    except zipfile.BadZipFile:
        return {'success': False, 'message': 'Некоректний ZIP архів.'}
    except Exception as e:
        return {'success': False, 'message': f'Помилка відновлення: {str(e)[:500]}'}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
