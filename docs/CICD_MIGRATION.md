# CI/CD Migration: GitHub Actions -> CircleCI + AppVeyor

Linux/container builds (Ubuntu, Arch, Fedora) run on **CircleCI**.
Windows builds (PyInstaller + NSIS) run on **AppVeyor**.

Version tags look like `1.0`, `1.0-beta.2`, `0.7.3` (no `v` prefix). The
default branch is `crew`.

## Tag filtering

* **CircleCI** (`.circleci/config.yml`): every job uses

  ```yaml
  filters:
    tags:
      only: /^\d+\.\d+.*/
    branches:
      ignore: /.*/
  ```

  So only tags matching `1.0`, `1.0-beta.2`, `0.7.3`, … trigger a pipeline.
  No branch push (including `crew`) consumes minutes.

* **AppVeyor** (`appveyor.yml`): `skip_non_tags: true` makes it build tags only.

`v`-prefixed tags trigger nothing. If you ever want them, change the regex to
`/^v?\d+\.\d+.*/`.

## Manual triggers

* **CircleCI** — trigger a pipeline against a version tag, or pass the optional
  `version` parameter:

  ```bash
  curl -X POST \
    -H "Circle-Token: $CIRCLECI_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tag":"1.0"}' \
    https://circleci.com/api/v2/project/gh/isam-ahmed0/Isam-AULauncher/pipeline
  ```

  A pipeline triggered with `{"branch":"crew","parameters":{"version":"1.0"}}`
  works too, but note the workflow filters above only run jobs for tags, so a
  pure branch trigger with a `version` parameter will not start jobs. Prefer
  triggering against a tag.

* **AppVeyor** — Project -> **New build** -> select the tag. (`skip_non_tags`
  skips branch builds; a tag build always runs.)

## 1. CircleCI setup

1. Go to <https://app.circleci.com> -> **Projects** -> **Set Up Project** for
   `isam-ahmed0/Isam-AULauncher` and let it read `.circleci/config.yml`.
2. Project **Settings -> Environment Variables** -> add:
   * `GITHUB_TOKEN` — a **fine-grained** GitHub PAT scoped to
     `isam-ahmed0/Isam-AULauncher` with **Contents: Read and write**
     (classic token alternative: `public_repo`). Used by the `release` job to
     create the release and upload the Linux packages.
3. Optionally restrict builds to tags in **Advanced Settings** (already handled
   by the workflow filters).

Push a tag to verify:

```bash
git tag 1.0 && git push origin 1.0
```

## 2. AppVeyor setup

1. Go to <https://ci.appveyor.com> -> **New Project** -> select
   `isam-ahmed0/Isam-AULauncher`. AppVeyor auto-detects `appveyor.yml`.
2. Create a GitHub token (classic, scope `public_repo` / `repo`) and encrypt it:
   **Account menu -> Encrypt YAML** (or `appveyor encrypt <token>`).
3. Paste the encrypted value into `appveyor.yml`:

   ```yaml
   auth_token:
     secure: <paste encrypted value here>
   ```

4. (Optional) Set the token as a project environment variable instead and use
   `auth_token: $(GITHUB_TOKEN)`; the `secure:` approach above is the built-in
   one.

AppVeyor and CircleCI both attach assets to the **same** GitHub release for a
tag. `force_update: true` lets AppVeyor upload even if CircleCI created the
release first (and vice versa).

## What changed vs. GitHub Actions

| GitHub Actions | Replacement |
| --- | --- |
| `build-linux.yml` / `arch` | CircleCI `build-arch` (machine + `docker run archlinux`) |
| `build-linux.yml` / `ubuntu` | CircleCI `build-ubuntu` (`ubuntu:22.04`) |
| `build-linux.yml` / `fedora` | CircleCI `build-fedora` (machine + `docker run fedora`) |
| `build-windows.yml` | AppVeyor `build_script` |
| `release.yml` (`softprops/action-gh-release`) | CircleCI `release` job + AppVeyor GitHub deploy |

Version embedding still goes through `build/set_version.py`; packaging still goes
through `build/ci/ubuntu_build.sh`, `arch_build.sh`, `fedora_build.sh`,
`build/package_all_zip.py`, and the three `installer/*.nsi` files with
`/DROOT=`, `/DVERSION=`, `/DFILE_VERSION=`.

## Notes

* The old `.github/workflows/*` files are left in place. If the repo is still
  connected to GitHub Actions, tag pushes will build on **both** systems —
  disable Actions (repo Settings -> Actions) to stop that.
* `.circleci-draft/config.yml` is superseded by `.circleci/config.yml` and can
  be deleted.
* The Ubuntu job runs on the official `python:3.11` image (built with
  `--enable-shared`, so PyInstaller always finds `libpython`; it also ships git,
  so no checkout bootstrap is needed). A bare `ubuntu:22.04` image lacks the
  Python shared library and fails with
  `Python shared library ('libpython3.10.so.1.0') was not found`.
* Python on Windows comes from the VS 2022 image (`C:\Python314-x64`), with a
  Chocolatey fallback if absent. NSIS 3.x is preinstalled; Chocolatey is only a
  fallback.
