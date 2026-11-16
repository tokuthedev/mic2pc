@echo off
chcp 65001 >nul
title mic2pc - Guvenlik Duvari Kalici Izin Araci

:: Yonetici haklari kontrolu ve otomatik isteme
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Yonetici izinleri aliniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ========================================================
echo           mic2pc - GUVENLIK DUVARI KALICI IZIN
echo ========================================================
echo.
echo UDP 50005 portu Windows Guvenlik Duvari'na kalici olarak ekleniyor...
echo.

:: Varsa eski kurali kaldir ve temiz kural ekle
netsh advfirewall firewall delete rule name="mic2pc UDP 50005" >nul 2>&1
netsh advfirewall firewall add rule name="mic2pc UDP 50005" dir=in action=allow protocol=UDP localport=50005 profile=any

if %errorlevel% equ 0 (
    echo ========================================================
    echo [BASARILI] UDP 50005 portuna kalici izin verildi!
    echo Windows artik bir daha ASLA guvenlik duvari penceresi
    echo acmayacak veya onay istemeyecektir.
    echo ========================================================
) else (
    echo [HATA] Kural eklenemedi. Lutfen yonetici olarak calistirin.
)

echo.
pause
