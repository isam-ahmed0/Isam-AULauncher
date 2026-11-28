"""CrewLauncher - pywebview (web) front-end entry.

Mirrors ``main_qt.main(argv, lock_held)``: parse args, build the shared
:class:`ui_registry.AppContext`, expose the JS bridge, show a frameless window
over the built Astro assets and block in ``webview.start()``.

Return codes
    0   ran (or user closed) successfully
    2   pywebview / webview backend unavailable -> caller falls back to Qt
    3   web assets missing (run ``npm run build``) -> caller falls back to Qt
"""
import argparse
import atexit
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from config import APP_NAME

log = logging.getLogger(__name__)

DEV_URL_DEFAULT = "http://127.0.0.1:4321"


def _acquire_lock():
    from config import Config
    from single_instance import ensure_single_instance
    return ensure_single_instance(Config())


def _with_event_query(url, event):
    """Mirror the resolved event into the URL for the first CSS paint."""
    if not event.active:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["event"] = event.name
    return urlunsplit((
        parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment
    ))


def _url_ready(url, timeout=0.6):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _spawn_dev_server(web_dir):
    """Start ``npm run dev`` for the Astro project. Returns True if spawned."""
    if not (web_dir / "package.json").is_file():
        return False
    if not (web_dir / "node_modules").is_dir():
        print("Web dev server needs dependencies first:\n"
              f"    cd {web_dir} && npm install", file=sys.stderr)
        return False
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        print("npm was not found on PATH — install Node.js to run --dev.",
              file=sys.stderr)
        return False
    env = dict(os.environ)
    env.setdefault("BROWSER", "none")
    try:
        subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(web_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError as exc:
        print(f"Could not start the Astro dev server: {exc}", file=sys.stderr)
        return False


def _resolve_url(args):
    """Return ``(url, cleanup)`` for the page to load, or ``(None, reason)``."""
    if args.dev:
        url = args.dev_url.rstrip("/")
        if _url_ready(url):
            return url, None
        from gui_web import assets
        print("Starting the Astro dev server…", file=sys.stderr)
        if _spawn_dev_server(assets.web_dir().parent):
            deadline = time.time() + 30
            while time.time() < deadline:
                if _url_ready(url):
                    return url, None
                time.sleep(0.5)
        print(f"Could not reach the dev server at {url}.\n"
              "Start it manually with:  cd web && npm run dev", file=sys.stderr)
        return None, "dev"

    from gui_web import assets
    if not assets.index_exists():
        return None, "assets"
    port, shutdown = assets.start_server()
    atexit.register(shutdown)
    return f"http://127.0.0.1:{port}/", shutdown


def _pick_gui():
    """Backend for pywebview on Linux: WebKitGTK when available, else Qt.

    Windows (WebView2) and macOS (WKWebView) use pywebview's default.
    """
    if not sys.platform.startswith("linux"):
        return None
    try:
        import gi  # noqa: F401
        return "gtk"
    except Exception:
        pass
    try:
        import qtpy  # noqa: F401
        return "qt"
    except Exception:
        return None


def main(argv=None, lock_held=False):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=APP_NAME, description=APP_NAME)
    parser.add_argument("--dev", action="store_true",
                        help="Load the Astro dev server instead of the build")
    parser.add_argument("--dev-url", default=DEV_URL_DEFAULT,
                        help="Dev server URL (default: %(default)s)")
    parser.add_argument("--event", default=None, metavar="NAME",
                        help="Force a seasonal event on (e.g. winter; 'none' disables)")
    args, _ = parser.parse_known_args(argv)

    try:
        import webview  # noqa: F401
    except Exception as exc:
        print(f"The web interface needs pywebview: {exc}\n"
              "Install it with:  pip install pywebview", file=sys.stderr)
        return 2

    from config import Config
    config = Config()
    if not lock_held and _acquire_lock() is None:
        return 0

    from ui_registry import AppContext
    from gui_web.api import LauncherApi
    from gui_web.events import Emitter

    url, cleanup = _resolve_url(args)
    if url is None:
        if cleanup == "assets":
            from gui_web import assets
            print(assets.missing_build_message(), file=sys.stderr)
        return 3

    from seasonal_events import load_event

    ctx = AppContext(config)
    event = load_event(config, getattr(ctx, "network", None), args.event)
    emitter = Emitter()
    api = LauncherApi(ctx, emitter)
    api.set_event(event)
    url = _with_event_query(url, event)

    # GameCore callbacks fire from worker threads -> they only push events.
    game = ctx.game
    game.on_status = lambda text, level="info": emitter.emit(
        "status", {"text": text, "level": level or "info"})
    game.on_progress = emitter.emit_progress
    game.on_started = lambda: emitter.emit("game_state", api.state())
    game.on_stopped = lambda: emitter.emit("game_state", api.state())

    if config.settings.get("discord_rpc", True):
        try:
            ctx.discord.connect()
            ctx.discord.update_status("In Launcher", "Browsing Menu")
        except Exception:
            pass

    import webview

    window = webview.create_window(
        title=APP_NAME,
        url=url,
        js_api=api,
        width=1280,
        height=800,
        min_size=(960, 600),
        frameless=True,
        easy_drag=False,
        text_select=True,
        background_color="#0e1016",
    )
    api.attach(window)
    emitter.attach(window)

    try:
        window.events.maximized += lambda *a: api.set_maximized(True)
        window.events.restored += lambda *a: api.set_maximized(False)
    except Exception:
        pass

    icon = None
    try:
        from gui_web.assets import resources_dir
        if sys.platform.startswith("win"):
            cand = resources_dir() / "icon.ico"
        else:
            cand = resources_dir() / "splash.png"
        if cand.is_file():
            icon = str(cand)
    except Exception:
        icon = None

    try:
        webview.start(gui=_pick_gui(), debug=bool(args.dev), icon=icon)
    finally:
        try:
            api.shutdown()
        except Exception:
            pass
        try:
            ctx.discord.disconnect()
        except Exception:
            pass
        try:
            ctx.network.close()
        except Exception:
            pass
        if cleanup:
            try:
                cleanup()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
