# Mod Catalog

The **Mod Browser** (Qt page 8, Web "Browse" page) lets users install BepInEx
mods from a remote catalog instead of hunting for DLLs on Discord. The catalog
is a single JSON file hosted in a GitHub repository you control. The launcher
never executes code from the catalog itself — it only downloads DLL files into
the active mod profile.

> The live catalog is `https://raw.githubusercontent.com/isam-ahmed0/au_mods/master/catalog.json`,
> configured as `MOD_CATALOG_URL` in `src/launcher/config.py`. Set the
> environment variable `ISAM_MOD_CATALOG_URL` to a URL **or a local file path**
> to test a catalog without editing code, e.g.
> `ISAM_MOD_CATALOG_URL=au_mods/catalog.json python src/launcher/main.py`.
>
> This is a plain raw-file GET, not a GitHub API call.

## Repository layout

```text
au_mods/                         # https://github.com/isam-ahmed0/au_mods
├── catalog.json                 # the manifest described below
└── README.md
```

`catalog.json` is served with a raw GitHub URL from the `master` branch. Each
`download_url` points at a release asset of the mod's own repository.

## Manifest format

```json
{
  "updated_at": "2026-11-27",
  "mods": [
    {
      "id": "com.example.cool-mod",
      "name": "Cool Mod",
      "author": "Someone",
      "category": "Gameplay",
      "description": "Short description shown in the Mod Browser.",
      "download_url": "https://github.com/<owner>/<repo>/releases/latest/download/CoolMod.zip",
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
| `id` | yes | Stable unique identifier (reverse-DNS style). Never change it. |
| `name` | yes | Display name. |
| `download_url` | yes | A `.zip` or direct `.dll` URL. Recommended: a GitHub `releases/latest/download/<asset>` URL. |
| `author`, `category`, `description` | no | Display only. `category` populates the filter combo. |
| `dependencies`, `incompatibilities` | no | Lists of mod ids; shown in the detail pane and checked after install by `mod_inspector.py`. |
| `game_version` | no | Informational note about game compatibility. |

There is intentionally **no `version`, `sha256` or `size`** field. Those change
with every release and would mean editing the catalog for each mod, every day.
Malformed entries (missing `id`/`name`/`download_url` or duplicate ids) make
the whole catalog fail validation; the Mod Browser reports the error in its
status bar.

## Publishing a mod update

1. Build a `.zip` containing the plugin `.dll` files (a `BepInEx/plugins/`
   prefix is fine — paths are flattened to their basename), or a single `.dll`.
2. Upload it to a **new GitHub release** in the mod's repository, keeping the
   **same asset filename** as before (e.g. `CoolMod.zip`).
3. Done. `.../releases/latest/download/CoolMod.zip` now serves the new file;
   the catalog entry does not change. Users press **Reinstall** in the Mod
   Browser (or *Reinstall Selected* on the Mods page) to fetch it.

If you rename the asset, the `releases/latest/download/<asset>` URL changes
too — in that case update `download_url` in `catalog.json` once.

## Install layout and safety

- Catalog mods are installed into `<appdata>/IsamAULauncher/Profiles/<profile>/`.
  Profiles are junctioned into `BepInEx/plugins`, so enabling a profile is what
  makes the mods visible to the game.
- Each profile has a `mods.json` recording installed catalog ids, filenames and
  enable/disable/order preferences. Old records that still contain a `version`
  key are harmless and ignored.
- Downloads are no longer checksum-verified; they come from HTTPS release
  assets. Archive members with `..`, absolute paths or drive letters are
  rejected, and only `.dll` files are extracted, flattened to a safe basename.
- Installing, reinstalling and removing require the game to be closed.

## Caching

There is **no caching**. Every catalog load performs a fresh network request
(with `Cache-Control: no-cache`), and every install re-downloads the file into
a temporary directory that is deleted afterwards. This is what makes a
`releases/latest` URL actually deliver the latest release. GitHub's CDN may
still serve a briefly stale raw file; add a timestamp query parameter to
`MOD_CATALOG_URL` if you need to bypass that.
