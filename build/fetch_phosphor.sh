#!/usr/bin/env bash
# Fetch individual Phosphor icons into the launcher's icon folder.
#
#   bash build/fetch_phosphor.sh                 # (re)download the icons the UI uses
#   bash build/fetch_phosphor.sh rocket-launch   # add another icon by name
#   WEIGHT=fill bash build/fetch_phosphor.sh heart
#
# Icons come from the official @phosphor-icons/core package on unpkg, so no git
# clone is needed. Only the icons we actually bundle are copied into the tree;
# this keeps the repo and the build small. Browse names at https://phosphoricons.com
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/src/launcher/resources/phosphor-icons"
VERSION="${PHOSPHOR_VERSION:-2.1.1}"
WEIGHT="${WEIGHT:-regular}"

# Default set = the icons referenced in src/launcher/gui_qt/window/main.py
DEFAULT_ICONS=(
    game-controller
    wrench
    user-circle
    puzzle-piece
    gear
    info
    package
    sidebar-simple
)

if [ "$#" -gt 0 ]; then
    ICONS=("$@")
else
    ICONS=("${DEFAULT_ICONS[@]}")
fi

mkdir -p "$DEST/SVGs/$WEIGHT"
url_base="https://unpkg.com/@phosphor-icons/core@${VERSION}/assets/${WEIGHT}"

rc=0
for name in "${ICONS[@]}"; do
    out="$DEST/SVGs/$WEIGHT/${name}.svg"
    if curl -fsSL "$url_base/${name}.svg" -o "$out"; then
        echo "fetched ${WEIGHT}/${name}.svg"
    else
        rm -f "$out"
        echo "ERROR: '${name}' not found in '${WEIGHT}' weight" >&2
        rc=1
    fi
done

echo
echo "Phosphor icons are MIT licensed — see $DEST/LICENSE"
exit "$rc"
