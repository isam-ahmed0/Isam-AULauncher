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
    "~/.local/share/lutris/runners/wine/*/bin/wine",
    "~/.var/app/net.lutris.Lutris/data/lutris/runners/wine/*/bin/wine",
    "~/.steam/root/compatibilitytools.d/*/files/bin/wine",
    "~/.steam/steam/compatibilitytools.d/*/files/bin/wine",
    "~/.local/share/Steam/compatibilitytools.d/*/files/bin/wine",
)

_WINE_EXTRA_DIRS = ("/usr/bin", "/usr/local/bin", "/bin", "/opt/wine/bin")


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
        found.append({"name": Path(rp).parent.parent.name
                      if "runners" in rp or "compatibilitytools" in rp
                      else Path(rp).name, "path": rp})

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
