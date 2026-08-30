"""
Isam AULauncher — Lite entry point.
Directly launches the Dear PyGui GUI. No splash screen, no Qt dependency.
"""
import sys
import logging

logging.basicConfig(
    filename='launcher.log', level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
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
