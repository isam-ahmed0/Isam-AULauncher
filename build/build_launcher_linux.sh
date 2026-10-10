#!/usr/bin/env bash
# Build Isam AULauncher on Linux with PyInstaller (onedir).
#
#   python3 -m venv .venv
#   source .venv/bin/activate.fish
#   pip install -r src/launcher/requirements.txt
#   bash build/build_launcher_linux.sh
#
# Running from source (python src/launcher/main.py) is lighter still.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dist/linux

EXCLUDES=(
  --exclude-module PySide6.QtWebEngineCore
  --exclude-module PySide6.QtWebEngineWidgets
  --exclude-module PySide6.QtWebEngineQuick
  --exclude-module PySide6.QtQuick
  --exclude-module PySide6.QtQuickWidgets
  --exclude-module PySide6.QtQml
  --exclude-module PySide6.Qt3DCore
  --exclude-module PySide6.Qt3DRender
  --exclude-module PySide6.Qt3DAnimation
  --exclude-module PySide6.Qt3DExtras
  --exclude-module PySide6.Qt3DInput
  --exclude-module PySide6.Qt3DLogic
  --exclude-module PySide6.QtCharts
  --exclude-module PySide6.QtDataVisualization
  --exclude-module PySide6.QtPdf
  --exclude-module PySide6.QtPdfWidgets
  --exclude-module PySide6.QtDesigner
  --exclude-module PySide6.QtTest
  --exclude-module PySide6.QtSql
  --exclude-module PySide6.QtBluetooth
  --exclude-module PySide6.QtNfc
  --exclude-module PySide6.QtPositioning
  --exclude-module PySide6.QtSerialPort
  --exclude-module PySide6.QtSensors
  --exclude-module PySide6.QtHelp
  --exclude-module PySide6.QtWebSockets
  --exclude-module PySide6.QtWebChannel
  --exclude-module dearpygui
)

pyinstaller --noconfirm --onedir --windowed --noupx \
  --name IsamAULauncher \
  --distpath dist/linux \
  --workpath build/linux-work \
  --specpath build \
  --icon "$PWD/src/launcher/resources/icon.ico" \
  --add-data "$PWD/src/launcher/resources/icon.ico:resources" \
  --add-data "$PWD/src/launcher/resources/splash.png:resources" \
  --add-data "$PWD/src/launcher/resources/phosphor-icons:resources/phosphor-icons" \
  --add-data "$PWD/src/launcher/resources/login:resources/login" \
  --add-data "$PWD/DOC:DOC" \
  --add-data "$PWD/release/bepmods.zip:." \
  "${EXCLUDES[@]}" \
  "$PWD/src/launcher/main.py"

echo
echo "Built: dist/linux/IsamAULauncher/"
