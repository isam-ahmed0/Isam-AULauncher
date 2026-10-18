from PySide6.QtCore import QObject, QThread, Signal


class _UISignaler(QObject):
    """Bridge to dispatch callables from background threads to the main thread."""
    invoke = Signal(object)


class Worker(QThread):
    """Run a function in a background thread, emit finished signal."""
    finished = Signal()

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self._fn()
        finally:
            self.finished.emit()
