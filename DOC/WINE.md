# Wine setup for CrewLauncher

CrewLauncher uses Wine on Linux **only** to run Among Us (directly or via
Lutris) and to store the itch.io token that Among Us reads. Signing in to
itch.io requires Wine on Linux — if the `wine` command isn't detected the login
is blocked, with a **"I have Wine — Continue anyway"** button for cases where
Wine exists but wasn't auto-detected. The launcher does not install or modify
Wine, and it does not touch your Wine prefix configuration.

## Install Wine

Install Wine with your distribution's package manager. Pick the guide for your
distro from the official WineHQ downloads page:

- https://wiki.winehq.org/Download

After installing, confirm it works:

```sh
wine --version
```

The launcher looks for the `wine` command on your `PATH`. If it is missing you
will see a **"Wine Not Found"** popup.

## The global prefix

The launcher uses your existing global prefix:

- `$WINEPREFIX` if that environment variable is set, otherwise
- `~/.wine`

It never runs `wineboot`, `winetricks`, or any command that could change the
prefix. The only write it performs is the itch.io token file the game itself
uses (written by the built-in itch.io login flow):

```
<prefix>/drive_c/users/<user>/AppData/LocalLow/Innersloth/Among Us/itch
```

## Running Among Us

The launcher can add the game to **Lutris** for you (recommended) using the same
prefix, or launch it directly with `wine`. Both use the prefix above, so itch.io
sign-in carries over. See [LINUX.md](LINUX.md) for the launch options.

If you prefer to set up the game yourself, install and launch it through Lutris
(or your preferred Wine tool) with your own settings — as long as the game runs
in the same prefix the launcher reads the token from, sign-in carries over.

## Troubleshooting

- **`wine --version` fails** — Wine is not installed or not on your `PATH`.
- **Wrong prefix** — set `WINEPREFIX` before starting the launcher, choose it in
  **Settings → Linux**, or make sure your Lutris game uses the same prefix. The
  itch.io sign-in saves the token into the prefix configured here.
- **Login doesn't start** — the callback port is 7890. If another app holds it
  (for example an old Itch Login Fixer instance), the launcher shows a warning;
  close that app and try again.
