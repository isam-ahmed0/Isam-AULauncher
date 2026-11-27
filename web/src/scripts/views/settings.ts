/* Settings view: persisted preferences, interfaces and Linux tuning --------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { confirmModal } from "../modal";
import { store, update } from "../store";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

type Settings = Record<string, any>;
let values: Settings = {};
let loaded = false;

/** Applied at boot and whenever the web-theme preference changes. */
export function applyWebTheme(theme: string): void {
  document.documentElement.dataset.theme = theme === "light" ? "light" : "dark";
}

export function initSettings(): void {
  wireSegmented("setting-web-theme", "web_theme");
  wireSegmented("setting-backend", "display_backend");
  wireSwitch("setting-auto-update", "auto_update");
  wireSwitch("setting-discord", "discord_rpc");
  wireSwitch("setting-shortcuts", "create_shortcuts");
  wireSwitch("setting-warn-wine", "warn_plain_wine");

  ($("setting-theme") as HTMLSelectElement).addEventListener("change", (e) => {
    void save("theme", (e.target as HTMLSelectElement).value);
  });
  ($("setting-ui-mode") as HTMLSelectElement).addEventListener("change", (e) => {
    void changeInterface((e.target as HTMLSelectElement).value);
  });
  ($("setting-gpu") as HTMLSelectElement).addEventListener("change", (e) => {
    void save("gpu_id", (e.target as HTMLSelectElement).value);
  });
  ($("setting-wine-binary") as HTMLSelectElement).addEventListener("change", (e) => {
    void save("wine_binary", (e.target as HTMLSelectElement).value);
  });

  $("settings-open-config").addEventListener("click", () => {
    if (store.paths.appdata) void api("open_path", store.paths.appdata);
  });
  $("settings-restart").addEventListener("click", async () => {
    if (await confirmModal("Restart launcher", "Save changes and restart now?", "Restart")) {
      void api("app_restart");
    }
  });

  on("system", () => applySystem());
}

export async function loadSettings(force = false): Promise<void> {
  if (loaded && !force) return;
  const res = await api<Settings>("settings_get");
  if (!res.ok || !res.data) {
    toast({ title: "Settings failed", message: res.ok ? "" : res.error, level: "danger" });
    return;
  }
  values = res.data;
  loaded = true;

  // The startup "system" event may have been missed; read it directly too.
  const sys = await api<any>("system_info");
  if (sys.ok && sys.data) {
    update({ system: { ...store.system, ...sys.data } });
  }
  applyForm();
}

function applyForm(): void {
  applyWebTheme(values.web_theme || "dark");

  setSegmented("setting-web-theme", values.web_theme || "dark");
  setSegmented("setting-backend", values.display_backend || "");
  setSwitch("setting-auto-update", values.auto_update !== false);
  setSwitch("setting-discord", values.discord_rpc !== false);
  setSwitch("setting-shortcuts", values.create_shortcuts !== false);
  setSwitch("setting-warn-wine", values.warn_plain_wine !== false);

  ($("setting-theme") as HTMLSelectElement).value = values.theme || "Forest";
  ($("setting-ui-mode") as HTMLSelectElement).value = values.ui_mode || "web";

  const linux = store.app.platform === "linux";
  $("settings-linux").hidden = !linux;
  $("setting-backend-row").hidden = !linux;
  applySystem();
}

function applySystem(): void {
  fillGpus();
  fillWines();
  const runner = store.system.runner || store.system.wine;
  const kind = store.system.runner_kind === "proton" ? "Proton" : "Wine";
  $("settings-wine-detected").textContent = runner ? `${kind} — ${runner}` : "Not found";
  $("setting-wine-prefix").textContent = store.system.prefix || "—";
}

function fillWines(): void {
  const select = $("setting-wine-binary") as HTMLSelectElement;
  const current = values.wine_binary || store.system.wine_binary || "";
  select.replaceChildren();

  const auto = document.createElement("option");
  auto.value = "";
  auto.textContent = "Auto-detect (prefers Proton)";
  select.appendChild(auto);

  const runners = store.system.runners || store.system.wines || [];
  let found = current === "";
  for (const runner of runners) {
    const option = document.createElement("option");
    option.value = runner.path;
    const kind = runner.kind === "proton" ? "Proton" : "Wine";
    option.textContent = `${kind} · ${runner.name} — ${runner.path}`;
    select.appendChild(option);
    if (runner.path === current) found = true;
  }
  if (current && !found) {
    // Keep an existing configured runner visible even if it is not detected now.
    const option = document.createElement("option");
    option.value = current;
    option.textContent = `Configured: ${current}`;
    select.appendChild(option);
  }
  select.value = current;
}

function fillGpus(): void {
  const select = $("setting-gpu") as HTMLSelectElement;
  const current = values.gpu_id || select.value || "";
  select.replaceChildren();
  const auto = document.createElement("option");
  auto.value = "";
  auto.textContent = "System default";
  select.appendChild(auto);
  for (const gpu of store.system.gpus || []) {
    const option = document.createElement("option");
    option.value = gpu.id || "";
    option.textContent = gpu.name || gpu.id || "Unknown GPU";
    select.appendChild(option);
  }
  select.value = current;
  $("settings-gpu-desc").textContent = store.system.gpus?.length
    ? `${store.system.gpus.length} adapter(s) detected`
    : "Auto-detected from the system.";
}

async function save(key: string, value: unknown): Promise<boolean> {
  const previous = values[key];
  values[key] = value;
  const res = await api("settings_set", key, value);
  if (!res.ok) {
    values[key] = previous;
    toast({ title: "Could not save setting", message: res.error, level: "danger" });
    applyForm();
    return false;
  }
  update({ settings: { ...store.settings, [key]: value } as typeof store.settings });
  if (key === "web_theme") applyWebTheme(String(value));
  return true;
}

async function changeInterface(mode: string): Promise<void> {
  if (!(await save("ui_mode", mode))) return;
  const restart = await confirmModal(
    "Switch interface",
    `Restart now to use the ${mode === "web" ? "Web" : mode.toUpperCase()} interface?`,
    "Restart",
  );
  if (restart) await api("app_restart");
  else toast({ title: "Saved", message: "Restart to apply the new interface.", level: "info" });
}

function setSwitch(id: string, on: boolean): void {
  $(id).classList.toggle("on", on);
}

function setSegmented(id: string, value: string): void {
  for (const button of $(id).querySelectorAll<HTMLButtonElement>("button")) {
    button.classList.toggle("on", (button.dataset.value ?? "") === value);
  }
}

function wireSwitch(id: string, key: string): void {
  $(id).addEventListener("click", () => {
    const next = !$(id).classList.contains("on");
    setSwitch(id, next);
    void save(key, next);
  });
}

function wireSegmented(id: string, key: string): void {
  for (const button of $(id).querySelectorAll<HTMLButtonElement>("button")) {
    button.addEventListener("click", () => {
      const value = button.dataset.value ?? "";
      setSegmented(id, value);
      void save(key, value);
    });
  }
}
