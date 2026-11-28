# CrewLauncher on Linux

The launcher runs natively on Linux, with the Itch Login Fixer's flow built
in (same OAuth client, same callback, same token file). Linux support is
**non-destructive**: the launcher only reads and writes the itch.io token that
the game already uses.

> The launcher **never** rebuilds, deletes or reconfigures your Wine prefix. If
> you already tuned Wine for other games, nothing here will change that.

## Requirements

- **Wine or Proton is required** on Linux. It is needed to run Among Us, and
  **itch.io** sign-in is gated on it: if no runner is detected, sign-in is
  blocked with a "Wine / Proton Not Found" popup.
- **No Lutris required.** The launcher launches the selected runner directly
  and injects the right GPU environment variables (PRIME / render-offload) so
  the game runs on the graphics card you choose.

The launcher shows a popup with [WINE.md](WINE.md) links if its detection of
Wine fails. It will **not** install Wine for you.

## First-run setup (GPU + Wine)

On first Linux launch, a setup wizard appears:

1. **GPU selection** — the launcher auto-detects your GPUs via `lspci`. Pick
   "System default" (auto), or a specific card (e.g. "NVIDIA RTX 4070 (discrete)",
   "AMD Radeon 780M (integrated)"). The launcher sets the right variables:
   - NVIDIA discrete: `__NV_PRIME_RENDER_OFFLOAD=1`,
     `__GLX_VENDOR_LIBRARY_NAME=nvidia`, `__VK_LAYER_NV_optimus=NVIDIA_only`,
     `DRI_PRIME=1`
   - AMD / Intel discrete: `DRI_PRIME=pci-...`
   - System default: no variables (let the system decide)

2. **Wine / Proton build** — auto-detects `wine`, `wine-staging`, Lutris
   runners, Proton-GE and Steam Proton `proton` scripts. Auto-detect prefers a
   Proton script; pick any entry to override it (e.g.
   `/home/you/.local/share/Steam/compatibilitytools.d/GE-Proton11-11-x86_64/proton`).
   Old selections of a Proton build's internal `files/bin/wine` are upgraded
   to its `proton` script automatically.

3. **Test** — optional "Test runner" button runs `wine --version` for Wine;
   Proton is verified by launching the game.

Settings are saved to `config.json` and are re-editable in **Settings → Graphics / Wine**.
Click **Re-run setup wizard** any time to change them.

## How it works

1. You run CrewLauncher natively on Linux.
2. Click **INSTALL** to download and extract Among Us into a folder (default
   `~/Games/Isam-AULauncher/Among-Us`). Installation itself is pure file I/O and
   needs no special setup.
3. When you click **Sign in with itch.io**, the launcher opens the itch.io login
   page in your browser and, once you authorize, stores the token into the Wine
   prefix — the same file the Itch Login Fixer wrote.
4. The launcher reads that token from
   `<prefix>/drive_c/users/<user>/AppData/LocalLow/Innersloth/Among Us/itch`.
5. When you click **LAUNCH**, the launcher runs `wine "Among Us.exe"` or
   `proton run "Among Us.exe"` with the selected GPU env vars. Among Us reads
   the same token file, so you are signed in.

The prefix is `$WINEPREFIX` if set, otherwise `~/.amongus/pfx`. `~/.amongus` is
the Proton compat-data root; Proton's real prefix is its `pfx` child. You can
override the prefix in `config.json` (shown read-only in Settings). An existing
token in the old `~/.wine` prefix is not copied — sign in once in the new
prefix.

Mod and asset profiles are switched with **symlinks** on Linux (Windows uses
directory junctions), so switching does not duplicate files. Removing a profile
link never deletes the profile's contents.

## Settings → Graphics

- **GPU** dropdown — list of detected GPUs with vendor/type tags. "System default"
  means no env vars are injected.
- **Re-run setup wizard** — reopens the full first-run flow.

## Settings → Wine / Proton

- **Runner** dropdown — auto-detected Wine binaries and Proton scripts;
  auto-detect prefers Proton.
- **Game / login prefix** — read-only display of the active prefix.

## Desktop shortcut

**Create Shortcut** writes a freedesktop `.desktop` launcher to
`~/.local/share/applications/isam-au.desktop` (and your Desktop folder if it
exists). The `Exec` line embeds the selected GPU env vars, runner path and
Proton compat variables so the shortcut launches with the same settings.

## Lutris (legacy)

Lutris code remains in the codebase for reference but is **no longer used** by
the launcher. If you previously added this install to Lutris, you can still
launch it manually from Lutris, but the launcher ignores Lutris entries.

## Installing on Linux

Build the launcher, then the installers:

```fish
source .venv/bin/activate.fish
pip install pillow                     # only needed to generate package icons
bash build/build_launcher_linux.sh     # -> dist/linux/CrewLauncher/ (thin, ~25 MB)
bash build/build_packages_linux.sh     # -> dist/packages/
```

Linux packages do not bundle PySide6/QtWebEngine. The package manager installs
them as dependencies; a portable `.run`/tarball install bootstraps a private
virtualenv from `requirements.txt` on first launch if they are missing.

`dist/packages/` contains:

- **`CrewLauncher-<ver>.run`** — universal self-extracting installer. Run it
  and it installs (no package manager needed):
  `./CrewLauncher-<ver>.run` (per-user, `~/.local`),
  `... --system` (`/opt`, needs root), or `... --uninstall`.
- **`isam-aulauncher-<ver>-1-x86_64.pkg.tar.zst`** — Arch/CachyOS/Manjaro:
  `sudo pacman -U isam-aulauncher-*.pkg.tar.zst`.
- **`isam-aulauncher_<ver>-1_amd64.deb`** — Debian/Ubuntu/Mint/Pop:
  `sudo apt install ./isam-aulauncher_*.deb`.
- **`isam-aulauncher-<ver>-1*.rpm`** — Fedora/RHEL/openSUSE:
  `sudo dnf install ./isam-aulauncher-*.rpm` (built only if `rpmbuild` is
  installed; `pacman -S rpm-tools`).

All installs place files under `/opt/isam-aulauncher` (or
`~/.local/share/IsamAULauncher` for the per-user `.run`), add an `isam-au`
command, a `Game` menu entry and an icon. Wine is an optional dependency
(the app detects it).

## Troubleshooting

- **"Wine / Proton Not Found"** — install Wine or select a `proton` script in
  Settings → Wine / Proton, then try again.
- **Login times out** — the login callback waits up to 5 minutes for your
  browser to return the token. Authorize the itch.io page and keep it open.
- **Token is not detected** — confirm your game runs in the same prefix the
  launcher used (`$WINEPREFIX` or `~/.amongus/pfx` for Proton).
- **Wrong GPU** — open Settings → Graphics, pick the correct GPU, re-launch.
- **Logs** — `~/.local/share/IsamAULauncher/logs/launcher.log`.