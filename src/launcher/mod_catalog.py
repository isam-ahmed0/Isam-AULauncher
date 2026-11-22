"""Remote mod catalog: fetch, cache, install, update and remove BepInEx mods.

This module is deliberately toolkit-free — it must never import PySide6 or
tkinter.  Qt only supplies callbacks/progress reporters.

The catalog is a JSON file served over HTTPS (see ``docs/MOD_CATALOG.md``).
Installed catalog mods are recorded in a per-profile ``mods.json`` so the
launcher can tell which version is installed without re-reading DLL metadata.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

from config import MOD_CATALOG_TTL, MOD_CATALOG_URL

log = logging.getLogger(__name__)

META_NAME = "mods.json"
_PREFIX_RE = re.compile(r"^\d{2,3}_")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class CatalogError(ValueError):
    """Raised when a catalog file is malformed."""


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------
def version_newer(candidate: str, current: str) -> bool:
    """True when ``candidate`` is newer than ``current``.

    Falls back to a plain string comparison for non-PEP440 game version tags.
    """
    candidate = (candidate or "").strip()
    current = (current or "").strip()
    if not candidate:
        return False
    if not current or current in ("Unknown", "Not Installed"):
        return True
    try:
        from packaging.version import Version, InvalidVersion
        return Version(candidate) > Version(current)
    except (ImportError, InvalidVersion, ValueError):
        return candidate != current


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ModEntry:
    id: str
    name: str
    version: str = ""
    author: str = ""
    category: str = "Other"
    description: str = ""
    download_url: str = ""
    sha256: str = ""
    size: int = 0
    dependencies: list = field(default_factory=list)
    incompatibilities: list = field(default_factory=list)
    game_version: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> "ModEntry":
        if not isinstance(raw, dict):
            raise CatalogError("Every catalog entry must be a JSON object")
        entry_id = str(raw.get("id") or "").strip()
        name = str(raw.get("name") or "").strip()
        url = str(raw.get("download_url") or "").strip()
        if not entry_id or not name:
            raise CatalogError("A mod entry needs both 'id' and 'name'")
        if not url:
            raise CatalogError(f"Mod '{name}' has no 'download_url'")
        sha = str(raw.get("sha256") or "").strip().lower()
        if sha and not _SHA_RE.match(sha):
            raise CatalogError(f"Mod '{name}' has an invalid sha256 (expected 64 hex chars)")

        def str_list(key: str) -> list:
            value = raw.get(key) or []
            if not isinstance(value, (list, tuple)):
                value = [value]
            return [str(v).strip() for v in value if str(v).strip()]

        try:
            size = int(raw.get("size") or 0)
        except (TypeError, ValueError):
            size = 0

        return cls(
            id=entry_id,
            name=name,
            version=str(raw.get("version") or "").strip(),
            author=str(raw.get("author") or "").strip(),
            category=str(raw.get("category") or "Other").strip() or "Other",
            description=str(raw.get("description") or "").strip(),
            download_url=url,
            sha256=sha,
            size=size,
            dependencies=str_list("dependencies"),
            incompatibilities=str_list("incompatibilities"),
            game_version=str(raw.get("game_version") or "").strip(),
        )

    @property
    def is_archive(self) -> bool:
        path = self.download_url.split("?", 1)[0].lower()
        return path.endswith(".zip") or path.endswith(".7z")


@dataclass
class ModCatalog:
    mods: list = field(default_factory=list)
    updated_at: str = ""

    @classmethod
    def from_text(cls, text: str) -> "ModCatalog":
        try:
            data = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise CatalogError(f"Catalog is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise CatalogError("Catalog root must be a JSON object")
        raw_mods = data.get("mods")
        if not isinstance(raw_mods, list):
            raise CatalogError("Catalog needs a 'mods' array")

        mods = []
        seen = set()
        for raw in raw_mods:
            entry = ModEntry.from_dict(raw)
            if entry.id in seen:
                raise CatalogError(f"Duplicate mod id in catalog: {entry.id}")
            seen.add(entry.id)
            mods.append(entry)
        return cls(mods=mods, updated_at=str(data.get("updated_at") or ""))

    def by_id(self, mod_id: str) -> Optional[ModEntry]:
        for entry in self.mods:
            if entry.id == mod_id:
                return entry
        return None


# ---------------------------------------------------------------------------
# Per-profile metadata (shared with the mod manager UI)
# ---------------------------------------------------------------------------
def load_meta(profile_dir: Path) -> dict:
    """Read ``mods.json`` from a profile, returning a normalized structure."""
    path = Path(profile_dir) / META_NAME
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "order": list(data.get("order") or []),
                    "disabled": list(data.get("disabled") or []),
                    "catalog": dict(data.get("catalog") or {}),
                }
    except (OSError, ValueError, TypeError):
        log.warning("Could not read mod metadata at %s", path)
    return {"order": [], "disabled": [], "catalog": {}}


def save_meta(profile_dir: Path, meta: dict) -> bool:
    """Atomically write ``mods.json`` into a profile."""
    path = Path(profile_dir) / META_NAME
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)
        os.replace(tmp, path)
        return True
    except OSError as exc:
        log.error("Failed to save mod metadata at %s: %s", path, exc)
        return False


def prune_meta(profile_dir: Path) -> dict:
    """Drop entries for files that no longer exist in the profile."""
    meta = load_meta(profile_dir)
    present = {p.name for p in Path(profile_dir).iterdir()} if Path(profile_dir).is_dir() else set()
    meta["order"] = [name for name in meta["order"] if name in present]
    meta["disabled"] = [name for name in meta["disabled"] if name in present]
    for mod_id in list(meta["catalog"]):
        record = meta["catalog"][mod_id]
        files = [record.get("filename")] + list(record.get("files") or [])
        if not any(f and f in present for f in files):
            meta["catalog"].pop(mod_id, None)
    save_meta(profile_dir, meta)
    return meta


# ---------------------------------------------------------------------------
# Archive handling
# ---------------------------------------------------------------------------
def _safe_basename(member_name: str) -> Optional[str]:
    """Return a safe file name for a zip member, or None if it is unsafe."""
    name = str(member_name).replace("\\", "/")
    if not name or name.endswith("/") or ":" in name:
        return None
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("..", ".") for part in path.parts):
        return None
    return path.name or None


def install_archive(archive: Path, dest: Path, preferred_name: str = "") -> list:
    """Copy every DLL in ``archive`` into ``dest``.

    Zip paths are flattened to their basename and traversal entries are
    rejected.  Returns the list of installed file names.
    """
    archive = Path(archive)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    installed = []

    def unique_name(name: str) -> str:
        candidate = name
        counter = 1
        while (dest / candidate).exists():
            stem, dot, ext = name.rpartition(".")
            candidate = f"{stem}-{counter}{dot}{ext}"
            counter += 1
        return candidate

    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                base = _safe_basename(member.filename)
                if not base or not base.lower().endswith(".dll"):
                    continue
                target = unique_name(base)
                with zf.open(member) as src, open(dest / target, "wb") as out:
                    shutil.copyfileobj(src, out)
                installed.append(target)
    else:
        name = preferred_name or archive.name
        if not name.lower().endswith(".dll"):
            raise CatalogError(f"Unsupported mod file: {archive.name}")
        base = _safe_basename(name)
        if not base:
            raise CatalogError(f"Unsafe mod file name: {name}")
        target = unique_name(base)
        shutil.copy2(str(archive), str(dest / target))
        installed.append(target)

    return installed


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class ModCatalogManager:
    """Fetch the remote catalog and manage catalog-installed mods."""

    def __init__(self, config, network, catalog_url: str = None):
        self.config = config
        self.network = network
        self.url = catalog_url or MOD_CATALOG_URL
        self.cache_file = Path(config.cache_dir) / "mods" / "catalog.json"
        self.download_dir = Path(config.cache_dir) / "mods" / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.catalog: Optional[ModCatalog] = None
        self.error = ""
        self.offline = False
        self._last_fetch = 0.0

    # ---------------------------------------------------------------- fetching
    def fetch(self, force: bool = False) -> Optional[ModCatalog]:
        """Fetch the catalog, falling back to the last cached copy offline."""
        now = time.time()
        if not force and self.catalog is not None and (now - self._last_fetch) < MOD_CATALOG_TTL:
            return self.catalog
        if not force and not self._cache_stale():
            cached = self._load_cache()
            if cached:
                self.catalog = cached
                self._last_fetch = now
                self.offline = False
                self.error = ""
                return cached

        text = None
        try:
            text = self.network.fetch_text(self.url)
        except Exception as exc:  # defensive: a broken transport must not kill startup
            log.warning("Mod catalog fetch failed: %s", exc)

        if text:
            try:
                catalog = ModCatalog.from_text(text)
            except CatalogError as exc:
                self.error = str(exc)
                log.error("Invalid mod catalog: %s", exc)
                catalog = None
            if catalog is not None:
                self._save_cache(text)
                self.catalog = catalog
                self._last_fetch = now
                self.offline = False
                self.error = ""
                return catalog

        cached = self._load_cache()
        self.catalog = cached
        self._last_fetch = now
        self.offline = cached is not None
        if not self.error:
            self.error = ("Using the cached mod catalog (offline)" if cached
                          else "No mod catalog available")
        return cached

    def _cache_stale(self) -> bool:
        try:
            return (time.time() - self.cache_file.stat().st_mtime) > MOD_CATALOG_TTL
        except OSError:
            return True

    def _load_cache(self) -> Optional[ModCatalog]:
        try:
            return ModCatalog.from_text(self.cache_file.read_text(encoding="utf-8"))
        except (OSError, CatalogError):
            return None

    def _save_cache(self, text: str) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.cache_file.parent), suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(tmp, self.cache_file)
        except OSError as exc:
            log.warning("Could not cache mod catalog: %s", exc)

    # ------------------------------------------------------------------ state
    def _profile(self, profile_name: str) -> Path:
        return Path(self.config.profiles_dir) / profile_name

    def installed(self, profile_name: str) -> dict:
        return load_meta(self._profile(profile_name)).get("catalog", {})

    def status(self, profile_name: str, catalog: ModCatalog = None) -> dict:
        """Map mod id -> 'install' | 'installed' | 'update' | 'unknown'."""
        catalog = catalog or self.catalog
        installed = self.installed(profile_name)
        result = {}
        if catalog:
            for entry in catalog.mods:
                record = installed.get(entry.id)
                if not record:
                    result[entry.id] = "install"
                elif version_newer(entry.version, str(record.get("version") or "")):
                    result[entry.id] = "update"
                else:
                    result[entry.id] = "installed"
        for mod_id in installed:
            result.setdefault(mod_id, "unknown")
        return result

    def available_updates(self, profile_name: str, catalog: ModCatalog = None) -> list:
        """Return catalog entries that have a newer version installed nowhere."""
        catalog = catalog or self.catalog
        if not catalog:
            return []
        states = self.status(profile_name, catalog)
        return [entry for entry in catalog.mods if states.get(entry.id) == "update"]

    def record_for_file(self, profile_name: str, filename: str) -> Optional[tuple]:
        """Return (mod_id, record) for a DLL that came from the catalog."""
        for mod_id, record in self.installed(profile_name).items():
            names = [record.get("filename")] + list(record.get("files") or [])
            if filename in names:
                return mod_id, record
        return None

    # --------------------------------------------------------------- install
    def install(
        self,
        entry: ModEntry,
        profile_name: str,
        progress_callback: Callable = None,
        is_running: Callable = None,
    ) -> tuple:
        """Download, verify and install a catalog mod into a profile.

        Returns ``(success, message)``.  ``progress_callback`` receives the
        same ``(downloaded, total, speed)`` triple as ``NetworkManager``.
        """
        if is_running and is_running():
            return False, "Close Among Us before installing mods."
        profile = self._profile(profile_name)
        if not profile.is_dir():
            return False, f"Profile '{profile_name}' was not found."

        preferred = Path(entry.download_url.split("?", 1)[0]).name or f"{entry.id}.bin"
        preferred = re.sub(r"[^A-Za-z0-9._-]", "_", preferred)
        archive = self.download_dir / preferred
        needs_download = not archive.exists() or not self._hash_ok(archive, entry)
        if needs_download:
            # Stale resume segments would poison a re-download of a changed file.
            for part in self.download_dir.iterdir():
                if part.name.startswith(preferred + ".part"):
                    try:
                        part.unlink()
                    except OSError:
                        pass
            if not self.network.download_file(entry.download_url, archive, progress_callback):
                return False, "Download failed."
            if not self._hash_ok(archive, entry):
                try:
                    archive.unlink(missing_ok=True)
                except OSError:
                    pass
                return False, "Download failed checksum verification — the file may be corrupted."

        staging = Path(tempfile.mkdtemp(dir=str(profile.parent), prefix=".modinstall-"))
        try:
            dlls = install_archive(archive, staging, preferred_name=preferred)
            if not dlls:
                return False, "The download contained no .dll files."

            meta = load_meta(profile)
            previous = (meta.get("catalog") or {}).get(entry.id) or {}
            for old in self._record_files(previous):
                target = profile / old
                if target.is_file():
                    try:
                        target.unlink()
                    except OSError as exc:
                        log.warning("Could not remove old mod file %s: %s", target, exc)

            for dll in dlls:
                shutil.move(str(staging / dll), str(profile / dll))

            meta.setdefault("catalog", {})[entry.id] = {
                "version": entry.version,
                "filename": dlls[0],
                "files": dlls,
                "installed_at": time.time(),
            }
            save_meta(profile, meta)
            return True, f"Installed {entry.name} v{entry.version}"
        except (OSError, zipfile.BadZipFile, CatalogError) as exc:
            log.exception("Failed to install mod %s", entry.id)
            return False, f"Install failed: {exc}"
        finally:
            shutil.rmtree(str(staging), ignore_errors=True)

    def uninstall(self, entry_id: str, profile_name: str) -> tuple:
        profile = self._profile(profile_name)
        meta = load_meta(profile)
        record = (meta.get("catalog") or {}).pop(entry_id, None)
        if record is None:
            return False, "Mod is not installed in this profile."
        for name in self._record_files(record):
            try:
                (profile / name).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("Could not remove mod file %s: %s", name, exc)
        meta["order"] = [n for n in meta.get("order", []) if n not in self._record_files(record)]
        meta["disabled"] = [n for n in meta.get("disabled", []) if n not in self._record_files(record)]
        save_meta(profile, meta)
        return True, "Mod removed."

    @staticmethod
    def _record_files(record: dict) -> list:
        files = []
        for name in [record.get("filename")] + list(record.get("files") or []):
            if name and name not in files:
                files.append(name)
        return files

    def _hash_ok(self, archive: Path, entry: ModEntry) -> bool:
        if not entry.sha256:
            return True
        try:
            digest = hashlib.sha256()
            with open(archive, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest() == entry.sha256
        except OSError:
            return False
