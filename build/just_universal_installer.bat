@echo off
REM Compile the universal online installer (no PyInstaller build needed).
REM
REM This installer always downloads the latest version from GitHub.
REM Never needs recompiling - one installer works for all releases.
REM
REM Prerequisites:
REM   1. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAU-Setup.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist" mkdir dist

echo ============================================================
echo  Compiling universal online installer
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
"%MAKENSIS%" "/DROOT=%ROOT%" "installer\IsamAU-Universal.nsi"
if errorlevel 1 (
  echo.
  echo Installer build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Universal installer: dist\IsamAU-Setup.exe
echo  (Always downloads latest version - never needs recompile)
echo ============================================================
pause
