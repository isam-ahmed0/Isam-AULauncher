"""Seasonal event parsing and resolution (toolkit-free).

The hosting repo serves a tiny text file next to ``release/message.txt``::

    # name: last active day (YYYY-MM-DD, inclusive)
    winter: YYYY-MM-DD

Events are generic; only names with a registered visual theme or effect affect
the UI. The remote file is the only event source; ``--event <name>`` forces an
event on for testing, and ``--event none`` forces every event off.
"""
import datetime as _dt
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from config import EVENTS_URL, EVENT_FETCH_TIMEOUT

_ROW_RE = re.compile(
    r"^\s*([a-z][a-z0-9_-]*)\s*:\s*(\d{4}-\d{2}-\d{2})(?:\s|$)",
    re.IGNORECASE,
)
_DISABLED = {"", "none", "off", "false", "0"}

DEFAULT_WEB_THEME = "aurora"

# Event name -> web theme used while that event is active.
EVENT_THEMES = {"winter": "winter"}
EVENT_THEME_IDS = frozenset(EVENT_THEMES.values())

# Events whose effects can be layered on top of any web theme.
FX_EVENTS = {"winter"}


@dataclass(frozen=True)
class SeasonEvent:
    """Resolved event state sent to the web UI and used by the bridge."""

    name: str
    active: bool
    end_date: str = ""
    forced: bool = False
    source: str = "inactive"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active": self.active,
            "end_date": self.end_date,
            "forced": self.forced,
            "source": self.source,
            "suppressed": self.source == "disabled",
            "theme": EVENT_THEMES.get(self.name, ""),
            "fx": self.name in FX_EVENTS,
        }


def parse_events(raw: Optional[str]) -> List[Tuple[str, str]]:
    """Return ``(name, end_date)`` rows, preserving file order."""
    events: List[Tuple[str, str]] = []
    seen = set()
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ROW_RE.match(stripped)
        if not match:
            continue
        name = match.group(1).lower()
        end_date = match.group(2)
        try:
            _dt.date.fromisoformat(end_date)
        except ValueError:
            continue
        if name in seen:
            continue
        seen.add(name)
        events.append((name, end_date))
    return events


def active_event(events: List[Tuple[str, str]], today: Optional[_dt.date] = None):
    """First event that has not ended yet, or ``(None, None)``."""
    day = today or _dt.date.today()
    for name, end_date in events:
        if day <= _dt.date.fromisoformat(end_date):
            return name, end_date
    return None, None


def resolve_event(
    raw: Optional[str] = "",
    force: Optional[str] = None,
    today: Optional[_dt.date] = None,
) -> SeasonEvent:
    """Resolve an event from cached file text plus an optional CLI override."""
    forced = str(force or "").strip().lower()
    if force is not None and forced in _DISABLED:
        return SeasonEvent("", False, forced=True, source="disabled")

    events = parse_events(raw)
    if forced:
        end_date = dict(events).get(forced, "")
        return SeasonEvent(forced, True, end_date, forced=True, source="cli")

    name, end_date = active_event(events, today)
    if not name:
        return SeasonEvent("", False, source="inactive")
    return SeasonEvent(name, True, end_date or "", source="remote")


def normalize_winter_choice(value: Any) -> str:
    """Winter switches are ``auto`` / ``on`` / ``off``.

    ``auto`` means "on while the Winter event is active"; ``on`` keeps it on
    for that event, and ``off`` disables it. Booleans from older configs and
    the UI map to ``on``/``off``.
    """
    if value is None:
        return "auto"
    if isinstance(value, bool):
        return "on" if value else "off"
    raw = str(value).strip().lower()
    if raw in ("", "auto", "default"):
        return "auto"
    if raw in ("1", "true", "on", "yes"):
        return "on"
    return "off"


def event_visuals_active(event: Optional[SeasonEvent] = None) -> bool:
    """True only when a resolved event supplies a theme or effects."""
    if not event or not event.active:
        return False
    return bool(EVENT_THEMES.get(event.name) or event.name in FX_EVENTS)


def winter_preset_active(settings: Any = None, event: Optional[SeasonEvent] = None) -> bool:
    """True only while the Winter event is active, never for a saved preset."""
    _ = settings  # retained for callers that pass the settings dict
    return bool(event and event.active and EVENT_THEMES.get(event.name) == "winter")


def resolve_winter_choice(value: Any, winter_active: bool) -> bool:
    """Apply the auto/on/off rule for one Winter switch."""
    choice = normalize_winter_choice(value)
    return choice == "on" or (choice == "auto" and winter_active)


def wants_winter_fx(settings: Any = None, event: Optional[SeasonEvent] = None) -> bool:
    """Whether snow and frost run (only during the Winter event)."""
    value = settings if isinstance(settings, dict) else {}
    return resolve_winter_choice(
        value.get("winter_fx"), winter_preset_active(value, event)
    )


def wants_winter_bg(settings: Any = None, event: Optional[SeasonEvent] = None) -> bool:
    """Whether the snowy backdrop shows (only during the Winter event)."""
    value = settings if isinstance(settings, dict) else {}
    winter = winter_preset_active(value, event)
    return (
        resolve_winter_choice(value.get("winter_fx"), winter)
        and resolve_winter_choice(value.get("winter_bg"), winter)
    )


def effective_web_theme(value: Any, event: Optional[SeasonEvent] = None) -> str:
    """Return the theme the web UI should paint right now.

    During a registered event the seasonal theme wins for everyone; the saved
    value stays in config and returns automatically once the event ends.
    """
    if event and event.active:
        theme = EVENT_THEMES.get(event.name)
        if theme:
            return theme
    raw = str(value or "").strip().lower()
    theme_id = {"dark": "aurora", "light": "aurora-light"}.get(raw, raw or DEFAULT_WEB_THEME)
    # Event-only presets are inert outside their event; a saved value must not
    # reveal or enable them.
    if theme_id in EVENT_THEME_IDS:
        return DEFAULT_WEB_THEME
    return theme_id


def fetch_events_text(network: Any = None) -> str:
    """Fetch events.txt from the same raw GitHub host as message.txt only."""
    try:
        if network is not None and hasattr(network, "session"):
            response = network.session.get(EVENTS_URL, timeout=EVENT_FETCH_TIMEOUT)
        else:
            import requests
            response = requests.get(EVENTS_URL, timeout=EVENT_FETCH_TIMEOUT)
        response.raise_for_status()
        return (response.text or "").strip()
    except Exception as exc:
        logging.debug("Seasonal events fetch failed: %s", exc)
        return ""


def load_event(config, network: Any = None, force: Optional[str] = None) -> SeasonEvent:
    """Fetch, cache and resolve the active event for this launch."""
    cached = str(config.settings.get("events_cache") or "")
    fetched = fetch_events_text(network)
    if fetched:
        cached = fetched
        if config.settings.get("events_cache") != fetched:
            config.settings["events_cache"] = fetched
            config.save_settings()
    return resolve_event(cached, force)
