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

* **AppVeyor** (`appveyor.yml`):

  ```yaml
  branches:
    only:
      - /^\d+\.\d+.*/     # applied to tag names too
  skip_non_tags: true
  ```

  `branches.only` filters **tag names as well as branches** in AppVeyor, so only
  version tags build (and then auto-deploy). Regular commits, including pushes
  to `crew`, start no Windows build.

`v`-prefixed tags trigger nothing. If you ever want them, change the regex to
`/^v?\d+\.\d+.*/`.

> **Config is read from the built ref's commit.** CircleCI and AppVeyor both
> compile the config from the commit that the triggering tag/branch points at.
> Editing the file locally does nothing until it is committed + pushed **and**
> the pipeline/build runs from a ref containing it. For an existing tag that
> predates a fix, move/recreate the tag on the new commit.

## Manual triggers

* **CircleCI** — the `manual` workflow is gated on the `build_manually` boolean
  parameter (default `false`), so pushes to `crew` never run it. Trigger it from
  the web UI (**Trigger Pipeline** -> add parameters) or the API:

  ```bash
  curl -X POST \
    -H "Circle-Token: $CIRCLECI_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"branch":"crew","parameters":{"build_manually":true,"version":"1.0-beta.4"}}' \
    https://circleci.com/api/v2/project/gh/isam-ahmed0/Isam-AULauncher/pipeline
  ```

  `version` is optional (blank falls back to `src/launcher/config.py`). Because
  the pipeline runs on `crew`, it uses the current branch HEAD config.

  You can also trigger against a tag with `{"tag":"1.0"}`; that runs the
  automatic `build-and-release` workflow.

* **AppVeyor** — Project -> **New build** -> select the tag.

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
5. On the AppVeyor project **General** tab, confirm **"Do not build tags" is
   unchecked** and that the project uses `appveyor.yml` from the repository.
   Otherwise tag builds (and therefore releases) never start.

AppVeyor and CircleCI both attach assets to the **same** GitHub release for a
tag. `force_update: true` lets AppVeyor upload even if CircleCI created the
release first (and vice versa).

## What changed vs. GitHub Actions

| GitHub Actions | Replacement |
| --- | --- |
| `build-linux.yml` / `arch` | CircleCI `build-arch` (machine + `docker run archlinux`) |
| `build-linux.yml` / `ubuntu` | CircleCI `build-ubuntu` (`python:3.11`) |
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
