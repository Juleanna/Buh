from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Користувач системи обліку ОЗ з ролями."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Адміністратор'
        ACCOUNTANT = 'accountant', 'Бухгалтер'
        INVENTORY_MANAGER = 'inventory_manager', 'Інвентаризатор'

    role = models.CharField(
        'Роль',
        max_length=20,
        choices=Role.choices,
        default=Role.ACCOUNTANT,
    )
    patronymic = models.CharField('По батькові', max_length=150, blank=True)
    position = models.CharField('Посада', max_length=255, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.get_full_name() or self.username

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join(p for p in parts if p)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    @property
    def is_inventory_manager(self):
        return self.role == self.Role.INVENTORY_MANAGER
