/* Assets view: AU-Assets-Swapper pack management --------------------------- */

import { api } from "../bridge";
import { confirmModal, openModal } from "../modal";
import { toast } from "../toast";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

interface PackMeta {
  name?: string;
  author?: string;
  description?: string;
  version?: string;
  thumbnail?: string;
  game_version?: string;
  created_at?: string;
  categories?: string[];
}

interface AssetFile {
  path: string;
  size: number;
}

interface PackInfo {
  name: string;
  active?: boolean;
  asset_count?: number;
  total_size?: number;
  categories?: Record<string, number>;
  metadata?: PackMeta;
}

interface PackDetail extends PackInfo {
  path?: string;
  assets?: Record<string, AssetFile[]>;
  thumbnail_data?: string | null;
}

interface AssetsState {
  installed?: boolean;
  game_path?: string;
  active?: string;
  packs?: PackInfo[];
  game_running?: boolean;
}

interface AddResult {
  copied?: number;
  skipped?: number;
  errors?: string[];
}

interface PickResult {
  path?: string | null;
  paths?: string[];
}

let packs: PackInfo[] = [];
let selected = "";
let activePack = "";
let detail: PackDetail | null = null;
let gamePath = "";
let gameRunning = false;
let installed = false;

const MUTATE_IDS = [
  "assets-pack-activate",
  "assets-pack-add-files",
  "assets-pack-add-folder",
  "assets-pack-info",
  "assets-pack-rename",
  "assets-pack-duplicate",
  "assets-pack-delete",
  "assets-deactivate",
];
const SELECT_IDS = ["assets-pack-open", "assets-pack-export"];

export function initAssets(): void {
  $("assets-refresh").addEventListener("click", () => void loadAssets());
  $("assets-create").addEventListener("click", createPack);
  $("assets-import").addEventListener("click", importPack);
  $("assets-pack-activate").addEventListener("click", activatePack);
  $("assets-deactivate").addEventListener("click", deactivatePack);
  $("assets-pack-add-files").addEventListener("click", addFiles);
  $("assets-pack-add-folder").addEventListener("click", addFolder);
  $("assets-pack-info").addEventListener("click", editInfo);
  $("assets-pack-open").addEventListener("click", openPack);
  $("assets-pack-export").addEventListener("click", exportPack);
  $("assets-pack-rename").addEventListener("click", renamePack);
  $("assets-pack-duplicate").addEventListener("click", duplicatePack);
  $("assets-pack-delete").addEventListener("click", deletePack);
}

export async function loadAssets(): Promise<void> {
  const data = await call<AssetsState>("Could not load packs", "assets_state");
  if (!data) return;

  packs = data.packs ?? [];
  activePack = data.active ?? "";
  gamePath = data.game_path ?? "";
  gameRunning = Boolean(data.game_running);
  installed = Boolean(data.installed);

  if (selected && !packs.some((p) => p.name === selected)) selected = "";
  if (!selected) selected = activePack || packs[0]?.name || "";

  renderState();
  renderList();
  if (selected) await loadDetail(selected);
  else {
    detail = null;
    renderDetail();
  }
}

async function loadDetail(name: string): Promise<void> {
  const data = await call<PackDetail>("Could not open pack", "assets_pack_detail", name);
  if (selected !== name) return;
  detail = data;
  renderDetail();
}

async function call<T>(
  title: string,
  method: string,
  ...args: unknown[]
): Promise<T | null> {
  const res = await api<T>(method, ...args);
  if (!res.ok) {
    toast({ title, message: res.error, level: "danger" });
    return null;
  }
  return res.data;
}

function guard(needPack = true): boolean {
  if (gameRunning) {
    toast({
      title: "Game is running",
      message: "Close Among Us before changing asset packs.",
      level: "warning",
    });
    return false;
  }
  if (needPack && !selected) {
    toast({ title: "No pack selected", message: "Create or select a pack first.", level: "warning" });
    return false;
  }
  return true;
}

function formatSize(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`;
}

/* --------------------------------------------------------------- rendering */

function renderState(): void {
  $("assets-game-notice").classList.toggle("show", gameRunning);
  $("assets-install-notice").classList.toggle("show", installed);
  $("assets-active-label").textContent = activePack
    ? `Active: ${activePack}`
    : "No active pack";
  $("assets-active-label").title = gamePath;
  $("assets-deactivate").hidden = !activePack;

  const hasPack = Boolean(selected);
  for (const id of MUTATE_IDS) {
    ($(id) as HTMLButtonElement).disabled = !hasPack || gameRunning;
  }
  for (const id of SELECT_IDS) {
    ($(id) as HTMLButtonElement).disabled = !hasPack;
  }
  ($("assets-deactivate") as HTMLButtonElement).disabled = !activePack || gameRunning;
}

function renderList(): void {
  const host = $("assets-list");
  host.replaceChildren();
  $("assets-pack-count").textContent = String(packs.length);

  if (!packs.length) {
    host.innerHTML = `
      <div class="empty" style="padding: 34px 16px;">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-layers" /></svg></span>
        <h3>No packs yet</h3>
        <p>Create a pack, then add matching asset files to it.</p>
        <button class="btn primary" id="assets-create-empty">Create a pack</button>
      </div>`;
    document.getElementById("assets-create-empty")?.addEventListener("click", createPack);
    return;
  }

  for (const pack of packs) {
    const row = document.createElement("button");
    row.className = `asset-item${pack.name === selected ? " selected" : ""}`;
    row.innerHTML = `
      <span class="a-icon"><svg class="icon"><use href="#i-layers" /></svg></span>
      <span style="min-width:0;">
        <span class="a-name"></span>
        <span class="a-meta"></span>
      </span>
      <span class="dot"></span>`;
    (row.querySelector(".a-name") as HTMLElement).textContent = pack.name;
    const count = pack.asset_count ?? 0;
    (row.querySelector(".a-meta") as HTMLElement).textContent =
      `${count} ${count === 1 ? "file" : "files"} · ${formatSize(pack.total_size ?? 0)}`;
    const dot = row.querySelector(".dot") as HTMLElement;
    dot.className = `dot${pack.active ? " success" : ""}`;
    dot.title = pack.active ? "Active pack" : "Inactive pack";
    row.addEventListener("click", () => {
      selected = pack.name;
      renderList();
      renderState();
      void loadDetail(pack.name);
    });
    host.appendChild(row);
  }
}

function renderDetail(): void {
  const pack = detail;
  const title = $("assets-pack-title");
  const path = $("assets-pack-path");
  const state = $("assets-pack-state");
  const summary = $("assets-pack-summary");
  const thumbWrap = $("assets-thumb-wrap");
  const thumb = $("assets-thumb") as HTMLImageElement;
  const files = $("assets-file-list");

  if (!pack) {
    title.textContent = "No pack selected";
    path.textContent = "";
    state.textContent = "Inactive";
    state.className = "pill";
    summary.textContent = "";
    thumbWrap.hidden = true;
    thumb.removeAttribute("src");
    $("assets-file-count").textContent = "0";
    files.innerHTML = `
      <div class="empty" style="padding: 28px 16px;">
        <p>Select a pack to see its replacement files.</p>
      </div>`;
    return;
  }

  const meta = pack.metadata ?? {};
  title.textContent = meta.name || pack.name;
  path.textContent = pack.path ?? "";
  path.title = pack.path ?? "";
  state.textContent = pack.active ? "Active" : "Inactive";
  state.className = `pill${pack.active ? " success" : ""}`;

  const info: string[] = [];
  if (meta.author) info.push(`By ${meta.author}`);
  if (meta.version) info.push(`v${meta.version}`);
  if (meta.game_version) info.push(`Game ${meta.game_version}`);
  if (meta.created_at) info.push(`Created ${meta.created_at.slice(0, 10)}`);
  summary.textContent = [meta.description || "No description yet.", info.join(" · ")]
    .filter(Boolean)
    .join("\n\n");

  if (pack.thumbnail_data) {
    thumb.src = pack.thumbnail_data;
    thumbWrap.hidden = false;
  } else {
    thumb.removeAttribute("src");
    thumbWrap.hidden = true;
  }

  renderFiles(pack);
}

function renderFiles(pack: PackDetail): void {
  const host = $("assets-file-list");
  host.replaceChildren();
  $("assets-file-count").textContent = String(pack.asset_count ?? 0);

  const groups = Object.entries(pack.assets ?? {}).filter(([, files]) => files.length);
  if (!groups.length) {
    host.innerHTML = `
      <div class="empty" style="padding: 28px 16px;">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-folder" /></svg></span>
        <h3>No assets in this pack</h3>
        <p>Add images, audio, fonts or AssetBundles. Names must match the game asset.</p>
      </div>`;
    return;
  }

  for (const [category, files] of groups) {
    const group = document.createElement("div");
    group.className = "assets-group";
    const head = document.createElement("div");
    head.className = "assets-group-head";
    const label = document.createElement("span");
    label.textContent = category;
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = `${files.length} · ${formatSize(files.reduce((n, f) => n + f.size, 0))}`;
    head.append(label, count);
    group.appendChild(head);

    for (const file of files) {
      const row = document.createElement("div");
      row.className = "asset-row";
      const name = document.createElement("span");
      name.className = "a-file";
      name.textContent = file.path;
      name.title = file.path;
      const size = document.createElement("span");
      size.className = "a-size";
      size.textContent = formatSize(file.size);
      const remove = document.createElement("button");
      remove.className = "mini danger";
      remove.title = "Remove file";
      remove.innerHTML = `<svg class="icon sm"><use href="#i-x"/></svg>`;
      remove.disabled = gameRunning;
      remove.addEventListener("click", () => void removeFile(pack.name, category, file.path));
      row.append(name, size, remove);
      group.appendChild(row);
    }
    host.appendChild(group);
  }
}

/* ----------------------------------------------------------------- dialogs */

function promptModal(
  title: string,
  label: string,
  value: string,
  save: (value: string, close: () => void) => Promise<void> | void,
  hint = "",
): void {
  const body = document.createElement("div");
  body.className = "asset-form";
  const row = document.createElement("div");
  row.className = "form-row";
  const lab = document.createElement("label");
  lab.textContent = label;
  const input = document.createElement("input");
  input.className = "field";
  input.value = value;
  input.maxLength = 60;
  row.append(lab, input);
  body.appendChild(row);
  if (hint) {
    const note = document.createElement("p");
    note.className = "asset-hint";
    note.textContent = hint;
    body.appendChild(note);
  }

  openModal({
    title,
    body,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Save",
        variant: "primary",
        onClick: (close) => void save(input.value.trim(), close),
      },
    ],
  });
  setTimeout(() => {
    input.focus();
    input.select();
  }, 40);
}

/* ----------------------------------------------------------------- actions */

function createPack(): void {
  if (!guard(false)) return;
  promptModal("New asset pack", "Pack name", "", async (name, close) => {
    if (!name) return;
    const data = await call<{ name: string }>("Create failed", "assets_pack_create", name);
    if (!data) return;
    close();
    selected = data.name;
    await loadAssets();
    toast({ title: "Pack created", message: data.name, level: "success" });
  }, "Use letters, numbers, spaces, dashes or underscores. Avoid slashes and reserved characters.");
}

async function importPack(): Promise<void> {
  if (!guard(false)) return;
  const picked = await call<PickResult>("Import failed", "pick_file", "archives", false);
  const path = picked?.path;
  if (!path) return;
  const preview = await call<PickResult & { suggested?: string; metadata?: PackMeta }>(
    "Import failed", "assets_pack_import_preview", path,
  );
  if (!preview) return;

  const meta = preview.metadata ?? {};
  const hint = [
    `Archive: ${path}`,
    [meta.author && `By ${meta.author}`, meta.version && `v${meta.version}`].filter(Boolean).join(" · "),
  ].filter(Boolean).join("\n");

  promptModal("Import pack", "Pack name", preview.suggested ?? "", async (name, close) => {
    if (!name) return;
    const data = await call<{ name: string }>("Import failed", "assets_pack_import", path, name);
    if (!data) return;
    close();
    selected = data.name;
    await loadAssets();
    toast({ title: "Pack imported", message: data.name, level: "success" });
  }, hint);
}

async function addFiles(): Promise<void> {
  if (!guard()) return;
  const picked = await call<PickResult>("File picker failed", "pick_file", "assets", true);
  const paths = picked?.paths ?? (picked?.path ? [picked.path] : []);
  if (!paths.length) return;

  const body = document.createElement("div");
  body.className = "asset-form";
  const note = document.createElement("p");
  note.className = "muted";
  note.textContent = `Selected ${paths.length} ${paths.length === 1 ? "file" : "files"}. Supported files are sorted into their asset category.`;
  const label = document.createElement("label");
  label.className = "asset-check";
  const overwrite = document.createElement("input");
  overwrite.type = "checkbox";
  overwrite.checked = true;
  label.append(overwrite, document.createTextNode(" Overwrite files with the same name"));
  body.append(note, label);

  openModal({
    title: "Add files",
    body,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Add",
        variant: "primary",
        onClick: (close) => void (async () => {
          const data = await call<AddResult>("Add failed", "assets_pack_add_files", selected, paths, overwrite.checked);
          if (!data) return;
          close();
          await loadAssets();
          toast({
            title: "Files added",
            message: `${data.copied ?? 0} copied${data.errors?.length ? `, ${data.errors.length} failed` : ""}`,
            level: data.errors?.length ? "warning" : "success",
          });
        })(),
      },
    ],
  });
}

async function addFolder(): Promise<void> {
  if (!guard()) return;
  const picked = await call<PickResult>("Folder picker failed", "pick_folder", "assets");
  const folder = picked?.path;
  if (!folder) return;
  const data = await call<AddResult>("Add failed", "assets_pack_add_folder", selected, folder);
  if (!data) return;
  await loadAssets();
  toast({
    title: "Folder added",
    message: `${data.copied ?? 0} files copied${data.errors?.length ? `, ${data.errors.length} failed` : ""}`,
    level: data.errors?.length ? "warning" : "success",
  });
}

function editInfo(): void {
  if (!guard()) return;
  const meta = detail?.metadata ?? {};
  const body = document.createElement("div");
  body.className = "asset-form";
  const inputs: Record<string, HTMLInputElement | HTMLTextAreaElement> = {};

  const addField = (key: string, label: string, value: string, textarea = false): void => {
    const row = document.createElement("div");
    row.className = "form-row";
    const lab = document.createElement("label");
    lab.textContent = label;
    const input = textarea
      ? document.createElement("textarea")
      : document.createElement("input");
    input.className = "field";
    if (input instanceof HTMLTextAreaElement) input.rows = 3;
    input.value = value;
    row.append(lab, input);
    body.appendChild(row);
    inputs[key] = input;
  };

  addField("name", "Display name", meta.name ?? selected);
  addField("author", "Author", meta.author ?? "");
  addField("version", "Version", meta.version ?? "1.0.0");
  addField("game_version", "Game version", meta.game_version ?? "");
  addField("description", "Description", meta.description ?? "", true);

  const thumbRow = document.createElement("div");
  thumbRow.className = "form-row thumb-row";
  const thumbLabel = document.createElement("label");
  thumbLabel.textContent = "Thumbnail";
  const thumbInput = document.createElement("input");
  thumbInput.className = "field";
  thumbInput.value = meta.thumbnail ?? "";
  const browse = document.createElement("button");
  browse.className = "btn";
  browse.textContent = "Browse";
  browse.addEventListener("click", async () => {
    const picked = await call<PickResult>("Image picker failed", "pick_file", "images", false);
    if (picked?.path) thumbInput.value = picked.path;
  });
  thumbRow.append(thumbLabel, thumbInput, browse);
  body.appendChild(thumbRow);
  inputs["thumbnail"] = thumbInput;

  openModal({
    title: "Pack info",
    body,
    wide: true,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Save",
        variant: "primary",
        onClick: (close) => void (async () => {
          const metadata: PackMeta = {
            name: inputs["name"].value.trim(),
            author: inputs["author"].value.trim(),
            description: inputs["description"].value.trim(),
            version: inputs["version"].value.trim() || "1.0.0",
            game_version: inputs["game_version"].value.trim(),
            thumbnail: inputs["thumbnail"].value.trim(),
            categories: meta.categories ?? [],
          };
          const data = await call<PackMeta>("Save failed", "assets_pack_save_info", selected, metadata);
          if (!data) return;
          close();
          await loadAssets();
          toast({ title: "Pack info saved", level: "success" });
        })(),
      },
    ],
  });
}

async function activatePack(): Promise<void> {
  if (!guard()) return;
  const data = await call<{ active?: string }>("Activate failed", "assets_pack_set_active", selected);
  if (!data) return;
  await loadAssets();
  toast({ title: "Pack activated", message: selected, level: "success" });
}

async function deactivatePack(): Promise<void> {
  if (!guard(false)) return;
  const data = await call<{ active?: string }>("Deactivate failed", "assets_pack_set_active", "");
  if (!data) return;
  await loadAssets();
  toast({ title: "Original assets restored", level: "success" });
}

async function openPack(): Promise<void> {
  if (!selected) return;
  await call("Could not open folder", "assets_pack_open", selected);
}

async function exportPack(): Promise<void> {
  if (!selected) return;
  const data = await call<{ path?: string | null }>("Export failed", "assets_pack_export", selected);
  if (data?.path) toast({ title: "Pack exported", message: data.path, level: "success" });
}

function renamePack(): void {
  if (!guard()) return;
  promptModal("Rename pack", "New name", selected, async (name, close) => {
    if (!name) return;
    const data = await call<{ name: string }>("Rename failed", "assets_pack_rename", selected, name);
    if (!data) return;
    close();
    selected = data.name;
    await loadAssets();
  });
}

function duplicatePack(): void {
  if (!guard()) return;
  promptModal("Duplicate pack", "New name", `${selected} copy`, async (name, close) => {
    if (!name) return;
    const data = await call<{ name: string }>("Duplicate failed", "assets_pack_duplicate", selected, name);
    if (!data) return;
    close();
    selected = data.name;
    await loadAssets();
    toast({ title: "Pack duplicated", message: data.name, level: "success" });
  });
}

async function deletePack(): Promise<void> {
  if (!guard()) return;
  const name = selected;
  const confirmed = await confirmModal(
    "Delete asset pack",
    `Delete "${name}" and all of its files? This cannot be undone.`,
    "Delete",
    true,
  );
  if (!confirmed) return;
  const data = await call("Delete failed", "assets_pack_delete", name);
  if (!data) return;
  selected = "";
  await loadAssets();
  toast({ title: "Pack deleted", message: name, level: "success" });
}

async function removeFile(pack: string, category: string, relpath: string): Promise<void> {
  if (!guard()) return;
  const data = await call<{ removed?: boolean }>(
    "Remove failed", "assets_pack_remove", pack, category, relpath,
  );
  if (!data) return;
  await loadAssets();
}
