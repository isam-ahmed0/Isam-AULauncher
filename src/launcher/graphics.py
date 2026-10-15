"""GPU detection and Wine-binary discovery (Linux).

Toolkit-free so both the Qt and Tk front-ends can share it. Nothing here
installs anything; detection is best-effort and degrades to empty results when
the usual tools (lspci, wine) are missing.
"""
import os
import re
import glob
import logging
import shutil
import subprocess
from pathlib import Path

from platform_utils import external_env, IS_LINUX

log = logging.getLogger(__name__)

VENDOR_INTEL = "intel"
VENDOR_NVIDIA = "nvidia"
VENDOR_AMD = "amd"
VENDOR_OTHER = "other"

_AUTO = ""
_AUTO_KEY = "auto"

_GPU_LINE = re.compile(
    r"^(?P<slot>[0-9a-f:.]+)\s+"
    r"(?:VGA compatible controller|3D controller|Display controller):\s*"
    r"(?P<desc>.+?)(?:\s+\(rev [0-9a-f]+\))?$",
    re.IGNORECASE,
)


def _vendor_of(text):
    low = text.lower()
    if "nvidia" in low:
        return VENDOR_NVIDIA
    if "intel" in low:
        return VENDOR_INTEL
    if "amd" in low or "advanced micro devices" in low or "ati " in low:
        return VENDOR_AMD
    return VENDOR_OTHER


def _vendor_from_sysfs(slot):
    base = Path("/sys/bus/pci/devices")
    try:
        for dev in base.glob("0000:*"):
            if dev.name.endswith(slot):
                vendor = (dev / "vendor").read_text().strip().lower()
                if vendor == "0x10de":
                    return VENDOR_NVIDIA
                if vendor == "0x8086":
                    return VENDOR_INTEL
                if vendor in ("0x1002", "0x1022"):
                    return VENDOR_AMD
    except Exception:
        pass
    return None


def _pretty_name(desc):
    name = desc.strip()
    for prefix in ("NVIDIA Corporation", "Intel Corporation",
                   "Advanced Micro Devices, Inc.", "Advanced Micro Devices Inc.",
                   "AMD/ATI", "AMD", "ATI Technologies Inc."):
        if name.startswith(prefix):
            name = name[len(prefix):].strip(" []")
            break
    return name or desc.strip()


def detect_gpus():
    """Return a list of GPUs as dicts.

    Keys: ``id`` (PCI slot), ``name``, ``vendor``, ``discrete``, ``pci_slot``,
    ``dri_prime``. Empty list when detection fails.
    """
    gpus = []
    try:
        out = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=8,
            env=external_env())
        if out.returncode != 0:
            return gpus
        for line in out.stdout.splitlines():
            m = _GPU_LINE.match(line.strip())
            if not m:
                continue
            slot = m.group("slot")
            desc = m.group("desc")
            vendor = _vendor_from_sysfs(slot) or _vendor_of(desc)
            gpus.append({
                "id": slot,
                "name": _pretty_name(desc),
                "vendor": vendor,
                "discrete": vendor != VENDOR_INTEL,
                "pci_slot": slot,
                "dri_prime": f"pci-0000:{slot}",
            })
    except FileNotFoundError:
        log.info("lspci not found; GPU detection unavailable")
    except Exception as e:
        log.warning("GPU detection failed: %s", e)
    return gpus


def find_gpu(gpus, gpu_id):
    """Return the GPU dict whose ``id`` matches, or None."""
    if not gpu_id:
        return None
    for g in gpus:
        if g.get("id") == gpu_id:
            return g
    return None


def gpu_env(gpu_id, gpus=None):
    """Environment variables that force the given GPU, or {} for auto/default."""
    if not gpu_id or gpu_id == _AUTO_KEY:
        return {}
    if gpus is None:
        gpus = detect_gpus()
    gpu = find_gpu(gpus, gpu_id)
    if gpu is None:
        return {}
    vendor = gpu.get("vendor")
    if vendor == VENDOR_NVIDIA:
        return {
            "__NV_PRIME_RENDER_OFFLOAD": "1",
            "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
            "__VK_LAYER_NV_optimus": "NVIDIA_only",
            "DRI_PRIME": "1",
        }
    if vendor in (VENDOR_AMD, VENDOR_INTEL):
        return {
            "DRI_PRIME": gpu.get("dri_prime") or "1",
            "__GLX_VENDOR_LIBRARY_NAME": "mesa",
            "__VK_LAYER_NV_optimus": "non_NVIDIA_only",
        }
    return {"DRI_PRIME": gpu.get("dri_prime") or "1"}


def describe_gpu(gpu_id, gpus=None):
    """Human-readable label for the selected GPU (or \"System default\")."""
    if not gpu_id or gpu_id == _AUTO_KEY:
        return "System default"
    if gpus is None:
        gpus = detect_gpus()
    gpu = find_gpu(gpus, gpu_id)
    if gpu is None:
        return f"Unknown GPU ({gpu_id})"
    return gpu["name"]


# ---------------------------------------------------------------------------
# Wine binary discovery
# ---------------------------------------------------------------------------
_WINE_NAMES = ("wine-staging", "wine", "wine64", "wine-stable", "wine-devel")

_WINE_GLOBS = (
    # Lutris (native + Flatpak)
    "~/.local/share/lutris/runners/wine/*/bin/wine",
    "~/.var/app/net.lutris.Lutris/data/lutris/runners/wine/*/bin/wine",
    # Steam compatibilitytools.d (GE-Proton, etc.)
    "~/.steam/root/compatibilitytools.d/*/files/bin/wine",
    "~/.steam/steam/compatibilitytools.d/*/files/bin/wine",
    "~/.local/share/Steam/compatibilitytools.d/*/files/bin/wine",
    # Official Steam Proton (steamapps/common/Proton *)
    "~/.steam/root/steamapps/common/Proton */files/bin/wine",
    "~/.steam/steam/steamapps/common/Proton */files/bin/wine",
    "~/.local/share/Steam/steamapps/common/Proton */files/bin/wine",
    "~/.steam/root/steamapps/common/Proton */dist/bin/wine",
    "~/.steam/steam/steamapps/common/Proton */dist/bin/wine",
    "~/.local/share/Steam/steamapps/common/Proton */dist/bin/wine",
    # PortProton (standalone + Flatpak)
    "~/PortProton/data/wine/*/bin/wine",
    "~/PortProton-Enhanced/data/wine/*/bin/wine",
    "~/.var/app/ru.linux_gaming.PortProton/data/PortProton/data/wine/*/bin/wine",
    "~/.local/share/flatpak/app/ru.linux_gaming.PortProton/current/active/files/PortProton/data/wine/*/bin/wine",
    # Bottles (native + Flatpak)
    "~/.local/share/bottles/runners/*/bin/wine",
    "~/.var/app/com.usebottles.bottles/data/bottles/runners/*/bin/wine",
    # Heroic Games Launcher
    "~/.config/heroic/wine/*/bin/wine",
    "~/.local/share/heroic/wine/*/bin/wine",
    "~/.var/app/com.heroicgameslauncher.hgl/data/heroic/wine/*/bin/wine",
    # Wine-GE standalone downloads
    "~/wine-ge-*/bin/wine",
    "~/Downloads/wine-ge-*/bin/wine",
    "~/.local/share/wine-ge-*/bin/wine",
    # Wine-TKG / custom builds
    "~/wine-tkg-*/bin/wine",
    "~/Downloads/wine-tkg-*/bin/wine",
)

_WINE_EXTRA_DIRS = ("/usr/bin", "/usr/local/bin", "/bin", "/opt/wine/bin")


def _extract_wine_name(path):
    """Extract a meaningful name from a wine binary path."""
    rp = str(Path(path).expanduser().resolve())
    parts = Path(rp).parts
    # Lutris runners
    if "lutris" in rp and "runners" in rp and "wine" in parts:
        idx = parts.index("wine")
        if idx + 1 < len(parts):
            return f"Lutris {parts[idx + 1]}"
    # Steam compatibilitytools.d
    if "compatibilitytools.d" in parts:
        idx = parts.index("compatibilitytools.d")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    # Steam Proton (steamapps/common/Proton */files|dist)
    if "steamapps" in parts and "common" in parts:
        idx = parts.index("common")
        if idx + 1 < len(parts) and parts[idx + 1].startswith("Proton"):
            proton_name = parts[idx + 1]
            # Determine files vs dist
            if "files" in parts:
                return f"{proton_name} (files)"
            if "dist" in parts:
                return f"{proton_name} (dist)"
            return proton_name
    # PortProton
    if "PortProton" in parts:
        idx = parts.index("PortProton")
        if idx + 1 < len(parts) and "wine" in parts:
            wine_idx = parts.index("wine")
            if wine_idx + 1 < len(parts):
                return f"PortProton {parts[wine_idx + 1]}"
        return "PortProton"
    # PortProton Flatpak
    if "ru.linux_gaming.PortProton" in rp:
        return "PortProton (Flatpak)"
    # Bottles
    if "bottles" in parts and "runners" in parts:
        idx = parts.index("runners")
        if idx + 1 < len(parts):
            return f"Bottles {parts[idx + 1]}"
    # Heroic
    if "heroic" in parts and "wine" in parts:
        idx = parts.index("wine")
        if idx + 1 < len(parts):
            return f"Heroic {parts[idx + 1]}"
    # Wine-GE standalone
    if "wine-ge" in rp:
        for p in parts:
            if p.startswith("wine-ge"):
                return f"GE-Proton {p.replace('wine-ge-', '')}"
    # Wine-TKG
    if "wine-tkg" in rp:
        for p in parts:
            if p.startswith("wine-tkg"):
                return f"Wine-TKG {p.replace('wine-tkg-', '')}"
    # Fallback: parent dir name
    name = Path(rp).parent.parent.name if len(Path(rp).parents) >= 2 else Path(rp).name
    # Clean up generic names
    if name in ("usr", "bin", "local", "opt", "home"):
        return "System wine"
    return name


def detect_wine_binaries():
    """Return a list of ``{"name", "path"}`` for Wine builds found on the system."""
    found = []
    seen = set()

    def add(path):
        try:
            rp = str(Path(path).expanduser().resolve())
        except Exception:
            rp = str(path)
        if rp in seen or not os.path.isfile(rp) or not os.access(rp, os.X_OK):
            return
        seen.add(rp)
        found.append({"name": _extract_wine_name(rp), "path": rp})

    for name in _WINE_NAMES:
        p = shutil.which(name)
        if p:
            add(p)
    for d in _WINE_EXTRA_DIRS:
        for name in _WINE_NAMES:
            cand = Path(d) / name
            if cand.exists():
                add(cand)
    for pattern in _WINE_GLOBS:
        for p in sorted(glob.glob(os.path.expanduser(pattern))):
            add(p)
    return found


def resolve_wine(override=None):
    """Path to the wine executable: explicit override, PATH, then first found."""
    if override:
        p = Path(override).expanduser()
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
    p = shutil.which("wine")
    if p:
        return p
    found = detect_wine_binaries()
    return found[0]["path"] if found else None


def describe_wine(path):
    """Short label for a wine path (or \"Not found\")."""
    if not path:
        return "Not found"
    return str(path)
