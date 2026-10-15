# Wine setup for CrewLauncher

CrewLauncher uses Wine on Linux to run Among Us and to store the itch.io token
that Among Us reads. Signing in to itch.io requires Wine — if the `wine` command
isn't detected the login is blocked. The launcher does not install or modify
Wine, and it does not touch your Wine prefix configuration.

## Install Wine

Install Wine with your distribution's package manager. Pick the guide for your
distro from the official WineHQ downloads page:

- https://wiki.winehq.org/Download

After installing, confirm it works:

```sh
wine --version
```

The launcher also detects **Wine-Staging**, **Proton-GE**, and **Lutris runners**
(under `~/.local/share/lutris/runners/wine/*/bin/wine` and Steam compatibility
tools). You can select any of these in **Settings → Wine**, or browse for a
custom Wine binary.

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

## GPU selection

On first Linux run (and anytime in **Settings → Graphics**), pick the GPU the
game should use. The launcher injects the appropriate environment variables:

| GPU choice                | Environment variables injected |
|---------------------------|--------------------------------|
| System default (auto)     | *(none)* — system decides      |
| NVIDIA discrete           | `__NV_PRIME_RENDER_OFFLOAD=1`, `__GLX_VENDOR_LIBRARY_NAME=nvidia`, `__VK_LAYER_NV_optimus=NVIDIA_only`, `DRI_PRIME=1` |
| AMD / Intel discrete      | `DRI_PRIME=pci-...` (PCI id)   |

You can also pick "System default" to let the system decide (no env vars).

## Running Among Us

The launcher runs `wine "Among Us.exe"` directly with the chosen Wine build and
GPU variables. No Lutris is involved — the launcher handles GPU offload itself.
The game reads the itch.io token from the prefix above, so sign-in carries over.

If you prefer to set up the game yourself, install and launch it through Lutris
(or your preferred Wine tool) with your own settings — as long as the game runs
in the same prefix the launcher reads the token from, sign-in carries over.

## Desktop shortcut

**Create Shortcut** writes a freedesktop `.desktop` file with the selected GPU
env vars and Wine path baked in, so launching from the desktop uses the same
settings.

## Troubleshooting

- **`wine --version` fails** — Wine is not installed or not on your `PATH`.
- **Wrong prefix** — set `WINEPREFIX` before starting the launcher, or choose it
  in **Settings → Wine** (displayed for info). The itch.io sign-in saves the
  token into the prefix configured here.
- **Wrong GPU** — open Settings → Graphics, pick the correct GPU, re-launch.
- **Login doesn't start** — the callback port is 7890. If another app holds it
  (for example an old Itch Login Fixer instance), the launcher shows a warning;
  close that app and try again.
- **Logs** — `~/.local/share/IsamAULauncher/logs/launcher.log`.