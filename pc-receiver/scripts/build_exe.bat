@echo off
title mic2pc - Build Executable
cd /d "%~dp0..\.."

echo ========================================================
echo               mic2pc - EXE OLUSTURUCU
echo ========================================================
echo.
echo Bagimliliklar kontrol ediliyor...
cd pc-receiver
call .\venv\Scripts\activate.bat
pip install pyinstaller -q

echo.
echo mic2pc.exe derleniyor (Tek dosya, ikonlu, penceresiz)...
pyinstaller --noconsole --onefile --name "mic2pc" --icon "icon.ico" --add-data "icon.png;." --add-data "icon.ico;." --add-data "fonts;fonts" --collect-all customtkinter --clean main.py

if exist "dist\mic2pc.exe" (
    copy /Y "dist\mic2pc.exe" "..\mic2pc.exe"
    echo.
    echo ========================================================
    echo [BASARILI] mic2pc.exe ana dizine olusturuldu!
    echo ========================================================
) else (
    echo.
    echo [HATA] Derleme basarisiz oldu.
)

pause
