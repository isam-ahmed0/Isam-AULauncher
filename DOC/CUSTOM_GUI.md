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

Custom GUIs can be organized in two ways:

**Directory-based (recommended):**
```
guis/
  my_gui/
    main.py          # entry point (required)
    resources/       # optional: images, extra modules, etc.
    __init__.py      # optional: makes it a proper Python package
```

**Legacy single-file:**
```
guis/
  my_gui.py          # entry point
```

Every `main.py` in a subdirectory of `guis/` (except names starting with `_`) and every `*.py` file directly in `guis/` is listed in **Settings > Interface**. You can open the folder from there, or press **Create Custom GUI** to drop a ready-to-edit template into it.

Directory-based GUIs take precedence over legacy single-file GUIs with the same name.

## Contract

A custom GUI is a normal Python file with two things:

```python
GUI_NAME = "My GUI"          # optional, shown in the Settings list

def main(context):           # required
    ...
    # when main() returns, the launcher exits
```

## The context object

`main()` receives an `AppContext` with the launcher backends and helpers. The API is intentionally broad to let you build any kind of GUI/CLI:

| Member | Description |
|--------|-------------|
| `context.config` | `Config` - settings dict, paths, `get_game_path()`, `get_version()`, `get_ui_mode()` ... |
| `context.network` | `NetworkManager` - `fetch_text(url)`, `get_releases()`, `download_file(...)` |
| `context.discord` | `DiscordRPC` - `connect()`, `update_status(state, details)`, `disconnect()` |
| `context.game` | `GameCore` - the raw game backend |
| `context.profiles` | `ProfileManager` (if available) |
| `context.version()` / `context.get_version()` | Installed game version (or `"Not Installed"`) |
| `context.game_path()` / `context.get_game_path()` | `Path` of the install folder or `None` |
| `context.set_game_path(path)` | Set install path |
| `context.is_installed()` | `True` when `Among Us.exe` exists |
| `context.is_running` | `True` while the game process is alive |
| `context.pid` | Game process id |
| `context.install(progress=None, status=None, version=None)` | Download/update the game; returns `True` on success |
| `context.download_game(...)`, `context.update_game(...)` | Aliases for `install()` |
| `context.launch(profile=None, method=None)` / `context.launch_game(...)` | Launch the game (uses your Wine/GPU setup on Linux); returns `True` on success |
| `context.stop()` / `context.stop_game()` | Stop the game |
| `context.poll()` | Refresh the running state (returns bool) |
| `context.guis_dir`, `context.appdata_dir`, `context.profiles_dir`, `context.cache_dir` | Launcher data directories |
| `context.log(message)` | Write to the launcher log |
| `context.get_setting(key, default)` / `context.set_setting(key, value, save=True)` / `context.get_settings()` / `context.save_settings()` | Access launcher settings |
| `context.fetch_text(url)`, `context.download_file(url, path, cb)`, `context.get_releases()` | Network helpers |
| `context.list_profiles()`, `context.create_profile(name)`, `context.delete_profile(name)`, `context.rename_profile(old,new)`, `context.get_active_profile()`, `context.set_active_profile(name)`, `context.switch_profile(name)`, `context.get_profile_path(name=None)`, `context.import_mods(profile_name=None, dll_paths=[])`, `context.list_mods(profile_name=None)`, `context.remove_mod(profile_name=None, mod_path=None)` | Profile & mod management |
| `context.run_thread(target, *args, **kwargs)`, `context.run_async(fn, callback=None)` | Threading helpers |
| `context.extract_zip(zip_path, extract_to, cb)`, `context.delete(path)`, `context.format_size(b)`, `context.open_folder(path=None)` | File utilities |
| `context.show_message(title, msg)`, `context.show_error(title, msg)` | Simple dialogs |
| `context.itch_login(callback=None)`, `context.get_itch_profile(timeout=8.0)`, `context.get_itch_username(timeout=8.0)`, `context.get_itch_token()`, `context.save_itch_token(token)`, `context.clear_itch_token()` | itch.io auth/profile |
| `context.APP_NAME`, `context.LAUNCHER_VERSION`, `context.IS_WINDOWS`, `context.IS_LINUX`, `context.get_platform()` | App info/platform |
| `context.get_wine_prefix()`, `context.get_wine_binary()`, `context.get_gpu()`, `context.set_gpu(id)`, `context.set_wine_binary(path)`, `context.get_default_game_dir()` | Linux/Wine helpers |
| `context.check_update(current_version=None)`, `context.get_latest_version()`, `context.restart_launcher()`, `context.get_launcher_log_path()` | Updates/system |
| `context.launch_modded(...)`, `context.get_mod_status(...)`, `context.get_mod_count(...)`, `context.add_to_path(...)` | Extended game/mod helpers |

Notes:

- `progress(pct)` and `status(text, level)` callbacks may fire from worker
  threads. With tkinter, marshal back with `root.after(0, ...)`.
- `context.launch()` on Linux uses the Wine build and GPU configured in the
  builtin interface's Settings. Run the setup wizard there first.
- Discord RPC only connects if you call `context.discord.connect()`
  (or the user enabled it and you leave it alone).

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
  (the name is the directory name or file name without `.py`).

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
   This creates a folder `guis/your_name/` with `main.py` inside.
4. Press **Edit Custom GUI** - your `main.py` opens in your text editor.
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

Create `guis/mini_launcher/main.py`:

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
