"""
Isam AULauncher — main entry point.
Default: PySide6 (Qt) GUI with splash screen. Use --gui-2 for legacy Dear PyGui GUI.
"""
import sys
import argparse
import logging

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QSharedMemory
from config import APP_NAME


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Isam AULauncher")
    parser.add_argument("--gui-2", action="store_true",
                        help="Use legacy Dear PyGui GUI")
    parser.add_argument("--no-splash", action="store_true",
                        help="Skip splash screen")
    parser.add_argument("--splash-2", action="store_true",
                        help="Use animated WebM video splash")
    args, _ = parser.parse_known_args()

    if args.gui_2:
        from gui_dpg.window import LauncherApp
        app = LauncherApp()
        app.run()
        sys.exit(0)

    qapp = QApplication(sys.argv)

    # Single instance lock
    _shared_mem = QSharedMemory("IsamAULauncher_SingleInstance")
    if not _shared_mem.create(1):
        QMessageBox.warning(
            None, APP_NAME,
            "Launcher is already running.\nPlease close the existing instance first.",
        )
        sys.exit(0)

    while True:
        try:
            from gui_qt.window import LauncherApp
            from gui_qt.splash import SplashScreen
            from gui_qt.theme import apply_theme

            apply_theme(qapp)
            launcher = LauncherApp(qapp)

            if args.no_splash:
                launcher._load_initial_data()
                launcher._load_itch_profile()
                launcher.window.show()
                qapp.exec()
                launcher.shutdown()
                break

            if args.splash_2:
                from gui_qt.video_splash import VideoSplash
                from gui_qt.splash import SplashScreen

                def on_video_done():
                    splash = SplashScreen()

                    def on_splash_done():
                        launcher.window.show()

                    splash.finished.connect(on_splash_done)

                    def boot():
                        splash.update_status("Loading profile...")
                        qapp.processEvents()
                        launcher._load_itch_profile_sync()
                        splash.update_status("Checking updates...")
                        qapp.processEvents()
                        launcher._load_initial_data_sync()
                        splash.update_status("Ready")
                        qapp.processEvents()
                        splash.finish()

                    splash.show()
                    QTimer.singleShot(50, boot)

                vsplash = VideoSplash()
                vsplash.finished.connect(on_video_done)
                vsplash.show()
                vsplash.play()

                qapp.exec()
                launcher.shutdown()
                break

            splash = SplashScreen()

            def on_splash_done():
                launcher.window.show()

            splash.finished.connect(on_splash_done)

            def boot():
                splash.update_status("Loading profile...")
                qapp.processEvents()
                launcher._load_itch_profile_sync()

                splash.update_status("Checking updates...")
                qapp.processEvents()
                launcher._load_initial_data_sync()

                splash.update_status("Ready")
                qapp.processEvents()
                splash.finish()

            splash.show()
            QTimer.singleShot(50, boot)

            qapp.exec()
            launcher.shutdown()
            break
        except KeyboardInterrupt:
            try:
                launcher.shutdown()
            except Exception:
                pass
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
