@echo off
REM Build the Itch Login Fixer into a single windowed exe.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

pyinstaller --noconfirm --onefile --windowed ^
  --name Itch_Login_Fixer ^
  --icon src\fixer\assets\icon.ico ^
  src\fixer\Itch_Login_Fixer.py

echo.
echo Built: dist\Itch_Login_Fixer.exe
pause