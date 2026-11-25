@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title LoL Asistan - Kurulum
cd /d "%~dp0"
echo.
echo   LoL Asistan kuruluyor...
echo.

call :python_bul
if not defined PY (
  echo   Python bulunamadi. Otomatik kuruluyor, 1-3 dakika surebilir...
  echo.
  call :python_kur
  call :python_bul
)
if not defined PY (
  echo.
  echo   Python otomatik kurulamadi.
  echo   Acilan sayfadan Python 3.12'yi elle kur ^(ilk ekranda "Add Python to PATH" kutusunu isaretle^),
  echo   sonra bu dosyayi tekrar calistir.
  start https://www.python.org/downloads/release/python-31210/
  pause
  exit /b 1
)
echo   Python hazir: !PY!
echo.
echo   Gerekli paketler kuruluyor...
"!PY!" -m pip install --upgrade pip -q --disable-pip-version-check
"!PY!" -m pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
  echo.
  echo   Paketler kurulamadi. Internet baglantini kontrol edip tekrar dene.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%i in (`"!PY!" araclar\pythonw_yolu.py`) do set "PYW=%%i"
powershell -NoProfile -ExecutionPolicy Bypass -File "araclar\kisayol.ps1" -Pythonw "!PYW!" -Klasor "%~dp0."

echo.
echo   Tamam! Masaustundeki "LoL Asistan" kisayoluyla acabilirsin.
echo.
start "" "!PYW!" "%~dp0LoLAsistan.pyw"
timeout /t 4 >nul
exit /b 0


rem ---------- Uygun Python'u bul (3.10 - 3.13) ----------
:python_bul
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>nul
    if not errorlevel 1 for /f "usebackq delims=" %%i in (`py -%%V araclar\python_yolu.py`) do set "PY=%%i"
  )
)
if defined PY exit /b 0
python -c "import sys" >nul 2>nul
if not errorlevel 1 for /f "usebackq delims=" %%i in (`python araclar\python_yolu.py`) do set "PY=%%i"
if defined PY exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b 0


rem ---------- Python 3.12'yi otomatik kur ----------
:python_kur
where winget >nul 2>nul
if not errorlevel 1 (
  echo   Windows paket yoneticisi ^(winget^) ile kuruluyor...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" exit /b 0

echo   python.org'dan indiriliyor...
set "KURULUM_EXE=%TEMP%\python-3.12.10-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $env:KURULUM_EXE"
if not exist "%KURULUM_EXE%" exit /b 1
echo   Kuruluyor...
"%KURULUM_EXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_doc=0
del "%KURULUM_EXE%" >nul 2>nul
exit /b 0
