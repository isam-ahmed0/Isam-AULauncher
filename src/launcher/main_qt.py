"""CrewLauncher - PySide6 (Qt) front-end entry."""
import sys
import argparse
import logging

from config import APP_NAME


def _acquire_lock():
    from config import Config
    from single_instance import ensure_single_instance
    config = Config()
    return ensure_single_instance(config)


def main(argv=None, lock_held=False):
    if argv is None:
        argv = sys.argv[1:]

    if not lock_held and _acquire_lock() is None:
        return 0

    from qt_platform import prepare_qt_platform
    if not prepare_qt_platform():
        print(
            "No working Qt platform found. Install libxcb-cursor0 (xcb-util-cursor)\n"
            "or start the launcher with --ui tk.",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(prog=APP_NAME, description=APP_NAME)
    parser.add_argument("--no-splash", action="store_true")
    parser.add_argument("--splash-2", action="store_true")
    args, _ = parser.parse_known_args(argv)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer

    qapp = QApplication(sys.argv)

    while True:
        launcher = None
        try:
            from gui_qt.window import LauncherApp
            from gui_qt.splash import SplashScreen
            from gui_qt.theme import apply_theme

            apply_theme(qapp)
            launcher = LauncherApp(qapp)

            if args.no_splash:
                launcher._load_initial_data()
                launcher._load_itch_profile()
                token = launcher._read_itch_token()
                if token:
                    launcher.window.show()
                else:
                    from gui_qt.login import LoginWindow
                    launcher._login_window = LoginWindow(prefix=launcher.config.get_wine_prefix())
                    launcher._login_window.show()
                qapp.exec()
                launcher.shutdown()
                break

            if args.splash_2:
                from gui_qt.video_splash import VideoSplash
                from gui_qt.splash import SplashScreen

                def on_video_done():
                    splash = SplashScreen()

                    def on_splash_done():
                        token = launcher._read_itch_token()
                        if token:
                            launcher.window.show()
                        else:
                            from gui_qt.login import LoginWindow
                            launcher._login_window = LoginWindow(prefix=launcher.config.get_wine_prefix())
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

            splash = SplashScreen()

            def on_splash_done():
                token = launcher._read_itch_token()
                if token:
                    launcher.window.show()
                else:
                    from gui_qt.login import LoginWindow
                    launcher._login_window = LoginWindow(prefix=launcher.config.get_wine_prefix())
                    launcher._login_window.show()

            splash.finished.connect(on_splash_done)

            _done = {"profile": False, "version": False}

            def check_done():
                if _done["profile"] and _done["version"]:
                    splash.update_status("Ready")
                    qapp.processEvents()
                    splash.finish()

            def profile_done():
                _done["profile"] = True
                check_done()

            def version_done():
                _done["version"] = True
                check_done()

            def profile_worker():
                try:
                    launcher._load_itch_profile_sync()
                except Exception:
                    pass
                launcher._invoke_main(profile_done)

            def version_worker():
                try:
                    launcher._load_initial_data_sync()
                except Exception:
                    pass
                launcher._invoke_main(version_done)

            splash.show()

            def boot():
                splash.update_status("Loading profile...")
                qapp.processEvents()
                launcher._run(profile_worker)
                splash.update_status("Checking updates...")
                qapp.processEvents()
                launcher._run(version_worker)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
