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

## Running

```bash
python src/launcher/main.py                 # default Qt interface
python src/launcher/main.py --ui tk         # lightweight Lite interface
python src/launcher/main.py --ui custom:mygui
python src/launcher/main.py --no-splash     # skip splash
python src/launcher/main.py --version
```

If Qt cannot start on Linux, the launcher falls back to Lite automatically.
The interface can also be changed in **Settings > Interface** or via the
`ui_mode` value in `config.json`.

## Checks

There is no automated test suite yet; use these before committing:

```bash
ruff check src/launcher                     # lint (config in ruff.toml)
python -m compileall -q src/launcher        # syntax check
python src/launcher/main.py --version       # entry point smoke test
```

Then run the app and exercise the changed screen in both `--ui qt` and
`--ui tk` where applicable.

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

CI: Linux jobs run on CircleCI (`.circleci/config.yml`), Windows jobs on
AppVeyor (`appveyor.yml`); both only build version tags. GitHub Actions
workflows in `.github/workflows/` are the older pipeline. See
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

The News page (Qt sidebar / Lite News button) shows the remote announcement
served from `release/message.txt` at `MESSAGE_URL` (see `src/launcher/news.py`).

- Edit `release/message.txt` in Markdown — links `[text](url)` and images
  `![alt](https://.../img.png)` are supported (host images on GitHub raw).
- Publish with `python scripts/sync_release.py` (same as other release files).
- Users are notified only when the content changes. To force a re-notification
  for an unchanged file, change the marker on the first line:
  `<!-- id: some-new-id -->`.
- The launcher caches the last message, so the News page still works offline.

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
