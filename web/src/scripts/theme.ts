/* Web theme registry -------------------------------------------------------
 * Palettes are defined in CSS (`styles/themes.css`); this module owns the
 * preset metadata and the single place that writes `data-theme`.
 */

export type ThemeMode = "dark" | "light";

export interface WebTheme {
  id: string;
  label: string;
  mode: ThemeMode;
  description: string;
  swatch: [string, string, string];
}

export const WEB_THEMES: WebTheme[] = [
  {
    id: "aurora",
    label: "Aurora",
    mode: "dark",
    description: "The original indigo glow. Still the default.",
    swatch: ["#0e1016", "#6366f1", "#22d3ee"],
  },
  {
    id: "aurora-light",
    label: "Aurora Light",
    mode: "light",
    description: "The original light look, now its own preset.",
    swatch: ["#f4f5f9", "#6366f1", "#22d3ee"],
  },
  {
    id: "forest",
    label: "Forest",
    mode: "dark",
    description: "Flat green fills, tight corners, no glow.",
    swatch: ["#07110c", "#4ade80", "#a3e635"],
  },
  {
    id: "violet",
    label: "Violet",
    mode: "dark",
    description: "Neon glass with bright, sharp edges.",
    swatch: ["#0d0a18", "#a78bfa", "#f472b6"],
  },
  {
    id: "ember",
    label: "Ember",
    mode: "dark",
    description: "Warm orange pills that lift on hover.",
    swatch: ["#130d0a", "#fb923c", "#f43f5e"],
  },
  {
    id: "slate",
    label: "Slate",
    mode: "dark",
    description: "Calm blue-gray with an underline marker.",
    swatch: ["#0c1118", "#60a5fa", "#94a3b8"],
  },
  {
    id: "mono",
    label: "Mono",
    mode: "dark",
    description: "Hard-edged terminal outline style.",
    swatch: ["#08090b", "#e8eaed", "#9aa0a8"],
  },
  {
    id: "winter",
    label: "Winter",
    mode: "dark",
    description: "Frosted ice, slow snowfall and a snowy backdrop.",
    swatch: ["#0b1d2b", "#bfe9ff", "#7dd3fc"],
  },
];

/** Event name -> web preset forced while that event is active. */
export const EVENT_THEMES: Record<string, string> = {
  winter: "winter",
};

export const EVENT_THEME_IDS = new Set(Object.values(EVENT_THEMES));
export const DEFAULT_WEB_THEME = "aurora";

const LEGACY: Record<string, string> = {
  dark: "aurora",
  light: "aurora-light",
};

const IDS = new Set(WEB_THEMES.map((theme) => theme.id));

/** Accept old `dark`/`light` values and ignore unknown ones. */
export function normalizeWebTheme(value: unknown): string {
  const raw = typeof value === "string" ? value.trim().toLowerCase() : "";
  const id = LEGACY[raw] || raw;
  return IDS.has(id) ? id : DEFAULT_WEB_THEME;
}

export function webTheme(id: string): WebTheme {
  return WEB_THEMES.find((theme) => theme.id === id) || WEB_THEMES[0];
}

/**
 * Seasonal events win over the saved preset while active; the saved value
 * returns automatically once the event ends.
 */
export function effectiveWebTheme(value: unknown, eventName?: string): string {
  const eventTheme = eventName ? EVENT_THEMES[eventName] : undefined;
  if (eventTheme) return eventTheme;
  const id = normalizeWebTheme(value);
  // Event-only presets disappear when no event is active.
  return EVENT_THEME_IDS.has(id) ? DEFAULT_WEB_THEME : id;
}

/**
 * Apply a preset immediately. `animate` is false at boot so the first paint
 * never flashes a transition; later picker changes cross-fade gently.
 */
export function applyWebTheme(
  value: unknown,
  animate = true,
  persist = true,
): WebTheme {
  const id = normalizeWebTheme(value);
  const theme = webTheme(id);
  const root = document.documentElement;
  const changed = root.dataset.theme !== id;

  root.dataset.theme = id;
  if (persist) {
    try {
      localStorage.setItem("cl-web-theme", id);
    } catch (_) {
      /* hardened webviews may deny storage; the bridge value still wins */
    }
  }

  if (animate && changed) {
    root.classList.add("theme-shift");
    window.setTimeout(() => root.classList.remove("theme-shift"), 200);
  }
  return theme;
}
