@echo off
REM Build the Isam AULauncher installer with NSIS.
REM
REM Requirements:
REM   1. Python on PATH (or activate your venv) with build\requirements.txt installed
REM   2. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAU-Setup.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist" mkdir dist

REM Read version from config.py
set "VERSION="
for /f "tokens=2 delims== " %%v in ('findstr "LAUNCHER_VERSION" src\launcher\config.py') do set "VERSION=%%~v"
set "VERSION=%VERSION:"=%"
if not defined VERSION set "VERSION=0.1"
echo Using version: %VERSION%

echo ============================================================
echo  [1/4] Building IsamAULauncher.exe
echo ============================================================
pyinstaller --noconfirm --onefile --windowed --noupx ^
  --name IsamAULauncher ^
  --icon src\launcher\resources\icon.ico ^
  --version-file build\version_info.txt ^
  --manifest build\app.manifest ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  src\launcher\main.py || exit /b 1

echo.
echo ============================================================
echo  [2/4] Building Itch_Login_Fixer.exe
echo ============================================================
pyinstaller --noconfirm --onefile --windowed --noupx ^
  --name Itch_Login_Fixer ^
  --icon src\fixer\assets\icon.ico ^
  --version-file build\version_info_fixer.txt ^
  --manifest build\app.manifest ^
  --hidden-import customtkinter ^
  --collect-submodules customtkinter ^
  src\fixer\Itch_Login_Fixer.py || exit /b 1

echo.
echo ============================================================
echo  [3/4] Fixing PE checksums
echo ============================================================
python scripts\fix_pe_checksum.py dist\IsamAULauncher.exe dist\Itch_Login_Fixer.exe

echo.
echo ============================================================
echo  [4/4] Locating NSIS and compiling installer
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
"%MAKENSIS%" "/DROOT=%ROOT%" "/DVERSION=%VERSION%" "installer\IsamAULauncher.nsi"
if errorlevel 1 (
  echo.
  echo Installer build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Installer: dist\IsamAU-Setup.exe (v%VERSION%)
echo ============================================================
pause
