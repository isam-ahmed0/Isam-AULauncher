"""CrewLauncher Lite — tkinter entry point.

Lightweight front-end (install / play / uninstall, Discord RPC, settings).
Shares the exact same toolkit-free backend as the Qt GUI; PySide6 is never
imported on any code path.
"""
import os
import sys
import argparse
import logging


def _ensure_import_path():
    """Make the launcher modules importable when run as a script."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


_ensure_import_path()

from config import APP_NAME, Config, LAUNCHER_VERSION  # noqa: E402
from network import NetworkManager, DiscordRPC  # noqa: E402
from single_instance import ensure_single_instance  # noqa: E402


def main(argv=None, lock_held=False):
    parser = argparse.ArgumentParser(prog="CrewLauncher-Lite", description=APP_NAME)
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args, _ = parser.parse_known_args(argv)

    if args.version:
        print(f"{APP_NAME} {LAUNCHER_VERSION}")
        return 0

    config = Config()
    lock = None
    if not lock_held:
        lock = ensure_single_instance(config)
        if lock is None:
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
