# AGENTS.md

CrewLauncher: Python 3.10+ desktop launcher for the free itch.io Among Us on
Windows/Linux. See `docs/ARCHITECTURE.md` for the full module map and
`docs/DEVELOPMENT.md` for the build/release process.

## Layout

- `src/launcher/` — main app. `main.py` selects the UI (`gui_qt/` Qt,
  `gui_tk/` Tk Lite, `ui_registry.py` custom GUIs). Everything else in the
  folder is the shared backend.
- `src/fixer/`, `src/bootstrapper/` — companion executables.
- `DOC/` — user docs, bundled into builds and fetched via raw GitHub URLs.
- `docs/` — developer docs, screenshots, plans.
- `release/` — assets staged for the update hosting repo and bundled into
  builds (`bepmods.zip`, `7z.exe`, version/news metadata).
- `build/`, `installer/`, `ux/` — PyInstaller/NSIS/packaging scripts and the
  Linux curl installer.
- `archive/` — historical code, never imported or built.

## Commands

```bash
python src/launcher/main.py --version   # entry point smoke test
ruff check src/launcher                 # lint (config in ruff.toml)
python -m compileall -q src/launcher    # syntax check
bash build/build_launcher_linux.sh      # Linux build
build\build_launcher.bat                # Windows build
```

No automated test suite exists; verify changes by running the app
(`--ui qt` and/or `--ui tk`) and exercising the affected screen.

## Rules

- The backend must never import PySide6 or tkinter; import GUI toolkits lazily
  inside functions so Lite and custom GUIs stay lightweight.
- Do not move/rename `DOC/`, `isam-client.zip`, or paths inside `release/` —
  builds, raw URLs and runtime downloads depend on them.
- Move superseded code to `archive/` instead of deleting it; add an entry to
  `archive/README.md`.
- Never commit build outputs, `__pycache__`, session dumps or new binaries.
- Keep `LAUNCHER_VERSION` (`src/launcher/config.py`) in sync with
  `release/LauncherVersion.txt`.
