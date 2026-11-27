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

/** Call a Python API method. Never throws — always resolves to an envelope. */
export async function api<T = unknown>(
  method: string,
  ...args: unknown[]
): Promise<Envelope<T>> {
  if (!isDesktop()) {
    await new Promise((r) => setTimeout(r, PREVIEW_TIMEOUT));
    return { ok: false, error: "Python bridge unavailable (browser preview)" };
  }
  await Promise.race([
    bridgeReady,
    new Promise((r) => setTimeout(r, PREVIEW_TIMEOUT)),
  ]);
  const fn = window.pywebview?.api?.[method];
  if (typeof fn !== "function") {
    return { ok: false, error: `Unknown API method: ${method}` };
  }
  try {
    const result = (await fn(...args)) as T;
    if (
      result &&
      typeof result === "object" &&
      "ok" in (result as Record<string, unknown>)
    ) {
      return result as unknown as Envelope<T>;
    }
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
