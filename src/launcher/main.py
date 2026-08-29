"""
Isam AULauncher — main entry point.
Default: PySide6 (Qt) GUI. Use --gui-2 for legacy Dear PyGui GUI.
"""
import sys
import argparse
import logging


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Isam AULauncher")
    parser.add_argument("--gui-2", action="store_true",
                        help="Use legacy Dear PyGui GUI")
    args, _ = parser.parse_known_args()

    while True:
        try:
            if args.gui_2:
                from gui_dpg.window import LauncherApp
            else:
                from gui_qt.window import LauncherApp

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
