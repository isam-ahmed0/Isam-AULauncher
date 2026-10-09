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
2. When you click **Sign in with itch.io**, the launcher starts the Windows
   `Itch_Login_Fixer.exe` using your global `wine`. The fixer opens the itch.io
   login page and writes the token into your Wine prefix.
3. The launcher reads that token from
   `<prefix>/drive_c/users/<user>/AppData/LocalLow/Innersloth/Among Us/itch`.
4. Among Us (installed and launched through Lutris) reads the same file, so you
   are signed in.

The global Wine prefix is `$WINEPREFIX` if set, otherwise `~/.wine`.

Mod and asset profiles are switched with **symlinks** on Linux (Windows uses
directory junctions), so switching does not duplicate files. Removing a profile
link never deletes the profile's contents.

## Installing and launching the game

Game installation and launching are handled by **Lutris**, not by this launcher,
so that your existing Wine settings stay untouched. Use the launcher for:

- itch.io sign-in (through the fixer),
- mod profiles and BepInEx mod management,
- region editing,
- extracting mod zips into a folder you choose.

Buttons that would install or launch the game on Linux show a short setup popup
with links back to this document and [WINE.md](WINE.md).

## Troubleshooting

- **"Wine Not Found"** — install Wine for your distribution and make sure the
  `wine` command works in a terminal, then try again.
- **Login times out** — finish the login in the fixer window that opened. The
  launcher waits for the token file to appear and then restarts automatically.
- **Token is not detected** — confirm your game runs in the same Wine prefix the
  launcher used (`$WINEPREFIX` or `~/.wine`).
