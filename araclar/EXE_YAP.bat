@echo off
chcp 65001 >nul
REM İsteğe bağlı: Python'a ihtiyaç duymayan tek bir LoLAsistan.exe üretir (dist klasörüne).
cd /d "%~dp0.."
set PY=py
where py >nul 2>nul || set PY=python
%PY% -m pip install -q pyinstaller -r requirements.txt
%PY% -m PyInstaller --noconfirm --onefile --windowed --name LoLAsistan --icon ikon.ico ^
  --add-data "data;data" --add-data "ui;ui" LoLAsistan.pyw
echo.
echo   Hazir: dist\LoLAsistan.exe
pause
