"""Python -> JavaScript event push.

GameCore status/progress callbacks fire from worker threads, so every push is
serialised here and handed to pywebview (which marshals it onto the GUI
thread).  Events raised before the page is ready are queued and flushed as
soon as the front-end calls ``app.ready()``.
"""
import json
import logging
import threading
import time

log = logging.getLogger(__name__)

_QUEUE_LIMIT = 512
_PROGRESS_INTERVAL = 0.10  # seconds between progress pushes


class Emitter:
    def __init__(self):
        self._window = None
        self._ready = False
        self._lock = threading.Lock()
        self._queue = []
        self._last_progress_at = 0.0
        self._last_progress = -1.0

    # ------------------------------------------------------------- wiring
    def attach(self, window):
        with self._lock:
            self._window = window

    def enable(self):
        """Called by the page once ``pywebview.api`` is reachable."""
        with self._lock:
            self._ready = True
            pending = self._queue
            self._queue = []
        for name, data in pending:
            self._push(name, data)

    def shutdown(self):
        with self._lock:
            self._ready = False
            self._window = None
            self._queue = []

    # ------------------------------------------------------------- sending
    def emit(self, name, data=None):
        with self._lock:
            if not self._ready or self._window is None:
                self._enqueue(name, data)
                return
        self._push(name, data)

    def emit_progress(self, pct, force=False):
        """Throttled progress push (0-100 float)."""
        now = time.monotonic()
        value = round(float(pct), 1)
        with self._lock:
            if not force and (
                now - self._last_progress_at < _PROGRESS_INTERVAL
                and abs(value - self._last_progress) < 1.0
            ):
                return
            self._last_progress_at = now
            self._last_progress = value
        self.emit("progress", {"pct": value})

    def _enqueue(self, name, data):
        if len(self._queue) >= _QUEUE_LIMIT:
            # Drop the oldest non-status event to stay bounded.
            for i, (queued, _) in enumerate(self._queue):
                if queued not in ("status", "progress"):
                    del self._queue[i]
                    break
            else:
                del self._queue[0]
        self._queue.append((name, data))

    def _push(self, name, data):
        with self._lock:
            window = self._window
            if window is None:
                return
        payload = json.dumps(data if data is not None else {}, default=str)
        code = (
            "try{window.__clEvent&&window.__clEvent("
            + json.dumps(name) + "," + payload
            + ")}catch(e){}"
        )
        try:
            window.run_js(code)
        except Exception as exc:  # window may be closing
            log.debug("event %s failed: %s", name, exc)
