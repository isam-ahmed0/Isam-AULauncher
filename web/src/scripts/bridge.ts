/* pywebview bridge --------------------------------------------------------
 * Thin, typed wrapper over `window.pywebview.api`.
 *
 * Every Python method returns { ok, data | error }; exceptions raised on the
 * Python side arrive as a rejected promise and are converted to the same
 * envelope here so callers only ever handle one shape.
 */

export type Envelope<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

interface WebviewApi {
  api: Record<string, (...args: unknown[]) => Promise<unknown>>;
}

declare global {
  interface Window {
    pywebview?: WebviewApi;
    __clEvent?: (name: string, data: unknown) => void;
  }
}

let resolveReady: (() => void) | null = null;
let isReady = false;

export const bridgeReady = new Promise<void>((resolve) => {
  resolveReady = () => {
    if (isReady) return;
    isReady = true;
    resolve();
  };
});

function markReady() {
  resolveReady?.();
}

window.addEventListener("pywebviewready", markReady);
if (window.pywebview?.api) markReady();

/** True when running inside the real launcher (not a plain browser). */
export function isDesktop(): boolean {
  return Boolean(window.pywebview?.api);
}

const PREVIEW_TIMEOUT = 1200;
const BRIDGE_WAIT = 2500;
const CALL_RETRY_DELAY = 150;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Wait until both the API object and the `pywebviewready` signal are present.
 * Calling an API method before that signal can lose the call entirely, which
 * used to leave the first screen stuck on its default "Not Installed" state.
 */
export async function bridgeAvailable(
  timeoutMs = BRIDGE_WAIT,
): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (isDesktop() && isReady) return true;
    await delay(50);
  }
  return isDesktop() && isReady;
}

function envelope<T>(result: unknown): Envelope<T> {
  if (
    result &&
    typeof result === "object" &&
    "ok" in (result as Record<string, unknown>)
  ) {
    return result as unknown as Envelope<T>;
  }
  return { ok: true, data: result as T };
}

/** Call a Python API method. Never throws — always resolves to an envelope. */
export async function api<T = unknown>(
  method: string,
  ...args: unknown[]
): Promise<Envelope<T>> {
  if (!isDesktop()) {
    await delay(PREVIEW_TIMEOUT);
    return { ok: false, error: "Python bridge unavailable (browser preview)" };
  }
  if (!(await bridgeAvailable())) {
    return { ok: false, error: "Python bridge is not ready yet" };
  }

  let fn = window.pywebview?.api?.[method];
  if (typeof fn !== "function") {
    // The API object can exist for a moment before all methods are installed.
    await delay(CALL_RETRY_DELAY);
    fn = window.pywebview?.api?.[method];
  }
  if (typeof fn !== "function") {
    return { ok: false, error: `Unknown API method: ${method}` };
  }

  try {
    let result = await fn(...args);
    if (result === undefined || result === null) {
      // Every Python method returns an envelope; undefined means the call was
      // dropped by a bridge that was not quite ready. Retry once.
      await delay(CALL_RETRY_DELAY);
      result = await fn(...args);
    }
    return envelope<T>(result);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
