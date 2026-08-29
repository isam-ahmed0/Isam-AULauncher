"""
Isam AULauncher — main entry point.
Dear PyGui powered, GPU-accelerated gaming launcher.
"""
import threading
import logging

from config import Config, APP_NAME
from network import NetworkManager
from window import LauncherApp


if __name__ == "__main__":
    while True:
        try:
            config = Config()
            network = NetworkManager()
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
