# CrewLauncher — Branding Guide

## Names

| Context            | Use                                  |
|--------------------|--------------------------------------|
| Product name       | **CrewLauncher**                     |
| Short brand        | **CREW AU** (sidebar title, hero)    |
| Creator credit     | **Isam**                             |
| Version            | `0.1` (fork baseline)                |

## Visual identity

- Dark theme: charcoal `#0e1116` / `#151a23` / `#1d2430`
- Signature gradient: **cyan `#00d4ff` → violet `#7c5cff`**
- Success `#2dd98a` · Info `#4f8dff` · Danger `#ff5470` · Accent `#a45cff` · Warm `#ffaf3d`
- Text `#eef1f8` · Muted `#8b93a7`
- Font: **Segoe UI** (Windows system font)

## Where branding lives

- `src/launcher/config.py` — `APP_NAME`, `BRAND_SHORT`, `MAKER`, `LAUNCHER_VERSION`
- Sidebar title + nav, hero banners, About dialog, Discord RPC text
- Console start/exit messages
- `release/LauncherVersion.txt` — launcher version served to the updater
- `release/Patches.xml` — news entries ("CrewLauncher Update")
- `scripts/make_icon.py` — generates the CrewLauncher icon

## Versioning

`LAUNCHER_VERSION` in `src/launcher/config.py` **must** match
`release/LauncherVersion.txt`. Bump both together.

## Do not rebrand

Upstream backend URLs (the `jogamerforgames2021/*` sources), game executable name
(`Among Us.exe`), AUnlocker/mod metadata, the Discord client ID and its
`isam_au` rich-presence image asset, the `isam-client.zip` payload, the Lutris
slug prefix (`among-us-isam`) and the per-user data directory names must stay
unchanged so updates, downloads and existing installs keep working. The project
repository itself lives at `https://github.com/icis-org/CrewLauncher`.