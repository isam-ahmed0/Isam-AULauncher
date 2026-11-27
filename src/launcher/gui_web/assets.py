"""Locate and serve the built web assets.

The Astro build (``web/`` at the repo root) writes its static output to
``src/launcher/resources/web``.  Assets are served over a tiny loopback HTTP
server instead of ``file://`` so ES modules, fonts and fetch() behave exactly
like they do under ``astro dev``.
"""
import functools
import http.server
import logging
import sys
import threading
from pathlib import Path

log = logging.getLogger(__name__)

_MIME = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".map": "application/json",
}


def resources_dir() -> Path:
    """``resources/`` for both source runs and frozen (PyInstaller) builds."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        # PyInstaller >= 6 onedir puts datas in ``_internal/``; 5.x next to the exe.
        for cand in (base / "_internal" / "resources", base / "resources"):
            if cand.is_dir():
                return cand
    # gui_web/assets.py -> gui_web -> launcher
    return Path(__file__).resolve().parent.parent / "resources"


def web_dir() -> Path:
    return resources_dir() / "web"


def index_file() -> Path:
    return web_dir() / "index.html"


def index_exists() -> bool:
    try:
        return index_file().is_file()
    except OSError:
        return False


def missing_build_message() -> str:
    return (
        "The web interface assets have not been built yet.\n\n"
        "Run:\n"
        "    cd web && npm install && npm run build\n\n"
        "or start the launcher with --ui qt / --ui tk."
    )


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Static handler with sane cache headers and correct JS mime types."""

    def guess_type(self, path):
        suffix = Path(path).suffix.lower()
        if suffix in _MIME:
            return _MIME[suffix]
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        log.debug("http: " + fmt, *args)


def start_server(directory=None):
    """Serve ``directory`` on a random loopback port.

    Returns ``(port, shutdown)``.  ``shutdown()`` is idempotent and safe to
    call from an atexit handler.
    """
    directory = Path(directory or web_dir())
    handler = functools.partial(_Handler, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True,
                              name="web-assets")
    thread.start()
    log.info("Serving web assets from %s on port %s", directory, port)

    def shutdown():
        try:
            httpd.shutdown()
            httpd.server_close()
        except Exception:
            pass

    return port, shutdown
