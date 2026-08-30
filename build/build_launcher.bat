@echo off
REM Build Isam AULauncher into a folder with all dependencies.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name IsamAULauncher ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  src\launcher\main.py

echo.
echo Built: dist\IsamAULauncher\
pause
