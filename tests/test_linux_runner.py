"""Tests for Linux Wine/Proton runner selection and the default prefix."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "launcher"))

import game_core  # noqa: E402
import graphics  # noqa: E402
from platform_utils import (  # noqa: E402
    compat_data_dir, proton_compat_dir, runner_env, steam_client_dir, wine_prefix,
)


class FakeConfig:
    def __init__(self, runner, prefix):
        self.runner = str(runner)
        self.prefix = Path(prefix)

    def get_wine_binary(self):
        return self.runner

    def get_wine_prefix(self):
        return self.prefix

    def get_gpu(self):
        return ""


class LinuxRunnerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.proton = self.root / "proton"
        self.proton.write_text("#!/bin/sh\n", encoding="utf-8")
        self.proton.chmod(0o755)
        self.wine = self.root / "bin" / "wine"
        self.wine.parent.mkdir()
        self.wine.write_text("#!/bin/sh\n", encoding="utf-8")
        self.wine.chmod(0o755)

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_prefix_is_proton_pfx(self):
        with patch.dict(os.environ, {"HOME": str(self.root)}, clear=True):
            self.assertEqual(wine_prefix(), self.root / ".amongus" / "pfx")
            self.assertEqual(compat_data_dir(), self.root / ".amongus")
            self.assertEqual(
                proton_compat_dir(wine_prefix()), self.root / ".amongus")

    def test_runner_classification_and_args(self):
        self.assertEqual(graphics.runner_kind(self.proton), "proton")
        self.assertEqual(graphics.runner_kind(self.wine), "wine")
        self.assertEqual(
            graphics.resolve_runner(str(self.proton)), str(self.proton.resolve()))
        self.assertEqual(
            graphics.resolve_runner(str(self.wine)), str(self.wine.resolve()))
        exe = "/games/Among Us/Among Us.exe"
        self.assertEqual(
            graphics.runner_args(str(self.proton), exe), ["run", exe])
        self.assertEqual(graphics.runner_args(str(self.wine), exe), [exe])

    def test_old_proton_wine_selection_resolves_to_proton(self):
        proton = self.root / "Steam" / "compatibilitytools.d" / "GE" / "proton"
        proton.parent.mkdir(parents=True)
        proton.write_text("#!/bin/sh\n", encoding="utf-8")
        proton.chmod(0o755)
        internal = proton.parent / "files" / "bin" / "wine"
        internal.parent.mkdir(parents=True)
        internal.write_text("#!/bin/sh\n", encoding="utf-8")
        internal.chmod(0o755)

        self.assertEqual(
            graphics.proton_script_for_wine(internal), str(proton))
        self.assertEqual(graphics.resolve_runner(str(internal)), str(proton))

    def test_config_migrates_old_proton_wine_selection(self):
        import json
        import config
        proton = self.root / "Steam" / "compatibilitytools.d" / "GE" / "proton"
        proton.parent.mkdir(parents=True)
        proton.write_text("#!/bin/sh\n", encoding="utf-8")
        proton.chmod(0o755)
        config_file = self.root / "config.json"
        config_file.write_text(
            json.dumps({"wine_binary": str(proton.parent / "files/bin/wine")}),
            encoding="utf-8")
        with patch("config.config_data_dir", return_value=self.root):
            cfg = config.Config()
        self.assertEqual(cfg.get_wine_binary(), str(proton))

    def test_proton_env_and_steam_root(self):
        root = self.root / "Steam"
        runner = root / "compatibilitytools.d" / "GE-Proton" / "proton"
        with patch.dict(os.environ, {"HOME": str(self.root)}, clear=True):
            env = runner_env(str(runner), self.root / ".amongus" / "pfx")
            self.assertEqual(env["WINEPREFIX"], str(self.root / ".amongus" / "pfx"))
            self.assertEqual(
                env["STEAM_COMPAT_DATA_PATH"], str(self.root / ".amongus"))
            self.assertEqual(
                env["STEAM_COMPAT_CLIENT_INSTALL_PATH"], str(root))
            self.assertEqual(steam_client_dir(str(runner)), root)

    def test_game_core_uses_proton_run(self):
        gp = self.root / "game"
        gp.mkdir()
        exe = gp / "Among Us.exe"
        exe.write_text("", encoding="utf-8")
        config = FakeConfig(self.proton, self.root / ".amongus" / "pfx")
        core = game_core.GameCore(config, None)
        with patch.dict(os.environ, {"HOME": str(self.root)}, clear=True):
            with patch.object(graphics, "resolve_runner", return_value=str(self.proton)):
                with patch("game_core.subprocess.Popen") as popen:
                    self.assertTrue(core.launch_wine(gp, exe))
        args, kwargs = popen.call_args
        self.assertEqual(args[0], [str(self.proton), "run", str(exe)])
        self.assertEqual(kwargs["cwd"], str(gp))
        self.assertEqual(
            kwargs["env"]["STEAM_COMPAT_DATA_PATH"], str(self.root / ".amongus"))


if __name__ == "__main__":
    unittest.main()
