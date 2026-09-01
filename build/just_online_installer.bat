@echo off
REM Compile the online NSIS installer only (no PyInstaller build).
REM
REM Prerequisites:
REM   1. dist\IsamAU-All.zip already uploaded as a GitHub Release asset
REM   2. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAU-Setup.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist" mkdir dist

REM Read version from config.py
set "VERSION="
for /f "tokens=2 delims== " %%v in ('findstr /B "LAUNCHER_VERSION =" src\launcher\config.py') do set "VERSION=%%~v"
set "VERSION=%VERSION:"=%"
if not defined VERSION set "VERSION=0.1"
echo Using version: %VERSION%

echo ============================================================
echo  Locating NSIS and compiling online installer
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
"%MAKENSIS%" "/DROOT=%ROOT%" "/DVERSION=%VERSION%" "installer\IsamAU-Online.nsi"
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
