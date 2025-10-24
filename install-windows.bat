@echo off
REM ============================================================
REM SMS Daemon Windows Service Installer
REM This script installs the SMS daemon as a Windows service
REM ============================================================

echo ============================================================
echo SMS Daemon Windows Service Installer
echo ============================================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get the script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
echo SMS Daemon directory: %SCRIPT_DIR%
echo.

REM Check if required files exist
if not exist "%SCRIPT_DIR%\sms_sender.py" (
    echo ERROR: sms_sender.py not found in %SCRIPT_DIR%
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%\config.py" (
    echo ERROR: config.py not found!
    echo Please copy config.py.example to config.py and configure it first
    pause
    exit /b 1
)

REM Find Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python and add it to PATH
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set PYTHON_BIN=%%i
echo Python found: %PYTHON_BIN%
echo.

REM Check and install dependencies
echo Checking Python dependencies...
python -c "import serial" >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing pyserial...
    python -m pip install pyserial
)

python -c "import mysql.connector" >nul 2>&1
if %errorLevel% neq 0 (
    echo Installing mysql-connector-python...
    python -m pip install mysql-connector-python
)

REM Install NSSM (Non-Sucking Service Manager) for Windows service
echo.
echo Installing NSSM (Windows Service Manager)...
if not exist "%SCRIPT_DIR%\nssm.exe" (
    echo.
    echo NSSM not found. Please download NSSM from:
    echo https://nssm.cc/download
    echo.
    echo Download nssm-2.24.zip, extract nssm.exe from win64 folder,
    echo and place it in: %SCRIPT_DIR%
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

echo Dependencies OK
echo.

REM Stop and remove existing service if it exists
echo Checking for existing service...
sc query "SMSDaemon" >nul 2>&1
if %errorLevel% equ 0 (
    echo Stopping existing service...
    net stop SMSDaemon >nul 2>&1
    echo Removing existing service...
    "%SCRIPT_DIR%\nssm.exe" remove SMSDaemon confirm >nul 2>&1
)

REM Install the service
echo Installing SMS Daemon service...
"%SCRIPT_DIR%\nssm.exe" install SMSDaemon "%PYTHON_BIN%" "%SCRIPT_DIR%\sms_sender.py"

REM Configure service
echo Configuring service...
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppDirectory "%SCRIPT_DIR%"
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon DisplayName "SMS Daemon Service"
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon Description "Sends SMS messages via GSM modem from MySQL database"
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon Start SERVICE_AUTO_START
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppStdout "%SCRIPT_DIR%\logs\service-stdout.log"
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppStderr "%SCRIPT_DIR%\logs\service-stderr.log"
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppRotateFiles 1
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppRotateOnline 1
"%SCRIPT_DIR%\nssm.exe" set SMSDaemon AppRotateBytes 5242880

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Service Commands:
echo   Start service:   net start SMSDaemon
echo   Stop service:    net stop SMSDaemon
echo   Restart service: net stop SMSDaemon ^&^& net start SMSDaemon
echo   View status:     sc query SMSDaemon
echo   Remove service:  nssm remove SMSDaemon confirm
echo.
echo Service Manager:
echo   Configure:       nssm edit SMSDaemon
echo   View logs:       type logs\service-stdout.log
echo   View errors:     type logs\service-stderr.log
echo.
echo Next Steps:
echo   1. Configure config.py with your settings
echo   2. Start service: net start SMSDaemon
echo   3. Check status: sc query SMSDaemon
echo   4. View logs: python view_logs.py
echo.
pause
