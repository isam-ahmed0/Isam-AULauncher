/* Lightweight modal helper ------------------------------------------------- */

export interface ModalOptions {
  title: string;
  body: HTMLElement | string;
  wide?: boolean;
  buttons?: Array<{
    label: string;
    variant?: "primary" | "ghost" | "danger" | "";
    onClick?: (close: () => void) => void;
  }>;
}

export function openModal(options: ModalOptions): () => void {
  const root = document.getElementById("modal-root");
  if (!root) return () => {};

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";

  const modal = document.createElement("div");
  modal.className = `modal${options.wide ? " wide" : ""}`;

  const head = document.createElement("div");
  head.className = "modal-head";
  const h3 = document.createElement("h3");
  h3.textContent = options.title;
  const closeBtn = document.createElement("button");
  closeBtn.className = "win-btn";
  closeBtn.style.width = "30px";
  closeBtn.style.height = "30px";
  closeBtn.style.borderRadius = "8px";
  closeBtn.innerHTML = `<svg class="icon sm"><use href="#i-x"/></svg>`;
  head.append(h3, closeBtn);

  const body = document.createElement("div");
  body.className = "modal-body";
  if (typeof options.body === "string") body.innerHTML = options.body;
  else body.appendChild(options.body);

  modal.append(head, body);

  const buttons = options.buttons ?? [{ label: "Close", variant: "primary" as const }];
  if (buttons.length) {
    const foot = document.createElement("div");
    foot.className = "modal-foot";
    for (const spec of buttons) {
      const btn = document.createElement("button");
      btn.className = `btn${spec.variant ? ` ${spec.variant}` : ""}`;
      btn.textContent = spec.label;
      btn.addEventListener("click", () => spec.onClick?.(close));
      foot.appendChild(btn);
    }
    modal.appendChild(foot);
  }

  backdrop.appendChild(modal);
  root.appendChild(backdrop);

  function close() {
    backdrop.remove();
    window.removeEventListener("keydown", onKey);
  }
  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") close();
  }
  window.addEventListener("keydown", onKey);
  closeBtn.addEventListener("click", close);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });

  return close;
}

export function confirmModal(
  title: string,
  message: string,
  confirmLabel = "Confirm",
  danger = false,
): Promise<boolean> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value: boolean) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };
    const close = openModal({
      title,
      body: `<p>${message}</p>`,
      buttons: [
        { label: "Cancel", variant: "ghost", onClick: () => { close(); finish(false); } },
        {
          label: confirmLabel,
          variant: danger ? "danger" : "primary",
          onClick: () => { close(); finish(true); },
        },
      ],
    });
  });
}
