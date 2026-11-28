# Development

## Setup

```bash
git clone https://github.com/isam-ahmed0/Isam-AULauncher
cd Isam-AULauncher
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r src/launcher/requirements.txt
```

Optional for building/packaging: `pip install -r build/requirements.txt`.

The default Web interface needs Node.js 22.23.4+ and the built Astro assets:

```bash
cd web && npm ci && npm run build   # writes ../src/launcher/resources/web/
```

Assets are gitignored and built on demand; for live editing use `npm run dev`
in `web/` and launch the app with `--dev`.

## Running

```bash
python src/launcher/main.py                 # default Web interface
python src/launcher/main.py --ui web --dev  # Web interface + Astro dev server
python src/launcher/main.py --ui qt         # full Qt interface (unchanged)
python src/launcher/main.py --ui tk         # lightweight Lite interface
python src/launcher/main.py --ui custom:mygui
python src/launcher/main.py --no-splash     # skip Qt splash
python src/launcher/main.py --version
```

If Web assets or pywebview are unavailable, the launcher falls back to Qt; if
Qt cannot start on Linux, it falls back to Lite. The interface can also be
changed in **Settings > Interface** or via the `ui_mode` value in
`config.json`. On Linux pywebview uses WebKitGTK when `gi` is installed,
otherwise the Qt WebEngine backend (`qtpy` is in `requirements.txt`).

## Checks

The only automated tests so far cover the mod catalog backend in `tests/`;
use these before committing:

```bash
cd web && npx tsc --noEmit && npm run build  # web types + assets
cd ..
ruff check src/launcher                     # lint (config in ruff.toml)
python -m compileall -q src/launcher        # syntax check
python src/launcher/main.py --version       # entry point smoke test
python -m unittest discover -s tests -v     # mod catalog backend tests
```

Then run the app and exercise the changed screen in `--ui web` (and `--ui qt`
/ `--ui tk` when shared code changes). The web views are plain TypeScript
modules under `web/src/scripts/views/`; add a matching Astro component in
`web/src/components/views/` and register the view in `router.ts`.

## Building

| Target | Command | Output |
|--------|---------|--------|
| Linux launcher | `bash build/build_launcher_linux.sh` | `dist/linux/CrewLauncher/` |
| Linux packages | `bash build/build_packages_linux.sh` | `.deb` / `.rpm` / tarball |
| Windows launcher | `build\build_launcher.bat` | `dist\CrewLauncher\` |
| Windows Lite | `build\build_launcher_lite.bat` | `dist\CrewLauncher_Lite\` |
| Windows offline/installers | `build\build_offline.bat`, `build\build_installer.bat` | `dist\` + NSIS setup exe |
| Fixer | `build\build_fixer.bat` | `dist\Itch_Login_Fixer\` |
| cx_Freeze variant | `build\build_launcher_cx.bat` | `dist\CrewLauncher_cx\` |
| Installer only | `installer\CrewLauncher.nsi` via `build\just_*_installer.bat` | setup exe |

All launcher builds generate the Web assets before packaging. Linux builds call
`build/web_assets.sh`, which runs `npm ci && npm run build` and verifies the
gitignored `src/launcher/resources/web/index.html`. CircleCI installs a
supported Node.js in all three Linux jobs (Fedora uses NodeSource 24);
AppVeyor installs Node via Chocolatey; GitHub Actions uses
`actions/setup-node`.

Linux packages are **thin** (~25 MB): `build/build_launcher_linux.sh` stages
Python sources, `DOC/`, `bepmods.zip` and a symlink-safe launcher script; it
does not bundle PySide6, QtWebEngine, ICU or a Python runtime. The package
metadata declares those as system dependencies (Arch: `pyside6`,
`qt6-webengine`, `python-pywebview`, `python-qtpy`, ...; deb/rpm: `python3`,
`python3-venv`, `python3-tk`, ...). If they are missing at runtime, the
launcher builds a private venv from `src/launcher/requirements.txt` once.
Only Pillow is needed at build time (package icon generation). Windows builds
stay self-contained PyInstaller + NSIS (~79 MB installer) and use system
WebView2 for the Web UI.

End-user installers live in `ux/`: `ux/setup.sh` (Linux: packages, `--user`,
update, uninstall, `--selfbuild`), `ux/setup.ps1` and `ux/setup.bat`
(Windows: downloads the NSIS installer, update, uninstall, `is-installed`).

CI: Linux jobs run on CircleCI (`.circleci/config.yml`), Windows jobs on
AppVeyor (`appveyor.yml`); both only build version tags. CircleCI also has
manual `test_target` workflows that build packages without publishing. GitHub
Actions workflows in `.github/workflows/` are the older pipeline. See
[CICD_MIGRATION.md](CICD_MIGRATION.md) for details.

## Release process

1. Bump `LAUNCHER_VERSION` in `src/launcher/config.py` **and**
   `release/LauncherVersion.txt` (they must match — see
   [BRANDING.md](BRANDING.md)).
2. Commit, then tag with a bare version (`1.0`, `1.0-beta.7`; no `v` prefix).
3. Push the tag — CircleCI/AppVeyor build and upload release artifacts.
4. If `release/` staging changed, run `python scripts/sync_release.py` to push
   it to the update hosting remote. `--dry-run` shows what would change.

Do not move or rename `DOC/`, `isam-client.zip` or `release/` contents: builds,
raw-GitHub doc URLs and runtime downloads depend on those exact paths.

## News messages

The News page (Web sidebar / Qt sidebar / Lite News button) shows the remote announcement
served from `release/message.txt` on the `crew` branch of
`isam-ahmed0/Isam-AULauncher` (`MESSAGE_URL`; see `src/launcher/news.py`).
The game-files repo (`jogamerforgames2021/AmongUsLauncherNew`) is not used for
messages.

- Edit `release/message.txt` in Markdown — links `[text](url)` and images
  `![alt](https://.../img.png)` are supported (host images on GitHub raw).
- The file is a feed: separate posts with a `---` line and put the newest
  post first. Start each post with a dated heading, e.g.
  `## 2026-10-26 — Update 1.1` (the launcher shows posts in file order).
- The "new message" prompt previews the newest post; the News page shows all.
- Publish by pushing `release/message.txt` to `crew` (or edit it directly on
  GitHub in the `crew` branch). No release-hosting sync is involved.
- Users are notified only when the content changes. To force a re-notification
  for an unchanged file, change the marker on the first line:
  `<!-- id: some-new-id -->`.
- The launcher caches the last message, so the News page still works offline.

## Seasonal events

The launcher only reads `EVENTS_URL` in `src/launcher/config.py`, using the
same raw-GitHub hosting pattern as `message.txt`. The checked-in
`release/events.txt` is just a template: it has no active rows or hardcoded
event dates. Publish the real file to the hosting repo to start an event.

Each active row is `name: YYYY-MM-DD`, where the date is the last day the event
is active (inclusive):

```txt
# name: last active day
winter: YYYY-MM-DD
```

Only registered event names affect the UI (currently `winter`). Add new rows
to the hosted file as future events are implemented, and register their
theme/effects in `src/launcher/seasonal_events.py` plus
`web/src/scripts/theme.ts`.

While an event is active its theme becomes the default for everyone and its
effects turn on; the saved theme stays in config and returns when the event
ends. Outside that window the event preset, Winter card, event status, effects
and background switches are hidden **and inert**: a saved Winter theme paints
as Aurora, and saved `auto`/`on`/`off` choices never start snow, frost or the
backdrop. `--event none` suppresses them for that launch without erasing the
saved config; a normal launch restores it.

For local testing, `python src/launcher/main.py --ui web --event winter`
forces the event on regardless of the hosted file. `--event none` forces it
off. There is no local-file fallback; offline launches use the last successful
remote fetch cached in config.

## Custom GUIs

Starter templates live in `src/launcher/resources/custom_gui_*.py` and are
copied into the user's `guis/` folder from Settings. The contract is documented
in [../DOC/CUSTOM_GUI.md](../DOC/CUSTOM_GUI.md).

## Conventions

- Keep the backend (`src/launcher/*.py`, not `gui_*/`) free of PySide6 and
  tkinter imports; import GUI toolkits lazily inside functions.
- New Qt screens: a page in `gui_qt/` plus, if it has behavior, a mixin under
  `gui_qt/window/`.
- New release-served assets go in `release/`; new user docs in `DOC/`; new
  developer docs in `docs/`.
- Historical code goes to `archive/` (never imported, never built) instead of
  being deleted outright — see [../archive/README.md](../archive/README.md).
- Never commit build outputs, `__pycache__`, session dumps or large binaries
  beyond the tracked `release/` assets.
- Structure and dependencies are described in [ARCHITECTURE.md](ARCHITECTURE.md).
