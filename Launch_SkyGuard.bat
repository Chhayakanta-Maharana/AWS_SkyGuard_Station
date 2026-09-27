@echo off
title DRDO AWS SkyGuard Station Launcher
cd /d "%~dp0"

echo ============================================================
echo      DRDO AWS SkyGuard Station - Ground Telemetry System
echo ============================================================
echo.

echo [1/3] Terminating any stale background instances...
taskkill /f /im AWS_SkyGuard_Station.exe >nul 2>&1
taskkill /f /im aws-telemetry-backend.exe >nul 2>&1

echo [2/3] Starting High-Performance Telemetry Engine...
start "" "backend\aws-telemetry-backend.exe" -port 8080 -static-dir "frontend\out"

timeout /t 1 >nul

echo [3/3] Opening SkyGuard Telemetry Dashboard...
start http://localhost:8080

if exist "dist\AWS_SkyGuard_Station.exe" (
    start "" "dist\AWS_SkyGuard_Station.exe"
)

echo.
echo ============================================================
echo  SkyGuard Station is LIVE at http://localhost:8080
echo ============================================================
timeout /t 3 >nul
exit
