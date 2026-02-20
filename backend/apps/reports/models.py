from django.db import models


class BackupRecord(models.Model):
    """Запис про створений бекап."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'В процесі'
        SUCCESS = 'success', 'Успішно'
        FAILED = 'failed', 'Помилка'

    filename = models.CharField('Назва файлу', max_length=255)
    file_size = models.BigIntegerField('Розмір (байт)', default=0)
    status = models.CharField(
        'Статус', max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    gdrive_file_id = models.CharField('Google Drive ID', max_length=255, blank=True)
    gdrive_link = models.URLField('Посилання GDrive', max_length=500, blank=True)
    error_message = models.TextField('Помилка', blank=True)
    is_auto = models.BooleanField('Автоматичний', default=False)
    created_at = models.DateTimeField('Створено', auto_now_add=True)

    class Meta:
        verbose_name = 'Резервна копія'
        verbose_name_plural = 'Резервні копії'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.filename} ({self.get_status_display()})'
