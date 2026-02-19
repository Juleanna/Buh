# 📘 Інструкція з встановлення — Система обліку основних засобів

> **Версія документа:** 1.0 | **Дата:** 17 лютого 2026 р.
>
> Ця інструкція охоплює всі способи встановлення системи обліку основних засобів підприємства відповідно до Податкового кодексу України (ПКУ).

---

## 📋 Зміст

1. [🐳 Docker Compose (найпростіший спосіб)](#1--docker-compose-найпростіший-спосіб)
2. [💻 Windows (ручна установка)](#2--windows-ручна-установка)
3. [🍎 macOS (ручна установка)](#3--macos-ручна-установка)
4. [🐧 Linux / Ubuntu (ручна установка)](#4--linux--ubuntu-ручна-установка)
5. [📦 Використання популярних інструментів](#5--використання-популярних-інструментів)
   - [5a. pgAdmin 4](#5a--pgadmin-4-для-postgresql)
   - [5b. DBeaver](#5b--dbeaver-для-postgresql)
   - [5c. VS Code](#5c--vs-code)
   - [5d. PyCharm](#5d--pycharm)
   - [5e. Postman](#5e--postman)
6. [🌐 Production deployment (бойовий сервер)](#6--production-deployment-бойовий-сервер)
7. [🔧 Troubleshooting (вирішення проблем)](#7--troubleshooting-вирішення-проблем)

---

## ⚙️ Системні вимоги

| Компонент | Мінімальна версія | Рекомендована версія |
|-----------|-------------------|----------------------|
| 🐍 Python | 3.11+ | 3.12 |
| 🟢 Node.js | 18+ | 20 LTS |
| 🐘 PostgreSQL | 16 | 16 |
| 🔴 Redis | 7+ (опціонально) | 7.2 |
| 🐙 Git | 2.30+ | остання |
| 🐳 Docker | 24+ (якщо Docker-спосіб) | остання |
| 💾 RAM | 4 ГБ | 8 ГБ |
| 💿 Диск | 2 ГБ вільних | 5 ГБ вільних |

---

## 🏗️ Архітектура проєкту

```
Buh/
├── backend/                # 🐍 Django 5.1 (REST API)
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env               # ⚙️ Змінні середовища
│   └── ...
├── frontend/              # ⚛️ React 18 + Vite 6
│   ├── package.json
│   └── ...
├── docker-compose.yml     # 🐳 Docker конфігурація
└── docs/
    └── INSTALLATION.md    # 📘 Цей файл
```

---

## 🔐 Змінні середовища

Перед будь-яким способом встановлення створіть файл `.env` у папці `backend/`:

```bash
# 📄 backend/.env

# 🔑 Секретний ключ Django (згенеруйте свій!)
DJANGO_SECRET_KEY=your-secret-key

# 🐛 Режим розробки (True для розробки, False для продакшену)
DEBUG=True

# 🐘 Налаштування PostgreSQL
POSTGRES_DB=buh_assets
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# 🌐 Дозволені джерела для CORS
CORS_ORIGINS=http://localhost:5173

# 🔴 Redis для Celery (опціонально)
CELERY_BROKER_URL=redis://localhost:6379/0
```

> 💡 **Порада:** Для генерації секретного ключа Django виконайте:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## 1. 🐳 Docker Compose (найпростіший спосіб)

> ✅ **Рекомендовано для початківців!** Цей спосіб автоматично встановить та налаштує все необхідне.

### 1.1 📥 Встановлення Docker Desktop

#### 🪟 Windows:
1. Перейдіть на [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Натисніть **"Download for Windows"**
3. Запустіть інсталятор `Docker Desktop Installer.exe`
4. ✅ Переконайтесь, що опція **"Use WSL 2 instead of Hyper-V"** увімкнена
5. Після встановлення перезавантажте комп'ютер 🔄
6. Запустіть Docker Desktop з меню Пуск

> 🖼️ *На екрані з'явиться іконка Docker (кит 🐋) у системному треї біля годинника*

#### 🍎 macOS:
```bash
# Через Homebrew:
brew install --cask docker

# Або завантажте .dmg з docker.com і перетягніть у Applications
```

#### 🐧 Linux (Ubuntu):
```bash
# Встановлення Docker Engine
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Додати поточного користувача до групи docker (щоб не писати sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### 1.2 ✅ Перевірка Docker

```bash
docker --version
# ✅ Очікуваний вивід: Docker version 27.x.x, build xxxxxxx

docker compose version
# ✅ Очікуваний вивід: Docker Compose version v2.x.x
```

### 1.3 📥 Клонування репозиторію

```bash
git clone https://github.com/your-username/Buh.git
cd Buh
```

> 💡 **Порада:** Замініть `your-username` на реальне ім'я користувача GitHub.

### 1.4 ⚙️ Налаштування змінних середовища

```bash
# Скопіюйте шаблон .env файлу (або створіть вручну)
cp backend/.env.example backend/.env

# Відредагуйте файл .env
# 🪟 Windows: notepad backend/.env
# 🍎 macOS/🐧 Linux: nano backend/.env
```

Вміст `backend/.env` для Docker:

```env
DJANGO_SECRET_KEY=your-secret-key-here-change-me
DEBUG=True
POSTGRES_DB=buh_assets
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CORS_ORIGINS=http://localhost
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

> ⚠️ **Зверніть увагу:** У `.env` файлі вказуйте `POSTGRES_HOST=localhost` — Docker Compose автоматично перевизначить хост на `db` та URL Redis на `redis://redis:6379/0` через секцію `environment` в `docker-compose.yml`. Також `CORS_ORIGINS=http://localhost` — бо фронтенд через Docker доступний на порті 80 (nginx).

### 1.5 🏗️ Збірка Docker-образів

Перед першим запуском потрібно зібрати Docker-образи для backend та frontend. Готові образи (PostgreSQL, Redis) завантажуються автоматично з Docker Hub.

```bash
# Збірка всіх образів
docker compose build
```

> 🖼️ *Docker завантажить базові образи (postgres:16-alpine, redis:7-alpine, node:20-alpine, python:3.12-slim, nginx:alpine) та зібрає два власних образи: **backend** і **frontend**.*

**Що відбувається при збірці:**

| Образ | Що збирається | Dockerfile |
|-------|--------------|------------|
| 🐍 **backend** | Python 3.12 + залежності з `requirements.txt` + `collectstatic` + Gunicorn | `backend/Dockerfile` |
| ⚛️ **frontend** | Node.js 20 → `npm ci` → `npm run build` → результат копіюється в nginx:alpine | `frontend/Dockerfile` |
| 🐘 db | Готовий образ `postgres:16-alpine` (завантажується з Docker Hub) | — |
| 🔴 redis | Готовий образ `redis:7-alpine` (завантажується з Docker Hub) | — |

**✅ Очікуваний вивід (збірка backend):**
```
[+] Building 2/2
 => [backend] ...
 => => COPY requirements.txt .
 => => RUN pip install --no-cache-dir -r requirements.txt
 => => COPY . .
 => => RUN ... python manage.py collectstatic --noinput
 => [backend] DONE
```

**✅ Очікуваний вивід (збірка frontend):**
```
 => [frontend build] npm ci
 => [frontend build] npm run build
 => [frontend] COPY --from=build /app/dist /usr/share/nginx/html
 => [frontend] COPY nginx.conf /etc/nginx/conf.d/default.conf
 => [frontend] DONE
```

> 💡 **Перезбірка:** Якщо ви змінили код, перезберіть конкретний сервіс:
> ```bash
> docker compose build backend    # Тільки backend
> docker compose build frontend   # Тільки frontend
> docker compose build            # Все разом
> ```

### 1.6 🚀 Запуск усіх сервісів

```bash
# Запуск усіх контейнерів у фоновому режимі
docker compose up -d
```

> 💡 **Порада:** Можна збирати і запускати однією командою:
> ```bash
> docker compose up -d --build
> ```

**✅ Очікуваний вивід:**
```
[+] Running 6/6
 ✔ Container buh_postgres     Started
 ✔ Container buh_redis        Started
 ✔ Container buh_backend      Started
 ✔ Container buh_celery       Started
 ✔ Container buh_celery_beat  Started
 ✔ Container buh_frontend     Started
```

> 📋 **Сервіси Docker Compose:**
>
> | Контейнер | Опис |
> |-----------|------|
> | `buh_postgres` | 🐘 PostgreSQL 16 — база даних |
> | `buh_redis` | 🔴 Redis 7 — брокер повідомлень для Celery |
> | `buh_backend` | 🐍 Django + Gunicorn — REST API (порт 8000) |
> | `buh_celery` | ⚙️ Celery Worker — фонові задачі (амортизація, сповіщення) |
> | `buh_celery_beat` | ⏰ Celery Beat — планувальник задач (щоденні/щомісячні) |
> | `buh_frontend` | ⚛️ React (nginx) — веб-інтерфейс + reverse proxy (порт 80) |
>
> **Порядок запуску:** db → redis → backend → celery, celery-beat, frontend.
> PostgreSQL та Redis мають healthcheck — backend не запуститься, поки вони не будуть готові.

### 1.7 📊 Перевірка статусу контейнерів

```bash
docker compose ps
```

**✅ Очікуваний вивід:**
```
NAME              IMAGE              COMMAND                  SERVICE       STATUS          PORTS
buh_postgres      postgres:16-alpine "docker-entrypoint.s…"  db            Up (healthy)    0.0.0.0:5432->5432/tcp
buh_redis         redis:7-alpine     "docker-entrypoint.s…"  redis         Up (healthy)    0.0.0.0:6379->6379/tcp
buh_backend       buh-backend        "gunicorn config.wsg…"  backend       Up              0.0.0.0:8000->8000/tcp
buh_celery        buh-backend        "celery -A config wo…"  celery        Up
buh_celery_beat   buh-backend        "celery -A config be…"  celery-beat   Up
buh_frontend      buh-frontend       "nginx -g daemon off…"  frontend      Up              0.0.0.0:80->80/tcp
```

> 🔴 Якщо якийсь контейнер має статус **"Exited"** або **"Restarting"**, перегляньте логи:
> ```bash
> docker compose logs backend      # Логи Django (Gunicorn)
> docker compose logs db           # Логи PostgreSQL
> docker compose logs frontend     # Логи nginx
> docker compose logs celery       # Логи Celery Worker
> docker compose logs celery-beat  # Логи Celery Beat
> docker compose logs redis        # Логи Redis
> ```

### 1.8 🗃️ Виконання міграцій та початкових налаштувань

```bash
# 📦 Застосування міграцій бази даних
docker compose exec backend python manage.py migrate
```

**✅ Очікуваний вивід:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, assets...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ...
```

```bash
# 🏷️ Створення 16 груп основних засобів відповідно до ПКУ
docker compose exec backend python manage.py seed_asset_groups
```

**✅ Очікуваний вивід:**
```
✅ Створено 16 груп основних засобів відповідно до ПКУ
```

> 📝 **Довідка:** Ця команда створить 16 груп ОЗ згідно з пп. 138.3.3 ПКУ:
> - Група 1: Земельні ділянки
> - Група 2: Капітальні витрати на поліпшення земель
> - Група 3: Будівлі, споруди, передавальні пристрої
> - Група 4: Машини та обладнання
> - ... і так далі до Групи 16.

```bash
# 👤 Створення суперкористувача (адміністратора)
docker compose exec backend python manage.py createsuperuser
```

**📝 Система запитає:**
```
Username (leave blank to use 'root'): admin
Email address: admin@example.com
Password: ********
Password (again): ********
Superuser created successfully. ✅
```

### 1.9 🎉 Перевірка роботи

Відкрийте у браузері:

| Сервіс | URL | Опис |
|--------|-----|------|
| ⚛️ Frontend | [http://localhost](http://localhost) | React-додаток (nginx, порт 80) |
| 🐍 Backend API | [http://localhost/api/](http://localhost/api/) | Django REST API (через nginx proxy) |
| 🔧 Django Admin | [http://localhost/admin/](http://localhost/admin/) | Панель адміністратора (через nginx proxy) |
| 🐍 Backend API (прямий) | [http://localhost:8000/api/](http://localhost:8000/api/) | Django REST API (прямий доступ до Gunicorn) |

> 💡 **Примітка:** Фронтенд (nginx) автоматично проксирує запити `/api/`, `/admin/`, `/media/`, `/static/` на backend. Тому основна точка входу — `http://localhost` (порт 80).

### 1.10 🛑 Зупинка та керування контейнерами

```bash
# 🛑 Зупинити всі контейнери
docker compose down

# 🛑 Зупинити та видалити всі дані (включно з базою!)
docker compose down -v

# 🔄 Перезапустити тільки backend
docker compose restart backend

# 🔄 Перезбудувати та перезапустити конкретний сервіс
docker compose up -d --build backend

# 📜 Переглянути логи в реальному часі (всіх сервісів)
docker compose logs -f

# 🔍 Переглянути логи конкретного сервісу
docker compose logs -f backend
docker compose logs -f celery

# 🐚 Відкрити shell у контейнері backend
docker compose exec backend bash

# 🐍 Відкрити Django shell
docker compose exec backend python manage.py shell
```

> 💡 **Корисні команди для Docker:**
> ```bash
> # Перевірити використання диску Docker
> docker system df
>
> # Очистити невикористані образи та кеш
> docker system prune
> ```

---

## 2. 💻 Windows (ручна установка)

> 🛠️ Цей спосіб дає повний контроль над кожним компонентом.

### 2.1 🐍 Встановлення Python 3.11+

1. Перейдіть на [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Завантажте **Python 3.12.x** (або 3.11.x)
3. Запустіть інсталятор

> ⚠️ **ДУЖЕ ВАЖЛИВО!** На першому екрані інсталятора обов'язково поставте галочку:
> **☑️ "Add Python to PATH"**
>
> 🖼️ *Ця галочка знаходиться внизу вікна інсталятора. Без неї команда `python` не працюватиме з командного рядка!*

4. Натисніть **"Install Now"** (або "Customize installation" для вибору шляху)
5. Дочекайтеся завершення встановлення

**✅ Перевірка:**
```cmd
python --version
# ✅ Python 3.12.x

pip --version
# ✅ pip 24.x from ...
```

> 🔴 **Якщо `python` не знайдено:** Перезапустіть командний рядок (або PowerShell). Якщо не допомогло — додайте Python до PATH вручну:
> `Панель керування → Система → Додаткові параметри → Змінні середовища → Path → Додати: C:\Users\<ім'я>\AppData\Local\Programs\Python\Python312\`

### 2.2 🟢 Встановлення Node.js 20

1. Перейдіть на [https://nodejs.org/](https://nodejs.org/)
2. Завантажте **Node.js 20 LTS** (кнопка "LTS Recommended")
3. Запустіть інсталятор `node-v20.x.x-x64.msi`
4. Натискайте "Next" на всіх кроках (стандартні налаштування підходять)
5. ✅ Переконайтеся, що **"Automatically install the necessary tools"** увімкнено

**✅ Перевірка:**
```cmd
node --version
# ✅ v20.x.x

npm --version
# ✅ 10.x.x
```

### 2.3 🐘 Встановлення PostgreSQL 16

1. Перейдіть на [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Натисніть **"Download the installer"** (від EDB — EnterpriseDB)
3. Завантажте **PostgreSQL 16.x** для Windows x86-64
4. Запустіть інсталятор

**📝 Під час встановлення:**

- **Installation Directory:** залиште за замовчуванням (`C:\Program Files\PostgreSQL\16`)
- **Select Components:**
  - ☑️ PostgreSQL Server
  - ☑️ pgAdmin 4 (корисний GUI для роботи з базою)
  - ☑️ Command Line Tools
- **Data Directory:** залиште за замовчуванням
- **Password:** введіть пароль для суперкористувача `postgres`

  > ⚠️ **Запам'ятайте цей пароль!** Він знадобиться для файлу `.env`

- **Port:** `5432` (за замовчуванням)
- **Locale:** `Ukrainian, Ukraine` або `Default locale`

5. Натисніть "Next" → "Finish"

> 🖼️ *Після встановлення pgAdmin 4 з'явиться у меню Пуск. PostgreSQL запуститься як служба Windows автоматично.*

**✅ Перевірка:**
```cmd
# Додайте PostgreSQL bin до PATH або вкажіть повний шлях:
"C:\Program Files\PostgreSQL\16\bin\psql" --version
# ✅ psql (PostgreSQL) 16.x
```

> 💡 **Порада:** Додайте `C:\Program Files\PostgreSQL\16\bin` до змінної середовища PATH для зручності.

### 2.4 🔴 Встановлення Redis (опціонально)

Redis офіційно не підтримує Windows, але є два варіанти:

#### Варіант A: Redis через WSL2 (рекомендовано) 🐧

```powershell
# 1. Увімкніть WSL2 (у PowerShell з правами адміністратора)
wsl --install

# 2. Перезавантажте комп'ютер
# 3. Відкрийте Ubuntu з меню Пуск та виконайте:
sudo apt update
sudo apt install -y redis-server
sudo service redis-server start

# 4. Перевірка:
redis-cli ping
# ✅ PONG
```

#### Варіант B: Memurai (Windows-версія Redis) 💾

1. Перейдіть на [https://www.memurai.com/](https://www.memurai.com/)
2. Завантажте **Memurai Developer Edition** (безкоштовна)
3. Встановіть через інсталятор
4. Memurai запуститься як служба Windows автоматично

**✅ Перевірка:**
```cmd
memurai-cli ping
# ✅ PONG
```

> 💡 **Примітка:** Redis не є обов'язковим. Він потрібен тільки для асинхронних задач Celery (наприклад, масовий імпорт або генерація звітів у фоні). Система працюватиме і без нього.

### 2.5 📥 Клонування репозиторію

```cmd
# Відкрийте cmd або PowerShell
git clone https://github.com/your-username/Buh.git
cd Buh
```

### 2.6 🐍 Налаштування Python-середовища (backend)

```cmd
# Перейти до папки backend
cd backend

# Створити віртуальне середовище
python -m venv venv

# Активувати віртуальне середовище
# 🪟 CMD:
venv\Scripts\activate

# 🪟 PowerShell:
venv\Scripts\Activate.ps1
```

> ⚠️ **Помилка в PowerShell?** Якщо з'являється помилка про виконання скриптів:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Потім спробуйте знову `venv\Scripts\Activate.ps1`

**✅ Після активації ви побачите `(venv)` перед рядком команд:**
```
(venv) C:\Users\...\Buh\backend>
```

```cmd
# Встановити залежності Python
pip install -r requirements.txt
```

**✅ Очікуваний вивід:**
```
Successfully installed Django-5.1.x djangorestframework-3.x.x psycopg2-binary-2.x ...
```

> 🔴 **Помилка `psycopg2`?** Спробуйте:
> ```cmd
> pip install psycopg2-binary
> ```
> Або встановіть [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

### 2.7 🗃️ Створення бази даних PostgreSQL

```cmd
# Підключіться до PostgreSQL через psql
"C:\Program Files\PostgreSQL\16\bin\psql" -U postgres
# Введіть пароль, який задали при встановленні
```

```sql
-- 📦 Створити базу даних
CREATE DATABASE buh_assets;

-- 👤 (Опціонально) Створити окремого користувача
CREATE USER buh_user WITH PASSWORD 'secure_password_123';

-- 🔑 Надати права
GRANT ALL PRIVILEGES ON DATABASE buh_assets TO buh_user;
ALTER DATABASE buh_assets OWNER TO buh_user;

-- 🚪 Вийти
\q
```

**✅ Очікуваний вивід:**
```
CREATE DATABASE
CREATE ROLE
GRANT
ALTER DATABASE
```

### 2.8 ⚙️ Налаштування файлу .env

Створіть файл `backend/.env`:

```cmd
# Або через Провідник / Блокнот:
notepad backend\.env
```

Вставте вміст:
```env
DJANGO_SECRET_KEY=your-very-long-secret-key-here
DEBUG=True
POSTGRES_DB=buh_assets
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CORS_ORIGINS=http://localhost:5173
CELERY_BROKER_URL=redis://localhost:6379/0
```

> ⚠️ Замініть `your_password` на реальний пароль PostgreSQL!

### 2.9 🚀 Запуск міграцій та наповнення даними

```cmd
cd backend

# Переконайтесь, що venv активовано!
# (venv) має бути на початку рядка

# 📦 Застосування міграцій
python manage.py migrate
```

**✅ Очікуваний вивід:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, assets...
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying assets.0001_initial... OK
  ...
```

```cmd
# 🏷️ Створення 16 груп ОЗ за ПКУ
python manage.py seed_asset_groups
```

**✅ Очікуваний вивід:**
```
✅ Створено 16 груп основних засобів відповідно до ПКУ
```

```cmd
# 👤 Створення адміністратора
python manage.py createsuperuser
```

Введіть логін, email та пароль за підказками.

### 2.10 ⚛️ Налаштування frontend (React)

Відкрийте **нове** вікно командного рядка:

```cmd
cd Buh\frontend

# 📦 Встановлення залежностей
npm install
```

**✅ Очікуваний вивід:**
```
added 200+ packages in 30s
```

> 🔴 **Помилка `npm ERR! code ERESOLVE`?** Спробуйте:
> ```cmd
> npm install --legacy-peer-deps
> ```

### 2.11 🎬 Запуск проєкту

Відкрийте **два** вікна командного рядка:

**🪟 Вікно 1 — Backend (Django):**
```cmd
cd Buh\backend
venv\Scripts\activate
python manage.py runserver
```

**✅ Очікуваний вивід:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
February 17, 2026 - 10:00:00
Django version 5.1.x, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

**🪟 Вікно 2 — Frontend (React + Vite):**
```cmd
cd Buh\frontend
npm run dev
```

**✅ Очікуваний вивід:**
```
  VITE v6.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
  ➜  press h + enter to show help
```

### 2.12 🎉 Перевірка

| Сервіс | URL |
|--------|-----|
| ⚛️ Frontend | [http://localhost:5173](http://localhost:5173) |
| 🐍 Backend API | [http://localhost:8000/api/](http://localhost:8000/api/) |
| 🔧 Django Admin | [http://localhost:8000/admin/](http://localhost:8000/admin/) |

> 🖼️ *У браузері повинна відкритися сторінка входу або головна панель системи обліку основних засобів.*

---

## 3. 🍎 macOS (ручна установка)

### 3.1 🍺 Встановлення Homebrew

Якщо Homebrew ще не встановлено:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**✅ Перевірка:**
```bash
brew --version
# ✅ Homebrew 4.x.x
```

### 3.2 🐍 Встановлення Python

```bash
brew install python@3.12
```

**✅ Перевірка:**
```bash
python3 --version
# ✅ Python 3.12.x

pip3 --version
# ✅ pip 24.x from ...
```

> 💡 **Примітка:** На macOS використовуйте `python3` та `pip3` замість `python` та `pip`.

### 3.3 🟢 Встановлення Node.js

```bash
brew install node@20

# Додати до PATH (якщо brew підкаже)
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**✅ Перевірка:**
```bash
node --version
# ✅ v20.x.x

npm --version
# ✅ 10.x.x
```

### 3.4 🐘 Встановлення PostgreSQL 16

```bash
brew install postgresql@16

# Запустити PostgreSQL як сервіс
brew services start postgresql@16

# Додати до PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**✅ Перевірка:**
```bash
psql --version
# ✅ psql (PostgreSQL) 16.x

# Перевірити, чи сервіс запущений
brew services list | grep postgresql
# ✅ postgresql@16 started ...
```

### 3.5 🔴 Встановлення Redis

```bash
brew install redis

# Запустити Redis як сервіс
brew services start redis
```

**✅ Перевірка:**
```bash
redis-cli ping
# ✅ PONG
```

### 3.6 📥 Клонування та налаштування

```bash
git clone https://github.com/your-username/Buh.git
cd Buh
```

### 3.7 🗃️ Створення бази даних

```bash
# Створити базу даних
createdb buh_assets

# Або через psql:
psql postgres
```

```sql
CREATE DATABASE buh_assets;
CREATE USER buh_user WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE buh_assets TO buh_user;
ALTER DATABASE buh_assets OWNER TO buh_user;
\q
```

### 3.8 🐍 Налаштування backend

```bash
cd backend

# Створити віртуальне середовище
python3 -m venv venv

# Активувати
source venv/bin/activate

# Встановити залежності
pip install -r requirements.txt
```

**✅ Після активації `(venv)` з'явиться на початку рядка:**
```
(venv) user@mac Buh/backend %
```

### 3.9 ⚙️ Налаштування .env

```bash
# Створити файл .env
nano backend/.env
```

Вставте вміст (див. [розділ "Змінні середовища"](#-змінні-середовища) вище).

> 💡 **У nano:** `Ctrl+O` — зберегти, `Ctrl+X` — вийти.

### 3.10 🚀 Міграції та запуск

```bash
# Міграції
python manage.py migrate

# Заповнити групи ОЗ
python manage.py seed_asset_groups

# Створити адміна
python manage.py createsuperuser

# Запустити backend
python manage.py runserver
```

### 3.11 ⚛️ Налаштування та запуск frontend

Відкрийте **новий термінал** (⌘+T):

```bash
cd Buh/frontend

# Встановити залежності
npm install

# Запустити dev-сервер
npm run dev
```

### 3.12 🎉 Готово!

Відкрийте у Safari або Chrome:
- ⚛️ Frontend: [http://localhost:5173](http://localhost:5173)
- 🐍 Backend: [http://localhost:8000/api/](http://localhost:8000/api/)
- 🔧 Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 4. 🐧 Linux / Ubuntu (ручна установка)

> 📝 Інструкція для Ubuntu 22.04 / 24.04 LTS. Для інших дистрибутивів команди можуть відрізнятися.

### 4.1 📦 Оновлення системи

```bash
sudo apt update && sudo apt upgrade -y
```

### 4.2 🐍 Встановлення Python 3.12

```bash
# Додати PPA для новіших версій Python (якщо потрібно)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Встановити Python 3.12 та необхідні пакети
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
```

**✅ Перевірка:**
```bash
python3.12 --version
# ✅ Python 3.12.x
```

> 💡 **Порада:** Якщо у вас вже є Python 3.11+, можна використовувати його:
> ```bash
> python3 --version
> ```

### 4.3 🟢 Встановлення Node.js 20

```bash
# Встановити через NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**✅ Перевірка:**
```bash
node --version
# ✅ v20.x.x

npm --version
# ✅ 10.x.x
```

### 4.4 🐘 Встановлення PostgreSQL 16

```bash
# Додати офіційний репозиторій PostgreSQL
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Встановити PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-client-16

# Перевірити статус сервісу
sudo systemctl status postgresql
# ✅ Active: active (exited)

# Запустити, якщо не запущено
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**✅ Перевірка:**
```bash
psql --version
# ✅ psql (PostgreSQL) 16.x
```

### 4.5 🔴 Встановлення Redis

```bash
sudo apt install -y redis-server

# Запустити та увімкнути автозапуск
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**✅ Перевірка:**
```bash
redis-cli ping
# ✅ PONG
```

### 4.6 🐙 Встановлення Git

```bash
sudo apt install -y git

git --version
# ✅ git version 2.x.x
```

### 4.7 📥 Клонування репозиторію

```bash
git clone https://github.com/your-username/Buh.git
cd Buh
```

### 4.8 🗃️ Створення бази даних

```bash
# Перемкнутися на користувача postgres
sudo -u postgres psql
```

```sql
-- 📦 Створити базу даних
CREATE DATABASE buh_assets;

-- 👤 Створити користувача
CREATE USER buh_user WITH PASSWORD 'secure_password_123';

-- 🔑 Надати права
GRANT ALL PRIVILEGES ON DATABASE buh_assets TO buh_user;
ALTER DATABASE buh_assets OWNER TO buh_user;

-- 🚪 Вийти
\q
```

### 4.9 🐍 Налаштування backend

```bash
cd backend

# Створити віртуальне середовище
python3.12 -m venv venv

# Активувати
source venv/bin/activate

# (venv) має з'явитися на початку рядка ✅

# Встановити залежності
pip install -r requirements.txt
```

> 🔴 **Помилка `psycopg2`?** Встановіть системні залежності:
> ```bash
> sudo apt install -y libpq-dev python3.12-dev gcc
> pip install psycopg2-binary
> ```

### 4.10 ⚙️ Налаштування .env

```bash
nano backend/.env
```

Вставте вміст (див. [розділ "Змінні середовища"](#-змінні-середовища) вище). Збережіть: `Ctrl+O`, `Enter`, `Ctrl+X`.

### 4.11 🚀 Міграції та наповнення

```bash
# Переконайтесь, що venv активовано
source venv/bin/activate

# 📦 Міграції
python manage.py migrate

# 🏷️ Групи ОЗ за ПКУ
python manage.py seed_asset_groups

# 👤 Суперкористувач
python manage.py createsuperuser
```

### 4.12 ⚛️ Налаштування та запуск frontend

Відкрийте **новий термінал** (Ctrl+Shift+T):

```bash
cd Buh/frontend

npm install
npm run dev
```

### 4.13 🎬 Запуск backend

У першому терміналі:

```bash
cd Buh/backend
source venv/bin/activate
python manage.py runserver
```

### 4.14 🎉 Готово!

| Сервіс | URL |
|--------|-----|
| ⚛️ Frontend | [http://localhost:5173](http://localhost:5173) |
| 🐍 Backend API | [http://localhost:8000/api/](http://localhost:8000/api/) |
| 🔧 Django Admin | [http://localhost:8000/admin/](http://localhost:8000/admin/) |

---

## 5. 📦 Використання популярних інструментів

### 5a. 🐘 pgAdmin 4 (для PostgreSQL)

> pgAdmin 4 — це графічний інтерфейс для керування базами даних PostgreSQL.

#### 📥 Встановлення

- **🪟 Windows:** Встановлюється разом з PostgreSQL (або окремо з [pgadmin.org](https://www.pgadmin.org/download/))
- **🍎 macOS:** `brew install --cask pgadmin4`
- **🐧 Linux:**
  ```bash
  curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
  sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'
  sudo apt update
  sudo apt install -y pgadmin4-desktop
  ```

#### 🔧 Налаштування з'єднання

1. Запустіть **pgAdmin 4**
2. 🖼️ *У лівій панелі натисніть правою кнопкою на **"Servers"** → **"Register" → "Server..."***

3. **Вкладка "General":**
   - **Name:** `Buh Local` (довільна назва)

4. **Вкладка "Connection":**
   | Поле | Значення |
   |------|----------|
   | Host name/address | `localhost` |
   | Port | `5432` |
   | Maintenance database | `postgres` |
   | Username | `postgres` |
   | Password | `your_password` |
   | ☑️ Save password | увімкнути |

5. Натисніть **"Save"**

#### 📦 Створення бази даних через pgAdmin

1. 🖼️ *Розгорніть сервер **"Buh Local"** у лівій панелі*
2. Правий клік на **"Databases"** → **"Create" → "Database..."**
3. **Database:** `buh_assets`
4. **Owner:** `postgres` (або `buh_user`, якщо створили)
5. Натисніть **"Save"**

> ✅ База даних `buh_assets` з'явиться у списку баз даних.

#### 👤 Створення користувача через pgAdmin

1. Розгорніть сервер → **"Login/Group Roles"**
2. Правий клік → **"Create" → "Login/Group Role..."**
3. **Вкладка "General":** Name: `buh_user`
4. **Вкладка "Definition":** Password: `secure_password_123`
5. **Вкладка "Privileges":**
   - ☑️ Can login
   - ☑️ Create databases (опціонально)
6. Натисніть **"Save"**

---

### 5b. 🦫 DBeaver (для PostgreSQL)

> DBeaver — безкоштовний універсальний клієнт для баз даних.

#### 📥 Встановлення

- **🪟 Windows:** Завантажте з [dbeaver.io](https://dbeaver.io/download/) → Windows Installer
- **🍎 macOS:** `brew install --cask dbeaver-community`
- **🐧 Linux:** `sudo snap install dbeaver-ce`

#### 🔧 Створення з'єднання

1. Запустіть DBeaver
2. Натисніть **🔌 "New Database Connection"** (іконка розетки з плюсом у верхньому лівому куті)
3. Оберіть **"PostgreSQL"** → **"Next"**

4. **Заповніть параметри:**
   | Поле | Значення |
   |------|----------|
   | Host | `localhost` |
   | Port | `5432` |
   | Database | `buh_assets` |
   | Username | `postgres` |
   | Password | `your_password` |
   | ☑️ Save password locally | увімкнути |

5. Натисніть **"Test Connection"**
   - 🖼️ *Має з'явитися повідомлення **"Connected"** із зеленою іконкою ✅*
   - Якщо DBeaver запропонує завантажити драйвер — натисніть **"Download"**

6. Натисніть **"Finish"**

#### 📦 Створення бази через DBeaver

1. Розгорніть з'єднання у лівій панелі
2. Правий клік на **"Databases"** → **"Create New Database"**
3. Введіть: `buh_assets`
4. Натисніть **"OK"**

#### 📊 Перегляд даних

Після міграцій ви зможете бачити всі таблиці:
1. Розгорніть `buh_assets` → **"Schemas"** → **"public"** → **"Tables"**
2. 🖼️ *Подвійний клік на таблицю (наприклад, `assets_assetgroup`) покаже дані*

---

### 5c. 💜 VS Code

> Visual Studio Code — рекомендований редактор для цього проєкту.

#### 📥 Встановлення

- **🪟 Windows:** [code.visualstudio.com](https://code.visualstudio.com/) → Download
- **🍎 macOS:** `brew install --cask visual-studio-code`
- **🐧 Linux:** `sudo snap install code --classic`

#### 🧩 Рекомендовані розширення

Відкрийте термінал і встановіть одразу все:

```bash
# 🐍 Python
code --install-extension ms-python.python
code --install-extension ms-python.pylint

# 🐍 Django
code --install-extension batisteo.vscode-django

# ⚛️ React / JavaScript
code --install-extension dsznajder.es7-react-js-snippets
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode

# 🐘 PostgreSQL
code --install-extension ckolkman.vscode-postgres

# 🐳 Docker
code --install-extension ms-azuretools.vscode-docker

# 🎨 Оформлення та зручність
code --install-extension formulahendry.auto-rename-tag
code --install-extension bradlc.vscode-tailwindcss
code --install-extension eamodio.vscode-gitlens
```

Або встановіть вручну через **Extensions** (Ctrl+Shift+X):
- 🔍 Пошук: "Python", "Django", "ES7 React", "ESLint", "Prettier", "Docker"

#### 🔧 Налаштування launch.json (для дебагу)

Створіть файл `.vscode/launch.json` у кореневій папці проєкту:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "🐍 Django: Runserver",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["runserver", "0.0.0.0:8000"],
      "django": true,
      "env": {
        "DJANGO_SETTINGS_MODULE": "config.settings"
      },
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    },
    {
      "name": "🐍 Django: Shell",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/backend/manage.py",
      "args": ["shell"],
      "django": true,
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    },
    {
      "name": "⚛️ Chrome: Frontend",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

> 🖼️ *Тепер у панелі **Run and Debug** (Ctrl+Shift+D) ви побачите три конфігурації для запуску.*

#### ⚙️ Налаштування settings.json

Створіть або відредагуйте `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.envFile": "${workspaceFolder}/backend/.env",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/node_modules": true
  },
  "emmet.includeLanguages": {
    "javascript": "javascriptreact"
  }
}
```

> 💡 **Для Windows** змініть шлях інтерпретатора на:
> `"${workspaceFolder}\\backend\\venv\\Scripts\\python.exe"`

---

### 5d. 🧠 PyCharm

> PyCharm Professional має вбудовану підтримку Django та баз даних.

#### 📥 Встановлення

- **🪟 Windows / 🍎 macOS / 🐧 Linux:** [jetbrains.com/pycharm](https://www.jetbrains.com/pycharm/download/)
- Оберіть **Professional** (платна, є безкоштовна 30-денна пробна версія) або **Community** (безкоштовна, але без Django-підтримки)

#### 🔧 Налаштування Python Interpreter

1. Відкрийте проєкт: **File → Open → виберіть папку `Buh`**
2. Перейдіть: **File → Settings (Ctrl+Alt+S) → Project: Buh → Python Interpreter**
3. Натисніть ⚙️ **"Add Interpreter" → "Add Local Interpreter..."**
4. Оберіть **"Existing"** і вкажіть шлях:
   - 🪟 Windows: `Buh\backend\venv\Scripts\python.exe`
   - 🍎 macOS / 🐧 Linux: `Buh/backend/venv/bin/python`
5. Натисніть **"OK"**

> 🖼️ *У нижньому правому куті PyCharm з'явиться назва інтерпретатора (наприклад, "Python 3.12 (venv)")*

#### 🐍 Увімкнення Django Support

1. **File → Settings → Languages & Frameworks → Django**
2. ☑️ **Enable Django Support**
3. **Django project root:** `Buh/backend`
4. **Settings:** `config/settings.py` (або ваш файл налаштувань)
5. **Manage script:** `manage.py`
6. Натисніть **"OK"**

#### ▶️ Створення Run Configuration

1. **Run → Edit Configurations... → "+" → Django Server**
2. **Name:** `Runserver`
3. **Host:** `0.0.0.0`
4. **Port:** `8000`
5. **Environment variables:** додайте змінні з `.env` або вкажіть:
   - **EnvFile plugin:** встановіть плагін "EnvFile" та підключіть `backend/.env`
6. Натисніть **"OK"**

> ✅ Тепер ви можете запускати Django сервер кнопкою ▶️ (Shift+F10) та дебажити 🐛 (Shift+F9).

#### 🐘 Підключення бази даних

1. Відкрийте вкладку **Database** (справа)
2. Натисніть **"+" → "Data Source" → "PostgreSQL"**
3. Заповніть:
   | Поле | Значення |
   |------|----------|
   | Host | `localhost` |
   | Port | `5432` |
   | Database | `buh_assets` |
   | User | `postgres` |
   | Password | `your_password` |
4. Натисніть **"Test Connection"** → ✅ **"Succeeded"**
5. **"OK"**

> 🖼️ *Тепер ви можете переглядати таблиці, виконувати SQL-запити та бачити структуру бази прямо в PyCharm.*

---

### 5e. 🚀 Postman (для тестування API)

> Postman — інструмент для тестування REST API.

#### 📥 Встановлення

- Завантажте з [postman.com/downloads](https://www.postman.com/downloads/)
- Або: `brew install --cask postman` (macOS)

#### 📦 Створення колекції

1. Запустіть Postman
2. Натисніть **"New" → "Collection"**
3. Назва: `🏢 Buh - Облік ОЗ`

#### 📝 Основні запити для імпорту

Створіть наступні запити у колекції:

**1. 🔐 Авторизація (отримання токена):**
```
POST http://localhost:8000/api/auth/login/
Body (JSON):
{
    "username": "admin",
    "password": "your_password"
}
```

**2. 📋 Список груп ОЗ:**
```
GET http://localhost:8000/api/asset-groups/
Headers:
  Authorization: Token <your-token>
```

**3. 📋 Список основних засобів:**
```
GET http://localhost:8000/api/assets/
Headers:
  Authorization: Token <your-token>
```

**4. ➕ Створення основного засобу:**
```
POST http://localhost:8000/api/assets/
Headers:
  Authorization: Token <your-token>
  Content-Type: application/json
Body (JSON):
{
    "name": "Комп'ютер HP ProBook",
    "inventory_number": "OZ-000001",
    "group": 4,
    "initial_cost": 35000.00,
    "commissioning_date": "2026-01-15"
}
```

**5. ✏️ Оновлення основного засобу:**
```
PUT http://localhost:8000/api/assets/1/
Headers:
  Authorization: Token <your-token>
  Content-Type: application/json
Body (JSON):
{
    "name": "Комп'ютер HP ProBook 450 G10",
    "initial_cost": 37500.00
}
```

**6. 🗑️ Видалення основного засобу:**
```
DELETE http://localhost:8000/api/assets/1/
Headers:
  Authorization: Token <your-token>
```

#### 💡 Налаштування змінних оточення в Postman

1. Натисніть **"Environments" → "+" (Create Environment)**
2. Назва: `Buh Local`
3. Додайте змінні:

   | Variable | Initial Value |
   |----------|---------------|
   | `base_url` | `http://localhost:8000/api` |
   | `token` | *(заповніть після авторизації)* |

4. У запитах використовуйте: `{{base_url}}/assets/` та `Authorization: Token {{token}}`

> 🖼️ *Це дозволить швидко перемикатися між локальним та продакшен-сервером.*

---

## 6. 🌐 Production deployment (бойовий сервер)

> ⚠️ **Увага!** Цей розділ для досвідчених адміністраторів. Deployment на бойовий сервер вимагає додаткових знань з безпеки.

### 6.1 🖥️ Підготовка сервера (Ubuntu 22.04+)

```bash
# Оновлення системи
sudo apt update && sudo apt upgrade -y

# Встановлення базових пакетів
sudo apt install -y build-essential libpq-dev python3.12 python3.12-venv \
    python3.12-dev nginx certbot python3-certbot-nginx git curl

# Встановлення Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Встановлення PostgreSQL 16
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16

# Встановлення Redis
sudo apt install -y redis-server
```

### 6.2 👤 Створення системного користувача

```bash
# Створити користувача для додатку
sudo useradd -m -s /bin/bash buh
sudo su - buh

# Клонувати репозиторій
git clone https://github.com/your-username/Buh.git
cd Buh
```

### 6.3 🐘 Налаштування PostgreSQL для production

```bash
sudo -u postgres psql
```

```sql
-- 🔐 Створити безпечного користувача
CREATE USER buh_prod WITH PASSWORD 'ДУЖЕ_СКЛАДНИЙ_ПАРОЛЬ_ТУТ_123!@#';
CREATE DATABASE buh_assets_prod OWNER buh_prod;
GRANT ALL PRIVILEGES ON DATABASE buh_assets_prod TO buh_prod;

-- 🔒 Обмежити підключення
ALTER USER buh_prod CONNECTION LIMIT 20;

\q
```

### 6.4 🐍 Налаштування backend

```bash
cd /home/buh/Buh/backend

# Створити venv
python3.12 -m venv venv
source venv/bin/activate

# Встановити залежності + gunicorn
pip install -r requirements.txt
pip install gunicorn
```

**⚙️ Production `.env` файл:**

```bash
nano /home/buh/Buh/backend/.env
```

```env
DJANGO_SECRET_KEY=ЗГЕНЕРОВАНИЙ_ДУЖЕ_ДОВГИЙ_СЕКРЕТНИЙ_КЛЮЧ
DEBUG=False
POSTGRES_DB=buh_assets_prod
POSTGRES_USER=buh_prod
POSTGRES_PASSWORD=ДУЖЕ_СКЛАДНИЙ_ПАРОЛЬ_ТУТ_123!@#
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CORS_ORIGINS=https://your-domain.com.ua
CELERY_BROKER_URL=redis://localhost:6379/0
ALLOWED_HOSTS=your-domain.com.ua,www.your-domain.com.ua
```

> ⚠️ **ОБОВ'ЯЗКОВО:** `DEBUG=False` для production!

### 6.5 📦 Міграції та статика

```bash
source venv/bin/activate

# Міграції
python manage.py migrate

# Групи ОЗ за ПКУ
python manage.py seed_asset_groups

# Суперкористувач
python manage.py createsuperuser

# 📁 Збирання статичних файлів
python manage.py collectstatic --noinput
```

**✅ Очікуваний вивід collectstatic:**
```
150 static files copied to '/home/buh/Buh/backend/staticfiles'.
```

### 6.6 🦄 Налаштування Gunicorn

Створіть файл конфігурації Gunicorn:

```bash
nano /home/buh/Buh/backend/gunicorn.conf.py
```

```python
# 🦄 Gunicorn configuration

# Прив'язка до сокету (Nginx буде проксирувати)
bind = "unix:/home/buh/Buh/backend/gunicorn.sock"

# Кількість воркерів (рекомендація: 2 * CPU_CORES + 1)
workers = 3

# Таймаут (секунди)
timeout = 120

# Логування
accesslog = "/home/buh/Buh/logs/gunicorn-access.log"
errorlog = "/home/buh/Buh/logs/gunicorn-error.log"
loglevel = "info"

# Перезапуск воркерів після N запитів (запобігає витокам пам'яті)
max_requests = 1000
max_requests_jitter = 50
```

```bash
# Створити папку для логів
mkdir -p /home/buh/Buh/logs
```

### 6.7 🔧 Systemd сервіс для Gunicorn

```bash
sudo nano /etc/systemd/system/buh-backend.service
```

```ini
[Unit]
Description=🏢 Buh - Django Backend (Gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
User=buh
Group=buh
WorkingDirectory=/home/buh/Buh/backend
Environment="PATH=/home/buh/Buh/backend/venv/bin"
ExecStart=/home/buh/Buh/backend/venv/bin/gunicorn \
    --config gunicorn.conf.py \
    config.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Увімкнути та запустити сервіс
sudo systemctl daemon-reload
sudo systemctl enable buh-backend
sudo systemctl start buh-backend

# Перевірити статус
sudo systemctl status buh-backend
# ✅ Active: active (running)
```

### 6.8 🔧 Systemd сервіс для Celery (опціонально)

```bash
sudo nano /etc/systemd/system/buh-celery.service
```

```ini
[Unit]
Description=🏢 Buh - Celery Worker
After=network.target redis-server.service

[Service]
User=buh
Group=buh
WorkingDirectory=/home/buh/Buh/backend
Environment="PATH=/home/buh/Buh/backend/venv/bin"
ExecStart=/home/buh/Buh/backend/venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable buh-celery
sudo systemctl start buh-celery
```

### 6.9 ⚛️ Збірка frontend для production

```bash
cd /home/buh/Buh/frontend

# Встановити залежності
npm install

# 🏗️ Зібрати production-версію
npm run build
```

**✅ Очікуваний вивід:**
```
vite v6.x.x building for production...
✓ 150 modules transformed.
dist/index.html                  0.50 kB │ gzip:  0.32 kB
dist/assets/index-xxxxx.css     25.00 kB │ gzip:  5.50 kB
dist/assets/index-xxxxx.js     180.00 kB │ gzip: 58.00 kB
✓ built in 5.00s
```

> 📁 Файли будуть у папці `frontend/dist/`.

### 6.10 🌐 Налаштування Nginx

```bash
sudo nano /etc/nginx/sites-available/buh
```

```nginx
# 🌐 Nginx конфігурація для Buh
server {
    listen 80;
    server_name your-domain.com.ua www.your-domain.com.ua;

    # 📁 Максимальний розмір завантаження (для імпорту файлів)
    client_max_body_size 20M;

    # ⚛️ Frontend (React static files)
    location / {
        root /home/buh/Buh/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 🐍 Backend API (Django через Gunicorn)
    location /api/ {
        proxy_pass http://unix:/home/buh/Buh/backend/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 🔧 Django Admin
    location /admin/ {
        proxy_pass http://unix:/home/buh/Buh/backend/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 📁 Django Static files (admin CSS/JS)
    location /static/ {
        alias /home/buh/Buh/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 📁 Media files (завантажені користувачами)
    location /media/ {
        alias /home/buh/Buh/backend/media/;
        expires 7d;
    }
}
```

```bash
# Активувати конфігурацію
sudo ln -s /etc/nginx/sites-available/buh /etc/nginx/sites-enabled/

# Видалити стандартну конфігурацію (опціонально)
sudo rm /etc/nginx/sites-enabled/default

# Перевірити конфігурацію Nginx
sudo nginx -t
# ✅ nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# ✅ nginx: configuration file /etc/nginx/nginx.conf test is successful

# Перезапустити Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 6.11 🔒 HTTPS з Let's Encrypt

```bash
# Встановити сертифікат SSL
sudo certbot --nginx -d your-domain.com.ua -d www.your-domain.com.ua
```

**📝 Certbot запитає:**
```
Enter email address: admin@your-domain.com.ua
(A)gree / (C)ancel: A
(Y)es / (N)o: Y  (або N, якщо не хочете розсилку)
```

**✅ Очікуваний вивід:**
```
Congratulations! You have successfully enabled HTTPS on https://your-domain.com.ua
```

```bash
# Перевірити автоматичне оновлення сертифіката
sudo certbot renew --dry-run
# ✅ Congratulations, all simulated renewals succeeded
```

> 🔒 Let's Encrypt автоматично налаштує Nginx на HTTPS та перенаправлення з HTTP.

### 6.12 🐘 Тюнінг PostgreSQL

Відредагуйте `postgresql.conf`:

```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
```

Змініть наступні параметри (для сервера з 4 ГБ RAM):

```ini
# 💾 Пам'ять
shared_buffers = 1GB                    # 25% від RAM
effective_cache_size = 3GB              # 75% від RAM
work_mem = 16MB                         # для операцій сортування
maintenance_work_mem = 256MB            # для VACUUM, CREATE INDEX

# 📝 WAL (Write-Ahead Logging)
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 2GB

# 🔍 Планувальник запитів
random_page_cost = 1.1                  # для SSD дисків
effective_io_concurrency = 200          # для SSD дисків

# 📊 Статистика
default_statistics_target = 100

# 🔗 З'єднання
max_connections = 100
```

```bash
# Перезапустити PostgreSQL
sudo systemctl restart postgresql

# Перевірити
sudo systemctl status postgresql
# ✅ Active: active (exited)
```

### 6.13 🔥 Налаштування фаєрволу

```bash
# Дозволити SSH, HTTP, HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Перевірити правила
sudo ufw status
# ✅ Status: active
# ✅ OpenSSH  ALLOW  Anywhere
# ✅ Nginx Full  ALLOW  Anywhere
```

> ⚠️ **Важливо:** НЕ відкривайте порти 5432 (PostgreSQL) та 6379 (Redis) для зовнішнього доступу!

### 6.14 ✅ Фінальна перевірка production

```bash
# Перевірити всі сервіси
sudo systemctl status postgresql
sudo systemctl status redis-server
sudo systemctl status buh-backend
sudo systemctl status buh-celery
sudo systemctl status nginx

# Перевірити логи
sudo journalctl -u buh-backend --since "1 hour ago"
tail -f /home/buh/Buh/logs/gunicorn-error.log
```

Відкрийте у браузері:
- 🌐 `https://your-domain.com.ua` — має відкритися React-додаток
- 🔧 `https://your-domain.com.ua/admin/` — Django Admin
- 🐍 `https://your-domain.com.ua/api/` — REST API

---

## 7. 🔧 Troubleshooting (вирішення проблем)

### 7.1 🐘 Проблеми з підключенням до бази даних

#### ❌ Помилка: `could not connect to server: Connection refused`

**Причина:** PostgreSQL не запущений або слухає не на тому порті.

**🛠️ Рішення:**

```bash
# Перевірити статус PostgreSQL
# 🐧 Linux:
sudo systemctl status postgresql
# Якщо не запущений:
sudo systemctl start postgresql

# 🍎 macOS:
brew services list | grep postgresql
# Якщо не запущений:
brew services start postgresql@16

# 🪟 Windows:
# Відкрийте Служби (services.msc) → знайдіть "postgresql-x64-16" → Запустити
```

#### ❌ Помилка: `FATAL: password authentication failed for user "postgres"`

**Причина:** Неправильний пароль у `.env` файлі.

**🛠️ Рішення:**

```bash
# 🐧 Linux — скинути пароль:
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'new_password';"

# Потім оновіть POSTGRES_PASSWORD у backend/.env
```

#### ❌ Помилка: `FATAL: database "buh_assets" does not exist`

**Причина:** База даних ще не створена.

**🛠️ Рішення:**
```bash
# Створіть базу даних:
sudo -u postgres psql -c "CREATE DATABASE buh_assets;"
# Або через pgAdmin / DBeaver (див. розділ 5)
```

#### ❌ Помилка: `django.db.utils.OperationalError: could not translate host name "db" to address`

**Причина:** Ви використовуєте `POSTGRES_HOST=db` (Docker) замість `localhost` (ручна установка).

**🛠️ Рішення:**
```bash
# У backend/.env змініть:
# Для Docker: POSTGRES_HOST=db
# Для ручної установки: POSTGRES_HOST=localhost
```

---

### 7.2 🌐 Помилки CORS

#### ❌ Помилка: `Access to XMLHttpRequest has been blocked by CORS policy`

**Причина:** Frontend звертається до Backend з іншого джерела (origin), і CORS не налаштовано.

**🛠️ Рішення:**

```bash
# 1. Перевірте backend/.env:
CORS_ORIGINS=http://localhost:5173

# 2. Якщо frontend працює на іншому порті, додайте його:
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 3. Перезапустіть Django сервер після зміни .env
```

> 💡 **Для розробки** можна тимчасово дозволити всі джерела (НЕ для production!):
> У `settings.py` додайте: `CORS_ALLOW_ALL_ORIGINS = True`

---

### 7.3 🔌 Порт вже зайнятий

#### ❌ Помилка: `Error: That port is already in use. (Port 8000)`

**🛠️ Рішення:**

```bash
# 🪟 Windows — знайти процес на порті 8000:
netstat -ano | findstr :8000
# Запам'ятайте PID (останній стовпець)
taskkill /PID <PID> /F

# 🍎 macOS / 🐧 Linux — знайти та завершити процес:
lsof -i :8000
kill -9 <PID>

# Або запустити на іншому порті:
python manage.py runserver 8001
```

#### ❌ Помилка: `Port 5173 is in use` (Vite)

**🛠️ Рішення:**

```bash
# 🪟 Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# 🍎 macOS / 🐧 Linux:
lsof -i :5173
kill -9 <PID>

# Або змінити порт у vite.config.js:
# server: { port: 3000 }
# Не забудьте оновити CORS_ORIGINS у backend/.env!
```

#### ❌ Помилка: `Port 5432 is in use` (PostgreSQL, при Docker)

**Причина:** Локальний PostgreSQL вже працює на порті 5432.

**🛠️ Рішення:**

```bash
# Варіант 1: Зупинити локальний PostgreSQL
# 🪟 Windows: services.msc → зупинити postgresql
# 🐧 Linux: sudo systemctl stop postgresql
# 🍎 macOS: brew services stop postgresql@16

# Варіант 2: Змінити порт у docker-compose.yml:
# ports:
#   - "5433:5432"  # Зовнішній порт 5433
```

---

### 7.4 🐍 Проблеми з Python / Django

#### ❌ Помилка: `ModuleNotFoundError: No module named 'django'`

**Причина:** Віртуальне середовище не активовано.

**🛠️ Рішення:**
```bash
# Активуйте venv:
# 🪟 Windows:
backend\venv\Scripts\activate

# 🍎 macOS / 🐧 Linux:
source backend/venv/bin/activate

# Перевірте, що (venv) видно на початку рядка
```

#### ❌ Помилка: `ImproperlyConfigured: Set the DJANGO_SECRET_KEY environment variable`

**Причина:** Файл `.env` не знайдено або не містить потрібну змінну.

**🛠️ Рішення:**
```bash
# Перевірте, що файл .env існує:
ls -la backend/.env

# Перевірте вміст:
cat backend/.env

# Переконайтесь, що DJANGO_SECRET_KEY не порожній
```

#### ❌ Помилка міграцій: `django.db.utils.ProgrammingError: relation already exists`

**🛠️ Рішення:**
```bash
# Скинути та повторити міграції (⚠️ ВИДАЛЯЄ ВСІ ДАНІ):
python manage.py migrate --run-syncdb

# Або для конкретного додатку:
python manage.py migrate assets zero
python manage.py migrate assets
```

---

### 7.5 ⚛️ Проблеми з Frontend / Node.js

#### ❌ Помилка: `npm ERR! code ERESOLVE` (конфлікт залежностей)

**🛠️ Рішення:**
```bash
# Варіант 1: Встановити з прапорцем legacy
npm install --legacy-peer-deps

# Варіант 2: Очистити кеш та перевстановити
rm -rf node_modules package-lock.json
npm install
```

#### ❌ Помилка: `Error: ENOSPC: System limit for number of file watchers reached`

**Причина:** Лімітована кількість inotify watchers (Linux).

**🛠️ Рішення:**
```bash
# Збільшити ліміт:
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### ❌ Помилка: `Vite requires Node.js version 18+`

**🛠️ Рішення:**
```bash
# Перевірити версію:
node --version

# Оновити Node.js:
# 🪟 Windows: завантажте нову версію з nodejs.org
# 🍎 macOS: brew upgrade node@20
# 🐧 Linux:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

### 7.6 🐳 Проблеми з Docker

#### ❌ Помилка: `docker: Cannot connect to the Docker daemon`

**🛠️ Рішення:**
```bash
# 🪟 Windows / 🍎 macOS: запустіть Docker Desktop
# 🐧 Linux:
sudo systemctl start docker

# Перевірити:
docker info
```

#### ❌ Помилка: `Bind for 0.0.0.0:5432 failed: port is already allocated`

**🛠️ Рішення:**
```bash
# Зупинити локальний PostgreSQL перед запуском Docker:
# 🪟 Windows: services.msc → зупинити postgresql
# 🐧 Linux: sudo systemctl stop postgresql
# 🍎 macOS: brew services stop postgresql@16

# Потім:
docker compose up -d
```

#### ❌ Контейнер `backend` постійно перезапускається

**🛠️ Рішення:**
```bash
# Перевірити логи:
docker compose logs backend

# Часті причини:
# 1. Немає .env файлу → створіть backend/.env
# 2. Неправильний POSTGRES_HOST → має бути "db" (не "localhost")
# 3. Контейнер db ще не готовий → перезапустіть:
docker compose restart backend
```

---

### 7.7 🔴 Проблеми з Redis / Celery

#### ❌ Помилка: `Error 111 connecting to localhost:6379. Connection refused.`

**Причина:** Redis не запущений.

**🛠️ Рішення:**
```bash
# 🐧 Linux:
sudo systemctl start redis-server

# 🍎 macOS:
brew services start redis

# 🪟 Windows (WSL):
sudo service redis-server start

# 🪟 Windows (Memurai):
# Перевірте службу Memurai в services.msc
```

> 💡 **Примітка:** Якщо Redis не потрібен (не використовуєте Celery), просто видаліть або закоментуйте `CELERY_BROKER_URL` у `.env`.

---

### 7.8 📝 Шпаргалка швидкої діагностики

| 🔍 Проблема | 🛠️ Перше, що перевірити |
|-------------|------------------------|
| Не підключається до БД | `POSTGRES_HOST` у `.env` (`localhost` чи `db`?) |
| CORS помилка | `CORS_ORIGINS` у `.env` містить URL фронтенда? |
| `ModuleNotFoundError` | Чи активовано `(venv)`? |
| Порт зайнятий | Чи не запущено інший екземпляр? |
| Docker не працює | Чи запущений Docker Desktop? |
| Міграції не проходять | Чи існує база даних? Чи правильний пароль? |
| Frontend не збирається | `node --version` >= 18? `npm install` виконано? |
| 500 Internal Server Error | Перегляньте логи Django: `python manage.py runserver` |

---

## 📌 Корисні команди (шпаргалка)

### 🐍 Django

```bash
# Запуск сервера розробки
python manage.py runserver

# Створити міграції після зміни моделей
python manage.py makemigrations

# Застосувати міграції
python manage.py migrate

# Створити суперкористувача
python manage.py createsuperuser

# Створити групи ОЗ за ПКУ
python manage.py seed_asset_groups

# Django shell (інтерактивна консоль)
python manage.py shell

# Збір статичних файлів (для production)
python manage.py collectstatic --noinput
```

### ⚛️ Frontend (React + Vite)

```bash
# Встановити залежності
npm install

# Запустити dev-сервер
npm run dev

# Збірка для production
npm run build

# Попередній перегляд production-збірки
npm run preview

# Лінтер
npm run lint
```

### 🐳 Docker

```bash
# Запуск усіх сервісів
docker compose up -d --build

# Зупинка
docker compose down

# Логи
docker compose logs -f

# Виконати команду в контейнері
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser

# Перезбірка одного сервісу
docker compose up -d --build backend
```

---

## 🎉 Вітаємо!

Якщо ви дійшли до цього місця — система обліку основних засобів має бути повністю встановлена та працювати! 🚀

📧 Якщо у вас виникли питання, створіть Issue на GitHub або зверніться до команди розробки.

> 📄 **Ліцензія:** Цей проєкт створено для обліку основних засобів підприємства відповідно до законодавства України (ПКУ, П(С)БО 7).
