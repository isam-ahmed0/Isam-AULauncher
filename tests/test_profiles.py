"""Tests for per-profile mod enable/disable and ordering."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

from gui_qt.profiles import ProfileManager  # noqa: E402
from mod_catalog import load_meta, save_meta  # noqa: E402


class ProfileManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mgr = ProfileManager(self.root)
        self.mgr.create_profile("P")
        self.profile = self.root / "P"
        (self.profile / "A.dll").write_bytes(b"a")
        (self.profile / "B.dll").write_bytes(b"b")
        save = load_meta(self.profile)
        save["catalog"] = {"m": {"version": "1.0", "filename": "A.dll", "files": ["A.dll"]}}
        save_meta(self.profile, save)

    def tearDown(self):
        self._tmp.cleanup()

    def test_toggle_updates_files_and_metadata(self):
        self.assertTrue(self.mgr.set_enabled("P", "A.dll", False))
        self.assertTrue((self.profile / "A.dll.disabled").is_file())
        meta = load_meta(self.profile)
        self.assertEqual(meta["disabled"], ["A.dll.disabled"])
        self.assertEqual(meta["catalog"]["m"]["filename"], "A.dll.disabled")
        self.assertTrue(self.mgr.set_enabled("P", "A.dll.disabled", True))
        self.assertTrue((self.profile / "A.dll").is_file())
        self.assertEqual(load_meta(self.profile)["disabled"], [])

    def test_reorder_is_unique_and_persisted(self):
        self.assertTrue(self.mgr.reorder_mod("P", "B.dll", -1))
        names = [p.name for p in self.mgr.list_mod_files("P")]
        self.assertEqual(names, ["B.dll", "A.dll"])
        fresh = ProfileManager(self.root)
        self.assertEqual([p.name for p in fresh.list_mod_files("P")], names)


if __name__ == "__main__":
    unittest.main()
