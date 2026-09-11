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
            from gui_qt.splash import SplashScreen
            from gui_qt.theme import apply_theme
            from config import Config

            # Create config and apply theme BEFORE showing anything
            _config = Config()
            apply_theme(qapp, _config)

            if args.no_splash:
                from gui_qt.window import LauncherApp
                launcher = LauncherApp(qapp)
                launcher._load_initial_data()
                launcher._load_itch_profile()
                token = launcher._read_itch_token()
                if token:
                    launcher.window.show()
                else:
                    from gui_qt.login import LoginWindow
                    launcher._login_window = LoginWindow()
                    launcher._login_window.show()
                qapp.exec()
                launcher.shutdown()
                break

            if args.splash_2:
                from gui_qt.video_splash import VideoSplash

                def on_video_done():
                    splash = SplashScreen()

                    def on_splash_done():
                        token = launcher._read_itch_token()
                        if token:
                            launcher.window.show()
                        else:
                            from gui_qt.login import LoginWindow
                            launcher._login_window = LoginWindow()
                            launcher._login_window.show()

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

            # DEFAULT: Show splash FIRST, build window behind it
            splash = SplashScreen()

            def on_splash_done():
                token = launcher._read_itch_token()
                if token:
                    launcher.window.show()
                else:
                    from gui_qt.login import LoginWindow
                    launcher._login_window = LoginWindow()
                    launcher._login_window.show()

            splash.finished.connect(on_splash_done)

            def boot():
                # Build window behind splash (user sees splash.png already)
                splash.update_status("Loading...")
                qapp.processEvents()

                from gui_qt.window import LauncherApp
                launcher = LauncherApp(qapp)

                splash.update_status("Loading profile...")
                qapp.processEvents()

                # Run network calls in background workers (non-blocking)
                _workers_done = {"profile": False, "version": False}

                def on_all_done():
                    _workers_done["profile"] = True
                    _workers_done["version"] = True
                    splash.update_status("Ready")
                    qapp.processEvents()
                    splash.finish()

                def check_both_done():
                    if _workers_done["profile"] and _workers_done["version"]:
                        on_all_done()

                def load_profile_done():
                    _workers_done["profile"] = True
                    check_both_done()

                def load_version_done():
                    _workers_done["version"] = True
                    check_both_done()

                # Profile fetch in background
                def profile_worker():
                    try:
                        launcher._fetch_itch_profile()
                    except Exception:
                        pass
                    launcher._invoke_main(load_profile_done)

                # Version check in background
                def version_worker():
                    try:
                        v = launcher.config.get_version()
                        if v:
                            launcher.current_version = v
                        latest = launcher.network.fetch_text(
                            "https://raw.githubusercontent.com/jogamerforgames2021/BootstrapperTEST/main/Version.txt"
                        )
                        if latest:
                            launcher.latest_version = latest
                        launcher._invoke_main(launcher._update_version_display)
                        launcher._invoke_main(launcher._update_main_btn)
                        if launcher.config.settings.get("discord_rpc"):
                            launcher.discord.connect()
                    except Exception:
                        pass
                    launcher._invoke_main(load_version_done)

                launcher._run(profile_worker)
                launcher._run(version_worker)

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
