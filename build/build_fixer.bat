@echo off
REM Build the Itch Login Fixer into a folder with all dependencies.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name Itch_Login_Fixer ^
  --icon src\fixer\assets\icon.ico ^
  --hidden-import customtkinter ^
  --collect-submodules customtkinter ^
  src\fixer\Itch_Login_Fixer.py

echo.
echo Built: dist\Itch_Login_Fixer\
pause
