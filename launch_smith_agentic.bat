@echo off
title SmithAgentic
echo Starting SmithAgentic...
cd /d C:\Users\asmith\Documents\Github\Smith_Agentic

echo Clearing port 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

set PYTHON=C:\Users\asmith\AppData\Local\anaconda3\python.exe

start "SmithAgentic Server" cmd /k "%PYTHON%" ui\server.py
timeout /t 4 /nobreak >nul
start "" "http://localhost:8765"
