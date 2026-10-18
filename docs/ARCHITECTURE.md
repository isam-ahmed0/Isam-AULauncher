# Architecture

CrewLauncher is a Python 3 desktop app. One **toolkit-free backend** does all
the real work (downloads, game process, config), and two front-ends sit on top
of it: a full Qt interface and a lightweight Tk "Lite" interface. Users can also
supply their own interface as a plain Python file (see
[../DOC/CUSTOM_GUI.md](../DOC/CUSTOM_GUI.md)).

```text
src/launcher/main.py            entry point + interface selection
    |
    +-- main_qt.py              Qt front-end   -> gui_qt/  (PySide6)
    +-- main_lite.py            Lite front-end -> gui_tk/  (tkinter/ttk)
    +-- ui_registry.py          custom:<name>  -> user's file in <appdata>/guis/
    |
    +---------------- shared backend (no GUI imports ever) ----------------+
    |  config.py         settings, per-user paths, URLs, branding          |
    |  game_core.py      install / update / launch / stop the game         |
    |  network.py        HTTP helpers, downloads, Discord RPC              |
    |  platform_utils.py OS paths, Wine prefix, Lutris/Steam lookups       |
    |  graphics.py       GPU selection, Wine binary resolution (Linux)     |
    |  file_manager.py   zip extraction, verify, shortcuts                 |
    |  mod_inspector.py  BepInEx DLL scanning (dupes/deps/metadata)        |
    |  itch_oauth.py     itch.io OAuth + EOS token flow                    |
    |  single_instance.py / app_restart.py / qt_platform.py                |
    +----------------------------------------------------------------------+
```

## Entry chain

1. `main.py` parses `--ui qt|tk|custom:<name>`, acquires the single-instance
   lock, resolves the mode via `ui_registry.resolve_mode()` and dispatches.
2. `main_qt.py` prepares the Qt platform (`qt_platform.py` picks X11/Wayland
   before PySide6 is imported), shows the splash and login gate, then runs
   `gui_qt.window.LauncherApp`.
3. `main_lite.py` runs `gui_tk.app.LauncherLiteApp`.
4. Custom GUIs are loaded by `ui_registry.run_custom_gui()` and receive an
   `AppContext` (config + network + game core). They never import the built-in
   GUIs.

If Qt cannot start on Linux, `main.py` transparently falls back to Lite.

## Backend modules (`src/launcher/`)

| Module | Responsibility |
|--------|----------------|
| `config.py` | `Config` class (settings JSON, game path, version, profiles), all service URLs, `APP_NAME` / `LAUNCHER_VERSION` branding |
| `game_core.py` | `GameCore`: download/update/install/launch/stop, BepInEx + `isam-client` setup. Reports through callbacks only (`on_status`, `on_progress`, `on_started`, `on_stopped`) |
| `network.py` | `NetworkManager` (sessions, retries, progress, text/JSON fetch), `DiscordRPC` |
| `platform_utils.py` | Cross-platform data dirs, Wine prefix discovery, Lutris/Steam/desktop integration helpers |
| `graphics.py` | `lspci` GPU detection, `DRI_PRIME`/`__NV_PRIME_RENDER_OFFLOAD` env, Wine binary lookup |
| `file_manager.py` | Extract zips with progress, file verification helpers |
| `mod_inspector.py` | Reads BepInEx plugin metadata; finds duplicates, missing deps, incompatibilities |
| `itch_oauth.py` | Full itch.io OAuth flow + EOS auth handoff (tools-free) |
| `itch_auth.py` | Qt adapter kept for compatibility (`gui_qt.login`, `window/itch_profile`) |
| `single_instance.py` | Cross-platform advisory lock in the app data dir |
| `app_restart.py` | Re-exec the launcher (used after UI/theme changes) |
| `qt_platform.py` | Chooses/persists the Qt display backend, distro hints for missing libs |
| `ui_registry.py` | Builtin GUI list, custom GUI discovery/loading, `AppContext` |

**Rule:** nothing under the backend may import PySide6 or tkinter, so Lite and
custom GUIs stay lightweight. GUI imports are always inside functions.

## Qt interface (`src/launcher/gui_qt/`)

- `window/main.py` — `LauncherApp`, the main window. Pages are built in
  `_build_*` methods; behavior comes from mixins:
  `window/game_actions.py`, `window/mod_manager.py`, `window/region_editor.py`,
  `window/itch_profile.py`, `window/updater.py`.
- `theme.py` + `themes/*.py` — palettes and the generated QSS.
- `splash.py` / `video_splash.py` — static and video splash screens.
- `login.py` — itch.io login window.
- `dialogs.py` — Settings page, About page, help dialogs.
- `assets_manager/` — asset-pack page (`tab.py`), pack files/manager
  (`manager.py`), pack metadata (`pack_info.py`), models and the app mixin.
- Feature widgets: `mod_details.py`, `mod_warnings.py`, `profiles.py`,
  `regions.py`, `version_picker.py`, `setup_wizard.py`, `theme_maker.py`,
  `widgets.py`, `icons.py`, `worker.py` (thread → signal bridge),
  `zipextract.py`, `game.py` (Qt signal facade over `GameCore`).

## Tk interface (`src/launcher/gui_tk/`)

- `app.py` — `LauncherLiteApp` (single window: install/play/uninstall,
  settings, Discord RPC).
- `login.py`, `setup_wizard.py`, `settings.py`, `theme.py`, `util.py`.

## Other executables

| Folder | Executable | Purpose |
|--------|-----------|---------|
| `src/fixer/` | `Itch_Login_Fixer.py` | Standalone tool that logs into itch.io and writes the token the launcher reads |
| `src/bootstrapper/` | `bootstrapper.py` | Legacy console downloader kept for old installs |

## Per-user data

Created by `config.config_data_dir()` (`%APPDATA%\IsamAULauncher`,
`~/.local/share/IsamAULauncher`, `~/Library/Application Support/IsamAULauncher`):

```text
config.json        settings
current_version.txt / game_path.txt
Profiles/          launcher profiles
guis/              user custom GUIs (see DOC/CUSTOM_GUI.md)
cache/             downloads
logs/launcher.log  log file
```

## Assets and release pipeline

- `DOC/` is bundled into the build and also fetched from raw GitHub URLs, so
  its path must not change.
- `release/` mirrors files served by the update hosting repo (see
  `scripts/sync_release.py`); `bepmods.zip` and `7z.exe` are also inputs to
  builds and installers.
- `isam-client.zip` in the repo root is downloaded at runtime by
  `game_core.py`; do not move it.
- `archive/` contains historical code that is never imported or built.
