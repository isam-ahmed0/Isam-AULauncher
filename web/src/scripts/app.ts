/* CrewLauncher web app entry ------------------------------------------------ */

import { api, bridgeAvailable, isDesktop } from "./bridge";
import "./events"; // installs window.__clEvent before Python can push
import { store, update, type EventState } from "./store";
import { on } from "./events";
import { initRouter, onNavigate, currentView } from "./router";
import { toast } from "./toast";
import { initHome, render as renderHome } from "./views/home";
import { initMods, loadProfiles } from "./views/mods";
import { initAssets, loadAssets } from "./views/assets";
import { initBrowse, loadCatalog } from "./views/browse";
import { initRegions, loadRegions } from "./views/regions";
import { initNews, loadNews } from "./views/news";
import { initAccount, loadAccount } from "./views/account";
import { initSettings, loadSettings } from "./views/settings";
import { applyWebTheme, effectiveWebTheme } from "./theme";
import { applyWinterFx, initWinterFx } from "./winter";
import { initUpdates, loadUpdates } from "./views/updates";
import { initAbout, loadAbout } from "./views/about";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

function initTitleBar(): void {
  $("win-min").addEventListener("click", () => void api("win_min"));
  $("win-max").addEventListener("click", () => void api("win_toggle_max"));
  $("win-close").addEventListener("click", () => void api("win_close"));

  // Double-click on the drag region toggles maximize (native behavior).
  $("titlebar-drag").addEventListener("dblclick", () => {
    void api("win_toggle_max");
  });
}

function initKeyboard(): void {
  window.addEventListener("keydown", (e) => {
    const target = e.target as HTMLElement | null;
    const typing =
      target &&
      (target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable);
    if (typing) return;

    if (e.key === "F5" || (e.ctrlKey && e.key.toLowerCase() === "r")) {
      e.preventDefault();
      void refresh();
    }
  });
}

function applyGameState(data: any): void {
  if (!data) return;
  update({ game: { ...store.game, ...data } });
  renderHome();
}

/** Re-read the authoritative local state; returns false on bridge errors. */
async function syncGameState(showToast = false): Promise<boolean> {
  const res = await api<any>("game_state");
  if (!res.ok || !res.data) return false;
  applyGameState(res.data);
  if (showToast) toast({ title: "Refreshed", level: "info", timeout: 1800 });
  return true;
}

async function refresh(): Promise<void> {
  await syncGameState(true);
}

function wireEvents(): void {
  on("status", (data) => {
    const sb = $("sb-status");
    if (sb && data?.text) sb.textContent = data.text;
    const dot = $("sb-dot");
    if (dot) {
      const level = data?.level ?? "info";
      dot.className = `dot ${level === "danger" ? "danger" : level === "warning" ? "warning" : level === "success" ? "success" : "info"}`;
    }
  });

  on("toast", (data) =>
    toast({
      title: data?.title ?? "Launcher",
      message: data?.message ?? "",
      level: data?.level ?? "info",
    }),
  );

  on("window_state", (data) => {
    store.maximized = Boolean(data?.maximized);
    const icon = $("win-max").querySelector("use");
    if (icon) icon.setAttribute("href", store.maximized ? "#i-minus" : "#i-maximize");
    $("win-max").title = store.maximized ? "Restore" : "Maximize";
  });

  on("game_state", (data) => applyGameState(data));
}

function applyTheme(animate = false): void {
  const eventName = store.event.active ? store.event.name : undefined;
  // Event themes are temporary: never mirror them over the saved preference.
  applyWebTheme(
    effectiveWebTheme(store.settings.web_theme, eventName),
    animate,
    !eventName,
  );
}

function applyWinter(animate = false): void {
  applyWinterFx(store.settings.winter_fx, store.settings.winter_bg, animate);
}

async function syncEvent(): Promise<void> {
  if (!isDesktop()) return;
  const res = await api<EventState>("event_info");
  if (res.ok && res.data) {
    update({ event: { ...store.event, ...res.data } });
    applyTheme();
    applyWinter();
  }
}

async function boot(): Promise<void> {
  initWinterFx();
  applyTheme();
  applyWinter();
  initTitleBar();
  initRouter();
  initKeyboard();
  wireEvents();
  initHome();
  initMods();
  initAssets();
  initBrowse();
  initRegions();
  initNews();
  initAccount();
  initSettings();
  initUpdates();
  initAbout();

  onNavigate((view) => {
    if (!isDesktop()) return;
    if (view === "mods") void loadProfiles();
    if (view === "assets") void loadAssets();
    if (view === "browse") void loadCatalog(false);
    if (view === "regions") void loadRegions();
    if (view === "news") void loadNews(false);
    if (view === "profile") void loadAccount();
    if (view === "settings") void loadSettings(false);
    if (view === "updates") void loadUpdates();
    if (view === "about") void loadAbout();
  });

  if (!(await bridgeAvailable())) {
    update({ preview: true, booted: true });
    $("sb-status").textContent = "Browser preview — Python bridge unavailable";
    $("hero-badge").textContent = "PREVIEW";
    $("hero-sub").textContent =
      "You are viewing the static build. Launch through CrewLauncher for live data.";
    $("sidebar-version").textContent = "preview";
    return;
  }

  // Tell Python the page is up first: flush queued events and start background
  // polls before asking for the initial snapshot.
  const ready = await api("ready");
  if (!ready.ok) {
    console.error("ready() failed", ready.error);
  }

  await syncEvent();

  const res = await api<any>("bootstrap");
  let bootstrapped = false;
  if (res.ok && res.data) {
    const data = res.data;
    update({
      app: data.app ?? store.app,
      game: { ...store.game, ...(data.state ?? {}) },
      settings: { ...store.settings, ...(data.settings ?? {}) },
      home: { ...store.home, ...(data.home ?? {}) },
      paths: { ...store.paths, ...(data.paths ?? {}) },
      booted: true,
    });
    bootstrapped = true;
  } else {
    console.error("bootstrap failed", res.ok ? "empty response" : res.error);
    update({ booted: true });
  }
  applyTheme();
  applyWinter();

  // Re-read local state after bootstrap. If the first bridge call was lost,
  // this still paints the correct installed version on the first screen.
  const synced = await syncGameState();
  if (!synced && !bootstrapped) {
    $("sb-status").textContent = "Could not read game state";
    toast({
      title: "Startup error",
      message: "Game state is unavailable; use the refresh button to retry.",
      level: "danger",
    });
  }
  renderHome();

  const sbVersion = $("sb-version");
  if (sbVersion) {
    sbVersion.textContent =
      `Launcher ${store.app.launcher_version} · Game ${store.game.version || "—"}`;
  }

  // Self-heal any missed state event while the window is open.
  window.setInterval(() => {
    if (isDesktop()) void syncGameState();
  }, 10000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && isDesktop()) void syncGameState();
  });

  onNavigate((view) => {
    document.title =
      view === "home" ? "CrewLauncher" : `CrewLauncher — ${view}`;
  });
  document.title =
    currentView() === "home"
      ? "CrewLauncher"
      : `CrewLauncher — ${currentView()}`;
}

void boot();
