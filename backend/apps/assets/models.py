from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


class AssetGroup(models.Model):
    """Група основних засобів згідно ПКУ ст. 138.3.3 та НП(С)БО 7."""

    code = models.CharField('Код групи', max_length=10, unique=True)
    name = models.CharField('Назва групи', max_length=255)
    min_useful_life_months = models.PositiveIntegerField(
        'Мінімальний строк корисного використання (міс.)',
        null=True,
        blank=True,
        help_text='Мінімальний строк згідно ПКУ. Null = не обмежено.',
    )
    account_number = models.CharField(
        'Рахунок обліку',
        max_length=10,
        help_text='Рахунок з Плану рахунків (10х)',
    )
    depreciation_account = models.CharField(
        'Рахунок зносу',
        max_length=10,
        default='131',
        help_text='Рахунок зносу (13х)',
    )

    class Meta:
        verbose_name = 'Група ОЗ'
        verbose_name_plural = 'Групи ОЗ'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class Location(models.Model):
    """Місцезнаходження — довідник."""
    name = models.CharField('Назва', max_length=500, unique=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Місцезнаходження'
        verbose_name_plural = 'Місцезнаходження'
        ordering = ['name']

    def __str__(self):
        return self.name


class Position(models.Model):
    """Посада — довідник."""
    name = models.CharField('Назва', max_length=255, unique=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Посада'
        verbose_name_plural = 'Посади'
        ordering = ['name']

    def __str__(self):
        return self.name


class ResponsiblePerson(models.Model):
    """Матеріально відповідальна особа (МВО) — довідник."""
    ipn = models.CharField('ІПН', max_length=10, unique=True)
    full_name = models.CharField('ПІП', max_length=255)
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsible_persons',
        verbose_name='Посада',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsible_persons',
        verbose_name='Місце розташування',
    )
    is_employee = models.BooleanField('Співробітник', default=False)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Матеріально відповідальна особа'
        verbose_name_plural = 'Матеріально відповідальні особи'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.position.name})' if self.position else self.full_name


class Asset(models.Model):
    """Основний засіб — інвентарний об'єкт."""

    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = 'straight_line', 'Прямолінійний'
        REDUCING_BALANCE = 'reducing_balance', 'Зменшення залишкової вартості'
        ACCELERATED_REDUCING = 'accelerated_reducing', 'Прискореного зменшення залишкової вартості'
        CUMULATIVE = 'cumulative', 'Кумулятивний'
        PRODUCTION = 'production', 'Виробничий'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'В експлуатації'
        DISPOSED = 'disposed', 'Списаний'
        CONSERVED = 'conserved', 'На консервації'

    organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        verbose_name='Організація',
    )
    inventory_number = models.CharField(
        'Інвентарний номер', max_length=50, unique=True
    )
    name = models.CharField('Назва', max_length=500)
    group = models.ForeignKey(
        AssetGroup,
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name='Група ОЗ',
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Вартісні характеристики
    initial_cost = models.DecimalField(
        'Первісна вартість, грн',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    residual_value = models.DecimalField(
        'Ліквідаційна вартість, грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    incoming_depreciation = models.DecimalField(
        'Вхідна амортизація (знос), грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Знос, нарахований до отримання ОЗ від іншої організації',
    )
    current_book_value = models.DecimalField(
        'Залишкова (балансова) вартість, грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    accumulated_depreciation = models.DecimalField(
        'Накопичений знос, грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    # Амортизація
    depreciation_method = models.CharField(
        'Метод амортизації',
        max_length=30,
        choices=DepreciationMethod.choices,
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    useful_life_months = models.PositiveIntegerField(
        'Строк корисного використання (міс.)',
    )
    # Для виробничого методу
    total_production_capacity = models.DecimalField(
        'Загальний обсяг продукції (одиниць)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Тільки для виробничого методу',
    )

    # Дати
    commissioning_date = models.DateField('Дата введення в експлуатацію')
    disposal_date = models.DateField('Дата вибуття', null=True, blank=True)
    depreciation_start_date = models.DateField(
        'Дата початку нарахування амортизації',
        help_text='Місяць, наступний за місяцем введення в експлуатацію',
    )

    # Додаткові ідентифікаційні поля
    quantity = models.PositiveIntegerField('Кількість', default=1)
    factory_number = models.CharField('Заводський номер', max_length=100, blank=True)
    passport_number = models.CharField('Номер паспорта', max_length=100, blank=True)
    manufacture_year = models.PositiveIntegerField('Рік випуску', null=True, blank=True)
    unit_of_measure = models.CharField('Одиниця виміру', max_length=20, default='шт.')
    depreciation_rate = models.DecimalField(
        'Норма амортизації (%)',
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Річний відсоток амортизації',
    )

    # Відповідальна особа та місце
    responsible_person = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        verbose_name='Матеріально відповідальна особа',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
        verbose_name='Місцезнаходження',
    )
    description = models.TextField('Опис / характеристики', blank=True)

    # Службові поля
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_assets',
        verbose_name='Створив',
    )
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)

    class Meta:
        verbose_name = 'Основний засіб'
        verbose_name_plural = 'Основні засоби'
        ordering = ['inventory_number']

    def __str__(self):
        return f'{self.inventory_number} — {self.name}'

    def clean(self):
        super().clean()
        errors = {}
        if self.depreciation_start_date and self.commissioning_date:
            if self.depreciation_start_date < self.commissioning_date:
                errors['depreciation_start_date'] = (
                    'Дата початку амортизації не може бути раніше дати введення в експлуатацію.'
                )
        if self.disposal_date and self.commissioning_date:
            if self.disposal_date < self.commissioning_date:
                errors['disposal_date'] = (
                    'Дата вибуття не може бути раніше дати введення в експлуатацію.'
                )
        if self.residual_value and self.initial_cost:
            if self.residual_value >= self.initial_cost:
                errors['residual_value'] = (
                    'Ліквідаційна вартість не може перевищувати первісну вартість.'
                )
        if self.incoming_depreciation and self.initial_cost:
            if self.incoming_depreciation > self.initial_cost:
                errors['incoming_depreciation'] = (
                    'Вхідна амортизація не може перевищувати первісну вартість.'
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.current_book_value or self.current_book_value == self.initial_cost:
            self.current_book_value = self.initial_cost - (self.incoming_depreciation or Decimal('0.00'))
        super().save(*args, **kwargs)


class AssetReceipt(models.Model):
    """Прихід (оприбуткування) основного засобу."""

    class ReceiptType(models.TextChoices):
        PURCHASE = 'purchase', 'Придбання'
        FREE_RECEIPT = 'free_receipt', 'Безоплатне отримання'
        CONTRIBUTION = 'contribution', 'Внесок до статутного капіталу'
        EXCHANGE = 'exchange', 'Обмін'
        SELF_MADE = 'self_made', 'Виготовлення власними силами'
        OTHER = 'other', 'Інше'

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='Основний засіб',
    )
    receipt_type = models.CharField(
        'Тип надходження',
        max_length=20,
        choices=ReceiptType.choices,
        default=ReceiptType.PURCHASE,
    )
    document_number = models.CharField('Номер документа', max_length=100)
    document_date = models.DateField('Дата документа')
    supplier = models.CharField('Постачальник / джерело', max_length=500, blank=True)
    supplier_organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receipts_as_supplier',
        verbose_name='Організація-постачальник',
    )
    amount = models.DecimalField(
        'Сума, грн',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    notes = models.TextField('Примітки', blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Прихід ОЗ'
        verbose_name_plural = 'Приходи ОЗ'
        ordering = ['-document_date']

    def __str__(self):
        return f'Прихід {self.document_number} — {self.asset}'


class AssetDisposal(models.Model):
    """Розхід (вибуття) основного засобу."""

    class DisposalType(models.TextChoices):
        SALE = 'sale', 'Продаж'
        LIQUIDATION = 'liquidation', 'Ліквідація'
        FREE_TRANSFER = 'free_transfer', 'Безоплатна передача'
        SHORTAGE = 'shortage', 'Нестача'
        OTHER = 'other', 'Інше'

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='disposals',
        verbose_name='Основний засіб',
    )
    disposal_type = models.CharField(
        'Тип вибуття',
        max_length=20,
        choices=DisposalType.choices,
    )
    document_number = models.CharField('Номер документа', max_length=100)
    document_date = models.DateField('Дата документа')
    reason = models.TextField('Причина вибуття')
    sale_amount = models.DecimalField(
        'Сума продажу, грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Заповнюється при продажу',
    )
    book_value_at_disposal = models.DecimalField(
        'Залишкова вартість на дату вибуття, грн',
        max_digits=15,
        decimal_places=2,
    )
    accumulated_depreciation_at_disposal = models.DecimalField(
        'Накопичений знос на дату вибуття, грн',
        max_digits=15,
        decimal_places=2,
    )
    notes = models.TextField('Примітки', blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вибуття ОЗ'
        verbose_name_plural = 'Вибуття ОЗ'
        ordering = ['-document_date']

    def __str__(self):
        return f'Вибуття {self.document_number} — {self.asset}'


class DepreciationRecord(models.Model):
    """Запис нарахування амортизації за місяць."""

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='depreciation_records',
        verbose_name='Основний засіб',
    )
    period_year = models.PositiveIntegerField('Рік')
    period_month = models.PositiveIntegerField('Місяць')
    depreciation_method = models.CharField(
        'Метод',
        max_length=30,
        choices=Asset.DepreciationMethod.choices,
    )
    amount = models.DecimalField(
        'Сума амортизації, грн',
        max_digits=15,
        decimal_places=2,
    )
    book_value_before = models.DecimalField(
        'Залишкова вартість до нарахування, грн',
        max_digits=15,
        decimal_places=2,
    )
    book_value_after = models.DecimalField(
        'Залишкова вартість після нарахування, грн',
        max_digits=15,
        decimal_places=2,
    )
    # Для виробничого методу
    production_volume = models.DecimalField(
        'Обсяг продукції за місяць',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_posted = models.BooleanField('Проведено', default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Нарахував',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Нарахування амортизації'
        verbose_name_plural = 'Нарахування амортизації'
        ordering = ['-period_year', '-period_month']
        unique_together = ['asset', 'period_year', 'period_month']

    def __str__(self):
        return f'{self.asset} — {self.period_month:02d}.{self.period_year} — {self.amount} грн'


class Inventory(models.Model):
    """Інвентаризація основних засобів."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Чернетка'
        IN_PROGRESS = 'in_progress', 'В процесі'
        COMPLETED = 'completed', 'Завершено'

    number = models.CharField('Номер інвентаризації', max_length=50, unique=True)
    date = models.DateField('Дата інвентаризації')
    order_number = models.CharField('Номер наказу', max_length=100)
    order_date = models.DateField('Дата наказу')
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories',
        verbose_name='Місце проведення',
    )
    notes = models.TextField('Примітки', blank=True)

    # МВО
    responsible_person = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventories_as_responsible',
        verbose_name='Матеріально відповідальна особа',
    )

    # Комісія
    commission_head = models.ForeignKey(
        ResponsiblePerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_inventories',
        verbose_name='Голова комісії',
    )
    commission_members = models.ManyToManyField(
        ResponsiblePerson,
        blank=True,
        related_name='inventories_as_member',
        verbose_name='Члени комісії',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inventories',
        verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Інвентаризація'
        verbose_name_plural = 'Інвентаризації'
        ordering = ['-date']

    def __str__(self):
        return f'Інвентаризація №{self.number} від {self.date}'


class InventoryItem(models.Model):
    """Рядок інвентаризаційного опису."""

    class Condition(models.TextChoices):
        GOOD = 'good', 'Справний'
        NEEDS_REPAIR = 'needs_repair', 'Потребує ремонту'
        UNUSABLE = 'unusable', 'Непридатний'

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Інвентаризація',
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='inventory_items',
        verbose_name='Основний засіб',
    )
    is_found = models.BooleanField('Фактична наявність', default=True)
    condition = models.CharField(
        'Стан',
        max_length=20,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    book_value = models.DecimalField(
        'Облікова вартість, грн',
        max_digits=15,
        decimal_places=2,
    )
    actual_value = models.DecimalField(
        'Фактична вартість, грн',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    difference = models.DecimalField(
        'Різниця, грн',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    notes = models.TextField('Примітки', blank=True)

    class Meta:
        verbose_name = 'Рядок інвентаризації'
        verbose_name_plural = 'Рядки інвентаризації'
        unique_together = ['inventory', 'asset']

    def __str__(self):
        status = 'Знайдено' if self.is_found else 'НЕСТАЧА'
        return f'{self.asset} — {status}'

    def save(self, *args, **kwargs):
        if self.actual_value is not None:
            self.difference = self.actual_value - self.book_value
        elif not self.is_found:
            self.difference = -self.book_value
        super().save(*args, **kwargs)


class Organization(models.Model):
    """Організація (юридична особа)."""
    name = models.CharField('Назва', max_length=500)
    short_name = models.CharField('Коротка назва', max_length=255, blank=True)
    edrpou = models.CharField('Код ЄДРПОУ', max_length=10, unique=True)
    address = models.TextField('Юридична адреса', blank=True)
    director = models.CharField('Директор', max_length=255, blank=True)
    accountant = models.CharField('Головний бухгалтер', max_length=255, blank=True)
    is_active = models.BooleanField('Активна', default=True)
    is_own = models.BooleanField(
        'Власна організація',
        default=False,
        help_text='Тільки одна організація може бути позначена як власна.',
    )

    class Meta:
        verbose_name = 'Організація'
        verbose_name_plural = 'Організації'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.is_own:
            Organization.objects.filter(is_own=True).exclude(pk=self.pk).update(is_own=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.short_name or self.name


class AccountEntry(models.Model):
    """Бухгалтерська проводка."""

    class EntryType(models.TextChoices):
        RECEIPT = 'receipt', 'Оприбуткування ОЗ'
        DEPRECIATION = 'depreciation', 'Нарахування амортизації'
        DISPOSAL = 'disposal', 'Вибуття ОЗ'
        REVALUATION = 'revaluation', 'Переоцінка'
        IMPROVEMENT = 'improvement', 'Поліпшення'
        REPAIR = 'repair', 'Ремонт'

    entry_type = models.CharField(
        'Тип операції', max_length=20, choices=EntryType.choices
    )
    date = models.DateField('Дата проводки')
    debit_account = models.CharField('Дебет рахунку', max_length=10)
    credit_account = models.CharField('Кредит рахунку', max_length=10)
    amount = models.DecimalField(
        'Сума, грн', max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    description = models.TextField('Опис операції')
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name='entries',
        verbose_name='Основний засіб',
    )
    document_number = models.CharField('Номер документа', max_length=100, blank=True)
    document_date = models.DateField('Дата документа', null=True, blank=True)
    is_posted = models.BooleanField('Проведено', default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Проводка'
        verbose_name_plural = 'Проводки'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.date} Дт {self.debit_account} Кт {self.credit_account} {self.amount} грн'


class AssetRevaluation(models.Model):
    """Переоцінка основного засобу згідно НП(С)БО 7 п.16-21."""

    class RevaluationType(models.TextChoices):
        UPWARD = 'upward', 'Дооцінка'
        DOWNWARD = 'downward', 'Уцінка'

    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name='revaluations',
        verbose_name='Основний засіб',
    )
    revaluation_type = models.CharField(
        'Тип переоцінки', max_length=10, choices=RevaluationType.choices
    )
    date = models.DateField('Дата переоцінки')
    document_number = models.CharField('Номер документа', max_length=100)

    # Вартість до переоцінки
    old_initial_cost = models.DecimalField(
        'Первісна вартість до переоцінки', max_digits=15, decimal_places=2
    )
    old_depreciation = models.DecimalField(
        'Знос до переоцінки', max_digits=15, decimal_places=2
    )
    old_book_value = models.DecimalField(
        'Залишкова вартість до переоцінки', max_digits=15, decimal_places=2
    )

    # Справедлива вартість
    fair_value = models.DecimalField(
        'Справедлива вартість', max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    # Вартість після переоцінки
    new_initial_cost = models.DecimalField(
        'Первісна вартість після переоцінки', max_digits=15, decimal_places=2
    )
    new_depreciation = models.DecimalField(
        'Знос після переоцінки', max_digits=15, decimal_places=2
    )
    new_book_value = models.DecimalField(
        'Залишкова вартість після переоцінки', max_digits=15, decimal_places=2
    )

    revaluation_amount = models.DecimalField(
        'Сума переоцінки', max_digits=15, decimal_places=2
    )
    notes = models.TextField('Примітки', blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Переоцінка'
        verbose_name_plural = 'Переоцінки'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_revaluation_type_display()} {self.asset} — {self.revaluation_amount} грн'


class AssetImprovement(models.Model):
    """Поліпшення / ремонт основного засобу."""

    class ImprovementType(models.TextChoices):
        CAPITAL = 'capital', 'Капітальний ремонт (поліпшення)'
        CURRENT = 'current', 'Поточний ремонт (витрати)'
        MODERNIZATION = 'modernization', 'Модернізація'
        RECONSTRUCTION = 'reconstruction', 'Реконструкція'

    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name='improvements',
        verbose_name='Основний засіб',
    )
    improvement_type = models.CharField(
        'Тип', max_length=20, choices=ImprovementType.choices
    )
    date = models.DateField('Дата')
    document_number = models.CharField('Номер документа', max_length=100)
    description = models.TextField('Опис робіт')
    amount = models.DecimalField(
        'Сума, грн', max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    contractor = models.CharField('Виконавець', max_length=500, blank=True)
    increases_value = models.BooleanField(
        'Збільшує первісну вартість',
        default=False,
        help_text='Капітальний ремонт та модернізація збільшують вартість ОЗ',
    )
    expense_account = models.CharField(
        'Рахунок витрат', max_length=10, default='91',
        help_text='Рахунок для списання витрат (91, 92, 93, 23)',
    )
    notes = models.TextField('Примітки', blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Створив',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Поліпшення / ремонт'
        verbose_name_plural = 'Поліпшення / ремонти'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_improvement_type_display()} {self.asset} — {self.amount} грн'


class AssetAttachment(models.Model):
    """Прикріплений файл до ОЗ (скани, фото, акти)."""

    class FileType(models.TextChoices):
        SCAN = 'scan', 'Скан документа'
        PHOTO = 'photo', 'Фотографія'
        ACT = 'act', 'Акт'
        INVOICE = 'invoice', 'Накладна'
        OTHER = 'other', 'Інше'

    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name='attachments',
        verbose_name='Основний засіб',
    )
    file = models.FileField('Файл', upload_to='attachments/%Y/%m/')
    file_type = models.CharField(
        'Тип файлу', max_length=20, choices=FileType.choices, default=FileType.OTHER
    )
    name = models.CharField('Назва', max_length=255)
    description = models.CharField('Опис', max_length=500, blank=True)
    file_size = models.PositiveIntegerField('Розмір (байт)', default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Завантажив',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вкладення'
        verbose_name_plural = 'Вкладення'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.name} ({self.asset.inventory_number})'

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """Журнал аудиту — логування всіх дій."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Створення'
        UPDATE = 'update', 'Зміна'
        DELETE = 'delete', 'Видалення'
        RECEIPT = 'receipt', 'Оприбуткування'
        DISPOSAL = 'disposal', 'Вибуття'
        DEPRECIATION = 'depreciation', 'Амортизація'
        REVALUATION = 'revaluation', 'Переоцінка'
        IMPROVEMENT = 'improvement', 'Поліпшення'
        INVENTORY = 'inventory', 'Інвентаризація'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name='Користувач',
    )
    action = models.CharField('Дія', max_length=20, choices=Action.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField('Об\'єкт', max_length=500)

    changes = models.JSONField('Зміни', default=dict, blank=True)
    ip_address = models.GenericIPAddressField('IP-адреса', null=True, blank=True)
    timestamp = models.DateTimeField('Час', auto_now_add=True)

    class Meta:
        verbose_name = 'Запис аудиту'
        verbose_name_plural = 'Журнал аудиту'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.timestamp} | {self.user} | {self.get_action_display()} | {self.object_repr}'


class Notification(models.Model):
    """Сповіщення для користувачів."""

    class NotificationType(models.TextChoices):
        DEPRECIATION_DONE = 'depreciation_done', 'Амортизація нарахована'
        DEPRECIATION_DUE = 'depreciation_due', 'Час нараховувати амортизацію'
        FULL_DEPRECIATION = 'full_depreciation', 'ОЗ повністю амортизовано'
        INVENTORY_DUE = 'inventory_due', 'Час проводити інвентаризацію'
        SHORTAGE_FOUND = 'shortage_found', 'Виявлено нестачу'
        HIGH_WEAR = 'high_wear', 'Високий знос ОЗ (>90%)'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Отримувач',
    )
    notification_type = models.CharField(
        'Тип', max_length=30, choices=NotificationType.choices
    )
    title = models.CharField('Заголовок', max_length=255)
    message = models.TextField('Повідомлення')
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name='Пов\'язаний ОЗ',
    )
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} → {self.recipient}'
