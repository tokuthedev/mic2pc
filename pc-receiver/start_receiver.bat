@echo off
title mic2pc Receiver
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Python sanal ortami bulunamadi, olusturuluyor...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)

echo mic2pc Receiver baslatiliyor...
venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo.
    echo Bir hata olustu.
    pause
)
