"""
Команда для заповнення довідника груп ОЗ згідно ПКУ ст. 138.3.3.
python manage.py seed_asset_groups
"""
from django.core.management.base import BaseCommand
from apps.assets.models import AssetGroup


GROUPS = [
    ('1', 'Земельні ділянки', None, '101', '131'),
    ('2', 'Капітальні витрати на поліпшення земель, не пов\'язані з будівництвом', 180, '102', '131'),
    ('3', 'Будівлі', 240, '103', '131'),
    ('4', 'Машини та обладнання', 60, '104', '131'),
    ('5', 'Транспортні засоби', 60, '105', '131'),
    ('6', 'Інструменти, прилади, інвентар, меблі', 48, '106', '131'),
    ('7', 'Тварини', 72, '107', '131'),
    ('8', 'Багаторічні насадження', 120, '108', '131'),
    ('9', 'Інші основні засоби', 144, '109', '131'),
    ('10', 'Бібліотечні фонди', None, '111', '132'),
    ('11', 'Малоцінні необоротні матеріальні активи', None, '112', '132'),
    ('12', 'Тимчасові (нетитульні) споруди', 60, '113', '132'),
    ('13', 'Природні ресурси', None, '114', '132'),
    ('14', 'Інвентарна тара', 72, '115', '132'),
    ('15', 'Предмети прокату', 60, '116', '132'),
    ('16', 'Довгострокові біологічні активи', 84, '161', '134'),
]


class Command(BaseCommand):
    help = 'Заповнення довідника груп ОЗ згідно ПКУ ст. 138.3.3'

    def handle(self, *args, **options):
        created_count = 0
        for code, name, min_life, account, depr_account in GROUPS:
            _, created = AssetGroup.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'min_useful_life_months': min_life,
                    'account_number': account,
                    'depreciation_account': depr_account,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Довідник груп ОЗ заповнено. '
                f'Створено: {created_count}, оновлено: {len(GROUPS) - created_count}'
            )
        )
