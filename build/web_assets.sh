#!/usr/bin/env bash
# Build and verify the Astro Web assets bundled by every launcher build.
# The output (src/launcher/resources/web/) is gitignored, so a clean checkout
# must always run this before packaging.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: Node.js/npm was not found; install Node.js 22.23.4+ and run 'cd web && npm ci && npm run build'." >&2
  exit 1
fi

if ! node -e '
  const [major, minor, patch] = process.versions.node.split(".").map(Number);
  const ok = major > 22 || (major === 22 && (minor > 23 || (minor === 23 && patch >= 4)));
  process.exit(ok ? 0 : 1);
'; then
  echo "ERROR: Node.js $(node --version) is not supported; Astro requires 22.23.4+." >&2
  exit 1
fi

echo "Building web assets..."
(cd web && npm ci && npm run build)

if [ ! -f src/launcher/resources/web/index.html ]; then
  echo "ERROR: src/launcher/resources/web/index.html is missing after 'npm run build'." >&2
  exit 1
fi
