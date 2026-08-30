@echo off
REM Build Isam AULauncher Lite - DPG GUI, no splash, fast startup.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name IsamAULauncher_Lite ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  src\launcher\main_lite.py

echo.
echo Built: dist\IsamAULauncher_Lite\
pause
