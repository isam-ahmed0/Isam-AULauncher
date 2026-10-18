# Archive

Historical code kept for reference only. **Nothing in this folder is imported,
built, packaged or shipped.** The build scripts, installers and CI only look at
`src/`, `release/`, `DOC/`, `ux/` and the repository root.

Everything here is still available in the Git history as well.

| Item | What it was | Why it is archived |
|------|-------------|--------------------|
| `gui_qt-legacy/` | The previous PySide6 interface (pre-redesign) | Replaced by `src/launcher/gui_qt/`; nothing imports it |
| `gui_ctk/` | CustomTkinter interface prototype (+ `main_ctk.py` entry) | Never finished; `src/launcher/main.py` already maps `--ctk` to the Qt UI. Imports are relative to `src/launcher/`, so it does not run from here |
| `dummy/` | Layout sketch (`sidebar-and-game.py`) used while designing the UI | Design scratch file |
| `circleci-draft/` | Older CircleCI draft config | Superseded by `.circleci/config.yml` |
| `setup-useless.sh` | Early draft of `ux/setup.sh` | Superseded by `ux/setup.sh` |
