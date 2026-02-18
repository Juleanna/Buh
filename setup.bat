@echo off
echo ================================================
echo   Oblik OZ -- Povne vstanovlennya z nulya
echo ================================================
echo.

:: -------------------------------------------------
:: 1. Perevirka Python
:: -------------------------------------------------
echo [1/8] Perevirka Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [POMYLKA] Python ne znajdeno!
    echo   Vstanovit Python 3.11+ z https://www.python.org/downloads/
    echo   Pry vstanovlenni obovyazkovo postavte galochku "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo   Znajdeno: Python %%v
echo.

:: -------------------------------------------------
:: 2. Perevirka Node.js
:: -------------------------------------------------
echo [2/8] Perevirka Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [POMYLKA] Node.js ne znajdeno!
    echo   Vstanovit Node.js 18+ z https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do echo   Znajdeno: Node.js %%v
echo.

:: -------------------------------------------------
:: 3. Perevirka PostgreSQL
:: -------------------------------------------------
echo [3/8] Perevirka PostgreSQL...
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [UVAGA] psql ne znajdeno v PATH.
    echo   Yakshcho PostgreSQL vstanovlenyj, dodajte shlyakh do bin u zminnu PATH.
    echo   Typovyj shlyakh: C:\Program Files\PostgreSQL\16\bin
    echo.
    echo   Abo stvorit bazu danykh vruchnu:
    echo   CREATE DATABASE buh_assets ENCODING 'UTF8';
    echo.
    set SKIP_DB=1
) else (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do echo   Znajdeno: PostgreSQL %%v
    set SKIP_DB=0
)
echo.

:: -------------------------------------------------
:: 4. Nalashtuvannya .env
:: -------------------------------------------------
echo [4/8] Nalashtuvannya konfiguracii...
cd /d "%~dp0backend"

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   Stvoreno .env z shablonu .env.example
    ) else (
        echo   Stvoryuyu .env z nalashtuvannyamy za zamovchuvanniam...
        (
            echo ## Nalashtuvannya systemy obliku osnovnykh zasobiv
            echo.
            echo # Django
            echo DJANGO_SECRET_KEY=django-insecure-auto-generated-%RANDOM%%RANDOM%%RANDOM%
            echo DEBUG=True
            echo.
            echo # PostgreSQL
            echo POSTGRES_DB=buh_assets
            echo POSTGRES_USER=postgres
            echo POSTGRES_PASSWORD=your_password_here
            echo POSTGRES_HOST=localhost
            echo POSTGRES_PORT=5432
            echo.
            echo # CORS
            echo CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
        ) > .env
    )
    echo.
    echo   *** VAZHLYVO: vidredagujte backend\.env ***
    echo   Vstanovit parol PostgreSQL (POSTGRES_PASSWORD)
    echo.
    notepad .env
    echo   Natysnit bud-yaku klavishu pislya zberezhennya .env...
    pause >nul
) else (
    echo   .env vzhe isnuye -- propuskayu.
)
echo.

:: -------------------------------------------------
:: 5. Python venv + zalezhnosti
:: -------------------------------------------------
echo [5/8] Stvorennya Python-seredovyshcha ta vstanovlennya zalezhnostej...

if exist "venv" (
    echo   Vydalyayu stare seredovyshche...
    rmdir /s /q venv
)
python -m venv venv
if %errorlevel% neq 0 (
    echo [POMYLKA] Ne vdalosya stvoryty virtualne seredovyshche
    pause
    exit /b 1
)
echo   Virtualne seredovyshche stvoreno.

call venv\Scripts\activate.bat
echo   Onovlennya pip...
python -m pip install --upgrade pip --quiet
echo   Vstanovlennya Python-zalezhnostej (ce mozhe zajnyaty kilka khvylyn)...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo.
    echo [POMYLKA] Ne vdalosya vstanovyty Python-zalezhnosti
    echo   Sprobujte vruchnu: cd backend ^& venv\Scripts\activate ^& pip install -r requirements.txt
    pause
    exit /b 1
)
echo   Python-zalezhnosti vstanovleno.
echo.

:: -------------------------------------------------
:: 6. Stvorennya bazy danykh
:: -------------------------------------------------
echo [6/8] Stvorennya bazy danykh ta migracii...

:: Sprobuvatystvoryty BD yakshcho psql dostupnyj
if "%SKIP_DB%"=="0" (
    echo   Sproba stvoryty bazu danykh buh_assets...

    :: Chytayemo dani z .env
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_USER" .env') do set "PGUSER=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_HOST" .env') do set "PGHOST=%%b"
    for /f "tokens=1,* delims==" %%a in ('findstr "POSTGRES_PORT" .env') do set "PGPORT=%%b"

    psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE buh_assets ENCODING 'UTF8';" 2>nul
    if %errorlevel% equ 0 (
        echo   Baza danykh buh_assets stvorena.
    ) else (
        echo   Baza danykh vzhe isnuye abo ne vdalosya stvoryty -- prodovzhuyu.
    )
)

echo   Vykonannya migracij...
python manage.py makemigrations accounts assets documents reports 2>nul
python manage.py migrate
if %errorlevel% neq 0 (
    echo.
    echo [POMYLKA] Migracii ne vdalysya. Pereverte:
    echo   1. PostgreSQL zapushchenyj
    echo   2. Baza danykh buh_assets isnuye
    echo   3. Nalashtuvannya v backend\.env korektni
    echo.
    echo   Stvoryty BD vruchnu: psql -U postgres -c "CREATE DATABASE buh_assets;"
    pause
    exit /b 1
)
echo   Migracii vykonano uspishno.
echo.

:: -------------------------------------------------
:: 7. Pochatkovi dani + superkorystuvach
:: -------------------------------------------------
echo [7/8] Zapovnennya pochatkovykh danykh...
python manage.py seed_asset_groups
echo   16 grup OZ zgidno PKU st. 138.3.3 stvoreno.
echo.

echo   Stvorennya superkorystuvacha (administratora):
echo   Vvedit login, email ta parol
echo.
python manage.py createsuperuser
echo.

:: -------------------------------------------------
:: 8. Frontend
:: -------------------------------------------------
echo [8/8] Vstanovlennya frontend-zalezhnostej...
cd /d "%~dp0frontend"

if exist "node_modules" (
    echo   Vydalyayu stari node_modules...
    rmdir /s /q node_modules
)

call npm install
if %errorlevel% neq 0 (
    echo.
    echo [POMYLKA] npm install ne vdavsya
    echo   Sprobujte vruchnu: cd frontend ^& npm install
    pause
    exit /b 1
)
echo   Frontend-zalezhnosti vstanovleno.
echo.

:: -------------------------------------------------
:: Gotovo!
:: -------------------------------------------------
echo.
echo ================================================
echo   Vstanovlennya zaversheno uspishno!
echo ================================================
echo.
echo   Dlya zapusku systemy:
echo.
echo     start.bat          -- zapustyty Backend + Frontend
echo     start-backend.bat  -- tilky Django server
echo     start-frontend.bat -- tilky React dev-server
echo     stop.bat           -- zupynyty vse
echo.
echo   Vidkryjte: http://localhost:5173
echo.
pause
