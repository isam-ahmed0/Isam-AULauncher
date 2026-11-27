# Wine / Proton setup for CrewLauncher

CrewLauncher uses a Wine or Proton runner on Linux to run Among Us and to
store the itch.io token the game reads. Signing in requires a runner; the
launcher does not install or modify Wine, Steam or your existing prefixes.

## Runner choices

The **Settings → Wine / Proton** dropdown lists every detected runner:

- **Wine** — `wine`, `wine-staging`, Lutris, Bottles, Heroic and custom builds.
- **Proton** — the `proton` script from GE-Proton / Steam Proton compatibility
  tools, including:
  `~/.local/share/Steam/compatibilitytools.d/<name>/proton`.

When the dropdown is set to **Auto-detect**, a detected Proton script is
preferred, otherwise the first Wine binary is used. Select a specific entry to
override that choice.

For GE-Proton, pick the `proton` script itself, for example:

```
/home/isam/.local/share/Steam/compatibilitytools.d/GE-Proton11-11-x86_64/proton
```

CrewLauncher runs it as `proton run "Among Us.exe"` with Steam's compat
variables set. The `files/bin/wine` binary inside the same folder is still
listed as a plain Wine runner if you want to avoid Proton's Steam wrapper;
older configs that pointed at that internal binary are upgraded to the
`proton` script automatically.

## Install a runner

Install Wine with your distribution's package manager (see
https://wiki.winehq.org/Download), or keep a Proton/GE-Proton build installed
through Steam. Confirm plain Wine with:

```sh
wine --version
```

## The default prefix

The launcher's game, itch.io token, regions file and fixer all use one prefix:

- `$WINEPREFIX` if that environment variable is set, otherwise
- `~/.amongus/pfx`

`~/.amongus` is the Proton **compat data root**. Proton stores its real Wine
prefix in the `pfx` child, so the launcher reads the token from the same place:

```
<prefix>/drive_c/users/<user>/AppData/LocalLow/Innersloth/Among Us/itch
```

An advanced override is still possible by setting `wine_prefix` in
`config.json`. The prefix is read-only in the GUI. If you had an itch.io token
in the old `~/.wine` prefix it is **not copied**; sign in once in the new
prefix. For Proton, set `STEAM_COMPAT_DATA_PATH` before starting the launcher
if you want to use a different compat root; otherwise `~/.amongus` is used.

The launcher never runs `wineboot`, `winetricks` or any command that rebuilds
the prefix. The only write it performs is the itch.io token file above.

## GPU selection

On first Linux run (and anytime in **Settings → Graphics**), pick the GPU the
game should use. The launcher injects these environment variables:

| GPU choice                | Environment variables injected |
|---------------------------|--------------------------------|
| System default (auto)     | *(none)* — system decides      |
| NVIDIA discrete           | `__NV_PRIME_RENDER_OFFLOAD=1`, `__GLX_VENDOR_LIBRARY_NAME=nvidia`, `__VK_LAYER_NV_optimus=NVIDIA_only`, `DRI_PRIME=1` |
| AMD / Intel discrete      | `DRI_PRIME=pci-...` (PCI id)   |

## Running Among Us

The launcher runs either:

```sh
wine "Among Us.exe"
```

or, for a Proton runner:

```sh
STEAM_COMPAT_DATA_PATH=~/.amongus \
STEAM_COMPAT_CLIENT_INSTALL_PATH=<steam root> \
proton run "Among Us.exe"
```

with the selected GPU variables. No Lutris is involved. The game reads the
itch.io token from the prefix above, so sign-in carries over to later launches.

## Desktop shortcut

**Create Shortcut** writes a freedesktop `.desktop` file with the selected GPU
variables, runner path and Proton compat variables baked in, so launching from
the desktop uses the same settings.

## Troubleshooting

- **Runner not found** — install Wine or point the dropdown at a `proton`
  script.
- **Wrong prefix** — check `$WINEPREFIX`, the `wine_prefix` value in
  `config.json`, and (for Proton) `STEAM_COMPAT_DATA_PATH`. The prefix shown in
  Settings is the one used for the token.
- **Wrong GPU** — open Settings → Graphics, pick the correct GPU, re-launch.
- **Login doesn't start** — the callback port is 7890. If another app holds it,
  close that app and try again.
- **Logs** — `~/.local/share/IsamAULauncher/logs/launcher.log`.
