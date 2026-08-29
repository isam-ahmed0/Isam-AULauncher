#!/usr/bin/env python3
"""Sync the release/ folder to the hosting GitHub repo.

The launcher fetches these files from the ROOT of the hosting repo
(jogamerforgames2021/AmongUsLauncherNew), e.g. Patches.xml, version.txt,
LauncherVersion.txt, AUnlockerStuff/Versions.json ... so this script keeps
that repo layout in sync with release/.

Usage:
    python scripts/sync_release.py            # commit + push release/ to 'hosting'
    python scripts/sync_release.py --dry-run  # show what would change
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
REMOTE = "hosting"
BRANCH = "main"


def git(*args):
    proc = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True
    )
    return proc.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="do not push")
    parser.add_argument("-m", "--message", default="Update release files", help="commit message")
    args = parser.parse_args()

    if not RELEASE.exists():
        print(f"release/ not found at {RELEASE}")
        sys.exit(1)

    remotes = git("remote")
    if REMOTE not in remotes:
        print(f"Remote '{REMOTE}' not configured. Add it with:")
        print(f"  git remote add {REMOTE} https://github.com/<you>/AmongUsLauncherNew")
        sys.exit(1)

    # Stage exactly the release directory
    git("rm", "--cached", "-rf", "--quiet", "release")
    subprocess.run(["git", "-C", str(ROOT), "add", "-f", "release"], check=True)

    status = git("status", "--porcelain", "--", "release")
    if not status and not git("diff", "--cached", "--name-only", "--", "release"):
        print("release/ is already up to date.")
        return

    print("Staged changes:")
    print(status or git("diff", "--cached", "--name-only", "--", "release"))

    if args.dry_run:
        print("\n[dry-run] Done - no commit/push performed.")
        return

    git("commit", "-m", args.message)
    print("\nPushing to remote '%s' (%s)..." % (REMOTE, BRANCH))
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "push", REMOTE, f"HEAD:{BRANCH}"],
        text=True
    )
    if proc.returncode != 0:
        print("Push failed. See output above.")
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()