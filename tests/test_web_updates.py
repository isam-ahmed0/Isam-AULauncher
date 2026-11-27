"""Checks for the web GUI's startup and forced launcher update flow."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

from gui_web.api import LauncherApi  # noqa: E402


class FakeEmitter:
    def __init__(self):
        self.events = []
        self.enabled = False

    def enable(self):
        self.enabled = True

    def emit(self, name, data=None):
        self.events.append((name, data))


def make_api(remote="1.0-alpha", skipped=""):
    ctx = SimpleNamespace(
        network=SimpleNamespace(fetch_text=lambda url: remote),
        config=SimpleNamespace(
            settings={"skipped_launcher_version": skipped},
        ),
    )
    return LauncherApi(ctx, FakeEmitter())


class WebUpdateTests(unittest.TestCase):
    def launcher_payload(self, api):
        events = [data for name, data in api.em.events if name == "launcher_update"]
        self.assertEqual(len(events), 1)
        return events[0]

    def test_ready_starts_launcher_check_once(self):
        api = make_api()
        spawns = []
        with patch("gui_web.api.IS_LINUX", False), \
                patch.object(api, "_emit_state"), \
                patch.object(api, "_spawn", side_effect=lambda fn, *a: spawns.append(fn)):
            self.assertTrue(api.ready()["ok"])
            self.assertTrue(api.em.enabled)
            # A second ready() must not schedule a duplicate check.
            api.ready()
        self.assertEqual(
            [fn.__name__ for fn in spawns],
            ["_poll_loop", "_update_check_worker"],
        )

    def test_older_remote_version_offers_force_update(self):
        api = make_api("1.0-alpha")
        with patch.object(api, "_check_game_update"):
            api._update_check_worker()
        payload = self.launcher_payload(api)
        self.assertFalse(payload["available"])
        self.assertTrue(payload["force_available"])
        self.assertEqual(payload["version"], "1.0-alpha")
        self.assertEqual(payload["current"], "1.0")

    def test_newer_remote_version_is_a_normal_update(self):
        api = make_api("1.1")
        with patch.object(api, "_check_game_update"):
            api._update_check_worker()
        payload = self.launcher_payload(api)
        self.assertTrue(payload["available"])
        self.assertFalse(payload["force_available"])

    def test_equal_and_invalid_versions_do_not_offer_force_update(self):
        for remote in ("1.0", "not-a-version", ""):
            with self.subTest(remote=remote):
                api = make_api(remote)
                with patch.object(api, "_check_game_update"):
                    api._update_check_worker()
                payload = self.launcher_payload(api)
                self.assertFalse(payload["available"])
                self.assertFalse(payload["force_available"])

    def test_skipped_version_hides_force_option(self):
        api = make_api("1.0-alpha", skipped="1.0-alpha")
        with patch.object(api, "_check_game_update"):
            api._update_check_worker()
        payload = self.launcher_payload(api)
        self.assertTrue(payload["skipped"])
        self.assertFalse(payload["available"])
        self.assertFalse(payload["force_available"])

    def test_force_update_targets_exact_tag_on_linux(self):
        api = make_api()
        with patch("gui_web.api.IS_WINDOWS", False), \
                patch.object(api, "open_url", return_value={"ok": True}) as open_url:
            result = api.update_launcher("1.0-alpha", force=True)
        self.assertTrue(result["ok"])
        open_url.assert_called_once_with(
            "https://github.com/isam-ahmed0/Isam-AULauncher/releases/tag/1.0-alpha")

    def test_update_requires_a_version(self):
        api = make_api()
        self.assertFalse(api.update_launcher("")["ok"])


if __name__ == "__main__":
    unittest.main()
