/* Winter effects -----------------------------------------------------------
 * The two Settings switches are auto/on/off: "auto" follows the effective
 * Winter preset (or event), "on" layers the effect over any preset and "off"
 * disables it. Snow is a capped canvas loop that pauses when hidden.
 */

export type WinterChoice = "auto" | "on" | "off";

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

/** Auto follows Winter; on layers anywhere; off always wins. */
function resolve(choice: WinterChoice, winterTheme: boolean): boolean {
  return choice === "on" || (choice === "auto" && winterTheme);
}

function seedFlakes(): void {
  const count = Math.max(42, Math.min(110, Math.floor((width * height) / 15000)));
  flakes = [];
  for (let i = 0; i < count; i += 1) {
    const depth = Math.random();
    flakes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      r: 0.8 + depth * 2.2,
      vy: 0.22 + depth * 0.72,
      drift: 0.12 + depth * 0.34,
      phase: Math.random() * Math.PI * 2,
      alpha: 0.22 + depth * 0.42,
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
  for (const flake of flakes) {
    context.beginPath();
    context.arc(flake.x, flake.y, flake.r, 0, Math.PI * 2);
    context.fillStyle = `rgba(226, 246, 255, ${flake.alpha})`;
    context.fill();
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
    flake.phase += 0.008 * delta;
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
  const winterTheme = document.documentElement.dataset.theme === "winter";
  active = resolve(fxChoice, winterTheme);
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

/** Set up the canvas once, then follow the current theme and saved choices. */
export function initWinterFx(): void {
  if (initialized) return;
  fxChoice = readChoice(FX_KEY);
  bgChoice = readChoice(BG_KEY);
  setup();
  refresh();
}

/** Apply the layerable Winter effect and background immediately. */
export function applyWinterFx(
  fx: unknown,
  bg: unknown,
  _animate = true,
): void {
  fxChoice = normalizeWinterChoice(fx);
  bgChoice = normalizeWinterChoice(bg);
  if (!initialized) setup();
  refresh();
}
