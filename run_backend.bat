@echo off
title SHRAMRAKSHAK Backend Server
cd /d "%~dp0backend"
echo ========================================================
echo Starting SHRAMRAKSHAK FastAPI Backend on 0.0.0.0:8000
echo ========================================================
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
