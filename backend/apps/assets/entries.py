"""
Автоматичне формування бухгалтерських проводок для операцій з основними засобами.

Проводки формуються відповідно до Плану рахунків бухгалтерського обліку
та НП(С)БО 7 «Основні засоби».

Рахунки:
    10x — Основні засоби (за групами)
    13x — Знос (амортизація) необоротних активів
    152 — Придбання (виготовлення) основних засобів (капітальні інвестиції)
    23  — Виробництво
    91  — Загальновиробничі витрати
    92  — Адміністративні витрати
    93  — Витрати на збут
    377 — Розрахунки з іншими дебіторами
    411 — Дооцінка (уцінка) основних засобів
    631 — Розрахунки з вітчизняними постачальниками
    746 — Інші доходи від звичайної діяльності
    975 — Уцінка необоротних активів і фінансових інвестицій
    976 — Списання необоротних активів
"""
from decimal import Decimal

from apps.assets.models import AccountEntry


def _create_entry(
    entry_type,
    date,
    debit_account,
    credit_account,
    amount,
    description,
    asset,
    document_number='',
    document_date=None,
    user=None,
):
    """
    Внутрішня допоміжна функція для створення одного запису AccountEntry.

    Returns:
        AccountEntry — збережений об'єкт проводки.
    """
    return AccountEntry.objects.create(
        entry_type=entry_type,
        date=date,
        debit_account=debit_account,
        credit_account=credit_account,
        amount=amount,
        description=description,
        asset=asset,
        document_number=document_number,
        document_date=document_date,
        is_posted=True,
        created_by=user,
    )


# ---------------------------------------------------------------------------
# 1. Оприбуткування основного засобу
# ---------------------------------------------------------------------------

def create_receipt_entries(asset, receipt, user=None):
    """
    Створює проводки при оприбуткуванні основного засобу.

    Проводка:
        Дт <рахунок групи ОЗ> (наприклад, 104)
        Кт 152 (Капітальні інвестиції)
        на суму оприбуткування.

    Args:
        asset: об'єкт Asset.
        receipt: об'єкт AssetReceipt (має поля amount, document_number,
                 document_date).
        user: користувач, який створює проводку (created_by).

    Returns:
        list[AccountEntry] — список створених проводок.
    """
    entries = []

    entry = _create_entry(
        entry_type=AccountEntry.EntryType.RECEIPT,
        date=receipt.document_date,
        debit_account=asset.group.account_number,
        credit_account='152',
        amount=receipt.amount,
        description=(
            f'Оприбуткування ОЗ {asset.inventory_number} «{asset.name}». '
            f'Тип надходження: {receipt.get_receipt_type_display()}.'
        ),
        asset=asset,
        document_number=receipt.document_number,
        document_date=receipt.document_date,
        user=user,
    )
    entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# 2. Нарахування амортизації
# ---------------------------------------------------------------------------

def create_depreciation_entries(asset, depreciation_record, user=None, expense_account='92'):
    """
    Створює проводки при нарахуванні амортизації.

    Проводка:
        Дт <рахунок витрат> (23/91/92/93, за замовчуванням 92)
        Кт <рахунок зносу групи ОЗ> (наприклад, 131)
        на суму нарахованої амортизації.

    Args:
        asset: об'єкт Asset.
        depreciation_record: об'єкт DepreciationRecord (має поля amount,
                             period_year, period_month).
        user: користувач, який створює проводку.
        expense_account: рахунок витрат ('23', '91', '92', '93'),
                         за замовчуванням '92' (адміністративні витрати).

    Returns:
        list[AccountEntry] — список створених проводок.
    """
    from datetime import date

    entries = []

    period_date = date(
        depreciation_record.period_year,
        depreciation_record.period_month,
        1,
    )

    entry = _create_entry(
        entry_type=AccountEntry.EntryType.DEPRECIATION,
        date=period_date,
        debit_account=expense_account,
        credit_account=asset.group.depreciation_account,
        amount=depreciation_record.amount,
        description=(
            f'Нарахування амортизації ОЗ {asset.inventory_number} «{asset.name}» '
            f'за {depreciation_record.period_month:02d}.{depreciation_record.period_year}. '
            f'Метод: {depreciation_record.get_depreciation_method_display()}.'
        ),
        asset=asset,
        document_number='',
        document_date=period_date,
        user=user,
    )
    entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# 3. Вибуття основного засобу
# ---------------------------------------------------------------------------

def create_disposal_entries(asset, disposal, user=None):
    """
    Створює проводки при вибутті основного засобу.

    Проводки:
        1) Списання накопиченого зносу:
           Дт <рахунок зносу> (наприклад, 131)
           Кт <рахунок ОЗ>   (наприклад, 104)
           на суму накопиченого зносу.

        2) Списання залишкової вартості:
           Дт 976 (Списання необоротних активів)
           Кт <рахунок ОЗ>
           на суму залишкової вартості.

        3) Якщо продаж — визнання доходу:
           Дт 377 (Розрахунки з іншими дебіторами)
           Кт 746 (Інші доходи від звичайної діяльності)
           на суму продажу.

    Args:
        asset: об'єкт Asset.
        disposal: об'єкт AssetDisposal (має поля accumulated_depreciation_at_disposal,
                  book_value_at_disposal, disposal_type, sale_amount,
                  document_number, document_date).
        user: користувач, який створює проводку.

    Returns:
        list[AccountEntry] — список створених проводок.
    """
    entries = []
    account_oz = asset.group.account_number
    account_depreciation = asset.group.depreciation_account

    # 1) Списання накопиченого зносу
    if disposal.accumulated_depreciation_at_disposal > Decimal('0.00'):
        entry_depreciation = _create_entry(
            entry_type=AccountEntry.EntryType.DISPOSAL,
            date=disposal.document_date,
            debit_account=account_depreciation,
            credit_account=account_oz,
            amount=disposal.accumulated_depreciation_at_disposal,
            description=(
                f'Списання зносу при вибутті ОЗ {asset.inventory_number} '
                f'«{asset.name}». {disposal.get_disposal_type_display()}.'
            ),
            asset=asset,
            document_number=disposal.document_number,
            document_date=disposal.document_date,
            user=user,
        )
        entries.append(entry_depreciation)

    # 2) Списання залишкової вартості
    if disposal.book_value_at_disposal > Decimal('0.00'):
        entry_book_value = _create_entry(
            entry_type=AccountEntry.EntryType.DISPOSAL,
            date=disposal.document_date,
            debit_account='976',
            credit_account=account_oz,
            amount=disposal.book_value_at_disposal,
            description=(
                f'Списання залишкової вартості при вибутті ОЗ '
                f'{asset.inventory_number} «{asset.name}». '
                f'{disposal.get_disposal_type_display()}.'
            ),
            asset=asset,
            document_number=disposal.document_number,
            document_date=disposal.document_date,
            user=user,
        )
        entries.append(entry_book_value)

    # 3) Якщо продаж — дохід від реалізації
    if (
        disposal.disposal_type == 'sale'
        and disposal.sale_amount
        and disposal.sale_amount > Decimal('0.00')
    ):
        entry_sale = _create_entry(
            entry_type=AccountEntry.EntryType.DISPOSAL,
            date=disposal.document_date,
            debit_account='377',
            credit_account='746',
            amount=disposal.sale_amount,
            description=(
                f'Дохід від продажу ОЗ {asset.inventory_number} «{asset.name}». '
                f'Покупець: {disposal.reason}.'
            ),
            asset=asset,
            document_number=disposal.document_number,
            document_date=disposal.document_date,
            user=user,
        )
        entries.append(entry_sale)

    return entries


# ---------------------------------------------------------------------------
# 4. Переоцінка основного засобу
# ---------------------------------------------------------------------------

def create_revaluation_entries(asset, revaluation, user=None):
    """
    Створює проводки при переоцінці основного засобу.

    Проводки:
        Дооцінка (upward):
            Дт <рахунок ОЗ> (наприклад, 104)
            Кт 411 (Дооцінка основних засобів — капітал у дооцінках)
            на суму дооцінки.

        Уцінка (downward):
            Дт 975 (Уцінка необоротних активів)
            Кт <рахунок ОЗ>
            на суму уцінки.

    Args:
        asset: об'єкт Asset.
        revaluation: об'єкт AssetRevaluation (має поля revaluation_type,
                     revaluation_amount, date, document_number).
        user: користувач, який створює проводку.

    Returns:
        list[AccountEntry] — список створених проводок.
    """
    entries = []
    account_oz = asset.group.account_number
    amount = abs(revaluation.revaluation_amount)

    if revaluation.revaluation_type == 'upward':
        entry = _create_entry(
            entry_type=AccountEntry.EntryType.REVALUATION,
            date=revaluation.date,
            debit_account=account_oz,
            credit_account='411',
            amount=amount,
            description=(
                f'Дооцінка ОЗ {asset.inventory_number} «{asset.name}». '
                f'Справедлива вартість: {revaluation.fair_value} грн.'
            ),
            asset=asset,
            document_number=revaluation.document_number,
            document_date=revaluation.date,
            user=user,
        )
        entries.append(entry)
    elif revaluation.revaluation_type == 'downward':
        entry = _create_entry(
            entry_type=AccountEntry.EntryType.REVALUATION,
            date=revaluation.date,
            debit_account='975',
            credit_account=account_oz,
            amount=amount,
            description=(
                f'Уцінка ОЗ {asset.inventory_number} «{asset.name}». '
                f'Справедлива вартість: {revaluation.fair_value} грн.'
            ),
            asset=asset,
            document_number=revaluation.document_number,
            document_date=revaluation.date,
            user=user,
        )
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# 5. Поліпшення / ремонт основного засобу
# ---------------------------------------------------------------------------

def create_improvement_entries(asset, improvement, user=None):
    """
    Створює проводки при поліпшенні або ремонті основного засобу.

    Проводки:
        Якщо поліпшення збільшує первісну вартість (increases_value=True):
            Дт <рахунок ОЗ> (наприклад, 104)
            Кт 152 (Капітальні інвестиції)
            на суму поліпшення.

        Якщо ремонт відноситься на витрати (increases_value=False):
            Дт <рахунок витрат improvement.expense_account> (наприклад, 91)
            Кт 631 (Розрахунки з вітчизняними постачальниками)
            на суму ремонту.

    Args:
        asset: об'єкт Asset.
        improvement: об'єкт AssetImprovement (має поля increases_value,
                     amount, expense_account, document_number, date).
        user: користувач, який створює проводку.

    Returns:
        list[AccountEntry] — список створених проводок.
    """
    entries = []

    if improvement.increases_value:
        # Капіталізація: збільшення первісної вартості ОЗ
        entry = _create_entry(
            entry_type=AccountEntry.EntryType.IMPROVEMENT,
            date=improvement.date,
            debit_account=asset.group.account_number,
            credit_account='152',
            amount=improvement.amount,
            description=(
                f'Поліпшення ОЗ {asset.inventory_number} «{asset.name}». '
                f'{improvement.get_improvement_type_display()}: {improvement.description}.'
            ),
            asset=asset,
            document_number=improvement.document_number,
            document_date=improvement.date,
            user=user,
        )
        entries.append(entry)
    else:
        # Витрати періоду: ремонт на витрати
        entry = _create_entry(
            entry_type=AccountEntry.EntryType.IMPROVEMENT,
            date=improvement.date,
            debit_account=improvement.expense_account,
            credit_account='631',
            amount=improvement.amount,
            description=(
                f'Ремонт ОЗ {asset.inventory_number} «{asset.name}». '
                f'{improvement.get_improvement_type_display()}: {improvement.description}.'
            ),
            asset=asset,
            document_number=improvement.document_number,
            document_date=improvement.date,
            user=user,
        )
        entries.append(entry)

    return entries


# ---------------------------------------------------------------------------
# 6. Переміщення основного засобу
# ---------------------------------------------------------------------------

def create_transfer_entries(transfer, transfer_item, user=None):
    """
    Створює інформаційну проводку при переміщенні ОЗ.

    Переміщення всередині організації не змінює вартість ОЗ,
    тому проводка має довідковий характер:
        Дт <рахунок ОЗ>  Кт <рахунок ОЗ> (той самий)
        на суму залишкової вартості.
    """
    entries = []
    asset = transfer_item.asset
    account_oz = asset.group.account_number

    from_name = transfer.from_location.name if transfer.from_location else '—'
    to_name = transfer.to_location.name if transfer.to_location else '—'

    entry = _create_entry(
        entry_type=AccountEntry.EntryType.TRANSFER,
        date=transfer.document_date,
        debit_account=account_oz,
        credit_account=account_oz,
        amount=transfer_item.book_value,
        description=(
            f'Переміщення ОЗ {asset.inventory_number} «{asset.name}» '
            f'з «{from_name}» до «{to_name}».'
        ),
        asset=asset,
        document_number=transfer.document_number,
        document_date=transfer.document_date,
        user=user,
    )
    entries.append(entry)

    return entries
