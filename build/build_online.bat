@echo off
REM Build the Isam AULauncher ONLINE installer with NSIS.
REM
REM Requirements:
REM   1. Python on PATH (or activate your venv) with build\requirements.txt installed
REM   2. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\IsamAU-Online.exe (downloads files from GitHub at install time)
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
echo  [1/4] Building IsamAULauncher
echo ============================================================
pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name IsamAULauncher ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  --add-data "release\bepmods.zip;." ^
  src\launcher\main.py || exit /b 1

echo.
echo ============================================================
echo  [2/4] Building Itch_Login_Fixer
echo ============================================================
pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name Itch_Login_Fixer ^
  --icon src\fixer\assets\icon.ico ^
  --hidden-import customtkinter ^
  --collect-submodules customtkinter ^
  src\fixer\Itch_Login_Fixer.py || exit /b 1

echo.
echo ============================================================
echo  [3/4] Creating IsamAU-All.zip for online installer
echo ============================================================
set "SEVENZ="
where 7z >nul 2>&1 && set "SEVENZ=7z"
if not defined SEVENZ if exist "%ProgramFiles%\7-Zip\7z.exe" set "SEVENZ=%ProgramFiles%\7-Zip\7z.exe"
if not defined SEVENZ if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SEVENZ=%ProgramFiles(x86)%\7-Zip\7z.exe"
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
echo  [4/4] Compiling online installer
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
