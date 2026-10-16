"""Cross-platform single-instance lock shared by every GUI front-end.

The lock is a per-user file in the appdata dir held open for the lifetime of
the process. ``acquire`` returns the open file (keep a reference to it!) or
``None`` when another instance already holds it. The lock is released by the
OS automatically when the process exits, even after a crash.
"""
import os
import sys
import time
import logging

from platform_utils import IS_WINDOWS


def _try_acquire(config):
    path = config.appdata_dir / "launcher.lock"
    try:
        f = open(str(path), "w")
        if IS_WINDOWS:
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        return None
    except Exception:
        logging.exception("Single-instance lock failed")
        return None


def acquire(config):
    """Try to take the launcher lock. Returns the open file or None.

    When this process was started by "Restart now" on Windows the old
    process may still be exiting, so retry briefly before giving up.
    """
    attempts = 20 if os.environ.get("ISAM_RESTARTING") == "1" else 1
    for i in range(attempts):
        lock = _try_acquire(config)
        if lock is not None:
            return lock
        if i + 1 < attempts:
            time.sleep(0.1)
    return None


def already_running_message():
    """Best-effort native warning that the launcher is already running."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        from config import APP_NAME
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            APP_NAME,
            "Launcher is already running.\nPlease close the existing instance first.",
        )
        root.destroy()
    except Exception:
        print("Launcher is already running.", file=sys.stderr)


def ensure_single_instance(config):
    """Acquire the lock or show the message and return None."""
    lock = acquire(config)
    if lock is None:
        already_running_message()
        return None
    return lock
