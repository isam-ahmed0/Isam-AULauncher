#!/usr/bin/env bash
# Build and verify the Astro Web assets bundled by every launcher build.
# The output (src/launcher/resources/web/) is gitignored, so a clean checkout
# must always run this before packaging.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm was not found; install Node.js 22+ and run 'cd web && npm ci && npm run build'." >&2
  exit 1
fi

echo "Building web assets..."
(cd web && npm ci && npm run build)

if [ ! -f src/launcher/resources/web/index.html ]; then
  echo "ERROR: src/launcher/resources/web/index.html is missing after 'npm run build'." >&2
  exit 1
fi
