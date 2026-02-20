"""Celery-задачі для резервного копіювання."""
import logging

from celery import shared_task

from . import gdrive
from .backup import create_full_backup, upload_and_record

logger = logging.getLogger(__name__)


@shared_task
def auto_backup_to_gdrive():
    """Щоденний автоматичний бекап на Google Drive."""
    if not gdrive.is_configured():
        logger.warning('Google Drive не налаштовано — автобекап пропущено')
        return {'status': 'skipped', 'reason': 'Google Drive not configured'}

    try:
        zip_path = create_full_backup()
        record = upload_and_record(zip_path, is_auto=True)
        return {
            'status': record.status,
            'filename': record.filename,
            'file_size': record.file_size,
        }
    except Exception as e:
        logger.error('Помилка автобекапу: %s', e)
        return {'status': 'error', 'error': str(e)}


@shared_task
def manual_backup_to_gdrive():
    """Ручний бекап на Google Drive (викликається через API)."""
    if not gdrive.is_configured():
        raise RuntimeError('Google Drive не налаштовано')

    zip_path = create_full_backup()
    record = upload_and_record(zip_path, is_auto=False)

    if record.status == 'failed':
        raise RuntimeError(record.error_message)

    return {
        'status': record.status,
        'filename': record.filename,
        'record_id': record.id,
    }
