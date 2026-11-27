/* Toasts ------------------------------------------------------------------ */

export interface ToastOptions {
  title: string;
  message?: string;
  level?: "info" | "success" | "warning" | "danger";
  timeout?: number;
}

const LEVEL_ICON: Record<string, string> = {
  info: "i-info",
  success: "i-check",
  warning: "i-alert",
  danger: "i-alert",
};

export function toast(options: ToastOptions): void {
  const host = document.getElementById("toasts");
  if (!host) return;

  const level = options.level ?? "info";
  const el = document.createElement("div");
  el.className = `toast ${level}`;

  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("class", "icon");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#${LEVEL_ICON[level] ?? "i-info"}`);
  icon.appendChild(use);

  const body = document.createElement("div");
  const title = document.createElement("div");
  title.className = "t-title";
  title.textContent = options.title;
  body.appendChild(title);
  if (options.message) {
    const msg = document.createElement("div");
    msg.className = "t-msg";
    msg.textContent = options.message;
    body.appendChild(msg);
  }

  el.append(icon, body);
  host.appendChild(el);

  const ttl = options.timeout ?? (level === "danger" ? 8000 : 5000);
  const dismiss = () => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 220);
  };
  if (ttl > 0) setTimeout(dismiss, ttl);
  el.addEventListener("click", dismiss);
}
