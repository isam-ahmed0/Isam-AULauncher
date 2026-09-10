"""Data models for the Assets Manager."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class AssetEntry:
    name: str
    asset_type: str
    source: str
    dll_source: str = ""
    has_replacement: bool = False
    width: Optional[int] = None
    height: Optional[int] = None


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
class PackProfile:
    name: str
    path: Path
    asset_count: int = 0
    categories: List[str] = field(default_factory=list)
    metadata: Optional[PackMetadata] = None
