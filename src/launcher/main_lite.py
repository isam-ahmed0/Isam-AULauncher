"""
Isam AULauncher — Lite entry point.
Directly launches the Dear PyGui GUI. No splash screen, no Qt dependency.
"""
import os
import sys
import logging
import tempfile
import threading
import subprocess
from pathlib import Path

logging.basicConfig(
    filename='launcher.log', level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def _check_launcher_update():
    """Check for launcher update in background. Downloads setup and runs it."""
    try:
        from config import LAUNCHER_VERSION, LAUNCHER_UPDATE_URL, LAUNCHER_SETUP_URL
        from network import NetworkManager

        net = NetworkManager()
        remote = net.fetch_text(LAUNCHER_UPDATE_URL)
        if not remote or remote.strip() == LAUNCHER_VERSION:
            return

        print(f"Update available: v{remote.strip()} (current: v{LAUNCHER_VERSION})")
        r = input("Download and install update? (y/n): ").strip().lower()
        if r != "y":
            return

        setup_path = Path(tempfile.gettempdir()) / "IsamAU-Setup.exe"
        print("Downloading update...")
        if net.download_file(LAUNCHER_SETUP_URL, setup_path):
            print("Starting installer...")
            subprocess.Popen([str(setup_path), "/S"])
            sys.exit(0)
        else:
            print("Download failed.")
    except Exception as e:
        logging.error(f"Launcher update check failed: {e}")


if __name__ == "__main__":
    t = threading.Thread(target=_check_launcher_update, daemon=True)
    t.start()

    try:
        from gui_dpg.window import LauncherApp
        app = LauncherApp()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(e, exc_info=True)
        print(f"Error: {e}")
        input("Press Enter to exit...")
