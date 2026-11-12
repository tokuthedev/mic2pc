@echo off
chcp 65001 >nul
title mic2pc - USB Baglanti Yardimcisi
echo ========================================================
echo         mic2pc - USB DUSUK GECIKMELI BAGLANTI
echo ========================================================
echo.
echo En dusuk gecikme (1-3 ms) ve 0 paket kaybi icin:
echo.
echo [Yontem 1: USB Tethering (Onerilen ve En Hizlisi)]
echo 1. Telefonunuzu USB kablosu ile bilgisayara baglayin.
echo 2. Telefon Ayarlari ^> Baglantilar / Ag ^> 'USB Baglantisi / USB Tethering'i acin.
echo 3. Bilgisayarinizda yeni bir ag karti (NDIS/RNDIS) belirecektir.
echo 4. mic2pc PC alici uygulamasinda gorunen 192.168.42.x (veya benzeri)
echo    IP adresini mobil uygulamaya girin ve Baglan'a basin!
echo.
echo ========================================================
echo [Yontem 2: ADB Reverse TCP Port Yonlendirme]
echo Eger ADB ile TCP port yonlendirme yapmak isterseniz:
echo.
where adb >nul 2>nul
if %errorlevel% neq 0 (
    echo [UYARI] Sisteminizde 'adb' komutu bulunamadi.
    echo Android SDK platform-tools klasorunu PATH degiskenine ekleyin.
) else (
    echo ADB algilandi, port yonlendirmesi yapiliyor...
    adb reverse tcp:50005 tcp:50005
    echo ADB Reverse basarili: Telefon uygulamasinda IP olarak 127.0.0.1 girin.
)
echo.
pause
