"""RegionManager — read/write Among Us regionInfo.json."""
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict

log = logging.getLogger(__name__)

REGION_DIR = Path.home() / "AppData" / "LocalLow" / "Innersloth" / "Among Us"
REGION_FILE = REGION_DIR / "regionInfo.json"

OFFICIAL_REGIONS = [
    {"Name": "North America", "PingServer": "https://among-us.mm.na.among.us", "Port": 443, "Ip": "https://among-us.mm.na.among.us"},
    {"Name": "Asia", "PingServer": "https://among-us.mm.ap.among.us", "Port": 443, "Ip": "https://among-us.mm.ap.among.us"},
    {"Name": "Europe", "PingServer": "https://among-us.mm.eu.among.us", "Port": 443, "Ip": "https://among-us.mm.eu.among.us"},
    {"Name": "Japan", "PingServer": "https://among-us.mm.jp.among.us", "Port": 443, "Ip": "https://among-us.mm.jp.among.us"},
    {"Name": "South America", "PingServer": "https://among-us.mm.sa.among.us", "Port": 443, "Ip": "https://among-us.mm.sa.among.us"},
]


def _make_region(name: str, ip: str, port: int = 443) -> Dict:
    return {
        "$type": "StaticHttpRegionInfo, Assembly-CSharp",
        "Name": name,
        "PingServer": ip,
        "Servers": [
            {
                "Name": "http-1",
                "Ip": ip,
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

    def add(self, name: str, ip: str, port: int = 443) -> bool:
        if any(r["Name"] == name for r in self.regions):
            return False
        self.regions.append(_make_region(name, ip, port))
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
        self._data["Regions"] = [_make_region(r["Name"], r["Ip"], r["Port"]) for r in OFFICIAL_REGIONS]
