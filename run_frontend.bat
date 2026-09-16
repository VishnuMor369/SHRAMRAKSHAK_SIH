@echo off
title SHRAMRAKSHAK Frontend Server
cd /d "%~dp0frontend"
echo ========================================================
echo Starting SHRAMRAKSHAK React Frontend on 0.0.0.0:5173
echo ========================================================
call npm.cmd run dev
pause
