"""Pack I/O — zip import/export for .aupack asset packs."""
import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QFileDialog, QInputDialog, QMessageBox, QWidget,
)

from .models import PackMetadata
from .profile_manager import AUASProfileManager, ASSET_SUBFOLDERS

log = logging.getLogger(__name__)


def export_pack(
    profile_mgr: AUASProfileManager,
    profile_name: str,
    parent: Optional[QWidget] = None,
) -> Optional[Path]:
    """Export a profile as a .aupack zip file."""
    profile_path = profile_mgr.profile_path(profile_name)
    if not profile_path.exists():
        return None

    save_path, _ = QFileDialog.getSaveFileName(
        parent, "Export Pack", f"{profile_name}.aupack",
        "AU Asset Pack (*.aupack);;All (*)",
    )
    if not save_path:
        return None

    if not save_path.endswith(".aupack"):
        save_path += ".aupack"

    meta = profile_mgr._load_pack_json(profile_path)
    if not meta:
        meta = PackMetadata(name=profile_name, author="Unknown", description="")

    pack_data = {
        "name": meta.name or profile_name,
        "author": meta.author or "Unknown",
        "description": meta.description or "",
        "version": meta.version or "1.0.0",
        "thumbnail": meta.thumbnail,
        "game_version": meta.game_version,
        "created_at": meta.created_at or datetime.now(timezone.utc).isoformat(),
        "categories": meta.categories or profile_mgr.get_profile_categories(profile_name),
    }

    try:
        with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("pack.json", json.dumps(pack_data, indent=4))
            for sub in ASSET_SUBFOLDERS:
                sub_path = profile_path / sub
                if sub_path.exists():
                    for f in sub_path.rglob("*"):
                        if f.is_file():
                            arcname = f"{sub}/{f.relative_to(sub_path)}"
                            zf.write(str(f), arcname)
        return Path(save_path)
    except Exception as e:
        log.error(f"Failed to export pack: {e}")
        return None


def import_pack(
    profile_mgr: AUASProfileManager,
    pack_path: Path,
    parent: Optional[QWidget] = None,
) -> Optional[str]:
    """Import a .aupack file as a new profile. Returns profile name or None."""
    if not pack_path.exists():
        return None

    try:
        with zipfile.ZipFile(str(pack_path), "r") as zf:
            names = zf.namelist()
            if "pack.json" not in names:
                QMessageBox.warning(parent, "Invalid Pack", "Pack does not contain pack.json")
                return None

            pack_data = json.loads(zf.read("pack.json"))
            suggested_name = pack_data.get("name", pack_path.stem)

            name, ok = QInputDialog.getText(
                parent, "Import Pack", "Profile name:", text=suggested_name,
            )
            if not ok or not name:
                return None

            if name in profile_mgr.list_profiles():
                reply = QMessageBox.question(
                    parent, "Profile Exists",
                    f'Profile "{name}" already exists. Overwrite?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return None
                profile_mgr.delete_profile(name)

            profile_mgr.create_profile(name)
            target = profile_mgr.profile_path(name)

            for arcname in names:
                if arcname == "pack.json":
                    meta = PackMetadata(
                        name=pack_data.get("name", ""),
                        author=pack_data.get("author", ""),
                        description=pack_data.get("description", ""),
                        version=pack_data.get("version", "1.0.0"),
                        thumbnail=pack_data.get("thumbnail"),
                        game_version=pack_data.get("game_version"),
                        created_at=pack_data.get("created_at"),
                        categories=pack_data.get("categories", []),
                    )
                    profile_mgr.save_pack_json(name, meta)
                    continue
                if arcname.endswith("/"):
                    continue
                parts = arcname.split("/", 1)
                if len(parts) == 2:
                    sub_dir = parts[0]
                    if sub_dir in ASSET_SUBFOLDERS:
                        out_path = target / arcname
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(arcname) as src, open(out_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            return name
    except Exception as e:
        log.error(f"Failed to import pack: {e}")
        QMessageBox.critical(parent, "Import Error", f"Failed to import pack:\n{e}")
        return None
