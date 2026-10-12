"""Qt adapter over the toolkit-free itch.io OAuth flow (``itch_oauth``).

Kept so the existing Qt GUI (``gui_qt.login`` / ``gui_qt.window.itch_profile``)
can keep importing ``ItchOAuthSession`` and ``save_itch_token`` unchanged while
the actual flow lives in the shared, PySide6-free ``itch_oauth`` module.
"""
from PySide6.QtCore import QObject, Signal

from itch_oauth import (
    ItchOAuthFlow, save_itch_token,
    CLIENT_ID, PORT, ITCH_REDIRECT, ITCH_SCOPE, ITCH_TIMEOUT,
)


class ItchOAuthSession(QObject):
    """One itch.io login attempt (Qt signal facade over ItchOAuthFlow).

    Start it, open ``auth_url()`` in the browser, then wait for the ``token``
    signal. ``failed`` and ``timed_out`` report the corresponding outcomes.
    """

    token = Signal(str)
    failed = Signal(str)
    timed_out = Signal()

    def __init__(self, timeout=ITCH_TIMEOUT, parent=None):
        super().__init__(parent)
        self._flow = ItchOAuthFlow(timeout)
        self._flow.on_token = self.token.emit
        self._flow.on_failed = self.failed.emit
        self._flow.on_timed_out = self.timed_out.emit

    def auth_url(self):
        return self._flow.auth_url()

    def start(self):
        self._flow.start()

    def stop(self):
        self._flow.stop()


__all__ = [
    "ItchOAuthSession", "save_itch_token",
    "CLIENT_ID", "PORT", "ITCH_REDIRECT", "ITCH_SCOPE", "ITCH_TIMEOUT",
]
