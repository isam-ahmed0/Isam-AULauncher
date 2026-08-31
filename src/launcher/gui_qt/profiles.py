"""ProfileManager — isolated mod profiles using directory junctions."""
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List

log = logging.getLogger(__name__)


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
        """Check if path is a directory junction."""
        try:
            return path.is_junction()
        except OSError:
            return False

    def get_junction_target(self, junction_path: Path) -> Optional[Path]:
        """Read where a junction points to."""
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
                plugins.rmdir()  # removes junction only
            elif plugins.exists():
                # plugins is a real folder — migrate its contents first
                return False
            else:
                # Folder doesn't exist, ensure parent exists
                plugins.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Failed to remove old plugins: {e}")
            return False

        # Create junction
        try:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(plugins), str(target)],
                capture_output=True, text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                log.error(f"mklink failed: {result.stderr}")
                return False
            return True
        except OSError as e:
            log.error(f"Failed to create junction: {e}")
            return False

    def remove_junction(self, game_path: Path) -> bool:
        """Remove the junction (for Vanilla / no mods)."""
        plugins = game_path / "BepInEx" / "plugins"
        try:
            if self.is_junction(plugins):
                plugins.rmdir()
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
            # Move existing .dll files to Default profile
            for dll in plugins.glob("*.dll"):
                try:
                    shutil.move(str(dll), str(self.profile_path("Default") / dll.name))
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
