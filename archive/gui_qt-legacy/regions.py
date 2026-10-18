"""RegionManager — read/write Among Us regionInfo.json."""
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict

log = logging.getLogger(__name__)

REGION_DIR = Path.home() / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
REGION_FILE = REGION_DIR / "regionInfo.json"

OFFICIAL_REGIONS = [
    {"Name": "North America", "PingServer": "matchmaker.among.us", "Ip": "https://matchmaker.among.us", "Port": 443},
    {"Name": "Asia", "PingServer": "matchmaker-as.among.us", "Ip": "https://matchmaker-as.among.us", "Port": 443},
    {"Name": "Europe", "PingServer": "matchmaker-eu.among.us", "Ip": "https://matchmaker-eu.among.us", "Port": 443},
    {"Name": "Japan", "PingServer": "matchmaker-jp.among.us", "Ip": "https://matchmaker-jp.among.us", "Port": 443},
    {"Name": "South America", "PingServer": "matchmaker-sa.among.us", "Ip": "https://matchmaker-sa.among.us", "Port": 443},
]


def _normalize_ping(ping: str) -> str:
    """Strip https:// prefix — PingServer is raw IP/hostname."""
    ping = ping.strip()
    for prefix in ("https://", "http://"):
        if ping.lower().startswith(prefix):
            ping = ping[len(prefix):]
    return ping.strip("/")


def _normalize_ip(ip: str) -> str:
    """Ensure https:// prefix — Servers[].Ip is a full URL."""
    ip = ip.strip()
    if not ip.startswith(("http://", "https://")):
        ip = "https://" + ip
    return ip.rstrip("/")


def _make_region(name: str, ping_server: str, server_ip: str, port: int = 443) -> Dict:
    return {
        "$type": "StaticHttpRegionInfo, Assembly-CSharp",
        "Name": name,
        "PingServer": _normalize_ping(ping_server),
        "Servers": [
            {
                "Name": "http-1",
                "Ip": _normalize_ip(server_ip),
                "Port": port,
                "UseDtls": False,
                "Players": 0,
                "ConnectionFailures": 0,
            }
        ],
        "TargetServer": None,
        "TranslateName": 1003,
    }


class RegionManager:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or REGION_FILE
        self._data: Dict = {"CurrentRegionIdx": 0, "Regions": []}

    @property
    def regions(self) -> List[Dict]:
        return self._data.get("Regions", [])

    @property
    def active_index(self) -> int:
        return self._data.get("CurrentRegionIdx", 0)

    @active_index.setter
    def active_index(self, idx: int):
        if 0 <= idx < len(self.regions):
            self._data["CurrentRegionIdx"] = idx

    def load(self) -> bool:
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
                return True
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Failed to load regions: {e}")
        return False

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            return True
        except OSError as e:
            log.error(f"Failed to save regions: {e}")
        return False

    def add(self, name: str, ping_server: str, server_ip: str, port: int = 443) -> bool:
        if any(r["Name"] == name for r in self.regions):
            return False
        self.regions.append(_make_region(name, ping_server, server_ip, port))
        return True

    def remove(self, index: int) -> bool:
        if 0 <= index < len(self.regions):
            self.regions.pop(index)
            if self._data["CurrentRegionIdx"] >= len(self.regions):
                self._data["CurrentRegionIdx"] = max(0, len(self.regions) - 1)
            return True
        return False

    def reset_official(self):
        self._data["CurrentRegionIdx"] = 0
        self._data["Regions"] = [_make_region(r["Name"], r["PingServer"], r["Ip"], r["Port"]) for r in OFFICIAL_REGIONS]
