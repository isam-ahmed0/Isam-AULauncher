/* Mod browser: catalog search, filters and one-click install/remove -------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

interface CatalogEntry {
  id: string;
  name: string;
  author: string;
  category: string;
  description: string;
  dependencies: string[];
  incompatibilities: string[];
  game_version: string;
  is_archive: boolean;
}

interface CatalogData {
  mods: CatalogEntry[];
  states: Record<string, string>;
  profile: string;
  error: string | null;
  offline: boolean;
  updated_at?: string;
}

let entries: CatalogEntry[] = [];
let states: Record<string, string> = {};
let installedIds = new Set<string>();
let loaded = false;  // whether a catalog has been received (not a cache)

const STATE_LABEL: Record<string, string> = {
  install: "Not installed",
  installed: "Installed",
  unknown: "Not in catalog",
};

export function initBrowse(): void {
  $("catalog-refresh").addEventListener("click", () => void loadCatalog(true));
  $("catalog-search").addEventListener("input", render);
  $("catalog-category").addEventListener("change", render);

  on("catalog_result", (data) => applyCatalog(data));
  on("catalog_install_done", (data) => {
    if (data?.ok) {
      states[data.id] = "installed";
      installedIds.add(data.id);
      render();
    }
    void loadCatalog(true);
  });
  on("mods_changed", (data) => {
    const ids = (data?.mods ?? [])
      .map((m: any) => m.catalog_id)
      .filter(Boolean) as string[];
    installedIds = new Set(ids);
    if (loaded) render();
  });
}

export async function loadCatalog(_force = false): Promise<void> {
  // Always fetch: the catalog and downloaded archives are never cached.
  const status = $("catalog-status");
  status.textContent = "Fetching catalog…";
  status.className = "pill";
  const res = await api("catalog_load", true);
  if (!res.ok) toast({ title: "Catalog failed", message: res.error, level: "danger" });
}

function applyCatalog(data: CatalogData): void {
  if (!data) return;
  entries = data.mods ?? [];
  states = data.states ?? {};
  loaded = true;

  const status = $("catalog-status");
  status.textContent = data.offline
    ? "Catalog unavailable"
    : `${entries.length} mods`;
  status.className = `pill${data.offline ? " warning" : " accent"}`;

  const errorBox = $("catalog-error");
  if (data.error) {
    $("catalog-error-text").textContent = data.error;
    errorBox.classList.add("show");
  } else {
    errorBox.classList.remove("show");
  }

  // category filter options
  const categories = [...new Set(entries.map((e) => e.category || "Other"))].sort();
  const select = $("catalog-category") as HTMLSelectElement;
  const current = select.value;
  select.innerHTML = `<option value="">All categories</option>`;
  for (const category of categories) {
    const opt = document.createElement("option");
    opt.value = category;
    opt.textContent = category;
    select.appendChild(opt);
  }
  select.value = categories.includes(current) ? current : "";

  render();
}

function render(): void {
  const query = ($("catalog-search") as HTMLInputElement).value.trim().toLowerCase();
  const category = ($("catalog-category") as HTMLSelectElement).value;
  const filtered = entries.filter((e) => {
    if (category && (e.category || "Other") !== category) return false;
    if (!query) return true;
    return (
      e.name.toLowerCase().includes(query) ||
      (e.description || "").toLowerCase().includes(query) ||
      (e.author || "").toLowerCase().includes(query)
    );
  });

  $("catalog-count").textContent =
    `${filtered.length} of ${entries.length} mods`;

  const host = $("catalog-grid");
  host.innerHTML = "";
  if (!filtered.length) {
    host.innerHTML = `
      <div class="empty" style="grid-column: 1 / -1;">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-compass" /></svg></span>
        <h3>No mods found</h3>
        <p>${loaded ? "Try another search or category." : "Fetching the catalog…"}</p>
      </div>`;
    return;
  }

  for (const entry of filtered) {
    const state = states[entry.id] ?? "install";
    const card = document.createElement("article");
    card.className = "mod-card";

    const top = document.createElement("div");
    top.className = "mc-top";
    top.innerHTML = `
      <span class="mc-icon"><svg class="icon"><use href="#i-puzzle" /></svg></span>
      <div style="min-width:0;">
        <h3></h3>
        <div class="mc-author"></div>
      </div>`;
    (top.querySelector("h3") as HTMLElement).textContent = entry.name;
    (top.querySelector(".mc-author") as HTMLElement).textContent =
      [entry.author, entry.category].filter(Boolean).join(" · ");

    const desc = document.createElement("p");
    desc.className = "mc-desc";
    desc.textContent = entry.description || "No description provided.";

    const tags = document.createElement("div");
    tags.className = "mc-tags";
    const badges: Array<[string, string]> = [
      [STATE_LABEL[state] ?? state, state === "installed" ? "success" : ""],
      ...(entry.game_version ? [[`for ${entry.game_version}`, ""] as [string, string]] : []),
      ...(entry.dependencies?.length ? [[`Requires: ${entry.dependencies.join(", ")}`, ""] as [string, string]] : []),
      ...(entry.incompatibilities?.length ? [[`Conflicts: ${entry.incompatibilities.join(", ")}`, "danger"] as [string, string]] : []),
    ];
    for (const [text, tone] of badges) {
      if (!text) continue;
      const pill = document.createElement("span");
      pill.className = `pill${tone ? ` ${tone}` : ""}`;
      pill.textContent = text;
      tags.appendChild(pill);
    }

    const foot = document.createElement("div");
    foot.className = "mc-foot";
    const install = document.createElement("button");
    install.className = `btn${state === "install" ? " primary" : ""}`;
    install.textContent = state === "install" ? "Install" : "Reinstall";
    install.addEventListener("click", async () => {
      const res = await api("catalog_install", entry.id);
      if (!res.ok) toast({ title: "Install failed", message: res.error, level: "danger" });
      else toast({ title: "Installing", message: entry.name, level: "info" });
    });

    const remove = document.createElement("button");
    remove.className = "btn ghost";
    remove.textContent = "Remove";
    remove.disabled = !installedIds.has(entry.id) && !["installed", "unknown"].includes(state);
    remove.addEventListener("click", async () => {
      const res = await api("catalog_remove", entry.id);
      if (!res.ok) toast({ title: "Remove failed", message: res.error, level: "danger" });
    });

    foot.append(install, remove);
    card.append(top, desc, tags, foot);
    host.appendChild(card);
  }
}
