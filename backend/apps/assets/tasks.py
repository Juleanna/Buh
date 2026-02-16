"""
Celery-задачі для автоматизації обліку основних засобів.

Задачі:
1. auto_calculate_depreciation  — масове нарахування амортизації за період
2. check_high_wear_assets       — пошук ОЗ із зносом > 90%
3. check_full_depreciation      — пошук повністю амортизованих ОЗ
4. send_depreciation_reminder   — нагадування про нарахування амортизації 1-го числа
"""
from decimal import Decimal

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction

from .depreciation import calculate_monthly_depreciation
from .entries import create_depreciation_entries
from .models import Asset, DepreciationRecord, Notification, AccountEntry

User = get_user_model()


@shared_task
def auto_calculate_depreciation(year, month):
    """
    Нарахування амортизації для всіх активних ОЗ за вказаний період.

    Логіка аналогічна DepreciationRecordViewSet.calculate, але виконується
    як фонова Celery-задача без прив'язки до HTTP-запиту.

    Args:
        year: рік періоду нарахування (int).
        month: місяць періоду нарахування (int).

    Returns:
        dict з кількістю створених записів та помилками.
    """
    assets = Asset.objects.filter(status=Asset.Status.ACTIVE)

    records_created = 0
    errors = []

    for asset in assets:
        # Перевірка: чи не нараховано вже
        if DepreciationRecord.objects.filter(
            asset=asset, period_year=year, period_month=month
        ).exists():
            errors.append({
                'asset_id': asset.id,
                'error': f'Амортизація за {month:02d}.{year} вже нарахована',
            })
            continue

        # Розрахунок суми амортизації
        amount = calculate_monthly_depreciation(asset)

        if amount <= 0:
            continue

        with transaction.atomic():
            record = DepreciationRecord.objects.create(
                asset=asset,
                period_year=year,
                period_month=month,
                depreciation_method=asset.depreciation_method,
                amount=amount,
                book_value_before=asset.current_book_value,
                book_value_after=asset.current_book_value - amount,
                is_posted=True,
            )

            # Оновлюємо вартісні характеристики активу
            asset.accumulated_depreciation += amount
            asset.current_book_value -= amount
            asset.save()

            # Створюємо бухгалтерські проводки
            create_depreciation_entries(asset, record)

        records_created += 1

    # Повідомляємо бухгалтерів про завершення нарахування
    accountants = User.objects.filter(role='accountant', is_active=True)
    for user in accountants:
        Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.DEPRECIATION_DONE,
            title=f'Амортизація за {month:02d}.{year} нарахована',
            message=(
                f'Автоматичне нарахування амортизації за {month:02d}.{year} завершено. '
                f'Створено записів: {records_created}. Помилок: {len(errors)}.'
            ),
        )

    return {
        'created': records_created,
        'errors': errors,
    }


@shared_task
def check_high_wear_assets():
    """
    Пошук ОЗ із зносом понад 90% та створення сповіщень.

    Знаходить активні основні засоби, де
    accumulated_depreciation / initial_cost > 0.9 (90% зносу),
    і створює Notification типу HIGH_WEAR для адміністраторів.
    """
    threshold = Decimal('0.9')
    assets = Asset.objects.filter(status=Asset.Status.ACTIVE)
    high_wear_assets = []

    for asset in assets:
        if asset.initial_cost > 0:
            wear_ratio = asset.accumulated_depreciation / asset.initial_cost
            if wear_ratio > threshold:
                high_wear_assets.append(asset)

    if not high_wear_assets:
        return {'high_wear_count': 0}

    # Сповіщуємо адміністраторів
    admins = User.objects.filter(role='admin', is_active=True)
    for user in admins:
        for asset in high_wear_assets:
            wear_pct = (
                asset.accumulated_depreciation / asset.initial_cost * 100
            ).quantize(Decimal('0.1'))

            Notification.objects.create(
                recipient=user,
                notification_type=Notification.NotificationType.HIGH_WEAR,
                title=f'Високий знос ОЗ: {asset.inventory_number}',
                message=(
                    f'Основний засіб {asset.inventory_number} "{asset.name}" '
                    f'має знос {wear_pct}% '
                    f'(накопичений знос: {asset.accumulated_depreciation} грн, '
                    f'первісна вартість: {asset.initial_cost} грн). '
                    f'Рекомендується розглянути списання або заміну.'
                ),
                asset=asset,
            )

    return {'high_wear_count': len(high_wear_assets)}


@shared_task
def check_full_depreciation():
    """
    Пошук повністю амортизованих ОЗ та створення сповіщень.

    Знаходить активні основні засоби, де
    current_book_value <= residual_value,
    і створює Notification типу FULL_DEPRECIATION для адміністраторів.
    """
    assets = Asset.objects.filter(status=Asset.Status.ACTIVE)
    fully_depreciated = []

    for asset in assets:
        if asset.current_book_value <= asset.residual_value:
            fully_depreciated.append(asset)

    if not fully_depreciated:
        return {'fully_depreciated_count': 0}

    # Сповіщуємо адміністраторів
    admins = User.objects.filter(role='admin', is_active=True)
    for user in admins:
        for asset in fully_depreciated:
            Notification.objects.create(
                recipient=user,
                notification_type=Notification.NotificationType.FULL_DEPRECIATION,
                title=f'ОЗ повністю амортизовано: {asset.inventory_number}',
                message=(
                    f'Основний засіб {asset.inventory_number} "{asset.name}" '
                    f'повністю амортизовано. '
                    f'Залишкова вартість: {asset.current_book_value} грн, '
                    f'ліквідаційна вартість: {asset.residual_value} грн. '
                    f'Подальше нарахування амортизації неможливе.'
                ),
                asset=asset,
            )

    return {'fully_depreciated_count': len(fully_depreciated)}


@shared_task
def send_depreciation_reminder():
    """
    Нагадування про необхідність нарахування амортизації.

    Виконується 1-го числа кожного місяця та створює
    Notification типу DEPRECIATION_DUE для бухгалтерів.
    """
    from django.utils import timezone

    now = timezone.now()
    current_month = now.month
    current_year = now.year

    accountants = User.objects.filter(role='accountant', is_active=True)
    notifications_created = 0

    for user in accountants:
        Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.DEPRECIATION_DUE,
            title=f'Час нараховувати амортизацію за {current_month:02d}.{current_year}',
            message=(
                f'Нагадування: необхідно нарахувати амортизацію основних засобів '
                f'за {current_month:02d}.{current_year}. '
                f'Перейдіть до розділу "Амортизація" для виконання розрахунку.'
            ),
        )
        notifications_created += 1

    return {'notifications_created': notifications_created}
