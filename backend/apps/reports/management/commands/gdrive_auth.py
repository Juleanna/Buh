"""
Одноразова авторизація Google Drive через OAuth2.

Використання:
    python manage.py gdrive_auth

Що робить:
1. Відкриває браузер для авторизації в Google акаунті
2. Зберігає токен в gdrive_token.json
3. Після цього бекапи працюватимуть автоматично
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Авторизація Google Drive через OAuth2 (одноразово)'

    def handle(self, *args, **options):
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds_path = settings.GDRIVE_CREDENTIALS_PATH
        if not creds_path or not os.path.isfile(creds_path):
            self.stderr.write(self.style.ERROR(
                f'Файл credentials не знайдено: {creds_path}\n'
                'Вкажіть GDRIVE_CREDENTIALS_PATH в .env'
            ))
            return

        token_path = os.path.join(settings.BASE_DIR, 'gdrive_token.json')

        self.stdout.write('Відкриваю браузер для авторизації Google Drive...\n')

        flow = InstalledAppFlow.from_client_secrets_file(creds_path, [
            'https://www.googleapis.com/auth/drive.file',
        ])
        creds = flow.run_local_server(port=8090)

        with open(token_path, 'w') as f:
            f.write(creds.to_json())

        self.stdout.write(self.style.SUCCESS(
            f'Токен збережено: {token_path}\n'
            'Google Drive готовий до роботи!'
        ))
