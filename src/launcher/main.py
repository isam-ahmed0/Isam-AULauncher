"""CrewLauncher - main entry point.

Interface selection (first match wins):

- ``--ui qt|tk|custom:<name>``  explicit choice
- ``--qt`` / ``--tk`` (``--lite``)  shortcuts
- config ``ui_mode``            saved preference (Settings > Interface)
- default                      Qt

On Linux the Qt interface automatically picks a working platform (X11 first,
then Wayland) and falls back to the Lite interface when Qt cannot start at
all, so users never need manual platform flags. Custom GUIs are plain Python
files in ``<appdata>/IsamAULauncher/guis/`` - see ``DOC/CUSTOM_GUI.md``.
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

from config import APP_NAME, LAUNCHER_VERSION  # noqa: E402


_QT_NOTICE_APP = None  # keep the fallback QApplication alive


def _notice(title, text):
    """Best-effort graphical notice; falls back to stderr."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, text)
        root.destroy()
        return
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        global _QT_NOTICE_APP
        _QT_NOTICE_APP = QApplication.instance() or QApplication([])
        QMessageBox.information(None, title, text)
        return
    except Exception:
        pass
    print(f"{title}: {text}", file=sys.stderr)


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="CrewLauncher", description=APP_NAME)
    parser.add_argument("--ui", default=None,
                        help="Interface to start: qt, tk or custom:<name>")
    parser.add_argument("--qt", action="store_true",
                        help="Use the Qt interface")
    parser.add_argument("--tk", "--lite", "-tk", "-lite", dest="tk",
                        action="store_true", help="Use the Lite (tkinter) interface")
    parser.add_argument("--ctk", "-ctk", dest="ctk", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--gui-2", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-splash", action="store_true", help="Skip splash screen")
    parser.add_argument("--splash-2", action="store_true",
                        help="Use animated WebM video splash")
    parser.add_argument("--version", action="store_true",
                        help="Print version and exit")
    args, rest = parser.parse_known_args(argv)
    args.rest = rest
    return args


def _run_custom(mode, config):
    """Run a custom GUI. Returns True on success, False if no entry point,
    or the exception when loading/running failed."""
    from ui_registry import run_custom_gui
    try:
        return run_custom_gui(mode, config)
    except Exception as e:
        logging.exception("Custom GUI failed to start")
        return e


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {LAUNCHER_VERSION}")
        return 0

    if args.gui_2:
        _notice(APP_NAME, "Dear PyGui is no longer supported.\n"
                          "Please use the default Qt interface.")
        return 0

    from config import Config
    from single_instance import ensure_single_instance
    config = Config()
    lock = ensure_single_instance(config)  # keep alive for the whole process
    if lock is None:
        return 0

    cli_mode = (args.ui or "").strip()
    if not cli_mode:
        if args.tk:
            cli_mode = "tk"
        elif args.qt:
            cli_mode = "qt"
        elif args.ctk:
            _notice(APP_NAME, "The CustomTkinter interface is not available yet.\n"
                              "Starting the Qt interface.")
            cli_mode = "qt"

    from ui_registry import resolve_mode
    mode = resolve_mode(cli_mode, config)

    if mode == "tk":
        from main_lite import main as lite_main
        return lite_main(args.rest, lock_held=True)

    if mode.startswith("custom:"):
        result = _run_custom(mode, config)
        if result is True:
            return 0
        detail = ""
        if isinstance(result, BaseException):
            detail = f"\n\nReason: {type(result).__name__}: {result}"
        _notice(APP_NAME,
                "The custom GUI could not be started (see the launcher log)."
                f"{detail}\n\nStarting the Qt interface.")
        mode = "qt"

    from qt_platform import prepare_qt_platform, distro_hint
    if not prepare_qt_platform(config.get_display_backend()):
        hint = distro_hint()
        logging.warning("No working Qt platform; falling back to Lite. %s", hint)
        os.environ["ISAM_QT_FALLBACK"] = "1"
        _notice(APP_NAME,
                "The Qt interface could not start on this system.\n"
                "This usually means a system library is missing.\n\n"
                f"{hint}\n\n"
                "Starting the lightweight Lite interface instead.")
        from main_lite import main as lite_main
        return lite_main(args.rest, lock_held=True)

    from main_qt import main as qt_main
    qt_argv = list(args.rest)
    if args.no_splash:
        qt_argv.append("--no-splash")
    if args.splash_2:
        qt_argv.append("--splash-2")
    return qt_main(qt_argv, lock_held=True)


if __name__ == "__main__":
    raise SystemExit(main())
