"""pywebview (web) front-end for CrewLauncher.

The web GUI is a builtin interface (``--ui web``) that talks to the shared,
toolkit-free backend through :class:`gui_web.api.LauncherApi`.  Nothing in
this package imports PySide6 or tkinter.
"""
from gui_web.main import main  # noqa: F401

__all__ = ["main"]
