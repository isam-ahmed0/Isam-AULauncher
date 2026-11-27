/* Mods view: profiles + installed plugin management ------------------------ */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { openModal } from "../modal";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

interface ProfileInfo {
  name: string;
  active: boolean;
  count: number;
  enabled: number;
}

interface ModInfo {
  filename: string;
  name: string;
  enabled: boolean;
  size: number;
  size_text: string;
  catalog_id: string | null;
}

let profiles: ProfileInfo[] = [];
let activeProfile = "Default";
let selectedProfile = "Default";
let mods: ModInfo[] = [];

export function initMods(): void {
  $("profile-activate").addEventListener("click", activateProfile);
  $("profile-new").addEventListener("click", createProfile);
  $("profile-rename").addEventListener("click", renameProfile);
  $("profile-delete").addEventListener("click", deleteProfile);
  $("mods-import").addEventListener("click", importMods);
  document.getElementById("mods-import-empty")?.addEventListener("click", importMods);
  $("mods-scan").addEventListener("click", scanIssues);

  $("profile-select").addEventListener("change", () => {
    selectedProfile = ($("profile-select") as HTMLSelectElement).value;
    void loadMods(selectedProfile);
  });

  on("profiles_changed", (data) => applyProfiles(data));
  on("mods_changed", (data) => applyMods(data));
  on("mod_issues", (data) => showIssues(data?.issues ?? []));
  on("catalog_install_done", () => {
    void loadProfiles();
  });

  void loadProfiles();
}

export async function loadProfiles(): Promise<void> {
  const res = await api<{ profiles: ProfileInfo[]; active: string }>("profiles_list");
  if (res.ok && res.data) {
    applyProfiles(res.data);
    await loadMods(selectedProfile);
  }
}

function applyProfiles(data: any): void {
  if (!data) return;
  profiles = data.profiles ?? [];
  activeProfile = data.active ?? activeProfile;
  const select = $("profile-select") as HTMLSelectElement;
  select.innerHTML = "";
  for (const p of profiles) {
    const option = document.createElement("option");
    option.value = p.name;
    option.textContent = `${p.name}${p.active ? "  • active" : ""}`;
    select.appendChild(option);
  }
  if (!profiles.some((p) => p.name === selectedProfile)) {
    selectedProfile = activeProfile;
  }
  select.value = selectedProfile;
  const activate = $("profile-activate") as HTMLButtonElement;
  activate.hidden = selectedProfile === activeProfile;
}

export async function loadMods(profile: string): Promise<void> {
  const res = await api<any>("mods_list", profile);
  if (res.ok && res.data) applyMods(res.data);
}

function applyMods(data: any): void {
  if (!data) return;
  mods = data.mods ?? [];
  $("mods-count").textContent = `${mods.length} mod${mods.length === 1 ? "" : "s"}`;
  $("mods-enabled").textContent = `${data.enabled ?? 0} enabled`;

  const host = $("mod-list");
  host.innerHTML = "";
  if (!mods.length) {
    host.innerHTML = `
      <div class="empty" style="padding: 34px 20px;">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-puzzle" /></svg></span>
        <h3>No plugins yet</h3>
        <p>Import a DLL or browse the catalog to add your first mod.</p>
        <button class="btn primary" id="mods-import-empty">Import mods</button>
      </div>`;
    document.getElementById("mods-import-empty")?.addEventListener("click", importMods);
    return;
  }

  mods.forEach((mod, index) => {
    const row = document.createElement("div");
    row.className = `mod-row${mod.enabled ? "" : " disabled"}`;

    const info = document.createElement("div");
    info.className = "mod-info";
    info.innerHTML = `
      <span class="m-icon"><svg class="icon"><use href="#i-puzzle" /></svg></span>
      <div style="min-width:0;">
        <div class="m-name"></div>
        <div class="m-meta">
          <span class="mono"></span>
          <span></span>
        </div>
      </div>`;
    (info.querySelector(".m-name") as HTMLElement).textContent = mod.name;
    (info.querySelector(".mono") as HTMLElement).textContent = mod.size_text;
    const meta = info.querySelectorAll(".m-meta span")[1] as HTMLElement;
    meta.textContent = mod.enabled ? "" : "disabled";

    const toggle = document.createElement("button");
    toggle.className = `switch${mod.enabled ? " on" : ""}`;
    toggle.title = mod.enabled ? "Disable mod" : "Enable mod";
    toggle.setAttribute("aria-label", toggle.title);
    toggle.addEventListener("click", () =>
      void api("mod_toggle", mod.filename, !mod.enabled));

    const moves = document.createElement("div");
    moves.style.display = "flex";
    moves.style.gap = "2px";
    for (const [delta, label] of [[-1, "Move up"], [1, "Move down"]] as const) {
      const btn = document.createElement("button");
      btn.className = "mini";
      btn.title = label;
      btn.innerHTML = `<svg class="icon sm" style="transform: rotate(${delta < 0 ? -90 : 90}deg);"><use href="#i-chevron"/></svg>`;
      btn.disabled = delta < 0 ? index === 0 : index === mods.length - 1;
      btn.addEventListener("click", () => void api("mod_move", mod.filename, delta));
      moves.appendChild(btn);
    }

    const remove = document.createElement("button");
    remove.className = "mini danger";
    remove.title = "Remove mod";
    remove.innerHTML = `<svg class="icon sm"><use href="#i-x"/></svg>`;
    remove.addEventListener("click", async () => {
      const res = await api("mod_remove", mod.filename);
      if (!res.ok) toast({ title: "Remove failed", message: res.error, level: "danger" });
    });

    row.append(info, toggle, moves, remove);
    host.appendChild(row);
  });
}

/* ------------------------------------------------------------- profiles */

function inputModal(
  title: string,
  label: string,
  value: string,
  save: (value: string, close: () => void) => Promise<void> | void,
): void {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="form-row">
      <label>${label}</label>
      <input class="field" id="modal-input" maxlength="60" />
    </div>`;
  const input = body.querySelector<HTMLInputElement>("#modal-input")!;
  input.value = value;

  openModal({
    title,
    body,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Save",
        variant: "primary",
        onClick: async (close) => {
          await save(input.value.trim(), close);
        },
      },
    ],
  });
  setTimeout(() => input.focus(), 40);
}

async function activateProfile(): Promise<void> {
  const res = await api("profile_activate", selectedProfile);
  if (!res.ok) {
    toast({ title: "Switch failed", message: res.error, level: "danger" });
    return;
  }
  toast({ title: "Profile active", message: selectedProfile, level: "success" });
  void loadProfiles();
}

function createProfile(): void {
  inputModal("New profile", "Name", "", async (name, close) => {
    if (!name) return;
    const res = await api("profile_create", name);
    if (!res.ok) {
      toast({ title: "Create failed", message: res.error, level: "danger" });
      return;
    }
    close();
    selectedProfile = name;
    void loadProfiles();
    toast({ title: "Profile created", message: name, level: "success" });
  });
}

function renameProfile(): void {
  const current = profiles.find((p) => p.name === selectedProfile);
  if (!current) return;
  inputModal("Rename profile", "New name", current.name, async (name, close) => {
    const res = await api("profile_rename", selectedProfile, name);
    if (!res.ok) {
      toast({ title: "Rename failed", message: res.error, level: "danger" });
      return;
    }
    close();
    selectedProfile = name;
    void loadProfiles();
  });
}

function deleteProfile(): void {
  const current = profiles.find((p) => p.name === selectedProfile);
  if (!current) return;
  openModal({
    title: "Delete profile",
    body: `<p>Delete profile <strong>${current.name}</strong> and all its mods? This cannot be undone.</p>`,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Delete",
        variant: "danger",
        onClick: async (close) => {
          const res = await api("profile_delete", selectedProfile);
          if (!res.ok) {
            toast({ title: "Delete failed", message: res.error, level: "danger" });
            return;
          }
          close();
          selectedProfile = activeProfile;
          void loadProfiles();
        },
      },
    ],
  });
}

/* --------------------------------------------------------------- actions */

async function importMods(): Promise<void> {
  const res = await api("mod_import");
  if (!res.ok) toast({ title: "Import failed", message: res.error, level: "danger" });
}

function scanIssues(): void {
  void api("mod_issues");
  toast({ title: "Scanning mods…", timeout: 1800 });
}

function showIssues(issues: any[]): void {
  const notice = $("mods-issues-notice");
  if (!issues.length) {
    notice.classList.remove("show");
    toast({ title: "No issues found", level: "success" });
    return;
  }
  $("mods-issues-text").textContent = issues
    .map((i) => i.description)
    .join("  •  ");
  notice.classList.add("show");
}
