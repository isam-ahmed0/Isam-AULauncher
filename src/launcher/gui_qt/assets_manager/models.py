"""Data models for the Assets Manager (AU-Assets-Swapper packs)."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict


@dataclass
class PackMetadata:
    name: str = ""
    author: str = ""
    description: str = ""
    version: str = "1.0.0"
    thumbnail: Optional[str] = None
    game_version: Optional[str] = None
    created_at: Optional[str] = None
    categories: List[str] = field(default_factory=list)


@dataclass
class AssetPack:
    name: str
    path: Path
    asset_count: int = 0
    total_size: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    metadata: Optional[PackMetadata] = None
    active: bool = False
