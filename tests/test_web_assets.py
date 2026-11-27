"""Checks for the Web bridge's asset-pack endpoints."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

from gui_web.api import LauncherApi  # noqa: E402


class FakeEmitter:
    def __init__(self):
        self.events = []

    def emit(self, name, data=None):
        self.events.append((name, data))


def ok(data=None):
    return {"ok": True, "data": data}


class WebAssetsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.game = Path(self._tmp.name) / "game"
        self.game.mkdir()
        self.ctx = SimpleNamespace(
            game=SimpleNamespace(is_running=False),
            game_path=lambda: self.game,
            config=SimpleNamespace(),
        )
        self.api = LauncherApi(self.ctx, FakeEmitter())

    def tearDown(self):
        self._tmp.cleanup()

    def touch(self, path: Path, text="x") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_state_reports_packs_active_selection_and_categories(self):
        self.assertTrue(self.api.assets_pack_create("Space")["ok"])
        self.assertTrue(self.api.assets_pack_set_active("Space")["ok"])
        result = self.api.assets_state()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertTrue(data["installed"])
        self.assertEqual(data["active"], "Space")
        self.assertIn("Sprites", data["categories"])
        self.assertEqual([p["name"] for p in data["packs"]], ["Space"])
        self.assertTrue(data["packs"][0]["active"])

    def test_create_add_files_and_detail(self):
        self.api.assets_pack_create("Space")
        sprite = self.touch(self.game / "src" / "sprite.png")
        added = self.api.assets_pack_add_files("Space", [str(sprite)])
        self.assertTrue(added["ok"])
        self.assertEqual(added["data"]["copied"], 1)

        detail = self.api.assets_pack_detail("Space")
        self.assertTrue(detail["ok"])
        self.assertEqual(detail["data"]["asset_count"], 1)
        self.assertEqual(detail["data"]["assets"]["Sprites"][0]["path"], "sprite.png")

    def test_running_game_blocks_pack_changes(self):
        self.ctx.game.is_running = True
        result = self.api.assets_pack_create("Space")
        self.assertFalse(result["ok"])
        self.assertIn("Close Among Us", result["error"])
        state = self.api.assets_state()
        self.assertTrue(state["data"]["game_running"])
        self.assertEqual(state["data"]["packs"], [])

    def test_save_info_updates_metadata(self):
        self.api.assets_pack_create("Space")
        result = self.api.assets_pack_save_info("Space", {
            "name": "Space Pack",
            "author": "Tester",
            "description": "New textures",
            "version": "2.0",
        })
        self.assertTrue(result["ok"])
        detail = self.api.assets_pack_detail("Space")
        self.assertEqual(detail["data"]["metadata"]["author"], "Tester")
        self.assertEqual(detail["data"]["metadata"]["version"], "2.0")

    def test_export_uses_native_save_dialog(self):
        self.api.assets_pack_create("Space")
        sprite = self.touch(self.game / "src" / "sprite.png")
        self.api.assets_pack_add_files("Space", [str(sprite)])
        dest = self.game.parent / "exports" / "space.zip"
        with patch.object(self.api, "pick_save", return_value=ok({"path": str(dest)})) as pick:
            result = self.api.assets_pack_export("Space")
        self.assertTrue(result["ok"])
        pick.assert_called_once_with("Space.zip")
        self.assertTrue(dest.is_file())
        with zipfile.ZipFile(dest) as zf:
            self.assertIn("Sprites/sprite.png", zf.namelist())

    def test_import_preview_and_import(self):
        archive = self.game.parent / "space.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("pack.json", json.dumps({
                "name": "Space", "author": "Tester", "version": "1.2",
            }))
            zf.writestr("Sprites/sprite.png", "x")
        preview = self.api.assets_pack_import_preview(str(archive))
        self.assertTrue(preview["ok"])
        self.assertEqual(preview["data"]["suggested"], "Space")
        imported = self.api.assets_pack_import(str(archive), "Imported")
        self.assertTrue(imported["ok"])
        self.assertTrue((self.game / "AUAS_Data" / "Imported" / "Sprites" / "sprite.png").is_file())

    def test_duplicate_rename_delete_and_deactivate(self):
        self.api.assets_pack_create("Space")
        self.api.assets_pack_set_active("Space")
        self.assertTrue(self.api.assets_pack_duplicate("Space", "Copy")["ok"])
        self.assertTrue(self.api.assets_pack_rename("Copy", "Renamed")["ok"])
        self.assertTrue(self.api.assets_pack_set_active("")["ok"])
        self.assertEqual(self.api.assets_state()["data"]["active"], "")
        self.assertTrue(self.api.assets_pack_delete("Renamed")["ok"])
        names = [p["name"] for p in self.api.assets_state()["data"]["packs"]]
        self.assertEqual(names, ["Space"])


if __name__ == "__main__":
    unittest.main()
