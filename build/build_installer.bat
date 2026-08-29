@echo off
REM Build the Isam AULauncher installer with Nuitka + NSIS.
REM
REM Requirements:
REM   1. Python on PATH with build\requirements.txt installed
REM   2. MSVC (Visual Studio) or MinGW64 C compiler
REM   3. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAULauncher-Setup-0.1.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist" mkdir dist

echo ============================================================
echo  [1/3] Building IsamAULauncher.exe with Nuitka
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
  src\launcher\main.py || exit /b 1

echo.
echo ============================================================
echo  [2/3] Building Itch_Login_Fixer.exe
echo ============================================================
python -m nuitka --mode=onefile ^
  --windows-disable-console ^
  --windows-icon-from-ico=src\fixer\assets\icon.ico ^
  --output-dir=dist ^
  --output-filename=Itch_Login_Fixer.exe ^
  src\fixer\Itch_Login_Fixer.py || exit /b 1

echo.
echo ============================================================
echo  [3/3] Locating NSIS and compiling installer
echo ============================================================
set "MAKENSIS="
if exist "%ProgramFiles(x86)%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if exist "%ProgramFiles%\NSIS\makensis.exe" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not defined MAKENSIS (
  echo NSIS was not found in the default install locations.
  echo Install it from: https://nsis.sourceforge.io/Download
  exit /b 1
)

echo Using: %MAKENSIS%
"%MAKENSIS%" "/DROOT=%ROOT%" "installer\IsamAULauncher.nsi"
if errorlevel 1 (
  echo.
  echo Installer build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Installer: dist\IsamAULauncher-Setup-0.1.exe
echo ============================================================
pause
