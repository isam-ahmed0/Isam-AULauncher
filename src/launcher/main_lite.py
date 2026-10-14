"""CrewLauncher Lite — tkinter entry point.

Lightweight front-end (install / play / uninstall, Discord RPC, settings).
Shares the exact same toolkit-free backend as the Qt GUI; PySide6 is never
imported on any code path.
"""
import os
import sys
import argparse
import logging

from functions.lite import *

ensure_import_path(os, sys)


from config import APP_NAME, Config, LAUNCHER_VERSION  # noqa: E402
from network import NetworkManager, DiscordRPC  # noqa: E402
from platform_utils import IS_WINDOWS  # noqa: E402


def _already_running_message():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            APP_NAME,
            "Launcher is already running.\nPlease close the existing instance first.",
        )
        root.destroy()
    except Exception:
        print("Launcher is already running.", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="CrewLauncher-Lite", description=APP_NAME)
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args, _ = parser.parse_known_args(argv)

    if args.version:
        print(f"{APP_NAME} {LAUNCHER_VERSION}")
        return 0

    config = Config()
    lock = acquire_single_instance(config, IS_WINDOWS)
    if lock is None:
        _already_running_message()
        return 0

    network = NetworkManager()
    discord = DiscordRPC()

    from gui_tk import LauncherLiteApp
    app = LauncherLiteApp(config, network, discord)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
