"""Утиліта для роботи з Google Drive API через OAuth2."""
import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def _token_path():
    """Шлях до збереженого OAuth2 токену."""
    return os.path.join(settings.BASE_DIR, 'gdrive_token.json')


def has_credentials_file():
    """Чи є файл OAuth credentials."""
    creds_path = getattr(settings, 'GDRIVE_CREDENTIALS_PATH', '')
    return bool(creds_path and os.path.isfile(creds_path))


def has_token():
    """Чи є збережений OAuth2 токен."""
    return os.path.isfile(_token_path())


def is_configured():
    """Перевірити, чи повністю налаштовано Google Drive інтеграцію."""
    folder_id = getattr(settings, 'GDRIVE_FOLDER_ID', '')
    return bool(folder_id and has_credentials_file() and has_token())


def get_drive_service():
    """Створити Google Drive API клієнт через OAuth2 токен."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_file = _token_path()
    if not os.path.isfile(token_file):
        raise RuntimeError(
            'OAuth2 токен не знайдено. Запустіть: python manage.py gdrive_auth'
        )

    creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Зберегти оновлений токен
        with open(token_file, 'w') as f:
            f.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def upload_file(local_path, filename, folder_id=None):
    """
    Завантажити файл на Google Drive.

    Returns:
        tuple: (file_id, web_view_link)
    """
    from googleapiclient.http import MediaFileUpload

    service = get_drive_service()
    target_folder = folder_id or settings.GDRIVE_FOLDER_ID

    file_metadata = {
        'name': filename,
        'parents': [target_folder],
    }

    media = MediaFileUpload(
        local_path,
        mimetype='application/zip',
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
    ).execute()

    file_id = file.get('id', '')
    web_link = file.get('webViewLink', '')

    logger.info('Файл %s завантажено на GDrive (id=%s)', filename, file_id)
    return file_id, web_link


def delete_file(file_id):
    """Видалити файл з Google Drive."""
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        logger.info('Файл %s видалено з GDrive', file_id)
    except Exception as e:
        logger.warning('Не вдалося видалити файл %s з GDrive: %s', file_id, e)


def list_files(folder_id=None):
    """Отримати список файлів у папці Google Drive."""
    service = get_drive_service()
    target_folder = folder_id or settings.GDRIVE_FOLDER_ID

    results = service.files().list(
        q=f"'{target_folder}' in parents and trashed = false",
        fields='files(id, name, size, createdTime, webViewLink)',
        orderBy='createdTime desc',
        pageSize=100,
    ).execute()

    return results.get('files', [])
