"""ProfileManager — isolated mod profiles using directory junctions."""
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List

from platform_utils import IS_WINDOWS
from mod_catalog import load_meta, save_meta

log = logging.getLogger(__name__)

DISABLED_SUFFIX = ".disabled"


class ProfileManager:
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> List[str]:
        """Return sorted list of profile folder names."""
        try:
            return sorted(
                [d.name for d in self.profiles_dir.iterdir() if d.is_dir()],
                key=str.lower,
            )
        except OSError:
            return []

    def profile_path(self, name: str) -> Path:
        return self.profiles_dir / name

    def create_profile(self, name: str) -> bool:
        """Create a new empty profile folder."""
        if not name or name in self.list_profiles():
            return False
        try:
            self.profile_path(name).mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            log.error(f"Failed to create profile {name}: {e}")
            return False

    def delete_profile(self, name: str, active_profile: str) -> bool:
        """Delete a profile folder. Cannot delete active profile."""
        if name == active_profile:
            return False
        if name not in self.list_profiles():
            return False
        try:
            shutil.rmtree(str(self.profile_path(name)))
            return True
        except OSError as e:
            log.error(f"Failed to delete profile {name}: {e}")
            return False

    def rename_profile(self, old: str, new: str) -> bool:
        """Rename a profile folder."""
        if not new or new == old:
            return False
        if new in self.list_profiles():
            return False
        if old not in self.list_profiles():
            return False
        try:
            self.profile_path(old).rename(self.profile_path(new))
            return True
        except OSError as e:
            log.error(f"Failed to rename profile {old} -> {new}: {e}")
            return False

    def is_junction(self, path: Path) -> bool:
        """True for a Windows junction or a POSIX symlink."""
        try:
            return path.is_symlink() or path.is_junction()
        except (OSError, AttributeError):
            return False

    def _remove_link(self, path: Path) -> None:
        """Remove a junction/symlink without touching the target's contents."""
        if path.is_symlink():
            path.unlink()
        else:
            path.rmdir()

    def get_junction_target(self, junction_path: Path) -> Optional[Path]:
        """Read where a junction (or symlink) points."""
        try:
            if junction_path.is_symlink():
                return junction_path.resolve()
        except OSError:
            pass
        try:
            if self.is_junction(junction_path):
                # On Windows, readlink works for junctions
                return Path(subprocess.check_output(
                    ["cmd", "/c", "dir", "/AL", str(junction_path.parent)],
                    text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ).split()[-1])
        except Exception:
            pass
        return None

    def get_active_plugins_dir(self, game_path: Path) -> Optional[Path]:
        """Return the physical plugins dir for the currently active profile.
        If junction is broken or not set, returns None."""
        plugins = game_path / "BepInEx" / "plugins"
        if not plugins.exists() and not self.is_junction(plugins):
            return None
        if self.is_junction(plugins):
            # Junction exists — find which profile it points to
            for name in self.list_profiles():
                if self.profile_path(name).resolve() == plugins.resolve():
                    return self.profile_path(name)
        return plugins

    def switch_to(self, profile_name: str, game_path: Path) -> bool:
        """Create junction: game_path/BepInEx/plugins -> profiles_dir/name."""
        plugins = game_path / "BepInEx" / "plugins"
        target = self.profile_path(profile_name)
        if not target.exists():
            log.error(f"Profile folder {target} does not exist")
            return False

        # Remove existing junction or empty folder
        try:
            if self.is_junction(plugins):
                self._remove_link(plugins)  # removes junction/symlink only
            elif plugins.exists():
                # plugins is a real folder — move its contents into the target profile
                for f in plugins.iterdir():
                    if f.is_file():
                        try:
                            shutil.move(str(f), str(target / f.name))
                        except OSError as e:
                            log.error(f"Failed to migrate mod {f}: {e}")
                plugins.rmdir()
            else:
                # Folder doesn't exist, ensure parent exists
                plugins.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Failed to remove old plugins: {e}")
            return False

        # Create junction (Windows) or symlink (POSIX)
        try:
            if IS_WINDOWS:
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(plugins), str(target)],
                    capture_output=True, text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode != 0:
                    log.error(f"mklink failed: {result.stderr}")
                    return False
            else:
                os.symlink(str(target.resolve()), str(plugins), target_is_directory=True)
            return True
        except OSError as e:
            log.error(f"Failed to create junction: {e}")
            return False

    def remove_junction(self, game_path: Path) -> bool:
        """Remove the junction (for Vanilla / no mods)."""
        plugins = game_path / "BepInEx" / "plugins"
        try:
            if self.is_junction(plugins):
                self._remove_link(plugins)
                return True
        except OSError as e:
            log.error(f"Failed to remove junction: {e}")
        return False

    def import_mods(self, profile_name: str, dll_paths: List[Path]) -> int:
        """Copy .dll files into a profile folder. Returns count copied."""
        target = self.profile_path(profile_name)
        if not target.exists():
            return 0
        copied = 0
        for src in dll_paths:
            try:
                shutil.copy2(str(src), str(target / src.name))
                copied += 1
            except OSError as e:
                log.error(f"Failed to copy mod {src}: {e}")
        return copied

    def move_mods(self, from_profile: str, to_profile: str, dll_names: list) -> int:
        """Move .dll files from one profile to another. Returns count moved."""
        src_dir = self.profile_path(from_profile)
        dst_dir = self.profile_path(to_profile)
        if not src_dir.exists() or not dst_dir.exists():
            return 0
        moved = 0
        for name in dll_names:
            src = src_dir / name
            dst = dst_dir / name
            if not src.exists():
                continue
            try:
                shutil.move(str(src), str(dst))
                moved += 1
            except OSError as e:
                log.error(f"Failed to move mod {src} -> {dst}: {e}")
        return moved

    # ------------------------------------------------------- mod-file handling
    def meta_path(self, name: str) -> Path:
        return self.profile_path(name) / "mods.json"

    def list_mod_files(self, name: str, include_disabled: bool = True) -> List[Path]:
        """List profile DLLs in the user's preferred order.

        BepInEx does not guarantee a strict load order from file names, so the
        order here is an organizational preference shown in the UI, not a
        promise about the game's plugin loading sequence.
        """
        profile = self.profile_path(name)
        if not profile.is_dir():
            return []
        files = []
        for path in profile.iterdir():
            if not path.is_file():
                continue
            lower = path.name.lower()
            if lower.endswith(".dll"):
                files.append(path)
            elif include_disabled and lower.endswith(".dll" + DISABLED_SUFFIX):
                files.append(path)

        meta = load_meta(profile)
        names = {p.name for p in files}
        order: List[str] = []
        for stored in meta.get("order", []):
            if stored in names and stored not in order:
                order.append(stored)
        for name in sorted((p.name for p in files), key=str.lower):
            if name not in order:
                order.append(name)

        by_name = {p.name: p for p in files}
        return [by_name[n] for n in order if n in by_name]

    def is_enabled(self, name: str, filename: str) -> bool:
        return not filename.lower().endswith(".dll" + DISABLED_SUFFIX)

    def set_enabled(self, name: str, filename: str, enabled: bool) -> bool:
        """Toggle a DLL between ``X.dll`` and ``X.dll.disabled``."""
        profile = self.profile_path(name)
        if not profile.is_dir():
            return False
        if enabled:
            if not filename.lower().endswith(".dll" + DISABLED_SUFFIX):
                return False
            source = profile / filename
            target = profile / filename[: -len(DISABLED_SUFFIX)]
        else:
            if not filename.lower().endswith(".dll"):
                return False
            source = profile / filename
            target = profile / (filename + DISABLED_SUFFIX)
        if not source.is_file() or target.exists():
            return False
        try:
            source.rename(target)
        except OSError as e:
            log.error("Failed to toggle mod %s: %s", filename, e)
            return False

        meta = load_meta(profile)
        disabled = [n for n in meta.get("disabled", []) if n not in (filename, target.name)]
        if not enabled:
            disabled.append(target.name)
        meta["disabled"] = disabled
        meta["order"] = [target.name if n == filename else n for n in meta.get("order", [])]
        for record in meta.get("catalog", {}).values():
            for key in ("filename",):
                if record.get(key) == filename:
                    record[key] = target.name
            record["files"] = [target.name if f == filename else f
                               for f in (record.get("files") or [])]
        save_meta(profile, meta)
        return True

    def reorder_mod(self, name: str, filename: str, delta: int) -> bool:
        """Move a mod up (``delta=-1``) or down (``delta=1``) in the list."""
        profile = self.profile_path(name)
        if not profile.is_dir():
            return False
        names = [p.name for p in self.list_mod_files(name)]
        if filename not in names:
            return False
        meta = load_meta(profile)
        order = [n for n in meta.get("order", []) if n in names]
        order.extend(n for n in names if n not in order)
        index = order.index(filename)
        target = index + delta
        if target < 0 or target >= len(order):
            return False
        order[index], order[target] = order[target], order[index]
        meta["order"] = order
        return save_meta(profile, meta)

    def ensure_first_profiles(self, game_path: Path) -> str:
        """On first run: if BepInEx/plugins has real files (not junction),
        move them into 'Default' profile, create junction, and create 'Vanilla'.
        Returns the name of the active profile."""
        plugins = game_path / "BepInEx" / "plugins"
        profiles = self.list_profiles()

        # Already has profiles — nothing to migrate
        if profiles:
            return ""

        # Create Vanilla (empty)
        self.create_profile("Vanilla")

        # Create Default from existing plugins if present
        if plugins.exists() and not self.is_junction(plugins):
            self.create_profile("Default")
            # Move existing files to Default profile
            for f in plugins.iterdir():
                if f.is_file():
                    try:
                        shutil.move(str(f), str(self.profile_path("Default") / f.name))
                    except OSError:
                        pass
            # Create junction
            self.switch_to("Default", game_path)
            return "Default"
        else:
            # No existing plugins — create Default empty too
            self.create_profile("Default")
            self.switch_to("Default", game_path)
            return "Default"
