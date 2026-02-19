"""
Multi-step migration for User.position: CharField -> FK to Position.
"""
import django.db.models.deletion
from django.db import migrations, models


def migrate_user_positions_forward(apps, schema_editor):
    """Create Position records from User.position text and set FK."""
    Position = apps.get_model('assets', 'Position')
    User = apps.get_model('accounts', 'User')

    for user in User.objects.exclude(position='').exclude(position__isnull=True):
        name = user.position.strip()
        if name:
            pos, _ = Position.objects.get_or_create(name=name)
            user.position_new = pos
            user.save(update_fields=['position_new'])


def migrate_user_positions_backward(apps, schema_editor):
    """Reverse: copy position name back to text field."""
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(position_new__isnull=False).select_related('position_new'):
        user.position = user.position_new.name
        user.save(update_fields=['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('assets', '0006_position_and_refactor'),
    ]

    operations = [
        # Step 1: Add temporary position_new FK
        migrations.AddField(
            model_name='user',
            name='position_new',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='assets.position',
                verbose_name='Посада (нова)',
            ),
        ),

        # Step 2: Data migration
        migrations.RunPython(migrate_user_positions_forward, migrate_user_positions_backward),

        # Step 3: Remove old position CharField
        migrations.RemoveField(
            model_name='user',
            name='position',
        ),

        # Step 4: Rename position_new to position
        migrations.RenameField(
            model_name='user',
            old_name='position_new',
            new_name='position',
        ),

        # Step 5: Fix field attributes
        migrations.AlterField(
            model_name='user',
            name='position',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='assets.position',
                verbose_name='Посада',
            ),
        ),
    ]
