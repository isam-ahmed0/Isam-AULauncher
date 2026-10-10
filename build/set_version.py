#!/usr/bin/env python3
"""Set LAUNCHER_VERSION in src/launcher/config.py.

Used by CI to stamp a version into the working copy (never committed). Also
handy locally:  python build/set_version.py 1.0.0

Exits non-zero if the LAUNCHER_VERSION line is missing or ambiguous.
"""
import re
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "src" / "launcher" / "config.py"
PATTERN = re.compile(r'(?m)^LAUNCHER_VERSION\s*=\s*".*?"')


def main(argv):
    if len(argv) != 2 or not argv[1].strip():
        print("usage: set_version.py <version>", file=sys.stderr)
        return 2

    version = argv[1].strip()
    text = CONFIG.read_text(encoding="utf-8")
    new, count = PATTERN.subn(f'LAUNCHER_VERSION = "{version}"', text)
    if count != 1:
        print(
            f"ERROR: expected exactly one LAUNCHER_VERSION line in {CONFIG}, found {count}",
            file=sys.stderr,
        )
        return 1

    CONFIG.write_text(new, encoding="utf-8")
    print(f'LAUNCHER_VERSION -> "{version}" in {CONFIG}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
