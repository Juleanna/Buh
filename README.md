# Система обліку основних засобів

Веб-додаток для обліку основних засобів відповідно до українського законодавства (НП(С)БО 7, ПКУ).

## Функціонал

- **Реєстр ОЗ** — облік основних засобів з інвентарними номерами
- **Прихід** — оприбуткування ОЗ (придбання, безоплатне отримання, внесок тощо)
- **Вибуття** — списання, продаж, ліквідація ОЗ
- **Амортизація** — 5 методів згідно НП(С)БО 7:
  - Прямолінійний
  - Зменшення залишкової вартості
  - Прискореного зменшення залишкової вартості
  - Кумулятивний
  - Виробничий
- **Інвентаризація** — створення, проведення, порівняння фактичних/облікових даних
- **PDF-документи** — інвентарна картка ОЗ-6, відомість амортизації, інвентаризаційний опис
- **Ролі** — адміністратор, бухгалтер, інвентаризатор
- **16 груп ОЗ** згідно ПКУ ст. 138.3.3 з мінімальними строками

## Технології

| Компонент | Технологія |
|-----------|-----------|
| Backend | Django 5.1 + DRF |
| Frontend | React 18 + TypeScript + Vite |
| UI | Ant Design 5 |
| БД | PostgreSQL 16 |
| Auth | JWT (simplejwt) |
| PDF | ReportLab |

## Швидкий старт

### 1. Запуск через Docker Compose

```bash
docker-compose up -d
```

### 2. Або ручний запуск

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Створити БД PostgreSQL: buh_assets
# Налаштувати змінні середовища або відредагувати config/settings.py

python manage.py makemigrations accounts assets
python manage.py migrate
python manage.py seed_asset_groups
python manage.py createsuperuser
python manage.py runserver
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Початкове налаштування

1. Відкрити http://localhost:5173
2. Увійти з обліковими даними суперкористувача
3. Довідник груп ОЗ заповнюється автоматично командою `seed_asset_groups`
4. Створити користувачів з потрібними ролями
5. Починати облік ОЗ

## API Endpoints

| Метод | URL | Опис |
|-------|-----|------|
| POST | /api/auth/login/ | Авторизація (JWT) |
| POST | /api/auth/refresh/ | Оновлення токена |
| GET | /api/auth/profile/ | Профіль |
| CRUD | /api/assets/groups/ | Групи ОЗ |
| CRUD | /api/assets/items/ | Основні засоби |
| GET | /api/assets/items/statistics/ | Статистика |
| CRUD | /api/assets/receipts/ | Приходи |
| CRUD | /api/assets/disposals/ | Вибуття |
| CRUD | /api/assets/depreciation/ | Нарахування амортизації |
| POST | /api/assets/depreciation/calculate/ | Масове нарахування |
| GET | /api/assets/depreciation/summary/ | Зведена відомість |
| CRUD | /api/assets/inventories/ | Інвентаризації |
| POST | /api/assets/inventories/{id}/populate/ | Заповнити ОЗ |
| POST | /api/assets/inventories/{id}/complete/ | Завершити |
| GET | /api/documents/asset-card/{id}/ | PDF картка ОЗ-6 |
| GET | /api/documents/depreciation-report/ | PDF відомість |
| GET | /api/documents/inventory-report/{id}/ | PDF опис інвентаризації |
| GET | /api/reports/dashboard/ | Дашборд |
