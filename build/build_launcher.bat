@echo off
REM Build Isam AULauncher into a single windowed exe.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

pyinstaller --noconfirm --onefile --windowed ^
  --name IsamAULauncher ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  --collect-all dearpygui ^
  src\launcher\main.py

echo.
echo Built: dist\IsamAULauncher.exe
pause