@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

title Slide Beautifier Backend

echo ==========================================
echo   Slide Beautifier Backend Launcher
echo ==========================================
echo.

set ADB=F:\as\platform-tools\adb.exe
set PORT=8080
set HOST=0.0.0.0

echo Backend folder:
echo %cd%
echo.

echo [1/6] Checking adb...

if not exist "%ADB%" (
    echo adb.exe not found:
    echo %ADB%
    echo.
    echo Backend will start without adb reverse.
    goto PYTHON_SETUP
)

echo adb found:
echo %ADB%
echo.

echo [2/6] Starting adb server...
"%ADB%" start-server

echo.
echo Current devices:
"%ADB%" devices
echo.

echo [3/6] Finding first online Android device...

set DEVICE_SERIAL=

REM Retry up to 15 times. Only accept status exactly "device".
REM Ignore offline / unauthorized / header lines.
for /l %%I in (1,1,15) do (
    for /f "skip=1 tokens=1,2" %%A in ('"%ADB%" devices') do (
        if "%%B"=="device" (
            set DEVICE_SERIAL=%%A
            goto FOUND_DEVICE
        )
    )

    echo No online device found yet. Waiting...
    timeout /t 2 /nobreak >nul
)

:FOUND_DEVICE

if "%DEVICE_SERIAL%"=="" (
    echo.
    echo No online Android device found.
    echo adb reverse was NOT set.
    echo.
    echo Make sure:
    echo 1. Emulator is already opened
    echo 2. It entered Android home screen
    echo 3. adb devices shows status: device
    echo.
    goto PYTHON_SETUP
)

echo.
echo Online device selected:
echo %DEVICE_SERIAL%
echo.

echo [4/6] Setting adb reverse...
echo Mapping Android 127.0.0.1:%PORT% to PC 127.0.0.1:%PORT%
echo.

"%ADB%" -s %DEVICE_SERIAL% reverse --remove-all
"%ADB%" -s %DEVICE_SERIAL% reverse tcp:%PORT% tcp:%PORT%

if errorlevel 1 (
    echo.
    echo adb reverse FAILED.
    echo Try manually:
    echo "%ADB%" -s %DEVICE_SERIAL% reverse tcp:%PORT% tcp:%PORT%
    echo.
) else (
    echo adb reverse set successfully.
)

echo.
echo Reverse list:
"%ADB%" -s %DEVICE_SERIAL% reverse --list
echo.

:PYTHON_SETUP

echo [5/6] Setting up Python environment...

if not exist .venv (
    echo Creating .venv...
    python -m venv .venv
)

echo.
echo Activating .venv...
call .venv\Scripts\activate

echo.
echo Installing requirements...
python -m pip install -r requirements.txt

echo.
echo [6/6] Starting FastAPI backend...
echo.
echo Browser test:
echo http://localhost:%PORT%/api/health
echo.
echo Android Constants.kt should use:
echo http://127.0.0.1:%PORT%/
echo.

uvicorn main:app --host %HOST% --port %PORT% --reload

pause