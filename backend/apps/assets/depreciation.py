"""
Розрахунок амортизації за 5 методами відповідно до НП(С)БО 7.

Методи:
1. Прямолінійний — рівномірно протягом строку корисного використання
2. Зменшення залишкової вартості — фіксований % від залишкової вартості
3. Прискореного зменшення залишкової вартості — подвоєна норма прямолінійного
4. Кумулятивний — сума чисел років (кумулятивний коефіцієнт)
5. Виробничий — пропорційно обсягу виробленої продукції
"""
from decimal import Decimal, ROUND_HALF_UP


def calc_straight_line(initial_cost, residual_value, useful_life_months,
                       incoming_depreciation=Decimal('0.00')):
    """
    1. Прямолінійний метод.
    Амортизація = (Первісна вартість - Ліквідаційна вартість - Вхідна амортизація) / Строк (міс.)

    При наявності вхідної амортизації «Строк» — це залишковий строк
    корисного використання (П(С)БО 7, п. 23).
    """
    if useful_life_months <= 0:
        return Decimal('0.00')
    depreciable_amount = initial_cost - residual_value - incoming_depreciation
    if depreciable_amount <= 0:
        return Decimal('0.00')
    monthly = depreciable_amount / Decimal(useful_life_months)
    return monthly.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calc_reducing_balance(initial_cost, residual_value, useful_life_months, current_book_value):
    """
    2. Метод зменшення залишкової вартості.
    Річна норма = 1 - (Лікв. вартість / Первісна вартість) ^ (1 / Строк у роках)
    Місячна амортизація = Залишкова вартість * Річна норма / 12
    """
    if useful_life_months <= 0 or initial_cost <= 0:
        return Decimal('0.00')

    useful_life_years = Decimal(useful_life_months) / Decimal('12')

    if residual_value <= 0:
        # Якщо ліквідаційна = 0, використовуємо прямолінійний
        return calc_straight_line(initial_cost, residual_value, useful_life_months)

    ratio = residual_value / initial_cost
    # n-й корінь: ratio ^ (1/n)
    annual_rate = Decimal('1') - Decimal(float(ratio) ** (1.0 / float(useful_life_years)))

    monthly = current_book_value * annual_rate / Decimal('12')
    return monthly.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calc_accelerated_reducing(useful_life_months, current_book_value):
    """
    3. Метод прискореного зменшення залишкової вартості.
    Річна норма = 2 / Строк корисного використання (у роках)
    Місячна амортизація = Залишкова вартість * Річна норма / 12
    """
    if useful_life_months <= 0:
        return Decimal('0.00')

    useful_life_years = Decimal(useful_life_months) / Decimal('12')
    annual_rate = Decimal('2') / useful_life_years

    monthly = current_book_value * annual_rate / Decimal('12')
    return monthly.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calc_cumulative(initial_cost, residual_value, useful_life_months, months_used,
                    incoming_depreciation=Decimal('0.00')):
    """
    4. Кумулятивний метод (сума чисел років).
    Кумулятивний коефіцієнт = Кількість років, що залишається / Сума чисел років
    Річна амортизація = (Первісна - Ліквідаційна - Вхідна амортизація) * Кумулятивний коефіцієнт
    Місячна = Річна / 12
    """
    if useful_life_months <= 0:
        return Decimal('0.00')

    useful_life_years = useful_life_months // 12
    if useful_life_years <= 0:
        useful_life_years = 1

    current_year = months_used // 12 + 1  # Поточний рік використання
    remaining_years = useful_life_years - current_year + 1

    if remaining_years <= 0:
        return Decimal('0.00')

    # Сума чисел років: 1 + 2 + ... + n = n*(n+1)/2
    sum_of_years = useful_life_years * (useful_life_years + 1) // 2

    depreciable_amount = initial_cost - residual_value - incoming_depreciation
    if depreciable_amount <= 0:
        return Decimal('0.00')
    cumulative_coefficient = Decimal(remaining_years) / Decimal(sum_of_years)
    annual = depreciable_amount * cumulative_coefficient
    monthly = annual / Decimal('12')

    return monthly.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calc_production(initial_cost, residual_value, total_capacity, monthly_volume,
                    incoming_depreciation=Decimal('0.00')):
    """
    5. Виробничий метод.
    Амортизація = (Первісна - Ліквідаційна - Вхідна амортизація) / Загальний обсяг * Обсяг за місяць
    """
    if not total_capacity or total_capacity <= 0 or not monthly_volume:
        return Decimal('0.00')

    depreciable_amount = initial_cost - residual_value - incoming_depreciation
    if depreciable_amount <= 0:
        return Decimal('0.00')
    rate_per_unit = depreciable_amount / total_capacity
    monthly = rate_per_unit * monthly_volume

    return monthly.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_monthly_depreciation(asset, production_volume=None, months_used=None):
    """
    Розрахунок місячної амортизації для об'єкта ОЗ за обраним методом.

    Args:
        asset: об'єкт Asset
        production_volume: обсяг продукції за місяць (для виробничого методу)
        months_used: кількість місяців використання (для кумулятивного)

    Returns:
        Decimal — сума амортизації за місяць
    """
    method = asset.depreciation_method
    incoming = getattr(asset, 'incoming_depreciation', Decimal('0.00')) or Decimal('0.00')

    # Перевірка: не амортизуємо нижче ліквідаційної вартості
    if asset.current_book_value <= asset.residual_value:
        return Decimal('0.00')

    if method == 'straight_line':
        amount = calc_straight_line(
            asset.initial_cost,
            asset.residual_value,
            asset.useful_life_months,
            incoming,
        )
    elif method == 'reducing_balance':
        amount = calc_reducing_balance(
            asset.initial_cost,
            asset.residual_value,
            asset.useful_life_months,
            asset.current_book_value,
        )
    elif method == 'accelerated_reducing':
        amount = calc_accelerated_reducing(
            asset.useful_life_months,
            asset.current_book_value,
        )
    elif method == 'cumulative':
        if months_used is None:
            from django.utils import timezone
            today = timezone.now().date()
            delta = (today.year - asset.depreciation_start_date.year) * 12 + (
                today.month - asset.depreciation_start_date.month
            )
            months_used = max(delta, 0)
        amount = calc_cumulative(
            asset.initial_cost,
            asset.residual_value,
            asset.useful_life_months,
            months_used,
            incoming,
        )
    elif method == 'production':
        amount = calc_production(
            asset.initial_cost,
            asset.residual_value,
            asset.total_production_capacity,
            production_volume or Decimal('0'),
            incoming,
        )
    else:
        amount = Decimal('0.00')

    # Не амортизуємо нижче ліквідаційної вартості
    max_amount = asset.current_book_value - asset.residual_value
    if amount > max_amount:
        amount = max_amount

    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
