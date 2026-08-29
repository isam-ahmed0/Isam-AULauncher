"""
Isam AULauncher — main entry point.
Dear PyGui powered, GPU-accelerated gaming launcher.
"""
import threading
import logging

from config import Config, APP_NAME
from network import NetworkManager
from window import LauncherApp


def check_launcher_update(network):
    try:
        from config import LAUNCHER_VERSION_URL, LAUNCHER_VERSION, LAUNCHER_DOWNLOAD_URL
        from pathlib import Path
        import subprocess
        latest = network.fetch_text(LAUNCHER_VERSION_URL)
        if latest and latest != LAUNCHER_VERSION:
            print(f"Update available: {latest} (current: {LAUNCHER_VERSION})")
            r = input("Download? (y/n): ").lower()
            if r in ("y", "yes"):
                new = Path(f"IsamAULauncher_{latest}.exe")
                if network.download_file(LAUNCHER_DOWNLOAD_URL, new):
                    print("Downloaded! Run the new launcher.")
                    subprocess.Popen([str(new)])
                    return False
                print("Download failed.")
        return True
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return True


if __name__ == "__main__":
    while True:
        try:
            config = Config()
            network = NetworkManager()
            threading.Thread(target=check_launcher_update, args=(network,), daemon=True).start()
            app = LauncherApp()
            app.run()
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.critical(e, exc_info=True)
            print(f"Error: {e}")
            r = input("Enter to restart, 'exit' to quit: ").strip().lower()
            if r == "exit":
                break
