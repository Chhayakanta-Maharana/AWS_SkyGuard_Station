@echo off
title SkyGuard AI - LAN Data Sender Launcher
cd /d "%~dp0"

echo ========================================================
echo   SkyGuard AI - LAN Telemetry Data Sender Launcher
echo ========================================================
echo.

:: Kill any stale/hung sender instances
taskkill /f /im lan_data_sender.exe >nul 2>&1

:: Prefer direct Python execution if Python is in PATH
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] Launching LAN Data Sender via Python runtime...
    python lan_data_sender.py
    if %ERRORLEVEL% EQU 0 goto :DONE
)

:: Fallback to compiled standalone executable
if exist "lan_data_sender.exe" (
    echo [*] Launching compiled lan_data_sender.exe...
    start "" "lan_data_sender.exe"
    goto :DONE
)

echo [!] Error: Neither Python nor lan_data_sender.exe could be launched.
pause

:DONE
