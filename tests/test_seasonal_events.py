"""Tests for the generic remote seasonal-event file."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

import seasonal_events  # noqa: E402


class SeasonalEventTests(unittest.TestCase):
    RAW = """
# events are name: enddate
winter: 2026-12-31
bad-date: 2026-99-99
broken line
summer: 2026-06-01
"""

    def test_parse_ignores_comments_and_invalid_rows(self):
        self.assertEqual(
            seasonal_events.parse_events(self.RAW),
            [("winter", "2026-12-31"), ("summer", "2026-06-01")],
        )

    def test_active_event_uses_end_date_inclusively(self):
        events = seasonal_events.parse_events(self.RAW)
        day = dt.date(2026, 12, 31)
        name, end = seasonal_events.active_event(events, day)
        self.assertEqual((name, end), ("winter", "2026-12-31"))

        name, _ = seasonal_events.active_event(events, dt.date(2027, 1, 1))
        self.assertIsNone(name)

    def test_force_enables_and_disables_events(self):
        forced = seasonal_events.resolve_event("", "winter")
        self.assertTrue(forced.active)
        self.assertTrue(forced.forced)
        self.assertEqual(forced.source, "cli")

        disabled = seasonal_events.resolve_event(self.RAW, "none")
        self.assertFalse(disabled.active)
        self.assertTrue(disabled.forced)

    def test_no_force_without_a_file_is_inactive(self):
        event = seasonal_events.resolve_event("", None)
        self.assertFalse(event.active)
        self.assertFalse(event.forced)

    def test_event_overrides_saved_theme_only_while_active(self):
        winter = seasonal_events.resolve_event(self.RAW, "winter")
        self.assertEqual(
            seasonal_events.effective_web_theme("violet", winter), "winter"
        )
        inactive = seasonal_events.resolve_event(self.RAW, "none")
        self.assertEqual(
            seasonal_events.effective_web_theme("violet", inactive), "violet"
        )
        self.assertEqual(
            seasonal_events.effective_web_theme("winter", inactive), "winter"
        )

    def test_winter_switches_auto_follow_the_effective_theme(self):
        winter = seasonal_events.resolve_event("", "winter")
        settings = {
            "web_theme": "forest", "winter_fx": "auto", "winter_bg": "auto",
        }
        self.assertFalse(seasonal_events.wants_winter_fx(settings))
        self.assertFalse(seasonal_events.wants_winter_bg(settings))

        self.assertTrue(seasonal_events.wants_winter_fx(settings, winter))
        self.assertTrue(seasonal_events.wants_winter_bg(settings, winter))

        settings["web_theme"] = "winter"
        self.assertTrue(seasonal_events.wants_winter_fx(settings))
        self.assertTrue(seasonal_events.wants_winter_bg(settings))

    def test_winter_switch_can_layer_over_other_themes(self):
        settings = {
            "web_theme": "forest", "winter_fx": "on", "winter_bg": "on",
        }
        self.assertTrue(seasonal_events.wants_winter_fx(settings))
        self.assertTrue(seasonal_events.wants_winter_bg(settings))

        settings["winter_fx"] = "off"
        self.assertFalse(seasonal_events.wants_winter_fx(settings))
        self.assertFalse(seasonal_events.wants_winter_bg(settings))

    def test_unregistered_event_does_not_auto_layer_winter(self):
        settings = {
            "web_theme": "forest", "winter_fx": "auto", "winter_bg": "auto",
        }
        summer = seasonal_events.resolve_event("", "summer")
        self.assertFalse(seasonal_events.wants_winter_fx(settings, summer))

        winter = seasonal_events.resolve_event("", "winter")
        self.assertTrue(seasonal_events.wants_winter_fx(settings, winter))

    def test_legacy_boolean_choices_still_normalize(self):
        self.assertEqual(seasonal_events.normalize_winter_choice(True), "on")
        self.assertEqual(seasonal_events.normalize_winter_choice(False), "off")
        self.assertEqual(seasonal_events.normalize_winter_choice(None), "auto")


if __name__ == "__main__":
    unittest.main()
