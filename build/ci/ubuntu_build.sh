#!/usr/bin/env bash
# Builds CrewLauncher for Debian / Ubuntu and produces:
#   dist/packages/CrewLauncher.deb
#   dist/packages/CrewLauncher-Linux.tar.gz
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "[ci-ubuntu] building launcher"
bash build/build_launcher_linux.sh

echo "[ci-ubuntu] building .deb package"
bash build/build_packages_linux.sh deb

echo "[ci-ubuntu] creating portable .tar.gz"
mkdir -p dist/packages
tar -C dist/linux -czf dist/packages/CrewLauncher-Linux.tar.gz CrewLauncher

echo "[ci-ubuntu] done. Packages:"
ls -lh dist/packages/CrewLauncher.deb dist/packages/CrewLauncher-Linux.tar.gz
