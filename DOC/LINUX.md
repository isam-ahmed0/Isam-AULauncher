# Isam AULauncher on Linux

The launcher now runs natively on Linux. Because Among Us and the Itch Login
Fixer are Windows programs, Linux support is **non-destructive**: the launcher
only reads and writes the itch.io token that the game already uses, and it runs
the Windows fixer through the **global Wine prefix** you already have.

> The launcher **never** creates, deletes or reconfigures your Wine prefix or
> your Lutris configuration. If you already tuned Wine for other games, nothing
> here will change that.

## Requirements

- A working **Wine** installation (the `wine` command on your `PATH`).
- Optionally **Lutris** to install and launch Among Us.

If Wine is not found, the launcher shows a popup and links you to
[WINE.md](WINE.md). It will **not** install Wine for you.

## How it works

1. You run Isam AULauncher natively on Linux.
2. Click **INSTALL** to download and extract Among Us into a folder (default
   `~/Games/Isam-AULauncher/Among-Us`). Installation itself is pure file I/O and
   needs no special setup.
3. When you click **Sign in with itch.io**, the launcher starts the Windows
   `Itch_Login_Fixer.exe` using your global `wine`. The fixer opens the itch.io
   login page and writes the token into your Wine prefix.
4. The launcher reads that token from
   `<prefix>/drive_c/users/<user>/AppData/LocalLow/Innersloth/Among Us/itch`.
5. When you click **LAUNCH**, the launcher starts the game through Lutris (see
   below). Among Us reads the same token file, so you are signed in.

The Wine prefix is `$WINEPREFIX` if set, otherwise `~/.wine`. You can override it
in **Settings → Linux → Wine prefix**.

Mod and asset profiles are switched with **symlinks** on Linux (Windows uses
directory junctions), so switching does not duplicate files. Removing a profile
link never deletes the profile's contents.

## Installing and launching the game

Installation runs inside the launcher (download + unzip). Launching uses
whichever method you choose in **Settings → Linux → Launch method**:

- **Ask every time** (default) — a popup lets you pick **Launch with Lutris**
  or **Launch with Wine** on each launch. Choose Lutris to control which GPU the
  game uses (Lutris → Configure → System options); Wine runs directly with your
  global prefix and may use a different GPU.
- **Always use Lutris** — launches through Lutris, adding the install first if
  needed.
- **Always use Wine** — runs the game directly with `wine`.

When you choose **Add to Lutris**, the launcher writes a small installer YAML to
its own cache and opens it with `lutris -i`. Lutris shows its normal install
confirmation — press **Install** and the game is added to your library using the
prefix above. The launcher then detects the new entry and launches it. Your
Lutris configuration is never edited directly.

Running directly with **Wine** is allowed but not recommended; the launcher
shows a warning first (disable it in Settings).

Multiple installs are supported: each Lutris entry gets a unique name, and you
switch between them with **Change Location** / **Locate Game**.

### Tools → Add to Lutris / Check Lutris

For an install that has files but no Lutris entry yet, use **Add to Lutris** in
the Tools page: it checks your library first and, if the game is missing, opens
Lutris so you can add it. **Check Lutris** verifies the current install and shows
the matching entry's name, numeric id and slug (or offers to add it). The main
page also shows a `Lutris:` status line, and **Settings → Game Info** lists the
same entry.

## Desktop shortcut

**Create Shortcut** writes a freedesktop `.desktop` launcher to
`~/.local/share/applications/isam-au.desktop` (and your Desktop folder if it
exists). It launches through Lutris when an entry exists, otherwise with Wine.

## Troubleshooting

- **"Wine Not Found"** — install Wine for your distribution and make sure the
  `wine` command works in a terminal, then try again.
- **Login times out** — finish the login in the fixer window that opened. The
  launcher waits for the token file to appear and then restarts automatically.
- **Token is not detected** — confirm your game runs in the same Wine prefix the
  launcher used (`$WINEPREFIX` or `~/.wine`).
- **"Lutris entry not detected"** — finish the Lutris install window, then click
  LAUNCH again.
