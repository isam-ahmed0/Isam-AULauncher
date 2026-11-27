/* Python -> JS event bus ---------------------------------------------------
 * Python pushes events with window.__clEvent(name, data); modules subscribe
 * with on(name, handler).  Handlers must be cheap: progress fires at up to
 * 10 Hz and is already throttled on the Python side.
 */

export type EventHandler = (data: any) => void;

const handlers = new Map<string, Set<EventHandler>>();

export function on(name: string, handler: EventHandler): () => void {
  let set = handlers.get(name);
  if (!set) {
    set = new Set();
    handlers.set(name, set);
  }
  set.add(handler);
  return () => set?.delete(handler);
}

export function off(name: string, handler: EventHandler): void {
  handlers.get(name)?.delete(handler);
}

export function dispatch(name: string, data: unknown): void {
  const set = handlers.get(name);
  if (!set) return;
  for (const handler of [...set]) {
    try {
      handler(data);
    } catch (err) {
      console.error(`[events] handler for "${name}" failed`, err);
    }
  }
}

// Installed before any Python push can arrive (module runs on first import).
window.__clEvent = dispatch;
