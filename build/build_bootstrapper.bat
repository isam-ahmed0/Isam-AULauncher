@echo off
REM Build the console bootstrapper into a single exe.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

pyinstaller --noconfirm --onefile --console --noupx ^
  --name IsamAULauncherBootstrapper ^
  --version-file build\version_info_bootstrapper.txt ^
  src\bootstrapper\bootstrapper.py

echo.
echo Built: dist\IsamAULauncherBootstrapper.exe
pause
