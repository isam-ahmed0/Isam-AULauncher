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


# Binary patterns — match BepInEx attribute strings in DLL bytes
_RE_PLUGIN = re.compile(
    rb'BepInPlugin\s*\(\s*"([^"]+)"\s*,\s*"([^"]*?)"\s*,\s*"([^"]*?)"\s*\)'
)
_RE_DEPENDENCY = re.compile(
    rb'BepInDependency\s*\(\s*"([^"]+)"'
)
_RE_INCOMPATIBILITY = re.compile(
    rb'BepInIncompatibility\s*\(\s*"([^"]+)"\s*\)'
)


def _read_dll_metadata(dll_path: Path) -> ModInfo:
    """Read BepInEx attributes from a single DLL via binary regex."""
    mod = ModInfo(filename=dll_path.name)
    try:
        data = dll_path.read_bytes()
    except Exception as e:
        logging.warning(f"Could not read {dll_path.name}: {e}")
        return mod

    m = _RE_PLUGIN.search(data)
    if m:
        mod.guid = m.group(1).decode("utf-8", errors="replace")
        mod.name = m.group(2).decode("utf-8", errors="replace")
        mod.version = m.group(3).decode("utf-8", errors="replace")

    for m in _RE_DEPENDENCY.finditer(data):
        dep_guid = m.group(1).decode("utf-8", errors="replace")
        if dep_guid and dep_guid not in mod.dependencies:
            mod.dependencies.append(dep_guid)

    for m in _RE_INCOMPATIBILITY.finditer(data):
        inc_guid = m.group(1).decode("utf-8", errors="replace")
        if inc_guid and inc_guid not in mod.incompatibilities:
            mod.incompatibilities.append(inc_guid)

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
