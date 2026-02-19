"""
Multi-step migration:
1. Create Position model
2. Add is_employee to ResponsiblePerson
3. Add temporary position_new FK to ResponsiblePerson
4. Data migration: populate Position from text values, set FKs
5. Remove old position CharField, rename position_new
6. Alter Inventory commission_head/members from User to ResponsiblePerson
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_positions_forward(apps, schema_editor):
    """Create Position records from existing text values and set FKs."""
    Position = apps.get_model('assets', 'Position')
    ResponsiblePerson = apps.get_model('assets', 'ResponsiblePerson')

    # Collect unique position names from ResponsiblePerson
    position_names = set()
    for rp in ResponsiblePerson.objects.exclude(position='').exclude(position__isnull=True):
        position_names.add(rp.position.strip())

    # Create Position records
    position_map = {}
    for name in position_names:
        if name:
            pos, _ = Position.objects.get_or_create(name=name)
            position_map[name] = pos

    # Set FK references on ResponsiblePerson
    for rp in ResponsiblePerson.objects.exclude(position='').exclude(position__isnull=True):
        name = rp.position.strip()
        if name in position_map:
            rp.position_new = position_map[name]
            rp.save(update_fields=['position_new'])


def migrate_positions_backward(apps, schema_editor):
    """Reverse: copy position name back to text field."""
    ResponsiblePerson = apps.get_model('assets', 'ResponsiblePerson')
    for rp in ResponsiblePerson.objects.filter(position_new__isnull=False).select_related('position_new'):
        rp.position = rp.position_new.name
        rp.save(update_fields=['position'])


def nullify_commission_head(apps, schema_editor):
    """Nullify commission_head and clear commission_members before changing FK target."""
    Inventory = apps.get_model('assets', 'Inventory')
    Inventory.objects.filter(commission_head__isnull=False).update(commission_head=None)
    for inv in Inventory.objects.all():
        inv.commission_members.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0005_assetreceipt_supplier_organization_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Create Position model
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Назва')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
            ],
            options={
                'verbose_name': 'Посада',
                'verbose_name_plural': 'Посади',
                'ordering': ['name'],
            },
        ),

        # Step 2: Add is_employee to ResponsiblePerson
        migrations.AddField(
            model_name='responsibleperson',
            name='is_employee',
            field=models.BooleanField(default=False, verbose_name='Співробітник'),
        ),

        # Step 3: Add temporary position_new FK field
        migrations.AddField(
            model_name='responsibleperson',
            name='position_new',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='assets.position',
                verbose_name='Посада (нова)',
            ),
        ),

        # Step 4: Data migration — populate positions
        migrations.RunPython(migrate_positions_forward, migrate_positions_backward),

        # Step 5: Remove old position CharField
        migrations.RemoveField(
            model_name='responsibleperson',
            name='position',
        ),

        # Step 6: Rename position_new to position
        migrations.RenameField(
            model_name='responsibleperson',
            old_name='position_new',
            new_name='position',
        ),

        # Step 7: Fix position field attributes (related_name, verbose_name)
        migrations.AlterField(
            model_name='responsibleperson',
            name='position',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='responsible_persons',
                to='assets.position',
                verbose_name='Посада',
            ),
        ),

        # Step 8: Nullify existing commission data (User IDs don't match ResponsiblePerson IDs)
        migrations.RunPython(nullify_commission_head, migrations.RunPython.noop),

        # Step 9: Change commission_head FK target
        migrations.AlterField(
            model_name='inventory',
            name='commission_head',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='headed_inventories',
                to='assets.responsibleperson',
                verbose_name='Голова комісії',
            ),
        ),

        # Step 10: Change commission_members M2M target
        migrations.AlterField(
            model_name='inventory',
            name='commission_members',
            field=models.ManyToManyField(
                blank=True,
                related_name='inventories_as_member',
                to='assets.responsibleperson',
                verbose_name='Члени комісії',
            ),
        ),
    ]
