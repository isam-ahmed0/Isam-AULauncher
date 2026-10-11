#!/usr/bin/env bash
# Linux CI build dispatcher.
# Usage:
#   bash build/ci/linux_build.sh [arch|ubuntu|fedora]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-arch}"

case "$TARGET" in
  arch|pacman)
    exec bash "$DIR/arch_build.sh"
    ;;
  ubuntu|deb|debian)
    exec bash "$DIR/ubuntu_build.sh"
    ;;
  fedora|rpm)
    exec bash "$DIR/fedora_build.sh"
    ;;
  *)
    echo "Unknown target: $TARGET (expected arch, ubuntu, or fedora)" >&2
    exit 1
    ;;
esac
