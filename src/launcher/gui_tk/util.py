"""Threading helpers for the Tk GUI.

Tk is not thread-safe, so background work is dispatched onto the main thread
through a queue drained by ``root.after``.
"""
import queue
import logging
import threading


class UIQueue:
    """Run callables on the Tk main thread from any thread."""

    def __init__(self, root, interval_ms: int = 40):
        self.root = root
        self._q = queue.Queue()
        self._interval = interval_ms
        self._alive = True
        self.root.after(self._interval, self._drain)

    def call(self, fn):
        """Schedule ``fn`` to run on the Tk main thread."""
        if self._alive:
            self._q.put(fn)

    def _drain(self):
        if not self._alive:
            return
        try:
            while True:
                fn = self._q.get_nowait()
                try:
                    fn()
                except Exception:
                    logging.exception("Error in UI callback")
        except queue.Empty:
            pass
        try:
            self.root.after(self._interval, self._drain)
        except Exception:
            self._alive = False

    def stop(self):
        self._alive = False


def run_thread(fn, name=None) -> threading.Thread:
    """Run ``fn`` in a daemon background thread."""
    t = threading.Thread(target=fn, name=name, daemon=True)
    t.start()
    return t
