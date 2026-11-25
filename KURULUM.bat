@echo off
chcp 65001 >nul
title LoL Asistan - Kurulum
cd /d "%~dp0"
echo.
echo   LoL Asistan kuruluyor, bu bir-iki dakika surebilir...
echo.

set PY=
where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo   Python bulunamadi.
  echo   Acilan sayfadan Python 3.12'yi kur, kurulumda "Add Python to PATH" kutusunu isaretle,
  echo   sonra bu dosyayi tekrar calistir.
  start https://www.python.org/downloads/release/python-3128/
  pause
  exit /b 1
)

%PY% -m pip install --upgrade pip -q
%PY% -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo.
  echo   Paketler kurulamadi. Cok yeni bir Python surumu kullaniyorsan Python 3.12 ile tekrar dene.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%i in (`%PY% araclar\pythonw_yolu.py`) do set PYW=%%i

powershell -NoProfile -ExecutionPolicy Bypass -File "araclar\kisayol.ps1" -Pythonw "%PYW%" -Klasor "%~dp0."

echo.
echo   Tamam! Masaustundeki "LoL Asistan" kisayoluyla acabilirsin.
echo.
start "" "%PYW%" "%~dp0LoLAsistan.pyw"
timeout /t 4 >nul
