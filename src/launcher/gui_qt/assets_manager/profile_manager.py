"""AUAS Profile Manager — junction-based AUAS_Data profile switching."""
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List

from .models import PackProfile, PackMetadata

log = logging.getLogger(__name__)

ASSET_SUBFOLDERS = ["Sprites", "Textures", "Audio", "Fonts", "Shaders", "Materials", "Prefabs"]


class AUASProfileManager:
    def __init__(self, profiles_base: Path):
        self.profiles_base = profiles_base
        self.profiles_base.mkdir(parents=True, exist_ok=True)

    def _profile_dir(self, name: str) -> Path:
        return self.profiles_base / name

    def list_profiles(self) -> List[str]:
        try:
            return sorted(
                [d.name for d in self.profiles_base.iterdir() if d.is_dir()],
                key=str.lower,
            )
        except OSError:
            return []

    def profile_path(self, name: str) -> Path:
        return self._profile_dir(name)

    def get_profile_count(self, name: str) -> int:
        count = 0
        p = self._profile_dir(name)
        if not p.exists():
            return 0
        for sub in ASSET_SUBFOLDERS:
            d = p / sub
            if d.exists():
                count += sum(1 for _ in d.iterdir())
        return count

    def get_profile_categories(self, name: str) -> List[str]:
        cats = []
        p = self._profile_dir(name)
        if not p.exists():
            return cats
        for sub in ASSET_SUBFOLDERS:
            d = p / sub
            if d.exists() and any(d.iterdir()):
                cats.append(sub)
        return cats

    def list_pack_profiles(self) -> List[PackProfile]:
        profiles = []
        for name in self.list_profiles():
            p = self._profile_dir(name)
            meta = self._load_pack_json(p)
            profiles.append(PackProfile(
                name=name,
                path=p,
                asset_count=self.get_profile_count(name),
                categories=self.get_profile_categories(name),
                metadata=meta,
            ))
        return profiles

    def create_profile(self, name: str) -> bool:
        if not name or name in self.list_profiles():
            return False
        try:
            p = self._profile_dir(name)
            p.mkdir(parents=True, exist_ok=True)
            for sub in ASSET_SUBFOLDERS:
                (p / sub).mkdir(exist_ok=True)
            return True
        except OSError as e:
            log.error(f"Failed to create AUAS profile {name}: {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        if name not in self.list_profiles():
            return False
        try:
            shutil.rmtree(str(self._profile_dir(name)))
            return True
        except OSError as e:
            log.error(f"Failed to delete AUAS profile {name}: {e}")
            return False

    def rename_profile(self, old: str, new: str) -> bool:
        if not new or new == old:
            return False
        if new in self.list_profiles() or old not in self.list_profiles():
            return False
        try:
            self._profile_dir(old).rename(self._profile_dir(new))
            return True
        except OSError as e:
            log.error(f"Failed to rename AUAS profile {old} -> {new}: {e}")
            return False

    def activate_profile(self, name: str, game_path: Path) -> bool:
        auas_data = game_path / "AUAS_Data"
        target = self._profile_dir(name)
        if not target.exists():
            log.error(f"AUAS profile folder {target} does not exist")
            return False
        try:
            if self.is_junction(auas_data):
                auas_data.rmdir()
            elif auas_data.exists():
                for item in auas_data.iterdir():
                    dest = target / item.name
                    if not dest.exists():
                        shutil.move(str(item), str(dest))
                auas_data.rmdir()
            else:
                auas_data.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Failed to remove old AUAS_Data: {e}")
            return False
        try:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(auas_data), str(target)],
                capture_output=True, text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                log.error(f"mklink failed: {result.stderr}")
                return False
            return True
        except OSError as e:
            log.error(f"Failed to create AUAS junction: {e}")
            return False

    def get_active_profile(self, game_path: Path) -> Optional[str]:
        auas_data = game_path / "AUAS_Data"
        if not auas_data.exists() and not self.is_junction(auas_data):
            return None
        if self.is_junction(auas_data):
            target = self.get_junction_target(auas_data)
            if target:
                for name in self.list_profiles():
                    if self._profile_dir(name).resolve() == target.resolve():
                        return name
        return None

    def remove_junction(self, game_path: Path) -> bool:
        auas_data = game_path / "AUAS_Data"
        try:
            if self.is_junction(auas_data):
                auas_data.rmdir()
                return True
        except OSError as e:
            log.error(f"Failed to remove AUAS junction: {e}")
        return False

    def is_junction(self, path: Path) -> bool:
        try:
            return path.is_junction()
        except OSError:
            return False

    def get_junction_target(self, junction_path: Path) -> Optional[Path]:
        try:
            if self.is_junction(junction_path):
                return Path(os.readlink(str(junction_path)))
        except Exception:
            pass
        try:
            if self.is_junction(junction_path):
                return Path(subprocess.check_output(
                    ["cmd", "/c", "dir", "/AL", str(junction_path.parent)],
                    text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ).split()[-1])
        except Exception:
            pass
        return None

    def _load_pack_json(self, profile_path: Path) -> Optional[PackMetadata]:
        pj = profile_path / "pack.json"
        if not pj.exists():
            return None
        try:
            import json
            data = json.loads(pj.read_text(encoding="utf-8-sig"))
            return PackMetadata(
                name=data.get("name", ""),
                author=data.get("author", ""),
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                thumbnail=data.get("thumbnail"),
                game_version=data.get("game_version"),
                created_at=data.get("created_at"),
                categories=data.get("categories", []),
            )
        except Exception:
            return None

    def save_pack_json(self, name: str, meta: PackMetadata) -> bool:
        import json
        pj = self._profile_dir(name) / "pack.json"
        try:
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
            pj.write_text(json.dumps(data, indent=4), encoding="utf-8")
            return True
        except Exception as e:
            log.error(f"Failed to save pack.json for {name}: {e}")
            return False

    def ensure_subfolders(self, path: Path):
        for sub in ASSET_SUBFOLDERS:
            (path / sub).mkdir(parents=True, exist_ok=True)
