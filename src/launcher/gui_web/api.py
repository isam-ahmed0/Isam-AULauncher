"""JS <-> Python bridge for the pywebview interface.

Every public method is exposed as ``window.pywebview.api.<name>()`` and
returns a JSON-serialisable ``{"ok": True, "data": ...}`` or
``{"ok": False, "error": ...}`` envelope.  Fast local work runs inline;
anything that touches the network or walks the disk runs on a worker thread
and reports back through :class:`gui_web.events.Emitter` events.

pywebview executes API calls on its own threads, but shared state is still
guarded by a lock so two JS calls can never mutate config at once.
"""
import base64
import logging
import os
import socket
import threading
import time
from pathlib import Path

from config import (APP_NAME, LAUNCHER_VERSION, DEFAULT_GAME_DIR,
                    LAUNCHER_UPDATE_URL, SOURCE_CODE_URL)
from platform_utils import IS_LINUX, IS_WINDOWS
from file_manager import FileManager

log = logging.getLogger(__name__)

_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
}
_MAX_IMAGE_BYTES = 12 * 1024 * 1024


def _ok(data=None):
    return {"ok": True, "data": data}


def _err(message):
    return {"ok": False, "error": str(message)}


class LauncherApi:
    """The object pywebview exposes to the page."""

    def __init__(self, ctx, emitter):
        self.ctx = ctx
        self.em = emitter
        self._lock = threading.RLock()
        self._window = None
        self._busy = False
        self._stop = threading.Event()
        self._started = False
        self._latest_version = None
        self._game_update = {"needed": False, "latest": None}
        self._releases = None
        self._releases_error = None
        self._maximized = False
        self._catalog_mgr = None
        self._regions_mgr = None
        self._catalog_cache = {"mods": [], "states": {}, "error": None, "offline": False}

    # ------------------------------------------------------------ plumbing
    def attach(self, window):
        self._window = window

    def set_maximized(self, value):
        """Track frameless-window maximize state (pywebview has no getter)."""
        self._maximized = bool(value)
        self.em.emit("window_state", {"maximized": self._maximized})

    def _spawn(self, target, *args):
        return self.ctx.run_thread(target, *args)

    def _emit_state(self):
        self.em.emit("game_state", self.state())

    def _running(self):
        try:
            return bool(self.ctx.game.is_running)
        except Exception:
            return False

    def _catalog(self):
        if self._catalog_mgr is None:
            from mod_catalog import ModCatalogManager
            self._catalog_mgr = ModCatalogManager(self.ctx.config, self.ctx.network)
        return self._catalog_mgr

    def _regions(self):
        if self._regions_mgr is None:
            from gui_qt.regions import RegionManager
            path = None
            if IS_LINUX:
                try:
                    prefix = self.ctx.config.get_wine_prefix()
                    if prefix:
                        user = os.environ.get("USER") or Path.home().name
                        path = (Path(prefix) / "drive_c" / "users" / user
                                / "AppData" / "LocalLow" / "Innersloth"
                                / "Among Us" / "regionInfo.json")
                except Exception as exc:
                    log.debug("could not resolve Wine region path: %s", exc)
            self._regions_mgr = RegionManager(path=path)
        return self._regions_mgr

    def _regions_payload(self):
        mgr = self._regions()
        return {
            "regions": mgr.regions,
            "active_index": mgr.active_index,
            "path": str(mgr.path),
            "exists": bool(mgr.path and mgr.path.is_file()),
        }

    def state(self):
        """Cheap, purely local snapshot of the game/launcher state."""
        ctx = self.ctx
        gp = ctx.game_path()
        try:
            running = bool(ctx.game.is_running)
        except Exception:
            running = False
        try:
            pid = int(ctx.pid or 0)
        except Exception:
            pid = 0
        installed = ctx.is_installed()
        version = ctx.version()
        latest = self._latest_version
        return {
            "installed": installed,
            "version": version,
            "path": str(gp) if gp else None,
            "running": running,
            "pid": pid,
            "busy": self._busy,
            "latest": latest,
            "update": dict(self._game_update),
            "needs_install": (gp is None) or (not installed),
            "launcher_version": LAUNCHER_VERSION,
            "active_profile": ctx.config.get_active_profile(),
        }

    # ------------------------------------------------------------ lifecycle
    def bootstrap(self):
        """One round-trip snapshot so the first paint needs no requests."""
        ctx = self.ctx
        cfg = ctx.config
        settings = cfg.settings
        home = {
            "image": settings.get("home_image_path", "") or "",
            "note": settings.get("home_note", "") or "",
            "image_data": self._read_image(settings.get("home_image_path", "")),
        }
        try:
            log_path = str(ctx.get_launcher_log_path() or "")
        except Exception:
            log_path = ""
        return _ok({
            "app": {
                "name": APP_NAME,
                "launcher_version": LAUNCHER_VERSION,
                "game_version": ctx.version(),
                "platform": "windows" if IS_WINDOWS else ("linux" if IS_LINUX else "other"),
                "dev": False,
            },
            "state": self.state(),
            "settings": self.settings_get().get("data", {}),
            "home": home,
            "paths": {
                "appdata": str(ctx.appdata_dir),
                "profiles": str(ctx.profiles_dir),
                "guis": str(ctx.guis_dir),
                "log": log_path,
                "default_game_dir": str(DEFAULT_GAME_DIR),
            },
        })

    def ready(self):
        """The page is up: flush queued events and start background work."""
        self.em.enable()
        # Push one authoritative snapshot as soon as the page can receive it;
        # the JS boot also re-reads game_state, so a lost early call self-heals.
        self._emit_state()
        if self._started:
            return _ok(True)
        self._started = True
        self._spawn(self._poll_loop)
        # Launcher + game checks run together at startup. The page already has
        # its event listeners installed before calling ready(), so the result
        # lands on the Updates page without pressing "Check for updates".
        self._spawn(self._update_check_worker)
        if IS_LINUX:
            self._spawn(self._detect_system)
        return _ok(True)

    def _poll_loop(self):
        """Catch game start/stop even when the process exits on its own."""
        while not self._stop.is_set():
            try:
                before = self.state()["running"]
                self.ctx.poll()
                after = self.state()["running"]
                if before != after:
                    self._emit_state()
            except Exception as exc:
                log.debug("poll failed: %s", exc)
            self._stop.wait(2.0)

    def shutdown(self):
        self._stop.set()
        self.em.shutdown()

    def _check_game_update(self):
        try:
            current = self.ctx.version()
            needed, latest = self.ctx.check_update(current)
            self._latest_version = latest
            self._game_update = {"needed": bool(needed), "latest": latest}
        except Exception as exc:
            log.debug("update check failed: %s", exc)
        self.em.emit("update_check", self._game_update)
        self._emit_state()

    def system_payload(self):
        """Local GPU + Wine/Proton snapshot for the Settings page."""
        payload = {
            "gpus": [], "gpu": "", "wine": "", "wines": [], "runners": [],
            "wine_binary": "", "runner": "", "runner_kind": "", "prefix": "",
        }
        try:
            import graphics
            gpus = graphics.detect_gpus() or []
            payload["gpus"] = gpus
            gpu_id = self.ctx.config.get_gpu()
            payload["gpu"] = graphics.describe_gpu(gpu_id, gpus) or ""
        except Exception as exc:
            log.debug("gpu detect failed: %s", exc)
        try:
            import graphics as g
            payload["wine_binary"] = self.ctx.config.get_wine_binary()
            runners = g.detect_runners() or []
            payload["runners"] = runners
            payload["wines"] = runners  # legacy key for older UI code
            runner = g.resolve_runner(payload["wine_binary"])
            payload["runner"] = runner or ""
            payload["runner_kind"] = g.runner_kind(runner) if runner else ""
            payload["wine"] = runner or ""  # legacy key
            payload["prefix"] = str(self.ctx.config.get_wine_prefix())
        except Exception as exc:
            log.debug("runner detect failed: %s", exc)
        return payload

    def _detect_system(self):
        """Push the startup GPU + Wine probe once the page is ready."""
        self.em.emit("system", self.system_payload())

    def system_info(self):
        """Re-read GPU/Wine data when Settings opens (no event dependency)."""
        return _ok(self.system_payload())

    # ------------------------------------------------------------ window
    def win_min(self):
        if self._window:
            self._window.minimize()
        return _ok(True)

    def win_max(self):
        if self._window:
            self._window.maximize()
            self.set_maximized(True)
        return _ok(True)

    def win_restore(self):
        if self._window:
            self._window.restore()
            self.set_maximized(False)
        return _ok(True)

    def win_toggle_max(self):
        if not self._window:
            return _ok(False)
        if self._maximized:
            self._window.restore()
            self.set_maximized(False)
        else:
            self._window.maximize()
            self.set_maximized(True)
        return _ok(True)

    def win_close(self):
        if self._window:
            self._window.destroy()
        return _ok(True)

    # ------------------------------------------------------------ game: state
    def game_state(self):
        return _ok(self.state())

    def game_install(self, folder=None, version=None):
        """Download/install the game (threaded, progress via events)."""
        with self._lock:
            if self._busy:
                return _err("An install or update is already running.")
            self._busy = True
        if folder:
            try:
                self.ctx.config.set_game_path(Path(folder))
            except Exception as exc:
                with self._lock:
                    self._busy = False
                return _err(f"Could not use that folder: {exc}")
        self._emit_state()
        self._spawn(self._install_worker, version)
        return _ok({"started": True})

    def _install_worker(self, version=None):
        ok = False
        try:
            gp = self.ctx.game_path()
            if not gp:
                self.em.emit("status", {"text": "No install folder selected",
                                        "level": "danger"})
                return
            if not version:
                version = self._latest_version
            if not version:
                self.em.emit("status", {"text": "Checking for the latest version…",
                                        "level": "info"})
                version = self.ctx.get_latest_version()
            if not version:
                self.em.emit("status", {"text": "Failed to fetch version info",
                                        "level": "danger"})
                return
            self.em.emit("status", {"text": f"Downloading v{version}…", "level": "info"})
            ok = bool(self.ctx.game.download_update(version, gp))
            if ok:
                self.ctx.config.set_version(version)
                self._latest_version = version
                self._game_update = {"needed": False, "latest": version}
                self.em.emit("progress", {"pct": 100.0, "force": True})
        except Exception as exc:
            log.exception("install failed")
            self.em.emit("status", {"text": f"Error: {exc}", "level": "danger"})
        finally:
            with self._lock:
                self._busy = False
            self.em.emit("install_done", {"ok": ok, "version": version})
            self._emit_state()

    def game_launch(self, force=False):
        """Launch the game; returns mod warnings first (unless forced)."""
        if not self.ctx.is_installed():
            return _err("Game not installed.")
        if not force:
            warnings = self._mod_warnings()
            if warnings:
                return _ok({"warnings": warnings})
        with self._lock:
            if self._busy:
                return _err("Another action is running.")
            self._busy = True
        self._emit_state()
        self._spawn(self._launch_worker)
        return _ok({"started": True})

    def _mod_warnings(self):
        try:
            from mod_inspector import inspect_profile_dlls
            profile = self.ctx.get_profile_path()
            if not profile:
                return []
            _, issues = inspect_profile_dlls(Path(profile))
            return [
                {"kind": i.kind, "severity": i.severity, "description": i.description}
                for i in (issues or [])
            ]
        except Exception as exc:
            log.debug("mod warning scan failed: %s", exc)
            return []

    def _launch_worker(self):
        ok = False
        try:
            if IS_LINUX:
                import graphics
                runner = graphics.resolve_runner(self.ctx.config.get_wine_binary())
                if not runner or not self.ctx.config.is_linux_setup_complete():
                    self.em.emit("status", {
                        "text": "Wine/Proton is not set up yet — run setup in Settings.",
                        "level": "warning",
                    })
                    self.em.emit("toast", {
                        "level": "warning", "title": "Setup required",
                        "message": "No Wine/Proton runner is configured. Open "
                                   "Settings → Graphics and run the setup wizard first.",
                    })
                    return
                ok = bool(self.ctx.game.launch_wine(
                    self.ctx.game_path(), self.ctx.game_path() / "Among Us.exe"))
            else:
                ok = bool(self.ctx.game.launch())
        except Exception as exc:
            log.exception("launch failed")
            self.em.emit("toast", {"level": "danger", "title": "Launch failed",
                                   "message": str(exc)})
        finally:
            with self._lock:
                self._busy = False
            if ok:
                self.em.emit("toast", {"level": "success", "title": "Launching",
                                       "message": "Starting Among Us…"})
            self._emit_state()

    def game_stop(self):
        with self._lock:
            if self._busy:
                return _err("Another action is running.")
            self._busy = True
        self._spawn(self._stop_worker)
        return _ok({"started": True})

    def _stop_worker(self):
        try:
            self.ctx.game.stop()
        except Exception as exc:
            log.debug("stop failed: %s", exc)
        finally:
            with self._lock:
                self._busy = False
            self._emit_state()

    # ------------------------------------------------------------ game: files
    def game_verify(self):
        gp = self.ctx.game_path()
        if not gp:
            return _err("Game not installed.")
        self.em.emit("status", {"text": "Verifying files…", "level": "info"})
        self._spawn(self._verify_worker, str(gp))
        return _ok({"started": True})

    def _verify_worker(self, path):
        result = {"ok": False, "error": "Unknown error"}
        try:
            r = FileManager.verify_game_folder(Path(path))
            result = {
                "ok": True,
                "valid": bool(r.get("valid")),
                "exe_found": bool(r.get("exe_found")),
                "missing": list(r.get("missing") or []),
                "file_count": int(r.get("file_count") or 0),
                "total_size": int(r.get("total_size") or 0),
                "size_text": FileManager.format_size(int(r.get("total_size") or 0)),
            }
        except Exception as exc:
            log.exception("verify failed")
            result = {"ok": False, "error": str(exc)}
        self.em.emit("verify_result", result)
        self.em.emit("status", {"text": "Verification finished", "level": "info"})

    def game_inspect_folder(self, path, purpose="change"):
        """Verify a folder the user picked (threaded) before we commit to it."""
        if not path:
            return _err("No folder given.")
        self._spawn(self._inspect_worker, str(path), purpose)
        return _ok({"started": True})

    def _inspect_worker(self, path, purpose):
        try:
            r = FileManager.verify_game_folder(Path(path))
            self.em.emit("folder_inspect", {
                "ok": True,
                "path": path,
                "purpose": purpose,
                "exe_found": bool(r.get("exe_found")),
                "missing": list(r.get("missing") or []),
                "file_count": int(r.get("file_count") or 0),
                "total_size": int(r.get("total_size") or 0),
                "size_text": FileManager.format_size(int(r.get("total_size") or 0)),
            })
        except Exception as exc:
            self.em.emit("folder_inspect", {"ok": False, "path": path,
                                            "purpose": purpose, "error": str(exc)})

    def game_apply_change(self, path, purpose="change", move_files=False):
        """Commit a folder choice (locate / change location)."""
        if not path:
            return _err("No folder given.")
        with self._lock:
            if self._busy:
                return _err("Another action is running.")
            self._busy = True
        self._spawn(self._change_worker, str(path), purpose, bool(move_files))
        return _ok({"started": True})

    def _change_worker(self, path, purpose, move_files):
        try:
            new_path = Path(path)
            if purpose == "locate":
                if not (new_path / "Among Us.exe").exists():
                    self.em.emit("toast", {
                        "level": "danger", "title": "Not a game folder",
                        "message": "Among Us.exe was not found in that folder.",
                    })
                    return
                self.ctx.config.set_game_path(new_path)
                if not self.ctx.config.get_version():
                    self.ctx.config.set_version(self._latest_version or "Unknown")
                self.em.emit("toast", {"level": "success", "title": "Game located",
                                       "message": str(new_path)})
            else:
                old = self.ctx.game_path()
                if (
                    move_files and old and old.exists()
                    and old != new_path and new_path.parent.exists()
                ):
                    self.em.emit("status", {"text": "Moving files…", "level": "info"})
                    try:
                        import shutil
                        shutil.move(str(old), str(new_path))
                    except (OSError, PermissionError) as exc:
                        self.em.emit("toast", {
                            "level": "danger", "title": "Move failed",
                            "message": str(exc),
                        })
                        return
                self.ctx.config.set_game_path(new_path)
                if not (new_path / "Among Us.exe").exists():
                    self.ctx.config.set_version("Not Installed")
                self.em.emit("toast", {"level": "success", "title": "Location set",
                                       "message": str(new_path)})
        except Exception as exc:
            log.exception("change location failed")
            self.em.emit("toast", {"level": "danger", "title": "Failed",
                                   "message": str(exc)})
        finally:
            with self._lock:
                self._busy = False
            self._emit_state()

    def game_open_folder(self):
        gp = self.ctx.game_path()
        if not gp or not Path(gp).exists():
            return _err("Game not installed.")
        return _ok(self.ctx.open_folder(gp))

    def game_create_shortcut(self):
        gp = self.ctx.game_path()
        if not gp:
            return _err("Game not installed.")
        try:
            if IS_LINUX:
                from platform_utils import create_desktop_shortcut
                gp = Path(gp)
                icon = None
                for cand in ("icon.png", "logo.png", "icon.ico"):
                    if (gp / cand).exists():
                        icon = gp / cand
                        break
                path = create_desktop_shortcut(
                    "Among Us (CREW AU)", gp / "Among Us.exe", str(gp),
                    prefix=self.ctx.config.get_wine_prefix(),
                    gpu=self.ctx.config.get_gpu(),
                    wine=self.ctx.config.get_wine_binary(),
                    icon_source=icon)
                return _ok({"message": f"Desktop shortcut created:\n{path}"})
            import win32com.client
            ver = self.ctx.config.get_version() or "Unknown"
            sc = Path.home() / "Desktop" / f"Among Us {ver}.lnk"
            sh = win32com.client.Dispatch("WScript.Shell")
            lnk = sh.CreateShortCut(str(sc))
            lnk.Targetpath = str(Path(gp) / "Among Us.exe")
            lnk.WorkingDirectory = str(gp)
            lnk.IconLocation = str(Path(gp) / "Among Us.exe")
            lnk.save()
            return _ok({"message": "Shortcut created on your Desktop."})
        except ImportError:
            return _err("pywin32 is not installed.")
        except Exception as exc:
            return _err(f"Failed to create shortcut: {exc}")

    # ------------------------------------------------------------ versions
    def game_versions(self):
        self._spawn(self._versions_worker)
        return _ok({"started": True})

    def _versions_worker(self):
        try:
            versions, error = self.ctx.network.get_releases()
            self._releases = [
                {"version": getattr(v, "version", None) or str(v),
                 "url": getattr(v, "url", ""),
                 "body": (getattr(v, "body", "") or "")[:400]}
                for v in (versions or [])
            ]
            self._releases_error = error
        except Exception as exc:
            self._releases = []
            self._releases_error = str(exc)
        self.em.emit("versions_result",
                     {"versions": self._releases, "error": self._releases_error})

    # ------------------------------------------------------------ folders
    def pick_folder(self, purpose="install"):
        """Native folder picker. Returns the chosen path or None."""
        import webview
        try:
            initial = str(DEFAULT_GAME_DIR)
            Path(initial).mkdir(parents=True, exist_ok=True)
        except Exception:
            initial = ""
        try:
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG, directory=initial,
                allow_multiple=False)
        except Exception as exc:
            return _err(f"Folder picker failed: {exc}")
        if not result:
            return _ok({"path": None})
        return _ok({"path": str(result[0]), "purpose": purpose})

    def pick_file(self, kinds="images", multiple=False):
        import webview
        if kinds == "images":
            types = ("Images (*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp)",)
        elif kinds == "mods":
            types = ("Mod files (*.dll;*.zip)", "All files (*.*)")
        else:
            types = ("All files (*.*)",)
        try:
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=bool(multiple),
                file_types=types)
        except Exception as exc:
            return _err(f"File picker failed: {exc}")
        if not result:
            return _ok({"path": None, "paths": []})
        paths = [str(p) for p in result]
        return _ok({"path": paths[0], "paths": paths})

    # ------------------------------------------------------------ home card
    @staticmethod
    def _read_image(path):
        if not path:
            return None
        p = Path(path)
        try:
            if not p.is_file() or p.stat().st_size > _MAX_IMAGE_BYTES:
                return None
            mime = _MIME.get(p.suffix.lower(), "image/png")
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{data}"
        except OSError:
            return None

    def home_image_set(self):
        picked = self.pick_file("images")
        if not picked.get("ok"):
            return picked
        path = picked["data"]["path"]
        if not path:
            return _ok({"path": None})
        data = self._read_image(path)
        if not data:
            return _err("That image could not be read (max 12 MB).")
        with self._lock:
            self.ctx.config.settings["home_image_path"] = path
            self.ctx.config.save_settings()
        return _ok({"path": path, "image_data": data})

    def home_image_clear(self):
        with self._lock:
            self.ctx.config.settings["home_image_path"] = ""
            self.ctx.config.save_settings()
        return _ok(True)

    def home_note_set(self, note):
        with self._lock:
            self.ctx.config.settings["home_note"] = (note or "")[:600]
            self.ctx.config.save_settings()
        return _ok(True)

    # ------------------------------------------------------------ profiles
    def profiles_list(self):
        """All profiles with their active state and mod counts."""
        try:
            names = self.ctx.list_profiles()
            active = self.ctx.get_active_profile()
            profiles = []
            pmanager = self.ctx.profiles
            for name in names:
                count, enabled = 0, 0
                if pmanager:
                    try:
                        files = pmanager.list_mod_files(name)
                        count = len(files)
                        enabled = sum(1 for f in files if pmanager.is_enabled(name, f.name))
                    except Exception:
                        pass
                profiles.append({
                    "name": name,
                    "active": name == active,
                    "count": count,
                    "enabled": enabled,
                })
            return _ok({"profiles": profiles, "active": active})
        except Exception as exc:
            return _err(str(exc))

    @staticmethod
    def _display_name(filename):
        lower = filename.lower()
        if lower.endswith(".dll.disabled"):
            return filename[:-len(".dll.disabled")]
        if lower.endswith(".dll"):
            return filename[:-4]
        return filename

    def profile_create(self, name):
        name = (name or "").strip()
        if not name:
            return _err("Enter a profile name.")
        with self._lock:
            if not self.ctx.create_profile(name):
                return _err("Profile already exists or could not be created.")
        self.em.emit("profiles_changed", self.profiles_list().get("data", {}))
        return _ok({"name": name})

    def profile_rename(self, old, new):
        new = (new or "").strip()
        if not new or old == new:
            return _err("Enter a different profile name.")
        if self._running():
            return _err("Close the game before renaming a profile.")
        was_active = old == self.ctx.get_active_profile()
        with self._lock:
            if not self.ctx.rename_profile(old, new):
                return _err("Profile could not be renamed (name may be taken).")
            if was_active:
                self.ctx.set_active_profile(new)
                self.ctx.switch_profile(new)
        self.em.emit("profiles_changed", self.profiles_list().get("data", {}))
        self.em.emit("mods_changed", self.mods_list().get("data", {}))
        return _ok({"name": new})

    def profile_delete(self, name):
        if name == self.ctx.get_active_profile():
            return _err("Switch to another profile before deleting this one.")
        with self._lock:
            if not self.ctx.delete_profile(name):
                return _err("Profile could not be deleted.")
        self.em.emit("profiles_changed", self.profiles_list().get("data", {}))
        return _ok(True)

    def profile_activate(self, name):
        """Switch the plugins link *and* persist the active profile."""
        if self._running():
            return _err("Close the game before switching profiles.")
        with self._lock:
            if not self.ctx.switch_profile(name):
                return _err("Could not link the game to that profile.")
            self.ctx.set_active_profile(name)
        self.em.emit("profiles_changed", self.profiles_list().get("data", {}))
        self.em.emit("mods_changed", self.mods_list().get("data", {}))
        self._emit_state()
        return _ok({"active": name})

    def profile_first_run(self):
        """One-time migration of an existing plugins folder into profiles."""
        gp = self.ctx.game_path()
        if not gp:
            return _err("No game folder is configured.")
        try:
            with self._lock:
                active = self.ctx.profiles.ensure_first_profiles(gp)
                if active:
                    self.ctx.set_active_profile(active)
            self.em.emit("profiles_changed", self.profiles_list().get("data", {}))
            return _ok({"active": active})
        except Exception as exc:
            return _err(str(exc))

    # ------------------------------------------------------------ mods
    def mods_list(self, profile=None):
        """Full mod list for a profile, with enabled state and catalog id."""
        profile = profile or self.ctx.get_active_profile()
        pmanager = self.ctx.profiles
        if not pmanager:
            return _err("Profile manager unavailable.")
        try:
            mgr = self._catalog()
            files = pmanager.list_mod_files(profile)
            installed = mgr.installed(profile)
            by_file = {}
            for mod_id, record in installed.items():
                names = list(record.get("files") or [])
                if record.get("filename") and record["filename"] not in names:
                    names.append(record["filename"])
                for filename in names:
                    by_file[filename] = {"id": mod_id}
            mods = []
            for path in files:
                info = by_file.get(path.name, {})
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                mods.append({
                    "filename": path.name,
                    "name": self._display_name(path.name),
                    "enabled": pmanager.is_enabled(profile, path.name),
                    "size": size,
                    "size_text": self.ctx.format_size(size),
                    "catalog_id": info.get("id"),
                })
            return _ok({
                "profile": profile,
                "mods": mods,
                "count": len(mods),
                "enabled": sum(1 for m in mods if m["enabled"]),
            })
        except Exception as exc:
            return _err(str(exc))

    def _emit_mods(self):
        result = self.mods_list()
        if result.get("ok"):
            self.em.emit("mods_changed", result["data"])

    def mod_toggle(self, filename, enabled):
        profile = self.ctx.get_active_profile()
        with self._lock:
            try:
                ok = self.ctx.profiles.set_enabled(profile, filename, bool(enabled))
            except Exception as exc:
                return _err(str(exc))
        if not ok:
            return _err("Could not toggle that mod.")
        self._emit_mods()
        return _ok({"filename": filename, "enabled": bool(enabled)})

    def mod_move(self, filename, delta):
        with self._lock:
            try:
                ok = self.ctx.profiles.reorder_mod(
                    self.ctx.get_active_profile(), filename, int(delta))
            except Exception as exc:
                return _err(str(exc))
        if not ok:
            return _err("Could not move that mod.")
        self._emit_mods()
        return _ok(True)

    def mod_remove(self, filename):
        if self._running():
            return _err("Close the game before removing mods.")
        profile = self.ctx.get_active_profile()
        try:
            with self._lock:
                mgr = self._catalog()
                record = mgr.record_for_file(profile, filename)
                if record:
                    ok, message = mgr.uninstall(record[0], profile)
                else:
                    target = self.ctx.get_profile_path(profile) / filename
                    target.unlink(missing_ok=True)
                    ok, message = True, f"Removed {filename}"
            if not ok:
                return _err(message)
            self._emit_mods()
            self.em.emit("toast", {"level": "success", "title": "Mod removed",
                                   "message": message})
            return _ok(True)
        except Exception as exc:
            return _err(str(exc))

    def mod_import(self):
        """Pick DLL/ZIP files and import them into the active profile."""
        if self._running():
            return _err("Close the game before importing mods.")
        picked = self.pick_file("mods", multiple=True)
        if not picked.get("ok"):
            return picked
        paths = picked["data"].get("paths") or []
        if not paths:
            return _ok({"started": False})
        self._spawn(self._import_worker, paths)
        return _ok({"started": True, "count": len(paths)})

    def _import_worker(self, paths):
        from mod_catalog import install_archive, CatalogError
        profile = self.ctx.get_active_profile()
        target = self.ctx.get_profile_path(profile)
        added = []
        errors = []
        if not target:
            self.em.emit("toast", {"level": "danger", "title": "Import failed",
                                   "message": "No active profile folder."})
            return
        target.mkdir(parents=True, exist_ok=True)
        for raw in paths:
            path = Path(raw)
            try:
                if path.suffix.lower() == ".zip":
                    names = install_archive(path, target)
                elif path.suffix.lower() == ".dll":
                    import shutil
                    target_file = target / path.name
                    shutil.copy2(path, target_file)
                    names = [target_file.name]
                else:
                    errors.append(f"{path.name}: unsupported file type")
                    continue
                added.extend(names)
            except (CatalogError, OSError) as exc:
                errors.append(f"{path.name}: {exc}")
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.em.emit("mods_changed", self.mods_list().get("data", {}))
        if added:
            self.em.emit("toast", {
                "level": "success", "title": "Mods imported",
                "message": f"Added {len(added)} file(s) to {profile}.",
            })
        if errors:
            self.em.emit("toast", {
                "level": "warning", "title": "Some files were skipped",
                "message": "\n".join(errors[:5]),
            })

    def mod_issues(self):
        """Scan installed DLLs for duplicate/missing/conflict warnings."""
        profile = self.ctx.get_profile_path()
        if not profile:
            return _err("No active profile folder.")
        self._spawn(self._issues_worker, str(profile))
        return _ok({"started": True})

    def _issues_worker(self, profile):
        try:
            from mod_inspector import inspect_profile_dlls
            _, issues = inspect_profile_dlls(Path(profile))
            payload = [{
                "kind": i.kind, "severity": i.severity,
                "description": i.description,
            } for i in (issues or [])]
        except Exception as exc:
            log.debug("mod issue scan failed: %s", exc)
            payload = []
        self.em.emit("mod_issues", {"issues": payload})

    # ------------------------------------------------------------ catalog
    @staticmethod
    def _entry_dict(entry):
        return {
            "id": entry.id,
            "name": entry.name,
            "author": entry.author,
            "category": entry.category,
            "description": entry.description,
            "dependencies": list(entry.dependencies or []),
            "incompatibilities": list(entry.incompatibilities or []),
            "game_version": entry.game_version,
            "is_archive": bool(entry.is_archive),
        }

    def catalog_get(self):
        """Cached catalog + install states, so view switches are instant."""
        return _ok(dict(self._catalog_cache))

    def catalog_load(self, force=False):
        """Fetch/refresh the remote mod catalog in the background."""
        self._spawn(self._catalog_worker, bool(force))
        return _ok({"started": True})

    def _catalog_worker(self, force):
        try:
            mgr = self._catalog()
            catalog = mgr.fetch(force=force)
            profile = self.ctx.get_active_profile()
            mods = [self._entry_dict(e) for e in (catalog.mods if catalog else [])]
            payload = {
                "mods": mods,
                "states": mgr.status(profile),
                "profile": profile,
                "error": mgr.error,
                "offline": bool(mgr.offline),
                "updated_at": getattr(catalog, "updated_at", ""),
            }
        except Exception as exc:
            log.exception("catalog fetch failed")
            payload = {
                "mods": [], "states": {}, "profile": self.ctx.get_active_profile(),
                "error": str(exc), "offline": True, "updated_at": "",
            }
        with self._lock:
            self._catalog_cache = payload
        self.em.emit("catalog_result", payload)

    def catalog_install(self, mod_id):
        if self._running():
            return _err("Close the game before installing mods.")
        catalog = self._catalog().catalog
        entry = catalog.by_id(mod_id) if catalog else None
        if not entry:
            return _err("That mod is no longer in the catalog.")
        self._spawn(self._catalog_install_worker, mod_id)
        return _ok({"started": True})

    def _catalog_install_worker(self, mod_id):
        def progress(downloaded, total, speed=None):
            pct = (float(downloaded) / float(total) * 100.0) if total else 0.0
            self.em.emit_progress(pct)

        try:
            entry = self._catalog().catalog.by_id(mod_id)
            with self._lock:
                ok, message = self._catalog().install(
                    entry, self.ctx.get_active_profile(),
                    progress_callback=progress,
                    is_running=self._running)
        except Exception as exc:
            log.exception("catalog install failed")
            ok, message = False, str(exc)
        self.em.emit("progress", {"pct": 100.0 if ok else 0.0, "done": True})
        self.em.emit("catalog_install_done", {"id": mod_id, "ok": ok, "message": message})
        self.em.emit("toast", {
            "level": "success" if ok else "danger",
            "title": "Mod install" if ok else "Install failed",
            "message": message,
        })
        self._emit_mods()
        self._catalog_worker(force=False)

    def catalog_remove(self, mod_id):
        if self._running():
            return _err("Close the game before removing mods.")
        self._spawn(self._catalog_remove_worker, mod_id)
        return _ok({"started": True})

    def _catalog_remove_worker(self, mod_id):
        try:
            with self._lock:
                ok, message = self._catalog().uninstall(
                    mod_id, self.ctx.get_active_profile())
        except Exception as exc:
            ok, message = False, str(exc)
        self.em.emit("toast", {
            "level": "success" if ok else "warning",
            "title": "Mod removed" if ok else "Could not remove mod",
            "message": message,
        })
        self._emit_mods()
        self._catalog_worker(force=False)

    # ------------------------------------------------------------ regions
    def regions_get(self):
        with self._lock:
            try:
                mgr = self._regions()
                mgr.load()
                return _ok(self._regions_payload())
            except Exception as exc:
                return _err(str(exc))

    def _regions_save(self):
        mgr = self._regions()
        if not mgr.save():
            raise OSError(f"Could not write {mgr.path}")
        payload = self._regions_payload()
        self.em.emit("regions_changed", payload)
        return payload

    def regions_add(self, name, ping_server, server_ip, port=443):
        name = (name or "").strip()
        ping_server = (ping_server or "").strip()
        server_ip = (server_ip or "").strip()
        if not name or not ping_server or not server_ip:
            return _err("Name, ping server and server URL are required.")
        with self._lock:
            try:
                mgr = self._regions()
                mgr.load()
                if not mgr.add(name, ping_server, server_ip, int(port)):
                    return _err("A region with that name already exists.")
                return _ok(self._regions_save())
            except Exception as exc:
                return _err(str(exc))

    def regions_remove(self, index):
        with self._lock:
            try:
                mgr = self._regions()
                mgr.load()
                if not mgr.remove(int(index)):
                    return _err("That region could not be removed.")
                return _ok(self._regions_save())
            except Exception as exc:
                return _err(str(exc))

    def regions_apply(self, index):
        with self._lock:
            try:
                mgr = self._regions()
                mgr.load()
                mgr.active_index = int(index)
                return _ok(self._regions_save())
            except Exception as exc:
                return _err(str(exc))

    def regions_reset(self):
        with self._lock:
            try:
                mgr = self._regions()
                mgr.load()
                mgr.reset_official()
                return _ok(self._regions_save())
            except Exception as exc:
                return _err(str(exc))

    def regions_ping(self, index):
        """TCP reachability probe (not an ICMP ping)."""
        try:
            mgr = self._regions()
            mgr.load()
            region = mgr.regions[int(index)]
            host = str(region.get("PingServer") or "").strip()
            if "://" in host:
                host = host.split("://", 1)[1]
            host = host.rstrip("/").split("/")[0]
            servers = region.get("Servers") or []
            port = int(servers[0].get("Port") or 443) if servers else 443
            if not host:
                return _err("That region has no ping server.")
        except Exception as exc:
            return _err(str(exc))
        self._spawn(self._ping_worker, int(index), host, port)
        return _ok({"started": True})

    def _ping_worker(self, index, host, port=443):
        start = time.monotonic()
        try:
            with socket.create_connection((host, port), timeout=3.0):
                ms = round((time.monotonic() - start) * 1000)
                ok, message = True, f"{host}:{port} — {ms} ms"
        except OSError as exc:
            ms, ok = None, False
            message = f"{host}:{port} — unreachable ({exc})"
        self.em.emit("region_ping", {
            "index": index, "ok": ok, "ms": ms, "message": message,
        })
        self.em.emit("toast", {
            "level": "success" if ok else "warning",
            "title": "Region check", "message": message,
        })

    # ------------------------------------------------------------ settings
    SETTING_KEYS = (
        "theme", "web_theme", "ui_mode", "display_backend", "auto_update",
        "discord_rpc", "create_shortcuts",
        "active_profile", "gpu_id", "wine_binary", "wine_prefix",
        "warn_plain_wine", "home_note",
    )

    def settings_get(self):
        s = self.ctx.config.settings
        payload = {key: s.get(key, "") for key in self.SETTING_KEYS}
        payload["web_theme"] = s.get("web_theme", "dark") or "dark"
        payload["ui_mode"] = s.get("ui_mode", "web") or "web"
        for key in ("auto_update", "discord_rpc", "create_shortcuts",
                    "warn_plain_wine"):
            payload[key] = bool(s.get(key, True))
        payload["active_profile"] = self.ctx.config.get_active_profile()
        return _ok(payload)

    def settings_set(self, key, value):
        if key not in self.SETTING_KEYS:
            return _err(f"Unknown setting: {key}")
        if key == "web_theme":
            value = "light" if value == "light" else "dark"
        elif key == "ui_mode":
            value = str(value or "web").strip() or "web"
        elif key == "display_backend":
            value = str(value or "").strip().lower()
            if value not in ("", "x11", "wayland"):
                return _err("Invalid display backend.")
        elif key == "wine_binary":
            value = str(value or "").strip()
            if value:
                path = Path(value).expanduser()
                if not path.is_file() or not os.access(str(path), os.X_OK):
                    return _err("That Wine/Proton runner was not found or is not runnable.")
                value = str(path.resolve())
        elif key == "wine_prefix":
            value = str(value or "").strip()
        with self._lock:
            self.ctx.config.settings[key] = value
            self.ctx.config.save_settings()
        return _ok({"key": key, "value": value})

    # ------------------------------------------------------------ news
    def news_cached(self):
        """Cached announcement, available immediately/offline."""
        try:
            import news as news_feed
            item = news_feed.get_cached_news(self.ctx.config)
            if not item:
                return _ok({"text": "", "posts": [], "identity": "", "offline": True})
            return _ok({
                "text": item.text,
                "posts": news_feed.split_posts(item.text),
                "identity": item.identity,
                "offline": True,
            })
        except Exception as exc:
            return _err(str(exc))

    def news_load(self, force=False):
        """Fetch the announcement in the background; cache it on success."""
        self._spawn(self._news_worker, bool(force))
        return _ok({"started": True})

    def _news_worker(self, force=False):
        """Always try the network; fall back to the cached copy when offline."""
        try:
            import news as news_feed
            item = news_feed.fetch_news(self.ctx.network)
            offline = item is None
            if item is None:
                item = news_feed.get_cached_news(self.ctx.config)
            else:
                with self._lock:
                    news_feed.cache_news(self.ctx.config, item)
            payload = {
                "text": item.text if item else "",
                "posts": news_feed.split_posts(item.text) if item else [],
                "identity": item.identity if item else "",
                "unseen": news_feed.is_unseen(self.ctx.config.settings, item),
                "offline": offline,
                "error": ("Offline — showing cached news." if offline and item
                          else "No announcements available yet." if not item else ""),
            }
        except Exception as exc:
            log.debug("news fetch failed: %s", exc)
            payload = {"text": "", "posts": [], "identity": "", "offline": True,
                       "unseen": False, "error": str(exc)}
        self.em.emit("news_result", payload)

    def news_mark_seen(self):
        try:
            import news as news_feed
            with self._lock:
                news_feed.mark_seen(
                    self.ctx.config, news_feed.get_cached_news(self.ctx.config))
            return _ok(True)
        except Exception as exc:
            return _err(str(exc))

    # ------------------------------------------------------------ itch.io
    def _itch_prefix(self):
        """Prefix holding the game's itch token (None on Windows)."""
        if IS_WINDOWS:
            return None
        try:
            return self.ctx.get_wine_prefix()
        except Exception:
            return None

    def itch_status(self):
        """Local token state immediately; profile fetch runs in background."""
        try:
            import itch_oauth
            prefix = self._itch_prefix()
            token = itch_oauth.read_itch_token(prefix)
            payload = {
                "signed_in": bool(token),
                "username": "",
                "profile": {},
                "prefix": str(prefix or ""),
            }
            self.em.emit("itch_status", payload)
            if token:
                self._spawn(self._itch_profile_worker, prefix)
            return _ok(payload)
        except Exception as exc:
            return _err(str(exc))

    def _itch_profile_worker(self, prefix=None):
        try:
            import itch_oauth
            username = itch_oauth.fetch_itch_username(prefix=prefix, timeout=8.0)
            profile = itch_oauth.fetch_itch_profile(
                prefix=prefix, timeout=8.0, username=username)
        except Exception as exc:
            log.debug("itch profile fetch failed: %s", exc)
            username, profile = None, {}
        self.em.emit("itch_status", {
            "signed_in": True,
            "username": username or (profile or {}).get("username") or "",
            "profile": profile if isinstance(profile, dict) else {},
            "prefix": str(prefix or ""),
        })

    def itch_login(self):
        """Start the local OAuth flow and open itch.io in the browser."""
        if getattr(self, "_itch_flow", None) is not None:
            return _err("A sign-in is already in progress.")

        def done(token):
            self._itch_flow = None
            self.em.emit("toast", {
                "level": "success", "title": "Signed in",
                "message": "itch.io account linked successfully.",
            })
            self.itch_status()

        def failed(message):
            self._itch_flow = None
            self.em.emit("toast", {
                "level": "danger", "title": "itch.io sign-in",
                "message": message,
            })

        try:
            flow = self.ctx.itch_login(callback=done, on_error=failed)
        except Exception as exc:
            return _err(str(exc))
        if not flow:
            return _err("Could not start sign-in (port 7890 may be busy).")
        self._itch_flow = flow
        self.em.emit("toast", {
            "level": "info", "title": "itch.io sign-in",
            "message": "Continue in your browser, then return here.",
        })
        return _ok({"started": True})

    def itch_logout(self):
        try:
            import itch_oauth
            target = itch_oauth.itch_token_file(self._itch_prefix())
            with self._lock:
                if target.exists():
                    target.unlink()
            ok = True
        except Exception as exc:
            log.debug("itch logout failed: %s", exc)
            ok = False
        if ok:
            self.em.emit("itch_status", {
                "signed_in": False, "username": "", "profile": {},
                "prefix": str(self._itch_prefix() or ""),
            })
        return _ok({"ok": bool(ok)})

    # ------------------------------------------------------------ updater
    def update_check(self):
        """Check both launcher and game updates in the background."""
        self._spawn(self._update_check_worker)
        return _ok({"started": True})

    def _update_check_worker(self):
        remote = None
        try:
            remote = (self.ctx.network.fetch_text(LAUNCHER_UPDATE_URL) or "").strip()
        except Exception as exc:
            log.debug("launcher update check failed: %s", exc)
        available = False
        force_available = False
        if remote:
            try:
                from packaging.version import Version
                remote_version = Version(remote)
                local_version = Version(LAUNCHER_VERSION)
                available = remote_version > local_version
                # Keep PEP 440 ordering for the automatic update, but expose a
                # manual override when the remote tag is merely different
                # (e.g. the test tag 1.0-alpha against a local 1.0 build).
                force_available = remote_version != local_version
            except Exception:
                available = False
                force_available = False
        skipped = remote == self.ctx.config.settings.get("skipped_launcher_version")
        self.em.emit("launcher_update", {
            "available": bool(available and not skipped),
            "force_available": bool(force_available and not available and not skipped),
            "version": remote,
            "current": LAUNCHER_VERSION,
            "skipped": bool(skipped),
        })
        self._check_game_update()

    def _check_game_update(self):
        try:
            current = self.ctx.version()
            needed, latest = self.ctx.check_update(current)
            if latest:
                self._latest_version = latest
                self._game_update = {"needed": bool(needed), "latest": latest}
        except Exception:
            needed, latest = False, None
        skipped = latest == self.ctx.config.settings.get("skipped_game_version")
        self.em.emit("game_update", {
            "needed": bool(needed and not skipped),
            "latest": latest,
            "skipped": bool(skipped),
        })
        self._emit_state()

    def update_skip_game(self, version):
        with self._lock:
            self.ctx.config.settings["skipped_game_version"] = str(version)
            self.ctx.config.save_settings()
        self.em.emit("game_update", {"needed": False, "latest": version, "skipped": True})
        return _ok(True)

    def update_skip_launcher(self, version):
        with self._lock:
            self.ctx.config.settings["skipped_launcher_version"] = str(version)
            self.ctx.config.save_settings()
        self.em.emit("launcher_update", {
            "available": False, "version": version,
            "current": LAUNCHER_VERSION, "skipped": True,
        })
        return _ok(True)

    def update_launcher(self, version, force=False):
        """Install on Windows; open the matching release page elsewhere.

        ``force`` targets the exact tag instead of the latest release. It is
        used by the Web UI when the remote version is older than the local one
        and the user explicitly opts in.
        """
        version = str(version or "").strip()
        if not version:
            return _err("No launcher version was supplied.")
        if IS_WINDOWS:
            url = (f"{SOURCE_CODE_URL}/releases/download/{version}/"
                   "CrewLauncher-Setup.exe")
            import tempfile
            target = Path(tempfile.gettempdir()) / "CrewLauncher-Setup.exe"
            self._spawn(self._launcher_install_worker, url, str(target))
            return _ok({"started": True})
        page = (f"{SOURCE_CODE_URL}/releases/tag/{version}" if force
                else f"{SOURCE_CODE_URL}/releases/latest")
        return self.open_url(page)

    def _launcher_install_worker(self, url, target):
        def progress(downloaded, total, speed=None):
            pct = (float(downloaded) / float(total) * 100.0) if total else 0.0
            self.em.emit_progress(pct)

        try:
            ok = self.ctx.network.download_file(url, Path(target), progress_callback=progress)
        except Exception:
            log.exception("launcher update download failed")
            ok = False
        self.em.emit("progress", {"pct": 100.0 if ok else 0.0, "done": True})
        if not ok:
            self.em.emit("toast", {
                "level": "danger", "title": "Update failed",
                "message": "Could not download the installer.",
            })
            return
        try:
            import subprocess
            subprocess.Popen([target])
        except Exception as exc:
            self.em.emit("toast", {"level": "danger", "title": "Update failed",
                                   "message": str(exc)})
            return
        self.em.emit("toast", {"level": "info", "title": "Installing update",
                               "message": "The launcher will now restart."})
        time.sleep(1.0)
        os._exit(0)

    def app_restart(self):
        """Relaunch with the same arguments (used after interface changes)."""
        try:
            from app_restart import restart
            self._spawn(lambda: restart())
            return _ok({"started": True})
        except Exception as exc:
            return _err(str(exc))

    # ------------------------------------------------------------ misc
    def open_url(self, url):
        import webbrowser
        if not url or not str(url).startswith(("http://", "https://")):
            return _err("Invalid URL.")
        webbrowser.open(str(url))
        return _ok(True)

    def open_path(self, path):
        try:
            p = Path(path)
            if not p.exists():
                return _err("Path does not exist.")
            return _ok(self.ctx.open_folder(p))
        except Exception as exc:
            return _err(str(exc))

    def log_text(self, limit=400):
        """Tail of the launcher log (About page / diagnostics)."""
        try:
            path = self.ctx.get_launcher_log_path()
            if not path or not Path(path).is_file():
                return _ok("")
            lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
            return _ok("\n".join(lines[-int(limit):]))
        except Exception as exc:
            return _err(str(exc))

    def app_info(self):
        return _ok({
            "name": APP_NAME,
            "launcher_version": LAUNCHER_VERSION,
            "game_version": self.ctx.version(),
            "platform": "windows" if IS_WINDOWS else ("linux" if IS_LINUX else "other"),
        })
