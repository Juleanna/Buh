"""
Команда для заповнення довідника місцезнаходжень.
python manage.py seed_locations
"""
from django.core.management.base import BaseCommand
from apps.assets.models import Location


LOCATIONS = [
    'м. Первомайськ',
    'сел. Арбузинка',
    'сел. Криве Озеро',
    'сел. Врадіївка',
]


class Command(BaseCommand):
    help = 'Заповнення довідника місцезнаходжень'

    def handle(self, *args, **options):
        created_count = 0
        for name in LOCATIONS:
            _, created = Location.objects.get_or_create(name=name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Довідник місцезнаходжень заповнено. '
                f'Створено: {created_count}, існувало: {len(LOCATIONS) - created_count}'
            )
        )
