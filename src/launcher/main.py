"""
CrewLauncher — main entry point.
Default: PySide6 (Qt) GUI with splash screen. Use --gui-2 for legacy Dear PyGui GUI.
Pass -lite / --lite / -tk / --tk to open the lightweight tkinter (lite) GUI instead.
"""
import sys
import argparse
import logging

from config import APP_NAME
from functions.splash import *
from functions.worker import *
from functions.help import *

_LITE_FLAGS = ("-lite", "--lite", "-tk", "--tk", "--tkinter", "--tkinter-gui", "--tkinter-gui-only", "--tkinter-only", "--its-lite-for-win7-too")


def _has_lite_flag(argv):
    """True if the command line asks for the lightweight tkinter GUI."""
    return any(arg in _LITE_FLAGS for arg in argv[1:])


if __name__ == "__main__":
    if _has_lite_flag(sys.argv):
        from main_lite import main as lite_main
        lite_argv = [arg for arg in sys.argv[1:] if arg not in _LITE_FLAGS]
        raise SystemExit(lite_main(lite_argv))

    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QTimer, QSharedMemory

    parser = argparse.ArgumentParser(description="CrewLauncher")
    parser.add_argument("-tk, --tk, -lite", action="store_true",
                        help="Use Lite GUI (Tkinter) instead of default PySide6 GUI")
    parser.add_argument("--no-splash", action="store_true",
                        help="Skip splash screen")
    parser.add_argument("--splash-2", action="store_true",
                        help="Use animated WebM video splash")
    args, _ = parser.parse_known_args()                       
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

                    splash.finished.connect(lambda: on_splash_done(launcher))

                    splash.show()
                    QTimer.singleShot(50, lambda: boot(splash, launcher, qapp))

                vsplash = VideoSplash()
                vsplash.finished.connect(on_video_done)
                vsplash.show()
                vsplash.play()

                qapp.exec()
                launcher.shutdown()
                break

            splash = SplashScreen()

            splash.finished.connect(lambda: on_splash_done(launcher))

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
            
            launcher._run(lambda: profile_worker(launcher, profile_done))
            launcher._run(lambda: version_worker(launcher, version_done))

            splash.show()

            QTimer.singleShot(50, lambda: boot(splash, launcher, qapp))

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
