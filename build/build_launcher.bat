@echo off
REM Build CrewLauncher into a folder with all dependencies.
REM Run this on Windows after: pip install -r requirements.txt
cd /d "%~dp0.."

if not exist "dist" mkdir dist

REM Web assets (Astro) are not committed; build them on demand.
where npm >nul 2>nul
if %errorlevel% equ 0 (
  echo Building web assets...
  pushd web
  call npm ci
  if errorlevel 1 goto :webfail
  call npm run build
  if errorlevel 1 goto :webfail
  popd
) else (
  echo npm not found - using previously built web assets. 1>&2
  if not exist "src\launcher\resources\web\index.html" goto :webmissing
)

pyinstaller --noconfirm --onedir --windowed --noupx ^
  --name CrewLauncher ^
  --icon src\launcher\resources\icon.ico ^
  --add-data "src\launcher\resources\icon.ico;resources" ^
  --add-data "src\launcher\resources\splash.png;resources" ^
  --add-data "src\launcher\resources\phosphor-icons;resources\phosphor-icons" ^
  --add-data "src\launcher\resources\login;resources\login" ^
  --add-data "src\launcher\resources\web;resources\web" ^
  --add-data "DOC;DOC" ^
  --add-data "release\bepmods.zip;." ^
  --hidden-import webview ^
  --hidden-import webview.platforms ^
  --hidden-import webview.platforms.winforms ^
  --hidden-import webview.platforms.edgechromium ^
  --hidden-import qtpy ^
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
  src\launcher\main.py

echo.
echo Built: dist\CrewLauncher\
pause
exit /b 0

:webfail
echo ERROR: web asset build failed (run "cd web && npm ci && npm run build"). 1>&2
exit /b 1

:webmissing
echo ERROR: src\launcher\resources\web\index.html is missing; install Node.js and run "cd web && npm ci && npm run build". 1>&2
exit /b 1
