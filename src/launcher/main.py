"""
Isam AULauncher — main entry point.
Default: PySide6 (Qt) GUI with splash screen. Use --gui-2 for legacy Dear PyGui GUI.
"""
import sys
import argparse
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Isam AULauncher")
    parser.add_argument("--gui-2", action="store_true",
                        help="Use legacy Dear PyGui GUI")
    parser.add_argument("--no-splash", action="store_true",
                        help="Skip splash screen")
    args, _ = parser.parse_known_args()

    if args.gui_2:
        from gui_dpg.window import LauncherApp
        app = LauncherApp()
        app.run()
        sys.exit(0)

    qapp = QApplication(sys.argv)

    while True:
        try:
            from gui_qt.window import LauncherApp
            from gui_qt.splash import SplashScreen
            from gui_qt.theme import apply_theme

            apply_theme(qapp)
            launcher = LauncherApp(qapp)

            if args.no_splash:
                launcher._load_itch_profile()
                launcher.window.show()
                qapp.exec()
                launcher.discord.disconnect()
                break

            splash = SplashScreen()

            def on_splash_done():
                launcher.window.show()

            splash.finished.connect(on_splash_done)

            def boot():
                splash.update_status("Loading profile...")
                launcher._load_itch_profile()
                splash.update_status("Checking updates...")
                QTimer.singleShot(1800, splash.finish)

            splash.show()
            QTimer.singleShot(300, boot)

            qapp.exec()
            launcher.discord.disconnect()
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.critical(e, exc_info=True)
            print(f"Error: {e}")
            try:
                r = input("Enter to restart, 'exit' to quit: ").strip().lower()
            except (EOFError, OSError):
                break
            if r == "exit":
                break
