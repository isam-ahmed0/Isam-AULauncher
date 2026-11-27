"""Small, dependency-free checks for the mod catalog backend.

Run with:  python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

from mod_catalog import (  # noqa: E402
    CatalogError, ModCatalog, ModCatalogManager, install_archive,
    load_meta, save_meta, version_newer,
)


class _Network:
    def __init__(self, text=None, payload=None):
        self.text = text
        self.payload = payload
        self.fetch_calls = 0
        self.download_calls = []
        self.payloads = []

    def fetch_text(self, url, headers=None):
        self.fetch_calls += 1
        return self.text

    def download_file(self, url, output_path, progress_callback=None):
        if self.payload is None:
            return False
        self.download_calls.append(url)
        self.payloads.append(self.payload)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.payload)
        return True


def _zip_bytes(dll_name="CoolMod.dll"):
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(f"BepInEx/plugins/{dll_name}", b"dll payload")
    return buffer.getvalue()


class CatalogParsingTests(unittest.TestCase):
    def test_parses_valid_catalog(self):
        text = json.dumps({
            "mods": [{
                "id": "com.example.cool",
                "name": "Cool Mod",
                "author": "Someone",
                "download_url": "https://example.invalid/cool.zip",
                "dependencies": ["com.example.lib", ""],
            }]
        })
        catalog = ModCatalog.from_text(text)
        self.assertEqual(len(catalog.mods), 1)
        entry = catalog.mods[0]
        self.assertEqual(entry.name, "Cool Mod")
        self.assertEqual(entry.author, "Someone")
        self.assertEqual(entry.dependencies, ["com.example.lib"])
        self.assertEqual(catalog.by_id("com.example.cool"), entry)

    def test_rejects_duplicate_ids_and_missing_url(self):
        with self.assertRaises(CatalogError):
            ModCatalog.from_text(json.dumps({"mods": [
                {"id": "a", "name": "A", "download_url": "https://x/a.zip"},
                {"id": "a", "name": "B", "download_url": "https://x/b.zip"},
            ]}))
        with self.assertRaises(CatalogError):
            ModCatalog.from_text(json.dumps({"mods": [
                {"id": "a", "name": "A"},
            ]}))

    def test_release_metadata_is_ignored(self):
        """Old catalogs with version/sha/size still parse; the fields are dropped."""
        catalog = ModCatalog.from_text(json.dumps({"mods": [{
            "id": "m", "name": "M", "version": "1.0.0",
            "sha256": "0" * 64, "size": 1234,
            "download_url": "https://example.invalid/releases/latest/download/m.dll",
        }]}))
        entry = catalog.mods[0]
        self.assertFalse(hasattr(entry, "version"))
        self.assertFalse(hasattr(entry, "sha256"))
        self.assertFalse(hasattr(entry, "size"))

    def test_version_helper_for_game_versions(self):
        self.assertTrue(version_newer("1.2.0", "1.1.9"))
        self.assertFalse(version_newer("1.1.0", "1.1.0"))
        self.assertFalse(version_newer("", "1.0.0"))


class ArchiveTests(unittest.TestCase):
    def test_zip_slip_is_blocked_and_dlls_are_flattened(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "mod.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("BepInEx/plugins/Good.dll", b"ok")
                zf.writestr("../../evil.dll", b"bad")
            dest = root / "profile"
            names = install_archive(archive, dest)
            self.assertEqual(names, ["Good.dll"])
            self.assertTrue((dest / "Good.dll").is_file())
            self.assertFalse((root.parent / "evil.dll").exists())


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "profiles" / "P").mkdir(parents=True)
        (self.root / "cache").mkdir()
        self.cfg = SimpleNamespace(
            profiles_dir=self.root / "profiles",
            cache_dir=self.root / "cache",
        )
        self.entry_text = json.dumps({"mods": [{
            "id": "m", "name": "M",
            "download_url": "https://example.invalid/releases/latest/download/m.zip",
        }]})

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetch_always_hits_network_and_writes_no_cache(self):
        network = _Network(self.entry_text)
        manager = ModCatalogManager(self.cfg, network)
        first = manager.fetch()
        network.text = self.entry_text.replace('"name": "M"', '"name": "M2"')
        second = manager.fetch()
        self.assertEqual(network.fetch_calls, 2)
        self.assertEqual(first.mods[0].name, "M")
        self.assertEqual(second.mods[0].name, "M2")
        self.assertFalse((self.root / "cache" / "mods").exists())

    def test_status_from_manifest(self):
        profile = self.cfg.profiles_dir / "P"
        manager = ModCatalogManager(self.cfg, _Network(self.entry_text))
        catalog = manager.fetch()
        self.assertEqual(manager.status("P", catalog)["m"], "install")
        save_meta(profile, {"catalog": {
            "m": {"filename": "M.dll", "files": ["M.dll"], "installed_at": 1},
        }})
        self.assertEqual(manager.status("P", catalog)["m"], "installed")
        save_meta(profile, {"catalog": {
            "other": {"filename": "Other.dll", "files": ["Other.dll"]},
        }})
        self.assertEqual(manager.status("P", catalog)["other"], "unknown")

    def test_install_and_uninstall(self):
        network = _Network(self.entry_text, _zip_bytes())
        manager = ModCatalogManager(self.cfg, network)
        catalog = manager.fetch()
        ok, message = manager.install(catalog.mods[0], "P")
        self.assertTrue(ok, message)
        profile = self.cfg.profiles_dir / "P"
        self.assertTrue((profile / "CoolMod.dll").is_file())
        record = load_meta(profile)["catalog"]["m"]
        self.assertNotIn("version", record)
        self.assertEqual(len(network.download_calls), 1)
        ok, _ = manager.uninstall("m", "P")
        self.assertTrue(ok)
        self.assertFalse((profile / "CoolMod.dll").exists())

    def test_reinstall_redownloads_latest_asset(self):
        """A stable releases/latest URL is re-downloaded on every install."""
        network = _Network(self.entry_text, _zip_bytes("CoolMod.dll"))
        manager = ModCatalogManager(self.cfg, network)
        entry = manager.fetch().mods[0]
        self.assertTrue(manager.install(entry, "P")[0])

        network.payload = _zip_bytes("CoolModV2.dll")
        self.assertTrue(manager.install(entry, "P")[0])

        self.assertEqual(len(network.download_calls), 2)
        self.assertEqual(len(set(network.download_calls)), 1)
        profile = self.cfg.profiles_dir / "P"
        self.assertFalse((profile / "CoolMod.dll").exists())
        self.assertTrue((profile / "CoolModV2.dll").is_file())


if __name__ == "__main__":
    unittest.main()
