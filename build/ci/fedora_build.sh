#!/usr/bin/env bash
# Runs INSIDE a fedora container (as root) to build CrewLauncher for Fedora / RHEL
# and produces:
#   dist/packages/CrewLauncher.rpm
#
# The workspace is expected at /work (bind-mounted from the CI checkout).
set -euo pipefail

echo "[ci-fedora] installing build dependencies"
dnf install -y --setopt=install_weak_deps=False \
  rpm-build python3 python3-pip python3-devel gcc binutils \
  mesa-libGL mesa-libEGL libglvnd-egl libglvnd-glx mesa-dri-drivers \
  fontconfig freetype libxkbcommon libxkbcommon-x11 \
  libxcb libX11 libXext libXrender libXi libSM libICE \
  libXrandr libXcursor libXfixes libXdamage libXcomposite dbus-libs \
  python3-tkinter tk

echo "[ci-fedora] creating python symlink"
ln -sf /usr/bin/python3 /usr/bin/python

echo "[ci-fedora] installing Python packages"
python3 -m pip install --upgrade pip
python3 -m pip install PySide6 requests pypresence pyinstaller pillow customtkinter

echo "[ci-fedora] building launcher + RPM package"
cd /work
bash build/build_launcher_linux.sh
bash build/build_packages_linux.sh rpm

chmod -R a+rw /work/dist /work/build 2>/dev/null || true
echo "[ci-fedora] done. Package:"
ls -lh /work/dist/packages/CrewLauncher.rpm
