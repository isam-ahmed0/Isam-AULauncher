"""ZipExtractor — list contents and extract zip files to the game folder."""
import logging
import zipfile
from pathlib import Path
from typing import List, Optional, Callable

log = logging.getLogger(__name__)


def list_contents(zip_path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return sorted(zf.namelist())
    except (zipfile.BadZipFile, OSError) as e:
        log.error(f"Failed to read zip: {e}")
        return []


def extract_to(
    zip_path: Path,
    target_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> bool:
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.infolist()
            total = len(members)
            for i, m in enumerate(members):
                zf.extract(m, target_dir)
                if progress_callback:
                    progress_callback(i + 1, total)
        return True
    except (zipfile.BadZipFile, OSError) as e:
        log.error(f"Extraction failed: {e}")
        return False
