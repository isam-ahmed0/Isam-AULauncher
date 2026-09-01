"""
Mod Compatibility Inspector — scans BepInEx plugin DLLs for metadata
and detects duplicates, missing dependencies, and incompatibilities.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModInfo:
    filename: str
    guid: str = ""
    name: str = ""
    version: str = ""
    dependencies: list = field(default_factory=list)
    incompatibilities: list = field(default_factory=list)


@dataclass
class Issue:
    kind: str          # "duplicate" | "missing_dep" | "conflict"
    severity: str      # "warning"
    description: str

    def __str__(self):
        return f"[{self.kind.upper()}] {self.description}"


def _utf16le(s: str) -> bytes:
    """Convert ASCII pattern to UTF-16LE bytes for .NET assembly matching."""
    return s.encode("utf-16-le")


# ASCII patterns — match if values happen to be ASCII in the binary
_RE_PLUGIN_ASCII = re.compile(
    rb'BepInPlugin\s*\(\s*"([^"]+)"\s*,\s*"([^"]*?)"\s*,\s*"([^"]*?)"\s*\)'
)
_RE_DEP_ASCII = re.compile(
    rb'BepInDependency\s*\(\s*"([^"]+)"'
)
_RE_INC_ASCII = re.compile(
    rb'BepInIncompatibility\s*\(\s*"([^"]+)"\s*\)'
)

# UTF-16LE patterns — match .NET user strings heap encoding
_RE_PLUGIN_UTF16 = re.compile(
    _utf16le(r'BepInPlugin\s*\(\s*"') + rb'([^\x00"]{1,200}?)' + _utf16le(r'"\s*,\s*"') + rb'([^\x00"]{0,200}?)' + _utf16le(r'"\s*,\s*"') + rb'([^\x00"]{0,100}?)' + _utf16le(r'"\s*\)')
)
_RE_DEP_UTF16 = re.compile(
    _utf16le(r'BepInDependency\s*\(\s*"') + rb'([^\x00"]{1,200}?)' + _utf16le(r'"')
)
_RE_INC_UTF16 = re.compile(
    _utf16le(r'BepInIncompatibility\s*\(\s*"') + rb'([^\x00"]{1,200}?)' + _utf16le(r'"\s*\)')
)


def _decode(raw: bytes) -> str:
    """Decode bytes to string, handling both raw ASCII and stripped UTF-16LE."""
    try:
        return raw.decode("utf-16-le").strip()
    except Exception:
        return raw.decode("utf-8", errors="replace").strip()


def _read_dll_metadata(dll_path: Path) -> ModInfo:
    """Read BepInEx attributes from a single DLL via binary regex."""
    mod = ModInfo(filename=dll_path.name)
    try:
        data = dll_path.read_bytes()
    except Exception as e:
        logging.warning(f"Could not read {dll_path.name}: {e}")
        return mod

    # --- Plugin GUID / name / version ---
    # Try ASCII first (faster, works for some DLLs)
    m = _RE_PLUGIN_ASCII.search(data)
    if m:
        mod.guid = m.group(1).decode("utf-8", errors="replace")
        mod.name = m.group(2).decode("utf-8", errors="replace")
        mod.version = m.group(3).decode("utf-8", errors="replace")
        logging.debug(f"[ASCII] {dll_path.name}: guid={mod.guid} name={mod.name} ver={mod.version}")
    else:
        # Try UTF-16LE (.NET user strings heap)
        m16 = _RE_PLUGIN_UTF16.search(data)
        if m16:
            mod.guid = _decode(m16.group(1))
            mod.name = _decode(m16.group(2))
            mod.version = _decode(m16.group(3))
            logging.debug(f"[UTF16] {dll_path.name}: guid={mod.guid} name={mod.name} ver={mod.version}")
        else:
            logging.debug(f"[NONE]  {dll_path.name}: no BepInPlugin attribute found")

    # --- Dependencies ---
    seen_deps = set()
    for m in _RE_DEP_ASCII.finditer(data):
        dep = m.group(1).decode("utf-8", errors="replace")
        if dep and dep not in seen_deps:
            mod.dependencies.append(dep)
            seen_deps.add(dep)
    if not mod.dependencies:
        for m in _RE_DEP_UTF16.finditer(data):
            dep = _decode(m.group(1))
            if dep and dep not in seen_deps:
                mod.dependencies.append(dep)
                seen_deps.add(dep)

    # --- Incompatibilities ---
    seen_inc = set()
    for m in _RE_INC_ASCII.finditer(data):
        inc = m.group(1).decode("utf-8", errors="replace")
        if inc and inc not in seen_inc:
            mod.incompatibilities.append(inc)
            seen_inc.add(inc)
    if not mod.incompatibilities:
        for m in _RE_INC_UTF16.finditer(data):
            inc = _decode(m.group(1))
            if inc and inc not in seen_inc:
                mod.incompatibilities.append(inc)
                seen_inc.add(inc)

    return mod


def inspect_profile_dlls(profile_path: Path):
    """Scan all DLLs in a profile directory and return (mods, issues)."""
    mods = []
    issues = []

    if not profile_path.is_dir():
        return mods, issues

    dlls = sorted(profile_path.glob("*.dll"))
    for dll in dlls:
        mod = _read_dll_metadata(dll)
        if mod.guid:
            mods.append(mod)

    # 1. Duplicate GUIDs
    guid_map = {}
    for mod in mods:
        guid_map.setdefault(mod.guid, []).append(mod)

    for guid, owners in guid_map.items():
        if len(owners) > 1:
            names = " and ".join(f'`{o.filename}`' for o in owners)
            issues.append(Issue(
                kind="duplicate",
                severity="warning",
                description=f'{names} share GUID `{guid}`.',
            ))

    # 2. Missing hard dependencies
    provided_guids = {mod.guid for mod in mods}
    for mod in mods:
        for dep in mod.dependencies:
            if dep not in provided_guids:
                issues.append(Issue(
                    kind="missing_dep",
                    severity="warning",
                    description=(
                        f'`{mod.filename}` requires `{dep}`, '
                        f'which is missing from this profile.'
                    ),
                ))

    # 3. Declared incompatibilities
    guid_to_file = {mod.guid: mod.filename for mod in mods}
    seen_conflicts = set()
    for mod in mods:
        for inc in mod.incompatibilities:
            if inc in guid_to_file:
                other = guid_to_file[inc]
                pair = tuple(sorted([mod.filename, other]))
                if pair not in seen_conflicts:
                    seen_conflicts.add(pair)
                    issues.append(Issue(
                        kind="conflict",
                        severity="warning",
                        description=(
                            f'`{mod.filename}` is marked incompatible '
                            f'with `{other}`.'
                        ),
                    ))

    return mods, issues
