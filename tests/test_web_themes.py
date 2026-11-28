import json
import tempfile
import unittest
from pathlib import Path

import config


class WebThemeTests(unittest.TestCase):
    def _load(self, payload):
        cfg = object.__new__(config.Config)
        with tempfile.TemporaryDirectory() as tmp:
            cfg.config_file = Path(tmp) / "config.json"
            cfg.config_file.write_text(json.dumps(payload))
            return cfg._load_settings()

    def test_default_is_aurora(self):
        self.assertEqual(self._load({})["web_theme"], "aurora")

    def test_legacy_dark_and_light_become_presets(self):
        self.assertEqual(self._load({"web_theme": "dark"})["web_theme"], "aurora")
        self.assertEqual(
            self._load({"web_theme": "light"})["web_theme"], "aurora-light"
        )

    def test_preset_values_are_preserved(self):
        self.assertEqual(
            self._load({"web_theme": "violet"})["web_theme"], "violet"
        )
        self.assertEqual(
            self._load({"web_theme": "winter"})["web_theme"], "winter"
        )

    def test_winter_toggles_default_to_auto(self):
        loaded = self._load({})
        self.assertEqual(loaded["winter_fx"], "auto")
        self.assertEqual(loaded["winter_bg"], "auto")


if __name__ == "__main__":
    unittest.main()
