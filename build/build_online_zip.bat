@echo off
REM Create IsamAU-All.zip and compile the online installer.
REM
REM Prerequisites: PyInstaller builds must already exist in dist\
REM   (run build_installer.bat or build_online.bat steps 1-2 first)
REM
REM Requires:
REM   1. 7-Zip on PATH or in Program Files
REM   2. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAU-All.zip + dist\IsamAU-Online.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist\IsamAULauncher" (
  echo ERROR: dist\IsamAULauncher not found. Run PyInstaller builds first.
  exit /b 1
)
if not exist "dist\Itch_Login_Fixer" (
  echo ERROR: dist\Itch_Login_Fixer not found. Run PyInstaller builds first.
  exit /b 1
)

REM Read version from config.py
set "VERSION="
for /f "tokens=2 delims== " %%v in ('findstr /B "LAUNCHER_VERSION =" src\launcher\config.py') do set "VERSION=%%~v"
set "VERSION=%VERSION:"=%"
if not defined VERSION set "VERSION=0.1"
echo Using version: %VERSION%

echo ============================================================
echo  [1/2] Creating IsamAU-All.zip
echo ============================================================
set "SEVENZ="
if exist "%ProgramFiles%\7-Zip\7z.exe" set "SEVENZ=%ProgramFiles%\7-Zip\7z.exe"
if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SEVENZ=%ProgramFiles(x86)%\7-Zip\7z.exe"
if not defined SEVENZ (
  echo 7-Zip not found. Install from: https://www.7-zip.org/
  exit /b 1
)

echo Using: %SEVENZ%
"%SEVENZ%" a -tzip "%ROOT%\dist\IsamAU-All.zip" ^
  "%ROOT%\dist\IsamAULauncher\" ^
  "%ROOT%\dist\Itch_Login_Fixer\" ^
  "%ROOT%\release\7z.exe" ^
  "%ROOT%\release\bepmods.zip" || exit /b 1
echo Created dist\IsamAU-All.zip

echo.
echo ============================================================
echo  [2/2] Compiling online installer
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
  echo Online installer build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Online installer: dist\IsamAU-Online.exe (v%VERSION%)
echo ============================================================
pause
