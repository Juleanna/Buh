<p align="center">
  <h1 align="center">🏛️ Система обліку основних засобів</h1>
  <p align="center">
    <em>Повнофункціональний веб-додаток для обліку основних засобів відповідно до українського законодавства</em>
  </p>
  <p align="center">
    <strong>НП(С)БО 7</strong> · <strong>ПКУ ст. 138.3.3</strong> · <strong>Наказ Мінфін №572</strong>
  </p>
</p>

---

## 📑 Зміст

- [✨ Можливості](#-можливості)
- [🛠️ Технології](#️-технології)
- [📁 Структура проєкту](#-структура-проєкту)
- [🚀 Швидкий старт](#-швидкий-старт)
- [⚙️ Змінні середовища](#️-змінні-середовища)
- [🗄️ Моделі бази даних](#️-моделі-бази-даних)
- [🌐 API довідник](#-api-довідник)
- [📄 Типи документів](#-типи-документів)
- [📉 Методи амортизації](#-методи-амортизації)
- [👥 Ролі та дозволи](#-ролі-та-дозволи)
- [⏰ Celery задачі](#-celery-задачі)
- [🧑‍💻 Розробка](#-розробка)
- [📖 Документація](#-документація)

---

## ✨ Можливості

### 📋 Облік основних засобів
| Функція | Опис |
|---------|------|
| 🏗️ **Реєстр ОЗ** | Повний облік з інвентарними номерами, групами, МВО, місцезнаходженням |
| 📥 **Прихід (ОЗ-1)** | Оприбуткування: придбання, безоплатне отримання, внесок, обмін, самостійне виготовлення |
| 📤 **Вибуття (ОЗ-3/ОЗ-4)** | Списання, продаж, ліквідація, безоплатна передача, нестача |
| 📉 **Амортизація** | 5 методів згідно НП(С)БО 7 з автоматичним нарахуванням |
| 📦 **Інвентаризація** | Створення, проведення, виявлення розбіжностей, комісія |
| 💰 **Переоцінка** | Дооцінка та уцінка з перерахунком коефіцієнтів |
| 🔧 **Поліпшення** | Капремонт, поточний ремонт, модернізація, реконструкція |

### 📄 Документи та звіти
| Документ | Форма | Формати |
|----------|-------|---------|
| 📋 Інвентарна картка | ОЗ-6 | PDF + Excel |
| 📥 Акт приймання-передачі | ОЗ-1 | PDF + Excel |
| 📤 Акт списання ОЗ | ОЗ-3 | PDF + Excel |
| 🚗 Акт списання автотранспорту | ОЗ-4 | PDF + Excel |
| 📉 Відомість амортизації | — | PDF + Excel |
| 📦 Інвентаризаційний опис | Наказ №572 | PDF + Excel |
| 📒 Журнал проводок | — | PDF + Excel |
| 📊 Оборотна відомість | — | PDF + Excel |

### 🔧 Системні можливості
| Функція | Опис |
|---------|------|
| 🔐 **JWT авторизація** | Access-токен 8 годин, Refresh 7 днів |
| 👥 **3 ролі** | Адміністратор, Бухгалтер, Інвентаризатор |
| 📝 **Журнал аудиту** | Логування всіх операцій з IP-адресою |
| 🔔 **Сповіщення** | Нагадування про амортизацію, знос >90%, інвентаризацію |
| 📊 **Дашборд** | Статистика, графіки за групами, останні операції |
| 🏷️ **QR-коди** | Генерація поодинці та масова (для інвентарних бирок) |
| 📥📤 **Імпорт/Експорт** | Excel-файли для масового завантаження ОЗ |
| 📒 **Бухгалтерські проводки** | Автоматичне формування Дт-Кт записів |
| 🏢 **Довідники** | Організації, локації, МВО, групи ОЗ |
| ⏰ **Celery задачі** | Автонарахування амортизації, нагадування |

---

## 🛠️ Технології

| Компонент | Технологія | Версія |
|-----------|------------|--------|
| 🐍 Backend | Django + Django REST Framework | 5.1 + 3.15 |
| ⚛️ Frontend | React + TypeScript + Vite | 18.3 + 5.6 + 6.0 |
| 🎨 UI бібліотека | Ant Design | 5.22 |
| 🗄️ База даних | PostgreSQL | 16 |
| 🔐 Авторизація | JWT (simplejwt) | 5.4 |
| 📄 PDF генерація | ReportLab | 4.2.5 |
| 📊 Excel генерація | openpyxl | 3.1.5 |
| 📦 Стан (frontend) | Zustand | 5.0 |
| 🗺️ Маршрутизація | React Router | 6.28 |
| 🌐 HTTP клієнт | Axios | 1.7 |
| ⏰ Черги задач | Celery + Redis | 5.4 |
| 🐳 Контейнеризація | Docker Compose | — |
| 🏷️ QR-коди | qrcode + Pillow | 8.0 |

---

## 📁 Структура проєкту

```
📦 Buh/
├── 📂 backend/                          # 🐍 Django-додаток
│   ├── 📂 config/                       # ⚙️ Конфігурація проєкту
│   │   ├── settings.py                  #    Основні налаштування
│   │   ├── urls.py                      #    Маршрутизація URL
│   │   ├── celery.py                    #    Конфігурація Celery
│   │   └── wsgi.py                      #    WSGI точка входу
│   ├── 📂 apps/
│   │   ├── 📂 accounts/                 # 👤 Користувачі та авторизація
│   │   │   ├── models.py                #    Модель User з ролями
│   │   │   ├── views.py                 #    Login, Register, Profile
│   │   │   └── serializers.py           #    Серіалізатори
│   │   ├── 📂 assets/                   # 🏗️ Основна бізнес-логіка
│   │   │   ├── models.py                #    17 моделей (820+ рядків)
│   │   │   ├── views.py                 #    16 ViewSet-ів
│   │   │   ├── serializers.py           #    Серіалізатори
│   │   │   ├── depreciation.py          #    Розрахунок амортизації
│   │   │   ├── entries.py               #    Формування проводок
│   │   │   ├── tasks.py                 #    Celery задачі
│   │   │   ├── audit.py                 #    Аудит логування
│   │   │   ├── notifications.py         #    Сповіщення
│   │   │   └── qr_excel.py              #    QR-коди, Excel імпорт/експорт
│   │   ├── 📂 documents/                # 📄 Генерація PDF/Excel
│   │   │   ├── views.py                 #    8 типів документів (3500+ рядків)
│   │   │   └── excel_utils.py           #    Утиліти для Excel
│   │   └── 📂 reports/                  # 📊 Аналітика та звіти
│   │       └── views.py                 #    Дашборд, зведені звіти
│   ├── requirements.txt                 # 📋 Python залежності
│   └── manage.py                        # 🔧 Django CLI
├── 📂 frontend/                         # ⚛️ React-додаток
│   ├── 📂 src/
│   │   ├── 📂 pages/                    # 📄 21 сторінка
│   │   │   ├── LoginPage.tsx            #    🔐 Авторизація
│   │   │   ├── DashboardPage.tsx        #    📊 Головна / Дашборд
│   │   │   ├── AssetsPage.tsx           #    📋 Реєстр ОЗ
│   │   │   ├── AssetDetailPage.tsx      #    📄 Картка ОЗ
│   │   │   ├── GroupsPage.tsx           #    📁 Групи ОЗ
│   │   │   ├── LocationsPage.tsx        #    📍 Місцезнаходження
│   │   │   ├── ResponsiblePersonsPage   #    👤 МВО
│   │   │   ├── OrganizationsPage.tsx    #    🏢 Організації
│   │   │   ├── ReceiptsPage.tsx         #    📥 Прихід ОЗ
│   │   │   ├── DisposalsPage.tsx        #    📤 Вибуття ОЗ
│   │   │   ├── DepreciationPage.tsx     #    📉 Амортизація
│   │   │   ├── InventoriesPage.tsx      #    📦 Інвентаризації
│   │   │   ├── InventoryDetailPage.tsx  #    📦 Деталі інвентаризації
│   │   │   ├── RevaluationsPage.tsx     #    💰 Переоцінки
│   │   │   ├── ImprovementsPage.tsx     #    🔧 Поліпшення
│   │   │   ├── EntriesPage.tsx          #    📒 Проводки
│   │   │   ├── TurnoverReportPage.tsx   #    📊 Оборотна відомість
│   │   │   ├── AuditLogPage.tsx         #    📝 Журнал аудиту
│   │   │   ├── NotificationsPage.tsx    #    🔔 Сповіщення
│   │   │   ├── UsersPage.tsx            #    👥 Управління користувачами
│   │   │   └── ProfilePage.tsx          #    ⚙️ Профіль
│   │   ├── 📂 components/               # 🧩 Компоненти
│   │   │   ├── AppLayout.tsx            #    Головний layout + меню
│   │   │   └── ExportButton.tsx         #    Кнопки PDF/Excel експорту
│   │   ├── 📂 store/                    # 🗄️ Zustand
│   │   │   └── authStore.ts             #    Стан авторизації
│   │   ├── 📂 api/                      # 🌐 API клієнт
│   │   │   └── client.ts               #    Axios з JWT інтерцепторами
│   │   ├── 📂 utils/                    # 🔧 Утиліти
│   │   │   ├── globalMessage.tsx        #    Глобальний antd message
│   │   │   └── downloadPdf.ts           #    Завантаження PDF/Excel
│   │   └── types.ts                     # 📝 TypeScript типи
│   ├── package.json                     # 📋 NPM залежності
│   └── vite.config.ts                   # ⚙️ Конфігурація Vite
├── 📂 docs/                             # 📖 Документація
│   ├── USER_GUIDE.md                    #    Інструкція користувача
│   └── INSTALLATION.md                  #    Інструкція по встановленню
├── docker-compose.yml                   # 🐳 Docker Compose
└── README.md                            # 📄 Цей файл
```

---

## 🚀 Швидкий старт

### 🐳 Варіант 1: Docker Compose (рекомендовано)

```bash
# 1. Клонувати репозиторій
git clone <url> && cd Buh

# 2. Запустити всі сервіси
docker-compose up -d

# 3. Виконати міграції та створити початкові дані
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py seed_asset_groups
docker-compose exec backend python manage.py createsuperuser

# 4. Відкрити http://localhost:5173
```

### 💻 Варіант 2: Ручна установка

#### 🐍 Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Створити БД PostgreSQL "buh_assets"
# Скопіювати .env.example → .env та налаштувати

python manage.py migrate
python manage.py seed_asset_groups    # 16 груп ОЗ згідно ПКУ
python manage.py createsuperuser
python manage.py runserver
```

#### ⚛️ Frontend

```bash
cd frontend
npm install
npm run dev
```

#### 🔗 Результат

| Сервіс | URL |
|--------|-----|
| 🌐 Frontend | http://localhost:5173 |
| 🐍 Backend API | http://localhost:8000/api/ |
| 🗄️ Django Admin | http://localhost:8000/admin/ |

> 📖 **Детальна інструкція** для різних ОС → [docs/INSTALLATION.md](docs/INSTALLATION.md)

---

## ⚙️ Змінні середовища

Файл `backend/.env`:

| Змінна | Опис | Приклад |
|--------|------|---------|
| `DJANGO_SECRET_KEY` | Секретний ключ Django | `django-insecure-xxx` |
| `DEBUG` | Режим відладки | `True` |
| `POSTGRES_DB` | Назва бази даних | `buh_assets` |
| `POSTGRES_USER` | Користувач PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `your_password` |
| `POSTGRES_HOST` | Хост бази даних | `localhost` |
| `POSTGRES_PORT` | Порт бази даних | `5432` |
| `CORS_ORIGINS` | Дозволені CORS-джерела | `http://localhost:5173` |
| `CELERY_BROKER_URL` | URL брокера Celery | `redis://localhost:6379/0` |

---

## 🗄️ Моделі бази даних

Система має **17 моделей** у додатку `assets`:

### 🔵 Основні сутності

| Модель | Опис | Ключові поля |
|--------|------|-------------|
| 🏗️ `Asset` | Основний засіб | inventory_number, name, group, initial_cost, current_book_value, depreciation_method, useful_life_months, status |
| 📥 `AssetReceipt` | Прихід ОЗ | asset, receipt_type, document_number, amount, supplier |
| 📤 `AssetDisposal` | Вибуття ОЗ | asset, disposal_type, document_number, reason, sale_amount, book_value_at_disposal |
| 📉 `DepreciationRecord` | Запис амортизації | asset, period_year, period_month, amount, method, book_value_before/after |
| 💰 `AssetRevaluation` | Переоцінка | asset, fair_value, revaluation_type, old/new_initial_cost, old/new_book_value |
| 🔧 `AssetImprovement` | Поліпшення | asset, improvement_type, amount, increases_value |

### 📦 Інвентаризація

| Модель | Опис | Ключові поля |
|--------|------|-------------|
| 📦 `Inventory` | Сеанс інвентаризації | number, date, status, location, commission_head, commission_members |
| 📋 `InventoryItem` | Рядок інвентаризації | inventory, asset, is_found, condition, book_value, actual_value, difference |

### 📚 Довідники

| Модель | Опис | Ключові поля |
|--------|------|-------------|
| 📁 `AssetGroup` | Група ОЗ (16 груп) | code, name, min_useful_life_months, account_number, depreciation_account |
| 📍 `Location` | Місцезнаходження | name, is_active |
| 👤 `ResponsiblePerson` | МВО | full_name, position, ipn, location |
| 🏢 `Organization` | Організація | name, edrpou, address, director, accountant |

### 🔧 Системні

| Модель | Опис | Ключові поля |
|--------|------|-------------|
| 👤 `User` | Користувач | username, role (admin/accountant/inventory_manager) |
| 📒 `AccountEntry` | Бухгалтерська проводка | entry_type, debit_account, credit_account, amount, asset |
| 📎 `AssetAttachment` | Вкладення | asset, file, file_type |
| 📝 `AuditLog` | Журнал аудиту | user, action, changes (JSON), ip_address |
| 🔔 `Notification` | Сповіщення | recipient, notification_type, title, message, is_read |

---

## 🌐 API довідник

Базовий URL: `http://localhost:8000/api/`

### 🔐 Авторизація (`/api/auth/`)

| Метод | Endpoint | Опис |
|-------|----------|------|
| `POST` | `/auth/login/` | 🔑 Отримання JWT токена |
| `POST` | `/auth/refresh/` | 🔄 Оновлення Access-токена |
| `POST` | `/auth/register/` | ➕ Реєстрація (тільки admin) |
| `GET` `PUT` | `/auth/profile/` | 👤 Профіль користувача |
| `PUT` | `/auth/change-password/` | 🔒 Зміна пароля |
| `CRUD` | `/auth/users/` | 👥 Управління користувачами |

### 🏗️ Основні засоби (`/api/assets/`)

| Метод | Endpoint | Опис |
|-------|----------|------|
| `CRUD` | `/assets/items/` | 📋 Реєстр ОЗ |
| `GET` | `/assets/items/statistics/` | 📊 Статистика |
| `GET` | `/assets/items/lookup/?inventory_number=` | 🔍 Пошук за інв. номером |
| `CRUD` | `/assets/groups/` | 📁 Групи ОЗ |
| `CRUD` | `/assets/locations/` | 📍 Місцезнаходження |
| `CRUD` | `/assets/responsible-persons/` | 👤 МВО |
| `CRUD` | `/assets/organizations/` | 🏢 Організації |
| `CRUD` | `/assets/receipts/` | 📥 Приходи |
| `CRUD` | `/assets/disposals/` | 📤 Вибуття |
| `CRUD` | `/assets/revaluations/` | 💰 Переоцінки |
| `CRUD` | `/assets/improvements/` | 🔧 Поліпшення |
| `CRUD` | `/assets/attachments/` | 📎 Вкладення |

### 📉 Амортизація

| Метод | Endpoint | Опис |
|-------|----------|------|
| `CRUD` | `/assets/depreciation/` | 📉 Записи амортизації |
| `POST` | `/assets/depreciation/calculate/` | ⚡ Масове нарахування (рік, місяць) |
| `GET` | `/assets/depreciation/summary/` | 📊 Зведена відомість |

### 📦 Інвентаризація

| Метод | Endpoint | Опис |
|-------|----------|------|
| `CRUD` | `/assets/inventories/` | 📦 Сеанси інвентаризації |
| `POST` | `/assets/inventories/{id}/populate/` | ⚡ Заповнити активами |
| `POST` | `/assets/inventories/{id}/complete/` | ✅ Завершити інвентаризацію |
| `CRUD` | `/assets/inventory-items/` | 📋 Рядки інвентаризації |

### 📒 Проводки та облік

| Метод | Endpoint | Опис |
|-------|----------|------|
| `CRUD` | `/assets/entries/` | 📒 Бухгалтерські проводки |
| `GET` | `/assets/entries/journal/` | 📖 Журнал проводок |

### 🔔 Сповіщення

| Метод | Endpoint | Опис |
|-------|----------|------|
| `GET` | `/assets/notifications/` | 🔔 Список сповіщень |
| `GET` | `/assets/notifications/unread_count/` | 🔢 Кількість непрочитаних |
| `POST` | `/assets/notifications/{id}/mark_read/` | ✅ Позначити прочитаним |
| `POST` | `/assets/notifications/mark_all_read/` | ✅ Позначити всі |

### 🏷️ QR-коди та Excel

| Метод | Endpoint | Опис |
|-------|----------|------|
| `GET/POST` | `/assets/items/qr/` | 🏷️ QR-код для одного ОЗ |
| `POST` | `/assets/qr/bulk/` | 🏷️ Масова генерація QR-кодів |
| `GET` | `/assets/export/excel/` | 📊 Експорт реєстру в Excel |
| `POST` | `/assets/import/excel/` | 📥 Імпорт ОЗ з Excel |

### 📄 Документи (`/api/documents/`)

> 💡 Всі документи підтримують `?export=xlsx` для Excel-формату

| Метод | Endpoint | Форма | Опис |
|-------|----------|-------|------|
| `GET` | `/documents/asset/{id}/card/` | ОЗ-6 | 📋 Інвентарна картка |
| `GET` | `/documents/receipt/{id}/act/` | ОЗ-1 | 📥 Акт приймання-передачі |
| `GET` | `/documents/disposal/{id}/act/` | ОЗ-3 | 📤 Акт списання ОЗ |
| `GET` | `/documents/disposal/{id}/vehicle-act/` | ОЗ-4 | 🚗 Акт списання автотранспорту |
| `GET` | `/documents/depreciation-report/` | — | 📉 Відомість амортизації |
| `GET` | `/documents/inventory/{id}/report/` | №572 | 📦 Інвентаризаційний опис |
| `GET` | `/documents/entries-report/` | — | 📒 Журнал проводок |
| `GET` | `/documents/turnover-statement/` | — | 📊 Оборотна відомість |

### 📊 Звіти (`/api/reports/`)

| Метод | Endpoint | Опис |
|-------|----------|------|
| `GET` | `/reports/dashboard/` | 📊 Дані дашборду |
| `GET` | `/reports/asset-summary/` | 📋 Зведений звіт по ОЗ |
| `GET` | `/reports/turnover-statement/` | 📊 Оборотна відомість (дані) |

---

## 📄 Типи документів

### 📋 ОЗ-6 — Інвентарна картка обліку основних засобів
Містить повну інформацію про ОЗ: реквізити організації, ЄДРПОУ, інвентарний номер, характеристики, вартісні дані, дані про переміщення та амортизацію.

### 📥 ОЗ-1 — Акт приймання-передачі основних засобів
Оформлює надходження ОЗ. Включає: тип надходження, постачальника, характеристики об'єкта, вартісні дані, підписи (Здав / Прийняв / Гол. бухгалтер).

### 📤 ОЗ-3 — Акт списання основних засобів
Оформлює вибуття ОЗ. Включає: фінансові дані на дату списання, причину, висновок комісії, підписи комісії та керівництва.

### 🚗 ОЗ-4 — Акт списання автотранспортних засобів
Спеціалізована форма для транспорту. Додатково: VIN-код, номер двигуна/шасі/кузова, пробіг, результати списання.

### 📉 Відомість амортизації
Зведена таблиця нарахованої амортизації за період з деталізацією по кожному ОЗ.

### 📦 Інвентаризаційний опис (Наказ Мінфін №572)
16-колонкова таблиця з фактичними та обліковими даними, підписами комісії, МВО, розпискою.

### 📒 Журнал проводок
Хронологічний перелік бухгалтерських записів: дата, Дт рахунок, Кт рахунок, сума, опис.

### 📊 Оборотна відомість
Залишки на початок періоду, дебетовий та кредитовий оборот, залишки на кінець.

---

## 📉 Методи амортизації

Згідно з **НП(С)БО 7 «Основні засоби»**, п. 26:

| # | Метод | Формула | Опис |
|---|-------|---------|------|
| 1️⃣ | **Прямолінійний** | `(ПВ - ЛВ) / Строк` | Рівномірне щомісячне нарахування |
| 2️⃣ | **Зменшення залишкової вартості** | `ЗВ × Норма%` | Норма = 1 - ⁿ√(ЛВ/ПВ) |
| 3️⃣ | **Прискореного зменшення** | `ЗВ × (2 / Строк)` | Подвійна норма від залишку |
| 4️⃣ | **Кумулятивний** | `(ПВ - ЛВ) × Кк` | Кк = залишок років / сума років |
| 5️⃣ | **Виробничий** | `(ПВ - ЛВ) × (Обсяг / Потужність)` | Пропорційно обсягу продукції |

> **ПВ** — первісна вартість, **ЛВ** — ліквідаційна вартість, **ЗВ** — залишкова вартість

---

## 👥 Ролі та дозволи

| Дозвіл | 🔴 Адміністратор | 🟡 Бухгалтер | 🟢 Інвентаризатор |
|--------|:-:|:-:|:-:|
| Управління користувачами | ✅ | ❌ | ❌ |
| Перегляд дашборду | ✅ | ✅ | ✅ |
| CRUD основних засобів | ✅ | ✅ | ❌ |
| Прихід / Вибуття | ✅ | ✅ | ❌ |
| Нарахування амортизації | ✅ | ✅ | ❌ |
| Переоцінки / Поліпшення | ✅ | ✅ | ❌ |
| Бухгалтерські проводки | ✅ | ✅ | ❌ |
| Проведення інвентаризації | ✅ | ✅ | ✅ |
| Генерація документів | ✅ | ✅ | ✅ |
| Журнал аудиту | ✅ | ✅ | ❌ |

---

## ⏰ Celery задачі

| Задача | Розклад | Опис |
|--------|---------|------|
| `auto_calculate_depreciation` | Вручну або щомісяця | ⚡ Масове нарахування амортизації |
| `check_high_wear_assets` | Щоденно | ⚠️ Сповіщення при зносі >90% |
| `check_full_depreciation` | Щоденно | 📢 Сповіщення при повній амортизації |
| `send_depreciation_reminder` | 1 числа кожного місяця | 📧 Нагадування про нарахування |

Для роботи Celery потрібен **Redis**:

```bash
# Запуск worker
celery -A config worker -l info

# Запуск планувальника
celery -A config beat -l info
```

---

## 🧑‍💻 Розробка

### 🔧 Корисні команди

```bash
# 🐍 Backend
python manage.py makemigrations    # Створити міграції
python manage.py migrate           # Застосувати міграції
python manage.py seed_asset_groups # Заповнити 16 груп ОЗ
python manage.py createsuperuser   # Створити суперкористувача
python manage.py runserver         # Запустити сервер розробки

# ⚛️ Frontend
npm run dev                        # Запустити dev-сервер
npm run build                      # Збірка production
npm run preview                    # Попередній перегляд збірки

# 🐳 Docker
docker-compose up -d               # Запустити у фоновому режимі
docker-compose logs -f backend     # Логи backend
docker-compose exec backend bash   # Консоль в контейнері
```

### 📁 16 груп ОЗ згідно ПКУ ст. 138.3.3

| Група | Назва | Мін. строк | Рахунок |
|-------|-------|-----------|---------|
| 1 | Земельні ділянки | — | 101 |
| 2 | Капітальні витрати на поліпшення земель | 180 міс. | 102 |
| 3 | Будівлі | 240 міс. | 103 |
| 4 | Машини та обладнання | 60 міс. | 104 |
| 5 | Транспортні засоби | 60 міс. | 105 |
| 6 | Інструменти, прилади, інвентар | 48 міс. | 106 |
| 7 | Тварини | 72 міс. | 107 |
| 8 | Багаторічні насадження | 120 міс. | 108 |
| 9 | Інші основні засоби | 144 міс. | 109 |
| 10 | Бібліотечні фонди | — | 111 |
| 11 | Малоцінні необоротні матеріальні активи | — | 112 |
| 12 | Тимчасові споруди | 60 міс. | 113 |
| 13 | Природні ресурси | 144 міс. | 114 |
| 14 | Інвентарна тара | 72 міс. | 115 |
| 15 | Предмети прокату | 60 міс. | 116 |
| 16 | Довгострокові біологічні активи | 84 міс. | 162 |

---

## 📖 Документація

| Документ | Опис |
|----------|------|
| 📖 [Інструкція користувача](docs/USER_GUIDE.md) | Детальний посібник для бухгалтерів та інвентаризаторів |
| 🔧 [Інструкція по встановленню](docs/INSTALLATION.md) | Установка на Windows, macOS, Linux, Docker |

---

## 📜 Ліцензія

Цей проєкт створено для внутрішнього використання згідно з вимогами українського законодавства щодо обліку основних засобів.

---

<p align="center">
  <strong>🇺🇦 Зроблено в Україні</strong>
</p>
