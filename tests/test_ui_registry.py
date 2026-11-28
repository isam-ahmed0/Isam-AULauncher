"""Tests for built-in Web interface availability reporting."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

import ui_registry  # noqa: E402


class WebAvailabilityTests(unittest.TestCase):
    def test_missing_pywebview(self):
        with patch.object(ui_registry, "_module_available", return_value=False):
            self.assertEqual(
                ui_registry._web_available(),
                (False, "missing pywebview"),
            )

    def test_missing_web_assets(self):
        with patch.object(ui_registry, "_module_available", return_value=True), \
                patch("gui_web.assets.index_exists", return_value=False):
            self.assertEqual(
                ui_registry._web_available(),
                (False, "web assets not built"),
            )

    def test_web_available(self):
        with patch.object(ui_registry, "_module_available", return_value=True), \
                patch("gui_web.assets.index_exists", return_value=True):
            self.assertEqual(ui_registry._web_available(), (True, ""))

    def test_list_guis_reports_web_reason(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(ui_registry, "_web_available",
                             return_value=(False, "missing pywebview")):
            guis = ui_registry.list_guis(SimpleNamespace(guis_dir=Path(tmp)))
        web = next(g for g in guis if g["id"] == "web")
        self.assertFalse(web["available"])
        self.assertEqual(web["reason"], "missing pywebview")


if __name__ == "__main__":
    unittest.main()
