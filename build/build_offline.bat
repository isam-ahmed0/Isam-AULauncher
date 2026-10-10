@echo off
REM Build the offline installer for CrewLauncher.
REM
REM Requirements:
REM   1. Python on PATH with build\requirements.txt installed
REM   2. NSIS (Unicode) installed from https://nsis.sourceforge.io/Download
REM
REM Produces: dist\CrewLauncher-Setup-Offline.exe
setlocal
cd /d "%~dp0.."
set "ROOT=%CD%"

if not exist "dist" mkdir dist

REM Read version (sets VERSION + FILE_VERSION)
call "%~dp0_version.bat"
echo Using version: %VERSION% (file %FILE_VERSION%)

echo ============================================================
echo  [1/3] Building CrewLauncher
echo ============================================================
pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name CrewLauncher ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  --add-data "DOC;DOC" ^
  --add-data "release\bepmods.zip;." ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtWebEngineQuick ^
  --exclude-module PySide6.QtQuick ^
  --exclude-module PySide6.QtQuickWidgets ^
  --exclude-module PySide6.QtQml ^
  --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.Qt3DRender ^
  --exclude-module PySide6.Qt3DAnimation ^
  --exclude-module PySide6.Qt3DExtras ^
  --exclude-module PySide6.Qt3DInput ^
  --exclude-module PySide6.Qt3DLogic ^
  --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtDataVisualization ^
  --exclude-module PySide6.QtPdf ^
  --exclude-module PySide6.QtPdfWidgets ^
  --exclude-module PySide6.QtDesigner ^
  --exclude-module PySide6.QtTest ^
  --exclude-module PySide6.QtSql ^
  --exclude-module PySide6.QtBluetooth ^
  --exclude-module PySide6.QtNfc ^
  --exclude-module PySide6.QtPositioning ^
  --exclude-module PySide6.QtSerialPort ^
  --exclude-module PySide6.QtSensors ^
  --exclude-module PySide6.QtHelp ^
  --exclude-module PySide6.QtWebSockets ^
  --exclude-module PySide6.QtWebChannel ^
  --exclude-module dearpygui ^
  src\launcher\main.py || exit /b 1

echo.
echo ============================================================
echo  [2/3] Building Itch_Login_Fixer
echo ============================================================
pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name Itch_Login_Fixer ^
  --icon src\fixer\assets\icon.ico ^
  --hidden-import customtkinter ^
  --collect-submodules customtkinter ^
  src\fixer\Itch_Login_Fixer.py || exit /b 1

echo.
echo ============================================================
echo  [3/3] Compiling offline installer
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
"%MAKENSIS%" "/DROOT=%ROOT%" "/DVERSION=%VERSION%" "/DFILE_VERSION=%FILE_VERSION%" "installer\CrewLauncher.nsi"
if errorlevel 1 (
  echo.
  echo Offline installer build FAILED.
  exit /b 1
)

echo.
echo ============================================================
echo  Done! Offline installer: dist\CrewLauncher-Setup-Offline.exe (v%VERSION%)
echo ============================================================
pause
