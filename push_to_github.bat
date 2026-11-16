@echo off
chcp 65001 >nul
title mic2pc - GitHub'a Yukle
cd /d "%~dp0"
set PATH=C:\Program Files\Git\cmd;%PATH%

echo ========================================================
echo              mic2pc - GITHUB'A YUKLEME ARACI
echo ========================================================
echo.
echo GitHub'da actiginiz reponun URL adresini yapistirin
echo (Ornek: https://github.com/kullanici_adiniz/mic2pc.git)
echo.
set /p REPO_URL="Repo URL: "

if "%REPO_URL%"=="" (
    echo [HATA] URL bos birakilamaz!
    pause
    exit /b
)

echo.
echo Git remote ayarlaniyor...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main

echo.
echo GitHub'a gonderiliyor (Push)...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [BASARILI] Kodlar GitHub'a gonderildi!
    echo Simdi GitHub reponuzdaki 'Actions' sekmesine gidin.
    echo 1-2 dakika icinde APK dosyaniz hazir olacaktir.
    echo ========================================================
) else (
    echo.
    echo [UYARI] Gonderim sirasinda bir hata olustu.
    echo GitHub girisinizin veya repo erisim izinlerinizin dogru oldugundan emin olun.
)

echo.
pause
