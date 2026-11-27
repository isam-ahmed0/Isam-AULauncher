/* About view: versions, links, paths and log diagnostics -------------------- */

import { api } from "../bridge";
import { store } from "../store";
import { toast } from "../toast";
import { checkUpdates } from "./updates";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

let loaded = false;

export function initAbout(): void {
  $("about-check-updates").addEventListener("click", () => void checkUpdates());
  $("about-log-refresh").addEventListener("click", () => void loadLog());
  for (const link of document.querySelectorAll<HTMLAnchorElement>("[data-external]")) {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      void api("open_url", link.href);
    });
  }
}

export async function loadAbout(): Promise<void> {
  if (loaded) return;
  const res = await api<any>("app_info");
  if (res.ok && res.data) {
    loaded = true;
    $("about-launcher").textContent = `v${res.data.launcher_version || "—"}`;
    $("about-game").textContent = res.data.game_version || "—";
    $("about-platform").textContent = res.data.platform || "—";
  }
  const paths = store.paths;
  $("about-paths").textContent = [
    `App data     ${paths.appdata || "—"}`,
    `Profiles     ${paths.profiles || "—"}`,
    `Interfaces   ${paths.guis || "—"}`,
    `Log          ${paths.log || "—"}`,
  ].join("\n");
  await loadLog();
}

async function loadLog(): Promise<void> {
  const res = await api<string>("log_text", 120);
  $("about-log").textContent = res.ok && res.data
    ? res.data
    : res.ok ? "No log entries." : `Could not read log: ${res.error}`;
}
