"""AssetsManagerMixin — adds the AUAS resource-pack page to LauncherApp."""
from .tab import AssetsManagerPage


class AssetsManagerMixin:
    def _build_assets_page(self) -> AssetsManagerPage:
        self.assets_page = AssetsManagerPage(
            game_path_getter=self.config.get_game_path,
            game_running_getter=self._assets_game_running,
        )
        return self.assets_page

    def _assets_game_running(self) -> bool:
        try:
            game = getattr(self, "game", None)
            return bool(game and game.is_running)
        except Exception:
            return False
