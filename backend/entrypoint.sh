#!/bin/bash
set -e

echo "=== Очікування на PostgreSQL ==="
while ! python -c "
import psycopg
conn = psycopg.connect(
    host='${POSTGRES_HOST:-localhost}',
    port=${POSTGRES_PORT:-5432},
    user='${POSTGRES_USER:-postgres}',
    password='${POSTGRES_PASSWORD:-postgres}',
    dbname='${POSTGRES_DB:-buh_assets}',
)
conn.close()
" 2>/dev/null; do
    echo "PostgreSQL ще не готовий — чекаю 2 сек..."
    sleep 2
done
echo "PostgreSQL доступний!"

echo "=== Застосування міграцій ==="
python manage.py migrate --noinput

echo "=== Збирання статичних файлів ==="
python manage.py collectstatic --noinput

echo "=== Створення суперюзера (якщо не існує) ==="
python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME:-admin}').exists():
    User.objects.create_superuser(
        username='${DJANGO_SUPERUSER_USERNAME:-admin}',
        password='${DJANGO_SUPERUSER_PASSWORD:-admin123}',
        role='admin',
        first_name='Адміністратор',
    )
    print('Суперюзер створено')
else:
    print('Суперюзер вже існує')
"

echo "=== Запуск: $@ ==="
exec "$@"
