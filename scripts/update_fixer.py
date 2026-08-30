"""Download latest ItchFixer exe to release/Fixer/ and dist/."""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "launcher"))

import requests
from config import FIXER_URL

ROOT = Path(__file__).parent.parent
RELEASE_PATH = ROOT / "release" / "Fixer" / "Itch_Login_Fixer.exe"
DIST_PATH = ROOT / "dist" / "Itch_Login_Fixer.exe"


def main():
    print(f"Downloading from:\n  {FIXER_URL}\n")
    try:
        r = requests.get(FIXER_URL, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Download failed: {e}")
        sys.exit(1)

    RELEASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    RELEASE_PATH.write_bytes(r.content)
    DIST_PATH.write_bytes(r.content)

    print(f"Saved to:\n  {RELEASE_PATH}\n  {DIST_PATH}")
    print(f"Size: {len(r.content):,} bytes")


if __name__ == "__main__":
    main()
