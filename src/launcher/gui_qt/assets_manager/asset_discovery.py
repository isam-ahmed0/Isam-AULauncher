"""Asset Discovery — DLL scanning (dnfile) + BepInEx log parsing."""
import logging
import re
from pathlib import Path
from typing import List, Optional

from .models import AssetEntry

log = logging.getLogger(__name__)

ASSET_TYPES = {"Sprite", "Texture2D", "AudioClip", "Font", "Shader", "Material", "GameObject"}

INTEROP_DLLS = [
    "UnityEngine.CoreModule.dll",
    "UnityEngine.AssetBundleModule.dll",
    "UnityEngine.AudioModule.dll",
    "UnityEngine.TextRenderingModule.dll",
    "UnityEngine.Physics2DModule.dll",
    "UnityEngine.UI.dll",
    "Il2Cppmscorlib.dll",
]

LOG_RE = re.compile(
    r"^\[(?P<level>\w+)\s*:\s*(?P<source>.+?)\]\s+(?P<message>.+)$"
)
AUAS_DUMP_RE = re.compile(
    r"\[AUAS-DUMP\]\s+(?:\[(?P<type>\w+)\]\s+)?(?P<path>.+)"
)
AUAS_PICK_RE = re.compile(r"\[AUAS-PICK\]\s+(.+)")
AUAS_LOADED_RE = re.compile(
    r"\[AUAS\]\s+Loaded\s+(?P<type>\w+)\s+replacement"
    r"(?:\s+from\s+bundle)?:\s+(?P<name>.+?)"
    r"(?:\s+\((?P<w>\d+)x(?P<h>\d+)\))?$"
)
AUAS_SCANNED_RE = re.compile(
    r"\[AUAS\]\s+Scanned:\s+(\d+)\s+sprites?,\s+(\d+)\s+textures?,\s+"
    r"(\d+)\s+audio,?\s+(\d+)\s+fonts?,\s+(\d+)\s+shaders?,\s+"
    r"(\d+)\s+materials?,\s+(\d+)\s+prefabs?\s+-\s+total\s+(\d+)\s+replacements?\."
)


def scan_dlls(game_path: Path) -> List[AssetEntry]:
    """Scan BepInEx/interop/ DLLs for asset-related types using dnfile."""
    entries: List[AssetEntry] = []
    interop_dir = game_path / "BepInEx" / "interop"
    if not interop_dir.exists():
        return entries

    try:
        import dnfile
    except ImportError:
        log.warning("dnfile not installed — DLL scanning disabled")
        return entries

    for dll_name in INTEROP_DLLS:
        dll_path = interop_dir / dll_name
        if not dll_path.exists():
            continue
        try:
            pe = dnfile.dnPE(str(dll_path), fast_load=True)
            if not pe.net or not pe.net.mdtables:
                continue
            typedefs = pe.net.mdtables.TypeDef
            if not typedefs:
                continue
            for row in typedefs:
                type_name = str(row.TypeName) if row.TypeName else ""
                namespace = str(row.TypeNamespace) if row.TypeNamespace else ""
                base = str(row.Extends) if row.Extends else ""
                full_type = f"{namespace}.{type_name}" if namespace else type_name
                if row.FieldList:
                    for field in row.FieldList:
                        field_name = str(field.Name) if field.Name else ""
                        field_type = str(field.Signature.FieldType) if field.Signature and field.Signature.FieldType else ""
                        if any(at in field_type for at in ASSET_TYPES):
                            entries.append(AssetEntry(
                                name=field_name,
                                asset_type=_clean_type(field_type),
                                source="dll",
                                dll_source=dll_name,
                            ))
                        elif "SerializeField" in str(getattr(field, "CustomAttributes", "")):
                            entries.append(AssetEntry(
                                name=field_name,
                                asset_type=_clean_type(field_type),
                                source="dll",
                                dll_source=dll_name,
                            ))
        except Exception as e:
            log.warning(f"Failed to scan {dll_name}: {e}")
    return entries


def _clean_type(raw: str) -> str:
    for t in ASSET_TYPES:
        if t in raw:
            return t
    bracket = raw.rfind("[")
    if bracket != -1:
        return raw[bracket + 1:raw.rfind("]")]
    dot = raw.rfind(".")
    if dot != -1:
        return raw[dot + 1:]
    return raw


def parse_logs(game_path: Path, known_dll_assets: Optional[List[AssetEntry]] = None) -> List[AssetEntry]:
    """Parse BepInEx logs for AUAS asset references."""
    entries: List[AssetEntry] = []
    bepinex = game_path / "BepInEx"
    if not bepinex.exists():
        return entries

    log_files = sorted(bepinex.glob("LogOutput*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return entries

    dll_names = {e.name for e in (known_dll_assets or [])}

    for log_file in log_files[:3]:
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            m = AUAS_LOADED_RE.search(line)
            if m:
                name = m.group("name")
                asset_type = m.group("type")
                w = int(m.group("w")) if m.group("w") else None
                h = int(m.group("h")) if m.group("h") else None
                if name not in dll_names:
                    entries.append(AssetEntry(
                        name=name, asset_type=asset_type, source="log",
                        width=w, height=h,
                    ))
                continue
            m = AUAS_DUMP_RE.match(line)
            if m:
                path_str = m.group("path")
                asset_type = m.group("type") or _guess_type_from_path(path_str)
                name = Path(path_str).stem
                if name not in dll_names:
                    entries.append(AssetEntry(
                        name=name, asset_type=asset_type, source="log",
                    ))
                continue
            m = AUAS_PICK_RE.search(line)
            if m:
                name = m.group(1).strip()
                if name not in dll_names:
                    entries.append(AssetEntry(
                        name=name, asset_type="Unknown", source="log",
                    ))
    return entries


def _guess_type_from_path(path_str: str) -> str:
    lower = path_str.lower()
    if any(lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".bmp", ".tga")):
        return "Texture2D"
    if any(lower.endswith(ext) for ext in (".ogg", ".wav", ".mp3")):
        return "AudioClip"
    if lower.endswith(".ttf") or lower.endswith(".otf"):
        return "Font"
    if lower.endswith(".shader"):
        return "Shader"
    if lower.endswith(".mat"):
        return "Material"
    if lower.endswith(".prefab"):
        return "GameObject"
    return "Unknown"


def discover_all(game_path: Path) -> List[AssetEntry]:
    """Run full discovery: DLL scanning + log parsing, merge into unified list."""
    dll_assets = scan_dlls(game_path)
    log_assets = parse_logs(game_path, dll_assets)

    seen = {}
    for entry in dll_assets + log_assets:
        key = (entry.name, entry.asset_type)
        if key not in seen:
            seen[key] = entry
        else:
            existing = seen[key]
            if entry.source == "log" and not existing.has_replacement:
                existing.has_replacement = True
                if entry.width:
                    existing.width = entry.width
                if entry.height:
                    existing.height = entry.height

    return list(seen.values())
