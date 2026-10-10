"""AUASManager — manages AU-Assets-Swapper packs in <gameroot>/AUAS_Data.

The AU-Assets-Swapper BepInEx plugin reads replacement assets from
``<gameroot>/AUAS_Data/<PackName>/<Category>/`` and selects the active pack
via ``ActivePack`` in ``<gameroot>/BepInEx/config/com.auassetsswapper.plugin.cfg``
(or ``None`` for the game's own assets). This manager mirrors that layout.
"""
import json
import logging
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import PackMetadata, AssetPack

log = logging.getLogger(__name__)

ASSET_CATEGORIES = [
    "Sprites", "Textures", "Audio", "Fonts",
    "Shaders", "Materials", "Prefabs", "TextAssets",
]

# Extension -> default category for "Add Files".
EXTENSION_CATEGORY = {
    ".png": "Sprites", ".jpg": "Sprites", ".jpeg": "Sprites",
    ".bmp": "Sprites", ".gif": "Sprites", ".webp": "Sprites", ".tga": "Sprites",
    ".wav": "Audio", ".ogg": "Audio", ".mp3": "Audio", ".flac": "Audio",
    ".aiff": "Audio", ".aif": "Audio",
    ".ttf": "Fonts", ".otf": "Fonts",
    ".ab": "Shaders",
    ".tsv": "TextAssets", ".txt": "TextAssets", ".csv": "TextAssets",
}

AUAS_FOLDER = "AUAS_Data"
AUAS_CONFIG_REL = Path("BepInEx") / "config" / "com.auassetsswapper.plugin.cfg"
AUAS_CONFIG_HEADER = (
    "## Settings file was created by plugin AU Assets Swapper\n"
    "## Plugin GUID: com.auassetsswapper.plugin\n"
)

README_TEXT = (
    "AU-Assets-Swapper swap folder\n"
    "=============================\n\n"
    "Place replacement assets in the appropriate subfolder:\n\n"
    "  Sprites/   - PNG/JPG images replace Sprite or Texture2D assets\n"
    "  Textures/  - PNG/JPG images replace raw Texture2D assets\n"
    "  Audio/     - WAV/OGG files replace AudioClip assets\n"
    "  Fonts/     - TTF/OTF files replace Font assets\n"
    "  Shaders/   - AssetBundle files (.ab) replace Shader assets\n"
    "  Materials/ - AssetBundle files (.ab) replace Material assets\n"
    "  Prefabs/   - AssetBundle files (.ab) replace Prefab/GameObject assets\n\n"
    "File names should match the asset name (without extension).\n"
    "Enable DumpAllAssets in the config to see all loaded asset names.\n"
    "Press F5 in-game to hot-reload replacements.\n"
    "Press F6 in-game to switch between packs.\n"
)


class AUASManager:
    def __init__(self, game_path: Optional[Path]):
        self.game_path = Path(game_path) if game_path else None

    # ------------------------------------------------------------------ paths
    @property
    def auas_dir(self) -> Optional[Path]:
        return self.game_path / AUAS_FOLDER if self.game_path else None

    @property
    def config_path(self) -> Optional[Path]:
        return self.game_path / AUAS_CONFIG_REL if self.game_path else None

    def is_installed(self) -> bool:
        """True when an AUAS_Data folder or the plugin config already exists."""
        if not self.game_path:
            return False
        return (self.auas_dir.exists() if self.auas_dir else False) or \
            (self.config_path.exists() if self.config_path else False)

    def _ensure_root(self) -> bool:
        d = self.auas_dir
        if not d:
            return False
        try:
            d.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            log.error(f"Failed to create AUAS_Data: {e}")
            return False

    # ------------------------------------------------------------------ packs
    def list_packs(self) -> List[str]:
        d = self.auas_dir
        if not d or not d.is_dir():
            return []
        names = []
        for entry in d.iterdir():
            if not entry.is_dir():
                continue
            if entry.name in ASSET_CATEGORIES:
                continue
            names.append(entry.name)
        return sorted(names, key=str.lower)

    def pack_path(self, name: str) -> Optional[Path]:
        if not self.auas_dir or not name:
            return None
        return self.auas_dir / name

    @staticmethod
    def is_valid_name(name: str) -> bool:
        if not name or name.strip() != name:
            return False
        if name in ASSET_CATEGORIES:
            return False
        if any(c in name for c in '<>:"/\\|?*'):
            return False
        return True

    def create_pack(self, name: str) -> bool:
        if not self._ensure_root() or not self.is_valid_name(name):
            return False
        target = self.pack_path(name)
        if target is None or target.exists():
            return False
        try:
            target.mkdir(parents=True, exist_ok=True)
            for cat in ASSET_CATEGORIES:
                (target / cat).mkdir(exist_ok=True)
            (target / "README.txt").write_text(README_TEXT, encoding="utf-8")
            self.save_metadata(name, PackMetadata(
                name=name, created_at=datetime.now(timezone.utc).isoformat(),
            ))
            return True
        except OSError as e:
            log.error(f"Failed to create AUAS pack {name}: {e}")
            return False

    def delete_pack(self, name: str) -> bool:
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return False
        was_active = self.get_active_pack() == name
        try:
            shutil.rmtree(str(target))
            if was_active:
                self.set_active_pack(None)
            return True
        except OSError as e:
            log.error(f"Failed to delete AUAS pack {name}: {e}")
            return False

    def duplicate_pack(self, src: str, new: str) -> bool:
        if not self.is_valid_name(new) or new == src:
            return False
        source = self.pack_path(src)
        dest = self.pack_path(new)
        if source is None or dest is None:
            return False
        if not source.is_dir() or dest.exists():
            return False
        try:
            shutil.copytree(str(source), str(dest))
            meta = self.get_metadata(new)
            if meta:
                meta.name = new
                self.save_metadata(new, meta)
            return True
        except OSError as e:
            log.error(f"Failed to duplicate AUAS pack {src} -> {new}: {e}")
            return False

    def rename_pack(self, old: str, new: str) -> bool:
        if not self.is_valid_name(new) or new == old:
            return False
        src = self.pack_path(old)
        dst = self.pack_path(new)
        if src is None or dst is None:
            return False
        if not src.is_dir() or dst.exists():
            return False
        try:
            src.rename(dst)
            meta = self.get_metadata(new)
            if meta and not meta.name:
                meta.name = new
                self.save_metadata(new, meta)
            if self.get_active_pack() == old:
                self.set_active_pack(new)
            return True
        except OSError as e:
            log.error(f"Failed to rename AUAS pack {old} -> {new}: {e}")
            return False

    # ------------------------------------------------------------------ active
    def get_active_pack(self) -> Optional[str]:
        cfg = self.config_path
        if not cfg or not cfg.exists():
            return None
        try:
            text = cfg.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None
        value = self._read_config_value(text, "General", "ActivePack")
        if value is None:
            return None
        value = value.strip()
        if value.lower() in ("", "none", "null"):
            return None
        return value

    def set_active_pack(self, name: Optional[str]) -> bool:
        cfg = self.config_path
        if not cfg:
            return False
        value = name if name else "None"
        try:
            text = cfg.read_text(encoding="utf-8-sig") if cfg.exists() else ""
        except OSError:
            text = ""
        new_text = self._write_config_value(text, "General", "ActivePack", value)
        try:
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(new_text, encoding="utf-8")
            return True
        except OSError as e:
            log.error(f"Failed to write AUAS config: {e}")
            return False

    @staticmethod
    def _read_config_value(text: str, section: str, key: str) -> Optional[str]:
        cur = None
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                cur = s[1:-1].strip()
                continue
            if cur != section or "=" not in s or s.startswith("#"):
                continue
            k, _, v = s.partition("=")
            if k.strip() == key:
                return v
        return None

    @staticmethod
    def _write_config_value(text: str, section: str, key: str, value: str) -> str:
        lines = text.splitlines()
        out: List[str] = []
        cur = None
        section_seen = False
        replaced = False
        for line in lines:
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                cur = s[1:-1].strip()
                if cur == section:
                    section_seen = True
                out.append(line)
                continue
            if cur == section and not replaced and "=" in s and not s.startswith("#"):
                k, _, _v = s.partition("=")
                if k.strip() == key:
                    out.append(f"{key} = {value}")
                    replaced = True
                    continue
            out.append(line)
        if not replaced:
            if not section_seen:
                if not out:
                    out = [l for l in AUAS_CONFIG_HEADER.splitlines()]
                out.append(f"[{section}]")
                out.append("")
            out.append(f"{key} = {value}")
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------------ metadata
    def get_metadata(self, name: str) -> Optional[PackMetadata]:
        target = self.pack_path(name)
        if target is None:
            return None
        pj = target / "pack.json"
        if not pj.exists():
            return None
        try:
            data = json.loads(pj.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
        return PackMetadata(
            name=data.get("name", ""),
            author=data.get("author", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            thumbnail=data.get("thumbnail"),
            game_version=data.get("game_version"),
            created_at=data.get("created_at"),
            categories=data.get("categories", []) or [],
        )

    def save_metadata(self, name: str, meta: PackMetadata) -> bool:
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return False
        data = {
            "name": meta.name,
            "author": meta.author,
            "description": meta.description,
            "version": meta.version,
            "thumbnail": meta.thumbnail,
            "game_version": meta.game_version,
            "created_at": meta.created_at,
            "categories": meta.categories,
        }
        try:
            (target / "pack.json").write_text(
                json.dumps(data, indent=4), encoding="utf-8")
            return True
        except Exception as e:
            log.error(f"Failed to save pack.json for {name}: {e}")
            return False

    # ------------------------------------------------------------------ assets
    @staticmethod
    def guess_category(filename: str) -> Optional[str]:
        return EXTENSION_CATEGORY.get(Path(filename).suffix.lower())

    def list_assets(self, name: str) -> Dict[str, List[Tuple[str, int]]]:
        """Return {category: [(relative filename, size)]} for a pack."""
        result: Dict[str, List[Tuple[str, int]]] = {}
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return result
        for cat in ASSET_CATEGORIES:
            cat_dir = target / cat
            if not cat_dir.is_dir():
                continue
            files: List[Tuple[str, int]] = []
            for f in sorted(cat_dir.rglob("*"), key=lambda p: p.name.lower()):
                if f.is_file():
                    try:
                        files.append((str(f.relative_to(cat_dir)), f.stat().st_size))
                    except OSError:
                        files.append((str(f.relative_to(cat_dir)), 0))
            if files:
                result[cat] = files
        return result

    def pack_stats(self, name: str) -> Tuple[int, int, Dict[str, int]]:
        """Return (total_files, total_bytes, {category: file_count})."""
        total_files = 0
        total_bytes = 0
        per_cat: Dict[str, int] = {}
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return 0, 0, per_cat
        for cat, files in self.list_assets(name).items():
            per_cat[cat] = len(files)
            total_files += len(files)
            total_bytes += sum(sz for _n, sz in files)
        return total_files, total_bytes, per_cat

    def get_pack(self, name: str) -> Optional[AssetPack]:
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return None
        total, size, per_cat = self.pack_stats(name)
        return AssetPack(
            name=name,
            path=target,
            asset_count=total,
            total_size=size,
            categories=per_cat,
            metadata=self.get_metadata(name),
            active=self.get_active_pack() == name,
        )

    def find_conflicts(self, name: str, items: List[Tuple[Path, str]]) -> List[str]:
        """Return the source names whose target already exists in the pack."""
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return []
        conflicts: List[str] = []
        for src, category in items:
            if category not in ASSET_CATEGORIES:
                continue
            if (target / category / Path(src).name).exists():
                conflicts.append(Path(src).name)
        return conflicts

    @staticmethod
    def _unique_dest(dest_dir: Path, filename: str) -> Path:
        dest = dest_dir / filename
        if not dest.exists():
            return dest
        stem, suffix = Path(filename).stem, Path(filename).suffix
        i = 1
        while True:
            candidate = dest_dir / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def copy_assets(self, name: str, items: List[Tuple[Path, str]],
                    overwrite: bool = True) -> Tuple[int, int, List[str]]:
        """Copy (source_file, category) pairs into the pack.

        When ``overwrite`` is False, colliding filenames are saved alongside
        the existing file as ``name (1).ext``.

        Returns (copied_count, skipped_count, error_messages).
        """
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return 0, 0, ["Pack does not exist"]
        copied = 0
        skipped = 0
        errors: List[str] = []
        for src, category in items:
            src = Path(src)
            if category not in ASSET_CATEGORIES:
                errors.append(f"{src.name}: unknown category '{category}'")
                continue
            dest_dir = target / category
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                if not src.exists():
                    errors.append(f"{src.name}: file not found")
                    continue
                dest = dest_dir / src.name
                if dest.exists() and not overwrite:
                    dest = self._unique_dest(dest_dir, src.name)
                shutil.copy2(str(src), str(dest))
                copied += 1
            except OSError as e:
                errors.append(f"{src.name}: {e}")
        return copied, skipped, errors

    def remove_asset(self, name: str, category: str, relpath: str) -> bool:
        target = self.pack_path(name)
        if target is None or category not in ASSET_CATEGORIES:
            return False
        cat_dir = (target / category).resolve()
        f = (cat_dir / relpath).resolve()
        if not str(f).startswith(str(cat_dir)) or not f.is_file():
            return False
        try:
            f.unlink()
            self._prune_empty_dirs(cat_dir)
            return True
        except OSError as e:
            log.error(f"Failed to remove asset {f}: {e}")
            return False

    @staticmethod
    def _prune_empty_dirs(root: Path) -> None:
        for d in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if d.is_dir():
                try:
                    next(d.iterdir())
                except StopIteration:
                    try:
                        d.rmdir()
                    except OSError:
                        pass
                except OSError:
                    pass

    # ------------------------------------------------------------------ pack I/O
    def export_pack(self, name: str, dest: Path) -> bool:
        target = self.pack_path(name)
        if target is None or not target.is_dir():
            return False
        if dest.suffix.lower() != ".zip":
            dest = dest.with_name(dest.stem + ".zip")
        meta = self.get_metadata(name) or PackMetadata(name=name)
        if not meta.name:
            meta.name = name
        if not meta.created_at:
            meta.created_at = datetime.now(timezone.utc).isoformat()
        data = {
            "name": meta.name,
            "author": meta.author or "Unknown",
            "description": meta.description,
            "version": meta.version or "1.0.0",
            "thumbnail": meta.thumbnail,
            "game_version": meta.game_version,
            "created_at": meta.created_at,
            "categories": meta.categories,
        }
        try:
            with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("pack.json", json.dumps(data, indent=4))
                for cat in ASSET_CATEGORIES:
                    cat_dir = target / cat
                    if not cat_dir.is_dir():
                        continue
                    for f in cat_dir.rglob("*"):
                        if f.is_file():
                            arcname = f"{cat}/{f.relative_to(cat_dir).as_posix()}"
                            zf.write(str(f), arcname)
            return True
        except Exception as e:
            log.error(f"Failed to export pack {name}: {e}")
            return False

    def import_pack(self, src: Path, name: str) -> Optional[str]:
        if not src.exists():
            return None
        if not self._ensure_root() or not self.is_valid_name(name):
            return None
        target = self.pack_path(name)
        if target is None:
            return None
        try:
            with zipfile.ZipFile(str(src), "r") as zf:
                names = zf.namelist()
                if "pack.json" not in names:
                    return None
                if target.exists():
                    shutil.rmtree(str(target))
                target.mkdir(parents=True)
                for cat in ASSET_CATEGORIES:
                    (target / cat).mkdir(exist_ok=True)
                resolved_target = target.resolve()
                for arcname in names:
                    if arcname == "pack.json" or arcname.endswith("/"):
                        continue
                    parts = arcname.split("/", 1)
                    if len(parts) != 2 or parts[0] not in ASSET_CATEGORIES:
                        continue
                    out_path = (target / arcname).resolve()
                    if not str(out_path).startswith(str(resolved_target)):
                        log.warning(f"Zip slip attempt blocked: {arcname}")
                        continue
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(arcname) as sf, open(out_path, "wb") as df:
                        shutil.copyfileobj(sf, df)
                pack_data = json.loads(zf.read("pack.json"))
                meta = PackMetadata(
                    name=pack_data.get("name", name) or name,
                    author=pack_data.get("author", ""),
                    description=pack_data.get("description", ""),
                    version=pack_data.get("version", "1.0.0"),
                    thumbnail=pack_data.get("thumbnail"),
                    game_version=pack_data.get("game_version"),
                    created_at=pack_data.get("created_at"),
                    categories=pack_data.get("categories", []) or [],
                )
                self.save_metadata(name, meta)
            return name
        except Exception as e:
            log.error(f"Failed to import pack {src}: {e}")
            return None

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def read_zip_meta(src: Path) -> Optional[PackMetadata]:
        try:
            with zipfile.ZipFile(str(src), "r") as zf:
                data = json.loads(zf.read("pack.json"))
            return PackMetadata(
                name=data.get("name", ""),
                author=data.get("author", ""),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
            )
        except Exception:
            return None
