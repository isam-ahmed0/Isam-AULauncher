# Isam AULauncher

A clean, modern launcher for Among Us — maintained by **Isam**.

This is a rebranded fork of the original "Shadow Slime" Among Us launcher.
All download/update endpoints and game logic are unchanged; the launcher now
carries the **Isam AULauncher** identity with a fresh, sleek interface.

## Structure

```
├── src/
│   ├── launcher/       main.py         - the Isam AULauncher GUI (Tkinter)
│   │                   resources/icon.ico
│   ├── bootstrapper/   bootstrapper.py - console updater
│   │                   launcher.json, AppDetail.json
│   └── fixer/          Itch_Login_Fixer.py + assets
├── release/            hosting/distribution layout (mirrors the hosting repo root)
├── scripts/            make_icon.py, sync_release.py
├── installer/          IsamAULauncher.nsi - NSIS installer script
├── build/              PyInstaller + NSIS build scripts, requirements.txt
└── scratch/            staging zips (gitignored)
```

## Branding

See [docs/BRANDING.md](docs/BRANDING.md) for the naming rules.

- Product name: **Isam AULauncher**
- Short brand: **ISAM AU**
- Made by: **Isam**

## Build (Windows)

```bat
pip install -r build\requirements.txt
build\build_launcher.bat        :: IsamAULauncher.exe
build\build_bootstrapper.bat    :: IsamAULauncherBootstrapper.exe
build\build_fixer.bat           :: Itch_Login_Fixer.exe
```

Outputs land in `dist/`.

## Build the installer (NSIS)

Install the NSIS Unicode compiler from https://nsis.sourceforge.io/Download,
then:

```bat
build\build_installer.bat
```

This builds `IsamAULauncher.exe` + `Itch_Login_Fixer.exe` and compiles
`dist\IsamAULauncher-Setup-0.1.exe`. The installer is per-user (no admin
needed), installs to `%LOCALAPPDATA%\Programs\Isam AULauncher`, and offers
component selection (Itch Login Fixer, support tools, desktop shortcut) plus
Start Menu shortcuts and a proper uninstaller.

Edit `installer\IsamAULauncher.nsi` for details (version, files, sections),
or override the version at compile time:

```bat
makensis /DVERSION=0.1 installer\IsamAULauncher.nsi
```

## Regenerate the icon

```bash
python scripts/make_icon.py
```

## Keeping the hosting repo in sync

The launcher pulls release data from the root of the hosting repo. After
editing files in `release/`:

```bash
python scripts/sync_release.py            # commit + push to 'hosting' remote
python scripts/sync_release.py --dry-run  # preview only
```

## Credits / upstream

Forked from `jogamerforgames2021/AmongUsLauncherNew` &
`jogamerforgames2021/BootstrapperTEST`. All upstream download endpoints,
Discord invite and YouTube links remain in place.