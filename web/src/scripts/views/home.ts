/* Home view: hero, main action, progress, status card, quick actions -------- */

import { api } from "../bridge";
import { store, updateGame } from "../store";
import { on } from "../events";
import { toast } from "../toast";
import { openModal } from "../modal";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`missing #${id}`);
  return el as T;
};

let versionsLoaded = false;

async function syncState(): Promise<void> {
  const res = await api<any>("game_state");
  if (res.ok && res.data) updateGame(res.data);
}

export function initHome(): void {
  $("main-action").addEventListener("click", onMainAction);
  $("versions-btn").addEventListener("click", showVersions);
  $("locate-btn").addEventListener("click", locateGame);
  $("btn-refresh").addEventListener("click", refreshState);

  for (const btn of document.querySelectorAll<HTMLButtonElement>("[data-action]")) {
    btn.addEventListener("click", () => runQuickAction(btn.dataset.action ?? ""));
  }

  $("update-banner-dismiss").addEventListener("click", () => {
    $("update-banner").classList.remove("show");
  });
  $("update-banner-action").addEventListener("click", async () => {
    const res = await api("game_install");
    if (!res.ok) toast({ title: "Install failed", message: res.error, level: "danger" });
  });

  $("home-image-btn").addEventListener("click", setHomeImage);
  $("home-note-btn").addEventListener("click", editHomeNote);
  $("home-clear-btn").addEventListener("click", clearHomeCard);

  spawnParticles();

  on("status", (data) => setStatusLine(data?.text ?? "", data?.level ?? "info"));
  on("progress", (data) => {
    if (data?.done) {
      setTimeout(hideProgress, 450);
      return;
    }
    renderProgress(data?.pct ?? 0);
  });
  on("game_state", () => render());
  on("update_check", (data) => {
    if (data?.needed && data?.latest) {
      const banner = $("update-banner");
      $("update-banner-text").textContent =
        `Game update available: v${data.latest}`;
      banner.classList.add("show");
    }
  });
  on("install_done", async (data) => {
    hideProgress();
    if (data?.ok) {
      toast({ title: "Install complete", message: `Among Us v${data.version ?? ""} is ready.`, level: "success" });
      $("update-banner").classList.remove("show");
    } else {
      toast({ title: "Install failed", message: "Check the log for details.", level: "danger" });
    }
    await syncState();
    render();
  });
  on("verify_result", (data) => showVerifyResult(data));
  on("versions_result", (data) => {
    versionsLoaded = true;
    renderVersions(data?.versions ?? [], data?.error);
  });
  on("folder_inspect", (data) => showFolderInspect(data));
  on("toast", (data) =>
    toast({
      title: data?.title ?? "Launcher",
      message: data?.message ?? "",
      level: data?.level ?? "info",
    }),
  );
  on("system", (data) => {
    store.system = data ?? store.system;
    const gpu = document.getElementById("sb-gpu");
    if (gpu) gpu.textContent = data?.gpu || "—";
  });

  render();
}

/* ------------------------------------------------------------- main flow */

async function onMainAction(): Promise<void> {
  const g = store.game;
  if (g.busy) {
    toast({ title: "Please wait", message: "Another action is still running.", level: "warning" });
    return;
  }
  if (g.running) {
    const res = await api("game_stop");
    if (!res.ok) toast({ title: "Stop failed", message: res.error, level: "danger" });
    return;
  }
  if (!g.installed || g.needs_install) {
    await installGame();
    return;
  }
  await launchGame();
}

async function installGame(version?: string): Promise<void> {
  if (store.game.path) {
    const res = await api("game_install", null, version ?? null);
    if (!res.ok) {
      toast({ title: "Install failed", message: res.error, level: "danger" });
      return;
    }
    showProgress(0, "Preparing download…");
    return;
  }
  // No folder yet — ask where to put the game.
  const picked = await api<{ path: string | null }>("pick_folder", "install");
  if (!picked.ok) {
    toast({ title: "Folder picker failed", message: picked.error, level: "danger" });
    return;
  }
  if (!picked.data?.path) return;
  const res = await api("game_install", picked.data.path, version ?? null);
  if (!res.ok) {
    toast({ title: "Install failed", message: res.error, level: "danger" });
    return;
  }
  showProgress(0, "Preparing download…");
}

async function launchGame(force = false): Promise<void> {
  const res = await api<{ warnings?: any[] }>("game_launch", force);
  if (!res.ok) {
    toast({ title: "Launch failed", message: res.error, level: "danger" });
    return;
  }
  if (res.data?.warnings?.length) {
    showModWarnings(res.data.warnings, force);
    return;
  }
  setStatusLine("Launching Among Us…", "info");
}

function showModWarnings(warnings: any[], force: boolean): void {
  const list = document.createElement("div");
  list.className = "stack";
  list.style.gap = "8px";
  for (const w of warnings) {
    const row = document.createElement("div");
    row.className = `live-status level-${w.severity === "error" ? "danger" : "warning"}`;
    row.innerHTML = `<svg class="icon"><use href="#i-alert"/></svg><span></span>`;
    (row.querySelector("span") as HTMLElement).textContent =
      w.description ?? String(w);
    list.appendChild(row);
  }
  openModal({
    title: "Mod warnings",
    body: list,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Launch anyway",
        variant: "primary",
        onClick: (close) => {
          close();
          void launchGame(true);
        },
      },
    ],
  });
}

async function refreshState(): Promise<void> {
  const res = await api<any>("game_state");
  if (res.ok && res.data) {
    updateGame(res.data);
    render();
    setStatusLine("Status refreshed", "info");
  }
}

async function locateGame(): Promise<void> {
  const picked = await api<{ path: string | null }>("pick_folder", "locate");
  if (!picked.ok || !picked.data?.path) return;
  const res = await api("game_apply_change", picked.data.path, "locate", false);
  if (!res.ok) toast({ title: "Locate failed", message: res.error, level: "danger" });
}

/* --------------------------------------------------------- quick actions */

async function runQuickAction(action: string): Promise<void> {
  switch (action) {
    case "open-folder": {
      const res = await api("game_open_folder");
      if (!res.ok) toast({ title: "Cannot open folder", message: res.error, level: "warning" });
      break;
    }
    case "change-location": {
      const picked = await api<{ path: string | null }>("pick_folder", "change");
      if (!picked.ok || !picked.data?.path) return;
      const res = await api("game_apply_change", picked.data.path, "change", false);
      if (!res.ok) toast({ title: "Failed", message: res.error, level: "danger" });
      break;
    }
    case "verify": {
      const res = await api("game_verify");
      if (!res.ok) toast({ title: "Verify failed", message: res.error, level: "danger" });
      else setStatusLine("Verifying files…", "info");
      break;
    }
    case "shortcut": {
      const res = await api<{ message?: string }>("game_create_shortcut");
      if (res.ok) toast({ title: "Shortcut", message: res.data?.message ?? "Created.", level: "success" });
      else toast({ title: "Shortcut failed", message: res.error, level: "danger" });
      break;
    }
  }
}

/* --------------------------------------------------------------- versions */

async function showVersions(): Promise<void> {
  const body = document.createElement("div");
  body.className = "stack";
  body.innerHTML = `
    <div class="live-status level-info">
      <svg class="icon"><use href="#i-clock"/></svg>
      <span>Fetching available game versions…</span>
    </div>
    <div id="versions-list" class="stack" style="gap:8px;"></div>`;

  openModal({
    title: "Game versions",
    body,
    wide: true,
    buttons: [{ label: "Close", variant: "primary", onClick: (close) => close() }],
  });

  if (!versionsLoaded) {
    const res = await api("game_versions");
    if (!res.ok) {
      renderVersions([], res.error);
    }
    // results arrive via the versions_result event
  } else {
    // already fetched once — re-request for freshness
    await api("game_versions");
  }
}

function renderVersions(versions: any[], error?: string | null): void {
  const host = document.getElementById("versions-list");
  if (!host) return;
  host.innerHTML = "";

  if (error) {
    host.innerHTML = `<div class="live-status level-danger"><svg class="icon"><use href="#i-alert"/></svg><span></span></div>`;
    (host.querySelector("span") as HTMLElement).textContent = error;
    return;
  }
  if (!versions.length) {
    host.innerHTML = `<p class="muted">No versions found.</p>`;
    return;
  }

  for (const v of versions) {
    const row = document.createElement("div");
    row.className = "quick";
    row.style.alignItems = "flex-start";

    const icon = document.createElement("span");
    icon.className = "q-icon";
    icon.innerHTML = `<svg class="icon"><use href="#i-download"/></svg>`;

    const col = document.createElement("div");
    col.style.minWidth = "0";
    col.style.flex = "1";

    const top = document.createElement("div");
    top.style.display = "flex";
    top.style.gap = "8px";
    top.style.alignItems = "center";
    top.innerHTML = `<strong>v${v.version ?? "?"}</strong>`;

    const install = document.createElement("button");
    install.className = "btn primary";
    install.style.marginLeft = "auto";
    install.textContent = "Install";
    install.addEventListener("click", async (e) => {
      e.stopPropagation();
      const res = await api("game_install", null, v.version);
      if (!res.ok) {
        toast({ title: "Install failed", message: res.error, level: "danger" });
        return;
      }
      document.querySelector(".modal-backdrop")?.remove();
      showProgress(0, `Downloading v${v.version}…`);
    });
    top.appendChild(install);

    const body = document.createElement("p");
    body.className = "muted";
    body.style.fontSize = "12.5px";
    body.style.marginTop = "4px";
    body.style.whiteSpace = "pre-wrap";
    body.textContent = (v.body || "No release notes.").slice(0, 400);

    col.append(top, body);
    row.append(icon, col);
    host.appendChild(row);
  }
}

/* --------------------------------------------------------------- progress */

function showProgress(pct: number, label: string): void {
  const wrap = $("progress-wrap");
  wrap.classList.add("show");
  renderProgress(pct);
  $("progress-text").textContent = label;
}

function renderProgress(pct: number): void {
  const wrap = $("progress-wrap");
  if (!wrap.classList.contains("show")) wrap.classList.add("show");
  const clamped = Math.max(0, Math.min(100, pct));
  $("progress-bar").style.width = `${clamped}%`;
  $("progress-pct").textContent = `${Math.round(clamped)}%`;
}

function hideProgress(): void {
  $("progress-wrap").classList.remove("show");
}

/* ---------------------------------------------------------------- results */

function showVerifyResult(data: any): void {
  if (!data) return;
  if (!data.ok) {
    toast({ title: "Verify failed", message: data.error ?? "Unknown error", level: "danger" });
    return;
  }
  const missing: string[] = data.missing ?? [];
  const body = document.createElement("div");
  body.className = "stack";
  body.style.gap = "10px";

  const summary = document.createElement("div");
  summary.className = data.valid ? "live-status level-success" : "live-status level-warning";
  summary.innerHTML = `
    <svg class="icon"><use href="#i-${data.valid ? "check" : "alert"}"/></svg>
    <span></span>`;
  (summary.querySelector("span") as HTMLElement).textContent = data.valid
    ? `All ${data.file_count} files verified (${data.size_text}).`
    : `${missing.length} file(s) missing or damaged.`;
  body.appendChild(summary);

  if (missing.length) {
    const pre = document.createElement("pre");
    pre.className = "mono";
    pre.style.maxHeight = "220px";
    pre.style.overflow = "auto";
    pre.style.userSelect = "text";
    pre.style.margin = "0";
    pre.textContent = missing.join("\n");
    body.appendChild(pre);
  }

  openModal({
    title: "File verification",
    body,
    buttons: [
      { label: "Close", variant: "ghost", onClick: (close) => close() },
      ...(missing.length
        ? [{
            label: "Repair (update)",
            variant: "primary" as const,
            onClick: (close: () => void) => {
              close();
              void installGame();
            },
          }]
        : []),
    ],
  });
}

function showFolderInspect(data: any): void {
  if (!data) return;
  if (!data.ok) {
    toast({ title: "Folder check failed", message: data.error ?? "", level: "danger" });
    return;
  }
  if (data.exe_found) {
    toast({ title: "Game found", message: data.path, level: "success" });
    return;
  }
  toast({
    title: "Among Us.exe not found",
    message: "Pick the folder that contains the game.",
    level: "warning",
  });
}

/* ------------------------------------------------------------ status line */

function setStatusLine(text: string, level: string): void {
  const live = $("live-status");
  const liveText = $("live-text");
  const liveDot = $("live-dot");
  const sbStatus = $("sb-status");
  const sbDot = $("sb-dot");

  if (text) {
    liveText.textContent = text;
    sbStatus.textContent = text;
  }
  live.className = `live-status level-${level}`;
  liveDot.className = `dot ${level === "danger" ? "danger" : level === "warning" ? "warning" : level === "success" ? "success" : "info"}`;
  sbDot.className = `dot ${level === "danger" ? "danger" : level === "warning" ? "warning" : level === "success" ? "success" : "info"}`;
}

/* ------------------------------------------------------------ home card */

async function setHomeImage(): Promise<void> {
  const res = await api<{ path: string | null; image_data: string | null }>("home_image_set");
  if (!res.ok) {
    if (res.error && !res.error.includes("cancel")) {
      toast({ title: "Image", message: res.error, level: "warning" });
    }
    return;
  }
  if (!res.data?.path) return;
  store.home.image = res.data.path;
  store.home.image_data = res.data.image_data;
  renderHomeCard();
  toast({ title: "Image set", level: "success" });
}

async function editHomeNote(): Promise<void> {
  const body = document.createElement("div");
  body.innerHTML = `
    <p class="muted" style="margin-bottom:10px;">Shown on the Home screen (max 600 characters).</p>
    <textarea class="field" id="note-input" maxlength="600" rows="5"
      placeholder="Write anything — a motto, a reminder, your crew's tag…"></textarea>`;
  const input = body.querySelector<HTMLTextAreaElement>("#note-input")!;
  input.value = store.home.note ?? "";

  openModal({
    title: "Home note",
    body,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Save",
        variant: "primary",
        onClick: async (close) => {
          const res = await api("home_note_set", input.value);
          if (!res.ok) {
            toast({ title: "Save failed", message: res.error, level: "danger" });
            return;
          }
          store.home.note = input.value.slice(0, 600);
          renderHomeCard();
          close();
        },
      },
    ],
  });
}

async function clearHomeCard(): Promise<void> {
  await api("home_image_clear");
  await api("home_note_set", "");
  store.home.image = "";
  store.home.image_data = null;
  store.home.note = "";
  renderHomeCard();
}

function renderHomeCard(): void {
  const thumb = $("home-thumb");
  const img = $("home-img") as HTMLImageElement;
  const note = $("home-note");
  const clear = $("home-clear-btn") as HTMLButtonElement;

  if (store.home.image_data) {
    img.src = store.home.image_data;
    thumb.classList.add("has-image");
  } else {
    img.removeAttribute("src");
    thumb.classList.remove("has-image");
  }

  note.textContent =
    store.home.note || "Add a note or an image to make this launcher yours.";

  clear.hidden = !store.home.image_data && !store.home.note;
}

/* ---------------------------------------------------------------- render */

export function render(): void {
  const g = store.game;

  // Do not flash "NOT INSTALLED" before the real state has loaded.
  if (!store.booted) {
    const badge = $("hero-badge");
    badge.textContent = "CHECKING…";
    badge.className = "pill";
    $("hero-sub").textContent = "Loading launcher state…";
    ($("main-action") as HTMLButtonElement).disabled = true;
    $("main-action-label").textContent = "…";
    return;
  }

  // hero badge + sub
  const badge = $("hero-badge");
  const sub = $("hero-sub");
  const playing = $("hero-playing") as HTMLElement;
  const profile = $("hero-profile");

  if (g.running) {
    badge.textContent = "RUNNING";
    badge.className = "pill success";
    sub.textContent = `Among Us v${g.version} is running${g.pid ? ` (PID ${g.pid})` : ""}.`;
    playing.hidden = false;
  } else if (g.busy) {
    badge.textContent = "WORKING";
    badge.className = "pill warning";
    sub.textContent = "An install, update or verification is in progress…";
    playing.hidden = true;
  } else if (g.needs_install) {
    badge.textContent = "NOT INSTALLED";
    badge.className = "pill";
    sub.textContent = g.path
      ? "No game files at the selected location — install to continue."
      : "Choose a folder and install Among Us to get started.";
    playing.hidden = true;
  } else if (g.update?.needed) {
    badge.textContent = "UPDATE READY";
    badge.className = "pill warning";
    sub.textContent = `v${g.latest ?? g.update.latest} is available for your install of v${g.version}.`;
    playing.hidden = true;
  } else {
    badge.textContent = "READY";
    badge.className = "pill success";
    sub.textContent = `Among Us v${g.version} is installed and up to date.`;
    playing.hidden = true;
  }

  profile.textContent = g.active_profile || "Default";

  // main button
  const label = $("main-action-label");
  const btn = $("main-action") as HTMLButtonElement;
  btn.disabled = g.busy && !g.running;
  if (g.running) label.textContent = "STOP";
  else if (g.busy) label.textContent = "WORKING…";
  else if (g.needs_install) label.textContent = "INSTALL";
  else if (g.update?.needed) label.textContent = "UPDATE";
  else label.textContent = "LAUNCH";

  // status card
  $("st-version").textContent = g.version || "—";
  $("st-latest").textContent = g.latest ?? g.update?.latest ?? "—";
  const pathEl = $("st-path");
  pathEl.textContent = g.path || "Not set";
  pathEl.title = g.path || "";
  $("st-profile").textContent = g.active_profile || "Default";

  // header pill
  $("home-version-pill").textContent = g.version ? `v${g.version}` : "v —";

  // sidebar + statusbar versions
  const sbVersion = document.getElementById("sb-version");
  if (sbVersion) {
    sbVersion.textContent = `Launcher ${store.app.launcher_version || "?"} · Game ${g.version || "—"}`;
  }
  const sideVersion = document.getElementById("sidebar-version");
  if (sideVersion) sideVersion.textContent = `v${store.app.launcher_version || "?"}`;

  const sbDetail = document.getElementById("sb-detail");
  if (sbDetail) sbDetail.textContent = g.path || "";

  if (!g.busy && !g.running && store.progress !== null) hideProgress();

  renderHomeCard();
}

/* ------------------------------------------------------------- cosmetics */

function spawnParticles(): void {
  const host = $("particles");
  for (let i = 0; i < 22; i++) {
    const p = document.createElement("span");
    p.className = "particle";
    p.style.left = `${Math.random() * 100}%`;
    p.style.bottom = `${Math.random() * 40}%`;
    p.style.animationDuration = `${7 + Math.random() * 9}s`;
    p.style.animationDelay = `${-Math.random() * 12}s`;
    p.style.opacity = String(0.3 + Math.random() * 0.6);
    host.appendChild(p);
  }
}
