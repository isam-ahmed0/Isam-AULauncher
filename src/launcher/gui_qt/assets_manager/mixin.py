"""AssetsManagerMixin — adds assets page to LauncherApp."""
from pathlib import Path
from typing import Optional

from .profile_manager import AUASProfileManager
from .tab import AssetsManagerTab


class AssetsManagerMixin:
    def _build_assets_page(self) -> AssetsManagerTab:
        gp = self.config.get_game_path()
        profiles_base = gp.parent / "AUAS_Profiles" if gp else Path.home() / "AUAS_Profiles"
        self.auas_profile_mgr = AUASProfileManager(profiles_base)
        self.assets_tab = AssetsManagerTab(
            self.auas_profile_mgr, self.config.get_game_path,
        )
        return self.assets_tab
