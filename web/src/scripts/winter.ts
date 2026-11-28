/* Winter effects -----------------------------------------------------------
 * Event-only visuals: snow/frost/background run only while a resolved event
 * says they may. The auto/on/off switches fine-tune that window; they cannot
 * reveal or start the effects outside it. Snow is a capped canvas loop that
 * pauses when hidden.
 */

export type WinterChoice = "auto" | "on" | "off";

export const WINTER_EVENT = "winter";

const FX_KEY = "cl-winter-fx";
const BG_KEY = "cl-winter-bg";

interface Flake {
  x: number;
  y: number;
  r: number;
  vy: number;
  drift: number;
  phase: number;
  alpha: number;
  kind: 0 | 1; // 0 = soft streak, 1 = six-arm crystal
}

let initialized = false;
let canvas: HTMLCanvasElement | null = null;
let context: CanvasRenderingContext2D | null = null;
let flakes: Flake[] = [];
let frame = 0;
let last = 0;
let width = 0;
let height = 0;
let dpr = 1;
let fxChoice: WinterChoice = "auto";
let bgChoice: WinterChoice = "auto";
let active = false;
let background = false;
let eventGate = false;
let reduceMotion = false;

/** Legacy booleans from saved configs still make sense. */
export function normalizeWinterChoice(value: unknown): WinterChoice {
  if (typeof value === "boolean") return value ? "on" : "off";
  const raw = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (raw === "" || raw === "auto" || raw === "default") return "auto";
  if (raw === "1" || raw === "true" || raw === "on" || raw === "yes") return "on";
  return "off";
}

function readChoice(key: string): WinterChoice {
  try {
    const value = localStorage.getItem(key);
    if (value !== null) return normalizeWinterChoice(value);
  } catch (_) {
    /* hardened webviews may deny storage */
  }
  return "auto";
}

function writeChoice(key: string, value: WinterChoice): void {
  try {
    localStorage.setItem(key, value);
  } catch (_) {
    /* hardened webviews may deny storage */
  }
}

/** Fine-tuning inside an active event; the event gate is checked by refresh(). */
function resolve(choice: WinterChoice, winterTheme: boolean): boolean {
  return choice === "on" || (choice === "auto" && winterTheme);
}

function forcedByUrl(): boolean {
  try {
    return (new URLSearchParams(location.search).get("event") || "") === WINTER_EVENT;
  } catch (_) {
    return false;
  }
}

function seedFlakes(): void {
  const count = Math.max(36, Math.min(78, Math.floor((width * height) / 22000)));
  flakes = [];
  for (let i = 0; i < count; i += 1) {
    const depth = Math.random();
    flakes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      r: 0.7 + depth * 1.8,
      vy: 0.12 + depth * 0.32,
      drift: 0.06 + depth * 0.18,
      phase: Math.random() * Math.PI * 2,
      alpha: 0.16 + depth * 0.3,
      kind: Math.random() < 0.18 ? 1 : 0,
    });
  }
}

function resize(): void {
  if (!canvas || !context) return;
  width = window.innerWidth;
  height = window.innerHeight;
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  seedFlakes();
  draw();
}

function draw(): void {
  if (!context) return;
  context.clearRect(0, 0, width, height);
  context.lineCap = "round";
  for (const flake of flakes) {
    const color = `rgba(226, 241, 250, ${flake.alpha})`;
    if (flake.kind === 0) {
      context.strokeStyle = color;
      context.lineWidth = Math.max(0.6, flake.r * 0.55);
      context.beginPath();
      context.moveTo(flake.x, flake.y - flake.r * 2.4);
      context.lineTo(flake.x + flake.r * 0.35, flake.y + flake.r * 1.8);
      context.stroke();
      continue;
    }

    context.save();
    context.translate(flake.x, flake.y);
    context.rotate(flake.phase);
    context.strokeStyle = color;
    context.lineWidth = Math.max(0.5, flake.r * 0.4);
    const arm = flake.r * 2.6;
    for (let i = 0; i < 3; i += 1) {
      const angle = (i * Math.PI) / 3;
      const dx = Math.cos(angle) * arm;
      const dy = Math.sin(angle) * arm;
      const bx = Math.cos(angle + 0.9) * arm * 0.42;
      const by = Math.sin(angle + 0.9) * arm * 0.42;
      context.beginPath();
      context.moveTo(-dx, -dy);
      context.lineTo(dx, dy);
      context.stroke();
      context.beginPath();
      context.moveTo(dx * 0.55, dy * 0.55);
      context.lineTo(dx * 0.55 + bx, dy * 0.55 + by);
      context.stroke();
      context.beginPath();
      context.moveTo(-dx * 0.55, -dy * 0.55);
      context.lineTo(-dx * 0.55 - bx, -dy * 0.55 - by);
      context.stroke();
    }
    context.restore();
  }
}

function tick(now: number): void {
  if (!active || document.hidden || reduceMotion) {
    frame = 0;
    return;
  }
  const delta = Math.min(3, (now - last) / 16.67 || 1);
  last = now;
  for (const flake of flakes) {
    flake.phase += (flake.kind === 1 ? 0.006 : 0.003) * delta;
    flake.y += flake.vy * delta;
    flake.x += Math.sin(flake.phase) * flake.drift * delta + 0.08 * delta;
    if (flake.y > height + 4) {
      flake.y = -4;
      flake.x = Math.random() * width;
    }
    if (flake.x > width + 4) flake.x = -4;
    if (flake.x < -4) flake.x = width + 4;
  }
  draw();
  frame = window.requestAnimationFrame(tick);
}

function start(): void {
  if (frame || !active || document.hidden || reduceMotion) return;
  last = performance.now();
  frame = window.requestAnimationFrame(tick);
}

function stop(): void {
  if (frame) window.cancelAnimationFrame(frame);
  frame = 0;
  if (context) context.clearRect(0, 0, width, height);
}

function syncDom(): void {
  const root = document.documentElement;
  if (active) root.dataset.winter = "1";
  else delete root.dataset.winter;
  if (active && background) root.dataset.winterBg = "1";
  else delete root.dataset.winterBg;
  writeChoice(FX_KEY, fxChoice);
  writeChoice(BG_KEY, bgChoice);
}

function refresh(): void {
  const winterTheme = eventGate && document.documentElement.dataset.theme === "winter";
  active = eventGate && resolve(fxChoice, winterTheme);
  background = active && resolve(bgChoice, winterTheme);
  syncDom();
  if (!active) {
    stop();
    return;
  }
  resize();
  if (reduceMotion) draw();
  else start();
}

function setup(): void {
  if (initialized) return;
  initialized = true;

  canvas = document.getElementById("winter-snow") as HTMLCanvasElement | null;
  context = canvas ? canvas.getContext("2d") : null;

  const query = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  if (query) {
    reduceMotion = query.matches;
    const onChange = (event: MediaQueryListEvent) => {
      reduceMotion = event.matches;
      if (reduceMotion) stop();
      else start();
    };
    if (typeof query.addEventListener === "function") {
      query.addEventListener("change", onChange);
    } else {
      query.addListener(onChange);
    }
  }

  window.addEventListener("resize", resize);
  document.addEventListener("visibilitychange", () => {
    if (active && !document.hidden) start();
    else stop();
  });
}

/** Set up the canvas once; saved choices stay inert until an event allows them. */
export function initWinterFx(eventActive = forcedByUrl()): void {
  if (initialized) return;
  eventGate = eventActive;
  fxChoice = readChoice(FX_KEY);
  bgChoice = readChoice(BG_KEY);
  setup();
  refresh();
}

/** Apply Winter effects only while the resolved event is active. */
export function applyWinterFx(
  fx: unknown,
  bg: unknown,
  eventActive = eventGate,
  _animate = true,
): void {
  eventGate = Boolean(eventActive);
  fxChoice = normalizeWinterChoice(fx);
  bgChoice = normalizeWinterChoice(bg);
  if (!initialized) setup();
  refresh();
}
