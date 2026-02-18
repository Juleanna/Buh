@echo off
setlocal EnableDelayedExpansion

echo ================================================
echo   Oblik OZ -- Vstanovlennya program
echo   Python, Node.js, PostgreSQL
echo ================================================
echo.

:: -------------------------------------------------
:: 1. Perevirka prav administratora
:: -------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [UVAGA] Potribni prava administratora dlya vstanovlennya program.
    echo Perezapusk z pravamy administratora...
    echo.
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs"
    exit /b
)

echo [OK] Prava administratora pidtverdzheno.
echo.

:: -------------------------------------------------
:: 2. Perevirka winget
:: -------------------------------------------------
echo [1/6] Perevirka Windows Package Manager (winget)...

winget --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [POMYLKA] winget ne znajdeno!
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('winget --version') do echo   Znajdeno: winget %%v
echo.

:: -------------------------------------------------
:: 3. Python
:: -------------------------------------------------
echo [2/6] Perevirka Python...
set "PYTHON_INSTALLED=0"
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        echo   Vzhe vstanovleno: Python %%v
        set "PYTHON_INSTALLED=1"
    )
)

if "!PYTHON_INSTALLED!"=="0" (
    echo   Python ne znajdeno. Vstanovlennya Python 3.12...
    echo.
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [POMYLKA] Ne vdalosya vstanovyty Python.
        echo   Sprobujte vruchnu: https://www.python.org/downloads/
        echo   Pry vstanovlenni postavte galochku "Add Python to PATH"
        echo.
    ) else (
        echo   Python 3.12 vstanovleno.
        call :RefreshPath
    )
)
echo.

:: -------------------------------------------------
:: 4. Node.js
:: -------------------------------------------------
echo [3/6] Perevirka Node.js...
set "NODE_INSTALLED=0"
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   Vzhe vstanovleno: Node.js %%v
        set "NODE_INSTALLED=1"
    )
)

if "!NODE_INSTALLED!"=="0" (
    echo   Node.js ne znajdeno. Vstanovlennya Node.js LTS...
    echo.
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [POMYLKA] Ne vdalosya vstanovyty Node.js.
        echo   Sprobujte vruchnu: https://nodejs.org/
        echo.
    ) else (
        echo   Node.js LTS vstanovleno.
        call :RefreshPath
    )
)
echo.

:: -------------------------------------------------
:: 5. PostgreSQL
:: -------------------------------------------------
echo [4/6] Perevirka PostgreSQL...
set "PG_INSTALLED=0"
where psql >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do (
        echo   Vzhe vstanovleno: PostgreSQL %%v
        set "PG_INSTALLED=1"
    )
)

if "!PG_INSTALLED!"=="0" (
    echo   PostgreSQL ne znajdeno. Vstanovlennya PostgreSQL 16...
    echo.
    echo   [UVAGA] Pid chas vstanovlennya PostgreSQL zyavytsya vikno,
    echo   de potribno zadaty parol dlya korystuvacha postgres.
    echo   Zapamyatayte cej parol -- vin znadobytsya dlya backend\.env
    echo.
    winget install PostgreSQL.PostgreSQL.16 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo [POMYLKA] Ne vdalosya vstanovyty PostgreSQL.
        echo   Sprobujte vruchnu: https://www.postgresql.org/download/windows/
        echo.
    ) else (
        echo   PostgreSQL 16 vstanovleno.
        call :RefreshPath

        :: Dodaty PostgreSQL bin do PATH potochnoyi sesiyi
        set "PG_BIN=C:\Program Files\PostgreSQL\16\bin"
        if exist "!PG_BIN!\psql.exe" (
            set "PATH=!PATH!;!PG_BIN!"
            echo   Dodano do PATH: !PG_BIN!
        )

        :: Pereviryty sluzhbu
        echo   Perevirka sluzhby PostgreSQL...
        sc query postgresql-x64-16 >nul 2>&1
        if !errorlevel! equ 0 (
            echo   Sluzhba postgresql-x64-16 znajdena.
            net start postgresql-x64-16 2>nul
        ) else (
            echo   [UVAGA] Sluzhba PostgreSQL ne znajdena.
            echo   Mozhlyvo potribno perezavantazhyty kompyuter.
        )
    )
)
echo.

:: -------------------------------------------------
:: 6. Onovlennya PATH ta finalna veryfikaciya
:: -------------------------------------------------
echo [5/6] Onovlennya PATH...
call :RefreshPath

:: Dodaty PostgreSQL do PATH yakshcho ye na dysku ale nemaye v PATH
if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
    echo !PATH! | findstr /i "postgresql" >nul
    if !errorlevel! neq 0 (
        set "PATH=!PATH!;C:\Program Files\PostgreSQL\16\bin"
        echo   Dodano PostgreSQL do PATH potochnoyi sesiyi.
    )
)
echo.

echo [6/6] Veryfikaciya vstanovlennya...
echo.
echo   +--------------+-------------------------------+
echo   : Programa     : Status                        :

:: Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        echo   : Python       : %%v                       :
    )
) else (
    echo   : Python       : NE ZNAJDENO                   :
)

:: Node.js
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   : Node.js      : %%v                        :
    )
) else (
    echo   : Node.js      : NE ZNAJDENO                   :
)

:: PostgreSQL
where psql >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3 delims= " %%v in ('psql --version 2^>^&1') do (
        echo   : PostgreSQL   : %%v                       :
    )
) else (
    if exist "C:\Program Files\PostgreSQL\16\bin\psql.exe" (
        echo   : PostgreSQL   : Vstanovleno, potribn restart  :
    ) else (
        echo   : PostgreSQL   : NE ZNAJDENO                   :
    )
)

echo   +--------------+-------------------------------+
echo.

:: -------------------------------------------------
:: Perevirka chy vse vstanovleno
:: -------------------------------------------------
set "ALL_OK=1"
where python >nul 2>&1 || set "ALL_OK=0"
where node >nul 2>&1 || set "ALL_OK=0"

if "!ALL_OK!"=="1" (
    echo ================================================
    echo   Vsi programy vstanovleno!
    echo ================================================
    echo.
    echo   Nastupnyj krok -- zapustyty setup.bat
    echo.
    choice /C YN /M "Zapustyty setup.bat zaraz? (Y/N)"
    if !errorlevel! equ 1 (
        echo.
        call "%~dp0setup.bat"
    )
) else (
    echo.
    echo [UVAGA] Deyaki programy ne vstanovleno abo ne znajdeno v PATH.
    echo.
    echo   Mozhlyvi rishennya:
    echo   1. Zakryjte ce vikno i vidkryjte nove (dlya onovlennya PATH)
    echo   2. Perezavantazhte kompyuter
    echo   3. Zapustit cej skrypt povtorno
    echo.
    echo   Pislya togo yak use vstanovleno -- zapustit setup.bat
    echo.
)

pause
exit /b

:: -------------------------------------------------
:: Funkciya: Onovyty PATH z reyestru
:: -------------------------------------------------
:RefreshPath
for /f "tokens=2,*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%b"
if defined SYS_PATH if defined USR_PATH (
    set "PATH=!SYS_PATH!;!USR_PATH!"
) else if defined SYS_PATH (
    set "PATH=!SYS_PATH!"
)
exit /b
