/* Updates view: launcher + game versions, install/skip/check actions -------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { store } from "../store";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

type UpdateState = {
  available?: boolean;
  needed?: boolean;
  version?: string | null;
  latest?: string | null;
  current?: string;
  skipped?: boolean;
};

let game: UpdateState = {};
let launcher: UpdateState = {};
let loaded = false;

export function initUpdates(): void {
  $("updates-check").addEventListener("click", () => void checkUpdates());
  $("updates-auto").addEventListener("click", () => toggle("auto_update", "updates-auto"));
  $("updates-mods").addEventListener("click", () => toggle("auto_check_mod_updates", "updates-mods"));

  on("update_check", (data) => applyGame(data));
  on("game_update", (data) => applyGame(data));
  on("launcher_update", (data) => applyLauncher(data));
  on("toast", (data) => {
    if (data?.title === "Install complete" || data?.title === "Install failed") {
      void checkUpdates();
    }
  });
}

export async function loadUpdates(): Promise<void> {
  if (loaded) return;
  const res = await api<Record<string, any>>("settings_get");
  if (res.ok && res.data) {
    loaded = true;
    $("updates-auto").classList.toggle("on", res.data.auto_update !== false);
    $("updates-mods").classList.toggle("on", res.data.auto_check_mod_updates !== false);
  }
  render();
}

export async function checkUpdates(): Promise<void> {
  $("launcher-update-detail").textContent = "Checking the latest release…";
  $("game-update-detail").textContent = "Checking the installed version…";
  const res = await api("update_check");
  if (!res.ok) toast({ title: "Update check failed", message: res.error, level: "danger" });
}

async function toggle(key: string, id: string): Promise<void> {
  const next = !$(id).classList.contains("on");
  $(id).classList.toggle("on", next);
  const res = await api("settings_set", key, next);
  if (!res.ok) {
    $(id).classList.toggle("on", !next);
    toast({ title: "Could not save setting", message: res.error, level: "danger" });
  }
}

function applyGame(data: any): void {
  if (!data) return;
  game = data;
  render();
}

function applyLauncher(data: any): void {
  if (!data) return;
  launcher = data;
  render();
}

function action(label: string, variant: string, run: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.className = `btn${variant ? ` ${variant}` : ""}`;
  button.textContent = label;
  button.addEventListener("click", run);
  return button;
}

function render(): void {
  const gameAvailable = Boolean(game.needed) && !game.skipped;
  const gameVersion = game.latest || game.version || "";
  const gameState = $("game-update-state");
  gameState.textContent = game.skipped ? "Skipped" : gameAvailable ? "Update available" : "Up to date";
  gameState.className = `pill${gameAvailable ? " warning" : game.skipped ? "" : " success"}`;
  $("game-update-detail").textContent = gameVersion
    ? gameAvailable
      ? `Version ${gameVersion} is ready to install. Current: ${store.game.version || "unknown"}.`
      : `Running ${store.game.version || gameVersion}.`
    : "Installed version is current.";

  const gameActions = $("game-update-actions");
  gameActions.replaceChildren();
  if (gameAvailable && gameVersion) {
    gameActions.appendChild(action("Update now", "primary", async () => {
      const res = await api("game_install");
      if (!res.ok) toast({ title: "Update failed", message: res.error, level: "danger" });
    }));
    gameActions.appendChild(action("Skip version", "ghost", async () => {
      await api("update_skip_game", gameVersion);
      game = { ...game, skipped: true };
      render();
    }));
  }

  const launcherAvailable = Boolean(launcher.available) && !launcher.skipped;
  const launcherVersion = launcher.version || "";
  const launcherState = $("launcher-update-state");
  launcherState.textContent = launcher.skipped
    ? "Skipped"
    : launcherAvailable ? "Update available" : "Up to date";
  launcherState.className = `pill${launcherAvailable ? " warning" : launcher.skipped ? "" : " success"}`;
  $("launcher-update-detail").textContent = launcherVersion
    ? `Current v${launcher.current || store.app.launcher_version} · latest v${launcherVersion}.`
    : `Current v${store.app.launcher_version || "unknown"}. No newer release found.`;
  $("launcher-update-card").classList.toggle("available", launcherAvailable);

  const launcherActions = $("launcher-update-actions");
  launcherActions.replaceChildren();
  if (launcherAvailable && launcherVersion) {
    const isWindows = store.app.platform === "windows";
    launcherActions.appendChild(action(
      isWindows ? "Install now" : "Open downloads",
      "primary",
      async () => {
        const res = await api("update_launcher", launcherVersion);
        if (!res.ok) toast({ title: "Update failed", message: res.error, level: "danger" });
      },
    ));
    launcherActions.appendChild(action("Skip version", "ghost", async () => {
      await api("update_skip_launcher", launcherVersion);
      launcher = { ...launcher, skipped: true };
      render();
    }));
  }
}
