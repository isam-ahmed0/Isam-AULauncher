/* Settings view: persisted preferences, interfaces and Linux tuning --------- */

import { api, isDesktop } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { confirmModal } from "../modal";
import { store, subscribe, update } from "../store";
import {
  EVENT_THEME_IDS,
  WEB_THEMES,
  applyWebTheme,
  effectiveWebTheme,
  normalizeWebTheme,
} from "../theme";
import { applyWinterFx, normalizeWinterChoice } from "../winter";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

type Settings = Record<string, any>;
let values: Settings = {};
let loaded = false;
let lastEvent = store.event;

function eventActive(): boolean {
  return store.event.active && (store.event.fx || Boolean(store.event.theme));
}

function activeEventName(): string | undefined {
  return store.event.active && store.event.theme ? store.event.name : undefined;
}

function eventThemeVisible(id: string): boolean {
  return store.event.active && store.event.theme === id;
}

function applyTheme(value: unknown, animate = true): void {
  const eventName = activeEventName();
  applyWebTheme(effectiveWebTheme(value, eventName), animate, !eventName);
}

function applyWinter(): void {
  applyWinterFx(values.winter_fx, values.winter_bg);
}

function applyEventVisibility(): void {
  const active = eventActive();
  for (const id of ["winter-event-row", "winter-fx-row", "winter-bg-row"]) {
    $(id).hidden = !active;
  }
}

export function initSettings(): void {
  applyEventVisibility();
  renderThemeCards();
  setThemeCards(effectiveWebTheme(store.settings.web_theme, activeEventName()));
  wireSegmented("setting-backend", "display_backend");
  wireSwitch("setting-auto-update", "auto_update");
  wireSwitch("setting-discord", "discord_rpc");
  wireSwitch("setting-shortcuts", "create_shortcuts");
  wireSwitch("setting-warn-wine", "warn_plain_wine");
  wireWinterSwitch("setting-winter-fx", "winter_fx");
  wireWinterSwitch("setting-winter-bg", "winter_bg");

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

  // Event state arrives after the page boots; show/hide event-only UI then.
  subscribe(() => {
    if (lastEvent === store.event) return;
    lastEvent = store.event;
    applyEventVisibility();
    renderThemeCards();
    setThemeCards(effectiveWebTheme(
      loaded ? values.web_theme : store.settings.web_theme,
      activeEventName(),
    ));
    applyWinter();
    applyEventBadge();
  });
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
  applyEventVisibility();
  renderThemeCards();
  applyTheme(values.web_theme);
  setThemeCards(effectiveWebTheme(values.web_theme, activeEventName()));
  applyWinter();
  applyEventBadge();

  setSegmented("setting-backend", values.display_backend || "");
  setSwitch("setting-auto-update", values.auto_update !== false);
  setSwitch("setting-discord", values.discord_rpc !== false);
  setSwitch("setting-shortcuts", values.create_shortcuts !== false);
  setSwitch("setting-warn-wine", values.warn_plain_wine !== false);
  setSwitch("setting-winter-fx", normalizeWinterChoice(values.winter_fx) !== "off");
  setSwitch("setting-winter-bg", normalizeWinterChoice(values.winter_bg) !== "off");

  ($("setting-theme") as HTMLSelectElement).value = values.theme || "Forest";
  ($("setting-ui-mode") as HTMLSelectElement).value = values.ui_mode || "web";

  const linux = store.app.platform === "linux";
  $("settings-linux").hidden = !linux;
  $("setting-backend-row").hidden = !linux;
  applySystem();
}

function applyEventBadge(): void {
  if (!eventActive()) return;
  const badge = $("winter-event-badge");
  const desc = $("winter-event-desc");
  badge.textContent = store.event.forced ? "Test" : "Active";
  const when = store.event.end_date ? ` until ${store.event.end_date}` : "";
  desc.textContent = `${store.event.forced ? "Forced with --event" : "Seasonal event"}${when}. Winter is the default theme; its snow and frost are on automatically and can also be layered on any preset.`;
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
  if (key === "web_theme") {
    applyTheme(value, false);
    setThemeCards(effectiveWebTheme(value, activeEventName()));
  }
  if (key === "winter_fx" || key === "winter_bg") applyWinter();
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

function renderThemeCards(): void {
  const host = $("setting-web-theme");
  host.replaceChildren();

  for (const theme of WEB_THEMES) {
    if (EVENT_THEME_IDS.has(theme.id) && !eventThemeVisible(theme.id)) continue;
    const card = document.createElement("button");
    card.type = "button";
    card.className = "theme-card";
    card.dataset.themeId = theme.id;
    card.setAttribute("aria-pressed", "false");

    const top = document.createElement("span");
    top.className = "tc-top";
    const swatches = document.createElement("span");
    swatches.className = "tc-swatches";
    for (const color of theme.swatch) {
      const swatch = document.createElement("i");
      swatch.style.setProperty("--sw", color);
      swatches.appendChild(swatch);
    }
    const name = document.createElement("span");
    name.className = "tc-name";
    name.textContent = theme.label;
    const mode = document.createElement("span");
    mode.className = "tc-mode";
    mode.textContent = theme.mode;
    top.append(swatches, name, mode);

    const desc = document.createElement("span");
    desc.className = "tc-desc";
    desc.textContent = theme.description;

    // Scoped preset tokens paint a real miniature of that theme's buttons.
    const sample = document.createElement("span");
    sample.className = "tc-sample";
    sample.dataset.previewTheme = theme.id;
    const primary = document.createElement("span");
    primary.className = "tc-btn";
    primary.textContent = "Play";
    const ghost = document.createElement("span");
    ghost.className = "tc-btn ghost";
    ghost.textContent = "Ghost";
    sample.append(primary, ghost);

    card.append(top, desc, sample);
    card.addEventListener("click", () => void chooseTheme(theme.id));
    host.appendChild(card);
  }
}

function setThemeCards(id: string): void {
  for (const card of $("setting-web-theme").querySelectorAll<HTMLButtonElement>(
    ".theme-card",
  )) {
    const on = card.dataset.themeId === id;
    card.classList.toggle("on", on);
    card.setAttribute("aria-pressed", String(on));
  }
}

async function chooseTheme(id: string): Promise<void> {
  const value = normalizeWebTheme(id);
  setThemeCards(value);
  applyWebTheme(value);
  applyWinter();
  if (!isDesktop()) {
    toast({
      title: "Preview only",
      message: "Theme applied here, but browser preview cannot save it.",
      level: "info",
      timeout: 2200,
    });
    return;
  }
  await save("web_theme", value);
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

// "auto" shows as on; switching it off then on makes it an explicit layer.
function wireWinterSwitch(id: string, key: string): void {
  $(id).addEventListener("click", () => {
    const next = !$(id).classList.contains("on");
    setSwitch(id, next);
    void save(key, next ? "on" : "off");
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
