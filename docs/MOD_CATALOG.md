# Mod Catalog

The **Mod Browser** (Qt, page 8) lets users install BepInEx mods from a remote
catalog instead of hunting for DLLs on Discord. The catalog is a single JSON
file plus one downloadable archive per mod, hosted in a GitHub repository you
control. The launcher never executes code from the catalog itself — it only
downloads DLL files into the active mod profile.

> The repository URL is `MOD_CATALOG_URL` in `src/launcher/config.py`. Set the
> environment variable `ISAM_MOD_CATALOG_URL` to point the launcher at a local
> or test catalog without editing code.

## Repository layout

```text
AU-Mod-Catalog/
├── catalog.json                 # the manifest described below
└── mods/
    ├── cool-mod-1.2.0.zip
    └── speed-changer-3.0.zip
```

`catalog.json` is served with a raw GitHub URL, and each `download_url` points
to a raw archive URL in the same repository (or a GitHub release asset). Raw
GitHub URLs must be committed to the default branch; release assets must be
attached to a published release.

## Manifest format

```json
{
  "updated_at": "2026-11-22",
  "mods": [
    {
      "id": "com.example.cool-mod",
      "name": "Cool Mod",
      "version": "1.2.0",
      "author": "Someone",
      "category": "Gameplay",
      "description": "Short description shown in the Mod Browser.",
      "download_url": "https://raw.githubusercontent.com/<owner>/<repo>/main/mods/cool-mod-1.2.0.zip",
      "sha256": "0123456789abcdef...",
      "size": 24576,
      "dependencies": ["com.example.lib"],
      "incompatibilities": [],
      "game_version": "2020.11.23s"
    }
  ]
}
```

### Fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable unique identifier (reverse-DNS style). Never change it between versions. |
| `name` | yes | Display name. |
| `version` | no | Compared with the installed version using `packaging.Version`; falls back to string comparison. |
| `author`, `category`, `description` | no | Display only. `category` populates the filter combo. |
| `download_url` | yes | `.zip` or a direct `.dll` URL. |
| `sha256` | no | Strongly recommended; the install is rejected if the hash does not match. |
| `size` | no | Bytes; informational. |
| `dependencies`, `incompatibilities` | no | Lists of mod ids; shown in the detail pane and checked after install by `mod_inspector.py`. |
| `game_version` | no | Informational note about game compatibility. |

Malformed entries (missing `id`/`name`/`download_url`, duplicate ids, invalid
`sha256`) make the whole catalog fail validation; the launcher then falls back
to its last cached copy and reports the error in the Mod Browser status bar.

## Publishing a mod update

1. Build a `.zip` containing the plugin `.dll` files (a `BepInEx/plugins/`
   prefix is fine — paths are flattened to their basename).
2. Compute the hash: `sha256sum cool-mod-1.2.0.zip`.
3. Add a new entry: keep `id` unchanged, bump `version`, point `download_url`
   at the new archive, and update `sha256`/`size`.
4. Commit and push. Users see an "Update available" badge and a one-time notice
   on launcher startup.

Because the download cache is keyed by file name, give each version a distinct
file name (`cool-mod-1.2.0.zip`, `cool-mod-1.3.0.zip`) so a new version never
reuses stale resume segments.

## Install layout and safety

- Catalog mods are installed into `<appdata>/IsamAULauncher/Profiles/<profile>/`.
  Profiles are junctioned into `BepInEx/plugins`, so enabling a profile is what
  makes the mods visible to the game.
- Each profile has a `mods.json` recording installed catalog ids/versions and
  the user's enable/disable and order preferences. Manually added DLLs still
  work and are left alone.
- Downloads are verified against `sha256` before installation. Archive members
  with `..`, absolute paths, or drive letters are rejected; only `.dll` files
  are extracted, flattened to a safe basename.
- Installing, updating and removing require the game to be closed.

## Caching

The catalog is cached at `<appdata>/IsamAULauncher/cache/mods/catalog.json`
with a one-hour TTL (`MOD_CATALOG_TTL`). If the network is unavailable, the
cached copy is used and the Mod Browser shows a "cached" indicator. Pressing
**Refresh Catalog** forces a fresh fetch.
