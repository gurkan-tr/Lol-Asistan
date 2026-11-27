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
  echo   Python otomatik kurulamadi. Ayrintilar: kurulum_log.txt
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
set "LOG=%~dp0kurulum_log.txt"
echo [%date% %time%] Python kurulumu basladi > "%LOG%"

rem 1) winget
where winget >nul 2>nul
if not errorlevel 1 (
  echo   Windows paket yoneticisi ^(winget^) ile kuruluyor...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
  echo winget cikis kodu: !errorlevel! >> "%LOG%"
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" exit /b 0

rem 2) python.org'dan indir: once Windows'un kendi curl'u, olmazsa PowerShell (TLS 1.2 zorunlu)
set "KURULUM_EXE=%TEMP%\python-3.12.10-amd64.exe"
set "URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
del "%KURULUM_EXE%" >nul 2>nul
echo   python.org'dan indiriliyor...
where curl >nul 2>nul
if not errorlevel 1 curl.exe -L --fail --retry 3 -o "%KURULUM_EXE%" "%URL%" >> "%LOG%" 2>&1
rem Yarim inmis (cok kucuk) dosyayi sil
if exist "%KURULUM_EXE%" for %%A in ("%KURULUM_EXE%") do if %%~zA LSS 1000000 del "%KURULUM_EXE%"
if not exist "%KURULUM_EXE%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri $env:URL -OutFile $env:KURULUM_EXE" >> "%LOG%" 2>&1
)
if not exist "%KURULUM_EXE%" (
  echo   Indirme basarisiz. Ayrintilar: kurulum_log.txt
  echo indirme basarisiz >> "%LOG%"
  exit /b 1
)

rem 3) Kur: ilerleme penceresi gorunur, hata olursa kullanici gorur
echo   Kuruluyor ^(acilan Python penceresini kapatma^)...
"%KURULUM_EXE%" /passive InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_doc=0 /log "%TEMP%\python_kurulum.log"
echo python kurulum cikis kodu: !errorlevel! >> "%LOG%"
if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
  echo   Sessiz kurulum olmadi, Python kurulum penceresi aciliyor.
  echo   Pencerede "Add python.exe to PATH" kutusunu isaretleyip "Install Now"a bas.
  "%KURULUM_EXE%" PrependPath=1 Include_launcher=1
)
del "%KURULUM_EXE%" >nul 2>nul
exit /b 0
