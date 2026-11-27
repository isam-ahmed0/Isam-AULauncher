"""Tests for the toolkit-free AU-Assets-Swapper pack manager."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

from assets_manager import ASSET_CATEGORIES, AUASManager, PackMetadata  # noqa: E402


class AssetsManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.game = Path(self._tmp.name) / "game"
        self.game.mkdir()
        self.mgr = AUASManager(self.game)

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, path: Path, text="x") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_create_pack_builds_expected_layout(self):
        self.assertTrue(self.mgr.create_pack("Space"))
        pack = self.game / "AUAS_Data" / "Space"
        for category in ASSET_CATEGORIES:
            self.assertTrue((pack / category).is_dir(), category)
        self.assertTrue((pack / "README.txt").is_file())
        meta = self.mgr.get_metadata("Space")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "Space")
        self.assertFalse(self.mgr.create_pack("Space"))
        self.assertFalse(self.mgr.create_pack("Bad/name"))

    def test_copy_stats_and_remove_asset(self):
        self.mgr.create_pack("Space")
        sprite = self.touch(self.game / "src" / "sprite.png")
        audio = self.touch(self.game / "src" / "jump.wav")
        copied, skipped, errors = self.mgr.copy_assets("Space", [
            (sprite, "Sprites"), (audio, "Audio"),
        ])
        self.assertEqual((copied, skipped, errors), (2, 0, []))
        total, size, categories = self.mgr.pack_stats("Space")
        self.assertEqual(total, 2)
        self.assertEqual(size, 2)
        self.assertEqual(categories, {"Sprites": 1, "Audio": 1})
        self.assertTrue(self.mgr.remove_asset("Space", "Sprites", "sprite.png"))
        self.assertFalse(self.mgr.remove_asset("Space", "Sprites", "sprite.png"))
        self.assertFalse(self.mgr.remove_asset("Space", "Sprites", "../Audio/jump.wav"))
        self.assertEqual(self.mgr.pack_stats("Space")[0], 1)

    def test_active_pack_preserves_other_config_values(self):
        cfg = self.game / "BepInEx" / "config" / "com.auassetsswapper.plugin.cfg"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(
            "[General]\nSomeKey = keep\nActivePack = None\n\n"
            "[Other]\nEnabled = true\n",
            encoding="utf-8",
        )
        self.mgr.create_pack("Space")
        self.assertTrue(self.mgr.set_active_pack("Space"))
        text = cfg.read_text(encoding="utf-8")
        self.assertIn("SomeKey = keep", text)
        self.assertIn("Enabled = true", text)
        self.assertIn("ActivePack = Space", text)
        self.assertEqual(self.mgr.get_active_pack(), "Space")
        self.assertTrue(self.mgr.set_active_pack(None))
        self.assertIsNone(self.mgr.get_active_pack())

    def test_rename_duplicate_and_delete_active_pack(self):
        self.mgr.create_pack("Space")
        self.mgr.set_active_pack("Space")
        self.assertTrue(self.mgr.rename_pack("Space", "Ocean"))
        self.assertEqual(self.mgr.get_active_pack(), "Ocean")
        self.assertEqual(self.mgr.get_metadata("Ocean").name, "Ocean")
        self.assertTrue(self.mgr.duplicate_pack("Ocean", "Ocean copy"))
        meta = self.mgr.get_metadata("Ocean copy")
        self.assertIsNotNone(meta)
        self.assertEqual(meta.name, "Ocean copy")
        self.assertTrue(self.mgr.delete_pack("Ocean"))
        self.assertIsNone(self.mgr.get_active_pack())
        self.assertIsNotNone(self.mgr.get_pack("Ocean copy"))

    def test_export_import_round_trip(self):
        self.mgr.create_pack("Space")
        sprite = self.touch(self.game / "src" / "sprite.png")
        self.mgr.copy_assets("Space", [(sprite, "Sprites")])
        meta = self.mgr.get_metadata("Space")
        meta.author = "Tester"
        meta.description = "Round trip"
        self.assertTrue(self.mgr.save_metadata("Space", meta))

        archive = self.game / "space.zip"
        self.assertTrue(self.mgr.export_pack("Space", archive))

        dest = self.game.parent / "other" / "game"
        dest.mkdir(parents=True)
        other = AUASManager(dest)
        self.assertEqual(other.import_pack(archive, "Imported"), "Imported")
        self.assertTrue((dest / "AUAS_Data" / "Imported" / "Sprites" / "sprite.png").is_file())
        imported = other.get_metadata("Imported")
        self.assertEqual(imported.author, "Tester")
        self.assertEqual(imported.description, "Round trip")

    def test_import_blocks_zip_slip_entries(self):
        archive = self.game.parent / "slip.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("pack.json", json.dumps({"name": "Slip"}))
            zf.writestr("Sprites/../../escaped.png", "bad")
        self.assertEqual(self.mgr.import_pack(archive, "Slip"), "Slip")
        self.assertFalse((self.game / "AUAS_Data" / "escaped.png").exists())
        self.assertFalse((self.game / "escaped.png").exists())

    def test_metadata_defaults_and_name_validation(self):
        meta = PackMetadata()
        self.assertEqual(meta.version, "1.0.0")
        self.assertEqual(meta.categories, [])
        for name in ("", " Sprites ", "Sprites", "a/b", "a\\b", "a?b"):
            with self.subTest(name=name):
                self.assertFalse(AUASManager.is_valid_name(name))
        self.assertTrue(AUASManager.is_valid_name("My Cool Pack"))


if __name__ == "__main__":
    unittest.main()
