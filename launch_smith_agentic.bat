@echo off
title SmithAgentic
echo Starting SmithAgentic...
cd /d "%~dp0"

echo Clearing port 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

start "SmithAgentic Server" cmd /k python ui\server.py
timeout /t 4 /nobreak >nul
start "" "http://localhost:8765"
