/* Account view: itch.io link state and OAuth flow --------------------------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { confirmModal } from "../modal";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

let loaded = false;

export function initAccount(): void {
  $("itch-signin").addEventListener("click", signIn);
  $("itch-signout").addEventListener("click", signOut);
  on("itch_status", (data) => applyStatus(data));
}

export async function loadAccount(): Promise<void> {
  if (loaded) return;
  const res = await api<any>("itch_status");
  if (res.ok && res.data) applyStatus(res.data);
}

function applyStatus(data: any): void {
  if (!data) return;
  loaded = true;
  const signedIn = Boolean(data.signed_in);
  const username = data.username || data.profile?.username || "";
  const gameName = data.profile?.among_us_name || "";
  const platforms: string[] = data.profile?.platforms || [];

  $("itch-name").textContent = signedIn
    ? (username || gameName || "itch.io account linked")
    : "Not signed in";
  $("itch-subtitle").textContent = signedIn
    ? "Your itch.io token is saved where the game can use it."
    : "Sign in to link the game to your itch.io profile.";
  $("itch-state").textContent = signedIn ? "Linked" : "No token";
  $("itch-state").className = `pill${signedIn ? " success" : ""}`;
  $("itch-username").textContent = username || "—";
  $("itch-game-name").textContent = gameName || "—";
  $("itch-platforms").textContent = platforms.length ? platforms.join(", ") : "—";
  $("itch-prefix").textContent = data.prefix || "System default";

  const tags = $("itch-tags");
  tags.replaceChildren();
  for (const label of platforms.slice(0, 5)) {
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = label;
    tags.appendChild(pill);
  }

  $("itch-signin").hidden = signedIn;
  $("itch-signout").hidden = !signedIn;
}

async function signIn(): Promise<void> {
  const res = await api("itch_login");
  if (!res.ok) toast({ title: "Sign-in failed", message: res.error, level: "danger" });
}

async function signOut(): Promise<void> {
  const ok = await confirmModal(
    "Sign out of itch.io",
    "Remove the saved token? Among Us will no longer see your itch.io account.",
    "Sign out",
    true,
  );
  if (!ok) return;
  const res = await api("itch_logout");
  if (!res.ok) toast({ title: "Sign-out failed", message: res.error, level: "danger" });
  else toast({ title: "Signed out", level: "success" });
}
