import os
import stat
import shutil
import zipfile
import logging
from pathlib import Path
from config import GAME_CRITICAL_DIRS


class FileManager:
    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path, progress_callback=None) -> bool:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                members = zf.infolist()
                total = len(members)
                for i, m in enumerate(members):
                    target = (extract_to / m.filename).resolve()
                    if not str(target).startswith(str(extract_to.resolve())):
                        logging.error(f"Zip slip attempt blocked: {m.filename}")
                        return False
                    zf.extract(m, extract_to)
                    if progress_callback:
                        progress_callback(i + 1, total)
            return True
        except (zipfile.BadZipFile, Exception) as e:
            logging.error(f"Extraction failed: {e}")
            return False

    @staticmethod
    def remove_readonly(func, path, exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    @staticmethod
    def safe_delete(path: Path) -> bool:
        try:
            if not path.exists():
                return True
            if path.is_dir():
                shutil.rmtree(path, onerror=FileManager.remove_readonly)
            else:
                path.unlink()
            return True
        except Exception as e:
            logging.error(f"Failed to delete {path}: {e}")
            return False

    @staticmethod
    def format_size(b: int) -> str:
        for u in ['B', 'KB', 'MB', 'GB']:
            if b < 1024:
                return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    @staticmethod
    def verify_game_folder(path: Path) -> dict:
        result = {"valid": False, "exe_found": False, "missing": [], "file_count": 0, "total_size": 0}
        if not path or not path.exists():
            return result

        exe = path / "Among Us.exe"
        if not exe.exists():
            result["missing"].append("Among Us.exe")
            return result

        result["exe_found"] = True

        for d in GAME_CRITICAL_DIRS:
            if not (path / d).exists():
                result["missing"].append(f"{d}/")

        try:
            for f in path.rglob("*"):
                if f.is_file():
                    result["file_count"] += 1
                    result["total_size"] += f.stat().st_size
        except PermissionError:
            pass

        result["valid"] = len(result["missing"]) == 0
        return result
