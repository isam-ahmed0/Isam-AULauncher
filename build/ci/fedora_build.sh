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

# Fedora's nodejs package can lag Astro's minimum (22.23.4), so use NodeSource.
echo "[ci-fedora] installing Node.js 24"
dnf install -y curl ca-certificates gnupg
curl -fsSL https://rpm.nodesource.com/setup_24.x | bash -
dnf install -y nodejs
node --version
npm --version

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
