"""Convert Organization.director and Organization.accountant from CharField to FK."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0007_add_responsible_person_to_inventory'),
    ]

    operations = [
        # 1. Drop old CharField columns
        migrations.RemoveField(model_name='organization', name='director'),
        migrations.RemoveField(model_name='organization', name='accountant'),

        # 2. Add new FK columns
        migrations.AddField(
            model_name='organization',
            name='director',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='director_of_organizations',
                to='assets.responsibleperson',
                verbose_name='Директор',
            ),
        ),
        migrations.AddField(
            model_name='organization',
            name='accountant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='accountant_of_organizations',
                to='assets.responsibleperson',
                verbose_name='Головний бухгалтер',
            ),
        ),
    ]
