"""
Сервіс створення сповіщень при ручних операціях.

Використовується у views.py для генерації Notification без Celery.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model

from .models import Asset, Notification

User = get_user_model()


def _get_recipients(roles, exclude_user=None):
    """Отримати активних користувачів за ролями, окрім виконавця."""
    qs = User.objects.filter(role__in=roles, is_active=True)
    if exclude_user:
        qs = qs.exclude(pk=exclude_user.pk)
    return list(qs)


def _notify(recipients, notification_type, title, message, asset=None):
    """Масове створення сповіщень для списку отримувачів."""
    notifications = [
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            asset=asset,
        )
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_receipt(receipt, user):
    """Сповіщення при оприбуткуванні ОЗ."""
    asset = receipt.asset
    recipients = _get_recipients(['admin', 'accountant'], exclude_user=user)
    _notify(
        recipients,
        Notification.NotificationType.DEPRECIATION_DONE,
        f'Оприбутковано ОЗ: {asset.inventory_number}',
        f'{user.get_full_name() or user.username} оприбуткував ОЗ '
        f'"{asset.name}" (інв. {asset.inventory_number}) '
        f'на суму {receipt.amount} грн.',
        asset=asset,
    )


def notify_disposal(disposal, user):
    """Сповіщення при вибутті ОЗ."""
    asset = disposal.asset
    recipients = _get_recipients(['admin', 'accountant'], exclude_user=user)
    _notify(
        recipients,
        Notification.NotificationType.DEPRECIATION_DONE,
        f'Списано ОЗ: {asset.inventory_number}',
        f'{user.get_full_name() or user.username} оформив вибуття ОЗ '
        f'"{asset.name}" (інв. {asset.inventory_number}). '
        f'Балансова вартість на момент списання: {disposal.book_value_at_disposal} грн.',
        asset=asset,
    )


def notify_depreciation(year, month, records_count, total_amount, user):
    """Сповіщення після ручного нарахування амортизації."""
    recipients = _get_recipients(['admin', 'accountant'], exclude_user=user)
    _notify(
        recipients,
        Notification.NotificationType.DEPRECIATION_DONE,
        f'Амортизація за {month:02d}.{year} нарахована',
        f'{user.get_full_name() or user.username} нарахував амортизацію '
        f'за {month:02d}.{year}. '
        f'Оброблено ОЗ: {records_count}, '
        f'загальна сума: {total_amount} грн.',
    )


def notify_revaluation(revaluation, user):
    """Сповіщення при переоцінці ОЗ."""
    asset = revaluation.asset
    rtype = 'дооцінку' if revaluation.revaluation_type == 'upward' else 'уцінку'
    recipients = _get_recipients(['admin', 'accountant'], exclude_user=user)
    _notify(
        recipients,
        Notification.NotificationType.DEPRECIATION_DONE,
        f'Переоцінка ОЗ: {asset.inventory_number}',
        f'{user.get_full_name() or user.username} провів {rtype} ОЗ '
        f'"{asset.name}" (інв. {asset.inventory_number}). '
        f'Зал. вартість: {revaluation.old_book_value} → {revaluation.new_book_value} грн. '
        f'Сума переоцінки: {revaluation.revaluation_amount} грн.',
        asset=asset,
    )


def notify_inventory_complete(inventory, results, user):
    """Сповіщення при завершенні інвентаризації."""
    recipients = _get_recipients(['admin', 'accountant'], exclude_user=user)

    shortages = results.get('shortages', 0)
    ntype = (
        Notification.NotificationType.SHORTAGE_FOUND
        if shortages > 0
        else Notification.NotificationType.INVENTORY_DUE
    )
    title = (
        f'Інвентаризація #{inventory.number}: виявлено нестач {shortages}'
        if shortages > 0
        else f'Інвентаризація #{inventory.number} завершена'
    )
    _notify(
        recipients,
        ntype,
        title,
        f'{user.get_full_name() or user.username} завершив інвентаризацію '
        f'#{inventory.number}. '
        f'Всього позицій: {results["total_items"]}, '
        f'знайдено: {results["found"]}, '
        f'нестач: {shortages}.',
    )


def check_high_wear_inline(assets_qs, user):
    """Перевірка зносу > 90% після нарахування амортизації (синхронно)."""
    threshold = Decimal('0.9')
    high_wear = []
    for asset in assets_qs:
        if asset.initial_cost > 0:
            wear = asset.accumulated_depreciation / asset.initial_cost
            if wear > threshold:
                high_wear.append(asset)

    if not high_wear:
        return

    admins = _get_recipients(['admin'])
    for asset in high_wear:
        wear_pct = (
            asset.accumulated_depreciation / asset.initial_cost * 100
        ).quantize(Decimal('0.1'))
        _notify(
            admins,
            Notification.NotificationType.HIGH_WEAR,
            f'Високий знос ОЗ: {asset.inventory_number}',
            f'ОЗ "{asset.name}" (інв. {asset.inventory_number}) має знос {wear_pct}%. '
            f'Рекомендується розглянути списання або заміну.',
            asset=asset,
        )


def check_full_depreciation_inline(assets_qs, user):
    """Перевірка повної амортизації після нарахування (синхронно)."""
    fully_depr = [
        a for a in assets_qs
        if a.current_book_value <= a.residual_value
    ]

    if not fully_depr:
        return

    admins = _get_recipients(['admin'])
    for asset in fully_depr:
        _notify(
            admins,
            Notification.NotificationType.FULL_DEPRECIATION,
            f'ОЗ повністю амортизовано: {asset.inventory_number}',
            f'ОЗ "{asset.name}" (інв. {asset.inventory_number}) '
            f'повністю амортизовано. '
            f'Залишкова: {asset.current_book_value} грн, '
            f'ліквідаційна: {asset.residual_value} грн.',
            asset=asset,
        )
