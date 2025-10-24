@echo off
REM ============================================================
REM SMS Daemon Windows Service Uninstaller
REM ============================================================

echo ============================================================
echo SMS Daemon Windows Service Uninstaller
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

REM Check if service exists
sc query "SMSDaemon" >nul 2>&1
if %errorLevel% neq 0 (
    echo Service not found. Nothing to uninstall.
    pause
    exit /b 0
)

echo Stopping service...
net stop SMSDaemon >nul 2>&1

if exist "%SCRIPT_DIR%\nssm.exe" (
    echo Removing service...
    "%SCRIPT_DIR%\nssm.exe" remove SMSDaemon confirm
) else (
    echo Removing service...
    sc delete SMSDaemon
)

echo.
echo ============================================================
echo Uninstallation Complete!
echo ============================================================
echo.
echo The SMS Daemon service has been removed.
echo Your files in the installation directory are still intact.
echo.
pause
