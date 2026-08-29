@echo off
REM Build Isam AULauncher into a single windowed exe using Nuitka.
REM Run this on Windows after: pip install -r requirements.txt
REM Requires: MSVC (Visual Studio) or MinGW64 C compiler
cd /d "%~dp0.."

if not exist "dist" mkdir dist

echo ============================================================
echo  Building IsamAULauncher.exe with Nuitka...
echo  (First build takes 5-15 minutes, subsequent builds are faster)
echo ============================================================
python -m nuitka --mode=onefile ^
  --include-package=ui ^
  --include-package=config ^
  --include-package=network ^
  --include-package=file_manager ^
  --windows-disable-console ^
  --windows-icon-from-ico=src\launcher\resources\icon.ico ^
  --output-dir=dist ^
  --output-filename=IsamAULauncher.exe ^
  src\launcher\main.py

echo.
echo Built: dist\IsamAULauncher.exe
pause
