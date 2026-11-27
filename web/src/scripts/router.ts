/* Client-side view switching ----------------------------------------------- */

const VIEWS = [
  "home",
  "mods",
  "browse",
  "regions",
  "news",
  "updates",
  "profile",
  "settings",
  "about",
] as const;

export type ViewId = (typeof VIEWS)[number];

export function isView(id: string): id is ViewId {
  return (VIEWS as readonly string[]).includes(id);
}

type Listener = (view: ViewId) => void;
const listeners = new Set<Listener>();
let current: ViewId = "home";

export function currentView(): ViewId {
  return current;
}

export function onNavigate(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function navigate(view: string): void {
  if (!isView(view)) return;
  current = view;

  for (const section of document.querySelectorAll<HTMLElement>(".view")) {
    section.classList.toggle("active", section.dataset.view === view);
  }
  for (const item of document.querySelectorAll<HTMLElement>(".nav-item")) {
    item.classList.toggle("active", item.dataset.view === view);
  }

  const content = document.getElementById("content");
  if (content) content.scrollTop = 0;

  try {
    history.replaceState(null, "", `#${view}`);
  } catch {
    /* file:// may deny history writes — harmless */
  }

  for (const listener of [...listeners]) {
    try {
      listener(current);
    } catch (err) {
      console.error("[router] listener failed", err);
    }
  }
}

export function initRouter(): void {
  for (const item of document.querySelectorAll<HTMLButtonElement>(".nav-item")) {
    item.addEventListener("click", () => navigate(item.dataset.view ?? "home"));
  }
  for (const btn of document.querySelectorAll<HTMLElement>("[data-goto]")) {
    btn.addEventListener("click", () => navigate(btn.dataset.goto ?? "home"));
  }

  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (isView(hash)) navigate(hash);
}
