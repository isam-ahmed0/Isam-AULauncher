"""Remote news/announcements (toolkit-free).

The hosting repo serves a Markdown note at ``MESSAGE_URL`` (release/message.txt).
This module fetches it, identifies it (for "show only when it changes" logic),
caches it for offline display and converts it to plain text for the Tk UI.
"""
import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from config import MESSAGE_URL

# Optional marker to force a re-notification regardless of content changes:
#   <!-- id: summer-update -->
_ID_RE = re.compile(r"<!--\s*id:\s*([^\s]+)\s*-->", re.IGNORECASE)

_URL_RE = re.compile(r"https?://[^\s<>()\[\]]+")


@dataclass
class NewsItem:
    text: str
    identity: str


def parse_news(raw: Optional[str]) -> Optional[NewsItem]:
    """Build a NewsItem from raw file text, or None if it is empty."""
    text = (raw or "").strip()
    if not text:
        return None
    m = _ID_RE.search(text)
    if m:
        identity = f"id:{m.group(1)}"
    else:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        identity = f"sha256:{digest}"
    return NewsItem(text=text, identity=identity)


def fetch_news(network) -> Optional[NewsItem]:
    """Fetch the remote message. Returns None on failure/empty."""
    try:
        raw = network.fetch_text(MESSAGE_URL)
    except Exception as e:
        logging.debug(f"News fetch failed: {e}")
        return None
    return parse_news(raw)


def is_unseen(settings: Dict[str, Any], item: Optional[NewsItem]) -> bool:
    if item is None:
        return False
    return item.identity != (settings.get("news_seen_hash") or "")


def mark_seen(config, item: Optional[NewsItem]) -> None:
    """Persist the item identity so it is not announced again."""
    if item is None:
        return
    if config.settings.get("news_seen_hash") == item.identity:
        return
    config.settings["news_seen_hash"] = item.identity
    config.save_settings()


def cache_news(config, item: Optional[NewsItem]) -> None:
    """Store the last fetched text so the News page works offline."""
    if item is None:
        return
    text = item.text
    if config.settings.get("news_cache") == text:
        return
    config.settings["news_cache"] = text
    config.save_settings()


def get_cached_news(config) -> Optional[NewsItem]:
    return parse_news(config.settings.get("news_cache") or "")


def split_posts(text: str):
    """Split the feed into posts. Posts are separated by a ``---`` line.

    Posts are shown in file order, so put the newest one first.
    """
    parts = re.split(r"^\s*---\s*$", text or "", flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def newest_post(item: Optional[NewsItem]) -> str:
    if item is None:
        return ""
    posts = split_posts(item.text)
    return posts[0] if posts else ""


def news_to_plain(text: str) -> str:
    """Lightweight Markdown → plain text for the Tk UI.

    Images and links keep their URLs as separate text so the Tk Text widget
    can make them clickable.
    """
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r"Image: \2", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*---\s*$", "─" * 46, text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "  - ", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.strip()


def extract_urls(text: str):
    """Unique http(s) URLs in text, in order of appearance."""
    seen = set()
    urls = []
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;:!?")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls
