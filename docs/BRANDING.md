# Isam AULauncher — Branding Guide

## Names

| Context            | Use                                  |
|--------------------|--------------------------------------|
| Product name       | **Isam AULauncher**                  |
| Short brand        | **ISAM AU** (sidebar title, hero)    |
| Creator credit     | **Isam**                             |
| Version            | `0.1` (fork baseline)                |

## Visual identity

- Dark theme: charcoal `#0e1116` / `#151a23` / `#1d2430`
- Signature gradient: **cyan `#00d4ff` → violet `#7c5cff`**
- Success `#2dd98a` · Info `#4f8dff` · Danger `#ff5470` · Accent `#a45cff` · Warm `#ffaf3d`
- Text `#eef1f8` · Muted `#8b93a7`
- Font: **Segoe UI** (Windows system font)

## Where branding lives

- `src/launcher/main.py` — `APP_NAME`, `BRAND_SHORT`, `MAKER`, `LAUNCHER_VERSION`
- Sidebar title + nav, hero banners, About dialog, Discord RPC text
- Console start/exit messages
- `release/LauncherVersion.txt` — launcher version served to the updater
- `release/Patches.xml` — news entries ("Isam AULauncher Update")
- `scripts/make_icon.py` — generates the Isam icon

## Versioning

`LAUNCHER_VERSION` in `src/launcher/main.py` **must** match
`release/LauncherVersion.txt`. Bump both together.

## Do not rebrand

Backend URLs, game executable name (`Among Us.exe`), AUnlocker/mod metadata,
Discord client ID and repository paths must stay unchanged so updates and
downloads keep working.