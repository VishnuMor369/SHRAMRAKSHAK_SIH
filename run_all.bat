@echo off
title SHRAMRAKSHAK One-Click Demo Launcher
cd /d "%~dp0"
echo ========================================================
echo  SHRAMRAKSHAK: AI-Powered SIF Intelligence Launcher
echo ========================================================
echo Starting Backend in separate window...
start "SHRAMRAKSHAK Backend (Port 8000)" /D "%~dp0" cmd /k "call run_backend.bat"
ping -n 4 127.0.0.1 >nul
echo Starting Frontend in separate window...
start "SHRAMRAKSHAK Frontend (Port 5173)" /D "%~dp0" cmd /k "call run_frontend.bat"
echo.
echo Both servers are starting up!
echo Laptop Dashboard:  http://localhost:5173
echo Mobile Supervisor: http://localhost:5173/supervisor
echo ========================================================
