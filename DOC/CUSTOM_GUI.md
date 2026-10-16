# Custom GUIs

CrewLauncher lets you replace its interface with your own Python program.
A custom GUI can be **anything**: a tkinter window, a terminal application, a
web server, an overlay - the launcher never injects or requires a GUI
toolkit. Your file can only import packages that exist in the Python
running the launcher (see [Available packages](#available-packages)).

## Where custom GUIs live

| OS | Folder |
|----|--------|
| Linux | `~/.local/share/IsamAULauncher/guis/` (or `$XDG_DATA_HOME`) |
| Windows | `%APPDATA%\IsamAULauncher\guis\` |
| macOS | `~/Library/Application Support/IsamAULauncher/guis/` |

Every `*.py` file in that folder (except names starting with `_`) is listed
in **Settings > Interface**. You can open the folder from there, or press
**Create Custom GUI** to drop a ready-to-edit template into it.

## Contract

A custom GUI is a normal Python file with two things:

```python
GUI_NAME = "My GUI"          # optional, shown in the Settings list

def main(context):           # required
    ...
    # when main() returns, the launcher exits
```

## The context object

`main()` receives an `AppContext` with the launcher backends and helpers:

| Member | Description |
|--------|-------------|
| `context.config` | `Config` - settings dict, paths, `get_game_path()`, `get_version()`, `get_ui_mode()` ... |
| `context.network` | `NetworkManager` - `fetch_text(url)`, `get_releases()`, `download_file(...)` |
| `context.discord` | `DiscordRPC` - `connect()`, `update_status(state, details)`, `disconnect()` |
| `context.game` | `GameCore` - the raw game backend |
| `context.version()` | Installed game version (or `"Not Installed"`) |
| `context.game_path()` | `Path` of the install folder or `None` |
| `context.is_installed()` | `True` when `Among Us.exe` exists |
| `context.is_running` | `True` while the game process is alive |
| `context.install(progress=None, status=None)` | Download/update the game; returns `True` on success |
| `context.launch()` | Launch the game (uses your Wine/GPU setup on Linux); returns `True` on success |
| `context.stop()` | Stop the game |
| `context.poll()` | Refresh the running state (returns bool) |
| `context.guis_dir` | The `guis/` folder as a `Path` |
| `context.log(message)` | Write to the launcher log |

Notes:

- `progress(pct)` and `status(text, level)` callbacks may fire from worker
  threads. With tkinter, marshal back with `root.after(0, ...)`.
- `context.launch()` on Linux uses the Wine build and GPU configured in the
  builtin interface's Settings. Run the setup wizard there first.
- Discord RPC only connects if you call `context.discord.connect()`
  (or the user enabled it and you leave it alone).

## Selecting a custom GUI

- **Settings > Interface** > choose it from the dropdown, then press
  **Restart now** (or restart the launcher manually).
- Or from a terminal: `CrewLauncher --ui custom:my_gui`
  (the name is the file name without `.py`).

The selection is stored as `ui_mode` in
`<appdata>/IsamAULauncher/config.json` (e.g. `"custom:my_gui"`).

## New to Python? Start here

You don't need to install anything - the launcher can create a working
example for you and you edit it in any text editor (Notepad, gedit,
VS Code, ...). No GUI framework knowledge is needed to begin.

1. Open **Settings > Interface** and press **Create Custom GUI**.
2. Pick a starter template (the list shows `[GUI]` or `[CLI]`):
   - `[GUI]` **Quick Launch** - one window, one big Launch button. The best
     first file.
   - `[GUI]` **Status Board** - a small dashboard with numbered exercises:
     change colors, rename buttons, check for updates.
   - `[GUI]` **Launcher Controls** - install, launch and stop the game with
     a progress bar.
   - `[GUI]` **Modern Panel** - a rounded dark window made with
     customtkinter (included in official builds).
   - `[CLI]` **Terminal Menu** - the whole launcher as a text menu in your
     terminal. Uses no GUI toolkit at all, so it runs everywhere.
   - `[CLI]` **Auto-Update & Launch** - hands-free: report, update, launch.
3. Give it a name and press OK.
4. Press **Edit Custom GUI** - your file opens in your text editor.
   Change a piece of text, for example the `text="..."` of a label, and
   save the file.
5. Pick your GUI in the dropdown and press **Restart now**.

CLI templates must be started from a terminal
(`CrewLauncher --ui custom:my_gui`); from a menu launcher they print a
note and exit, because there is no terminal to type into.

Your GUI replaces the builtin interface until you switch back. If the
launcher opens the builtin interface instead, your file has an error:
open `<appdata>/IsamAULauncher/logs/launcher.log` and read the last
lines to see what Python complained about (usually a missing `"`, `:`,
or `(`). Fix it, save, and restart again.

Suggested progression:

1. Change texts and window titles.
2. Change a number and watch what happens (counter example).
3. Add a button that sets a label to a new value.
4. Show launcher data: `context.version()`, `context.is_installed()`.
5. Add install/launch buttons with `context.install()` / `context.launch()`.

## Available packages

Official CrewLauncher builds bundle a small runtime for custom GUIs:

- Python standard library (including `tkinter`)
- `customtkinter` (+ `darkdetect`, `packaging`)
- `PySide6`, `requests`, `pypresence`, `Pillow`

Anything else (`numpy`, `pygame`, ...) will not import inside the frozen
app. When you run from source, the packages installed in that Python are
available instead. The Settings dropdown marks a custom GUI with
`(unavailable: missing ...)` when its imports cannot be found, and the
launcher shows the real error in a dialog when it falls back to Qt.

## When things go wrong

- If the file is missing or crashes during startup, the launcher logs the
  traceback to `<appdata>/IsamAULauncher/logs/launcher.log`, shows a short
  error dialog, and opens the builtin Qt interface instead.
- Your GUI only counts as "finished" when `main()` returns; after that the
  launcher exits. If your interface has its own event loop (e.g.
  `root.mainloop()`), return only when the user closes it.

## Minimal example

```python
import tkinter as tk

GUI_NAME = "Mini Launcher"

def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)

    version = tk.Label(root, text=f"Version: {context.version()}")
    version.pack(padx=20, pady=8)

    def launch():
        if not context.launch():
            print("Launch failed - check Wine setup")

    tk.Button(root, text="Launch", command=launch).pack(pady=4)
    tk.Button(root, text="Quit", command=root.destroy).pack(pady=4)
    root.mainloop()
```

Full annotated templates are created by **Settings > Interface > Create
Custom GUI**, or see the originals in `src/launcher/resources/`:
`custom_gui_minimal.py` (Quick Launch), `custom_gui_playground.py`
(Status Board), `custom_gui_template.py` (Launcher Controls),
`custom_gui_ctk.py` (Modern Panel), `custom_cli_menu.py` (Terminal Menu)
and `custom_cli_autolaunch.py` (Auto-Update & Launch).
