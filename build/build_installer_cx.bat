@echo off
REM Build the Isam AULauncher installer with Cx_Freeze + NSIS.
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
echo  [1/3] Building with Cx_Freeze
echo ============================================================
python build\cx_setup.py build --build-exe=dist\IsamAULauncher_cx
if errorlevel 1 (
  echo.
  echo Cx_Freeze build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  [2/3] Verifying build output
echo ============================================================
if not exist "dist\IsamAULauncher_cx\IsamAULauncher.exe" (
  echo ERROR: dist\IsamAULauncher_cx\IsamAULauncher.exe not found
  exit /b 1
)
if not exist "dist\IsamAULauncher_cx\Itch_Login_Fixer.exe" (
  echo ERROR: dist\IsamAULauncher_cx\Itch_Login_Fixer.exe not found
  exit /b 1
)
echo Build output verified.

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
"%MAKENSIS%" "/DROOT=%ROOT%" "/DVERSION=%VERSION%" "/DBUILD_CX=1" "installer\IsamAULauncher.nsi"
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
