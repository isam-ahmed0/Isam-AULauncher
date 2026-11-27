/* Regions view: list, add, apply, ping and reset --------------------------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";

import { openModal } from "../modal";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

interface Region {
  Name: string;
  PingServer: string;
  Servers?: Array<{ Ip: string; Port: number }>;
}

interface RegionsData {
  regions: Region[];
  active_index: number;
  path: string;
  exists: boolean;
}

let regions: Region[] = [];
let activeIndex = 0;
let loaded = false;

export function initRegions(): void {
  $("regions-add").addEventListener("click", addRegion);
  $("regions-reset").addEventListener("click", resetRegions);
  on("regions_changed", (data) => applyRegions(data));
}

export async function loadRegions(): Promise<void> {
  if (loaded) return;
  const res = await api<RegionsData>("regions_get");
  if (res.ok && res.data) applyRegions(res.data);
}

function applyRegions(data: any): void {
  if (!data) return;
  regions = data.regions ?? [];
  activeIndex = data.active_index ?? 0;
  loaded = true;

  $("regions-path").textContent =
    `${data.exists ? "Editing" : "Will create"} ${data.path}`;
  $("regions-count").textContent =
    `${regions.length} region${regions.length === 1 ? "" : "s"}`;

  const host = $("region-list");
  host.innerHTML = "";
  if (!regions.length) {
    host.innerHTML = `
      <div class="empty" style="padding: 30px 20px;">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-map" /></svg></span>
        <h3>No regions found</h3>
        <p>Add a custom region or reset to the official list.</p>
      </div>`;
    return;
  }

  regions.forEach((region, index) => {
    const server = region.Servers?.[0] ?? { Ip: "", Port: 443 };
    const row = document.createElement("div");
    row.className = `region-row${index === activeIndex ? " active" : ""}`;

    const idx = document.createElement("span");
    idx.className = "r-index";
    idx.textContent = String(index + 1);

    const name = document.createElement("span");
    name.className = "r-name";
    name.textContent = region.Name || "(unnamed)";
    if (index === activeIndex) {
      const badge = document.createElement("span");
      badge.className = "pill accent";
      badge.style.marginLeft = "8px";
      badge.textContent = "active";
      name.appendChild(badge);
    }

    const ping = document.createElement("span");
    ping.className = "r-host";
    ping.textContent = region.PingServer || "—";

    const url = document.createElement("span");
    url.className = "r-host";
    url.textContent = server.Ip || "—";

    const port = document.createElement("span");
    port.className = "mono faint";
    port.textContent = String(server.Port ?? 443);

    const actions = document.createElement("div");
    actions.className = "r-actions";
    for (const spec of [
      { icon: "#i-refresh", title: "Check reachability", fn: () => void api("regions_ping", index) },
      {
        icon: "#i-check",
        title: "Make active",
        fn: async () => {
          const res = await api("regions_apply", index);
          if (!res.ok) toast({ title: "Apply failed", message: res.error, level: "danger" });
        },
      },
      {
        icon: "#i-x",
        title: "Remove region",
        fn: () => {
          openModal({
            title: "Remove region",
            body: `<p>Remove <strong>${region.Name || "this region"}</strong>?</p>`,
            buttons: [
              { label: "Cancel", variant: "ghost", onClick: (close) => close() },
              {
                label: "Remove",
                variant: "danger",
                onClick: async (close) => {
                  const res = await api("regions_remove", index);
                  if (!res.ok) {
                    toast({ title: "Remove failed", message: res.error, level: "danger" });
                    return;
                  }
                  close();
                },
              },
            ],
          });
        },
      },
    ]) {
      const btn = document.createElement("button");
      btn.className = "mini";
      btn.title = spec.title;
      btn.innerHTML = `<svg class="icon sm"><use href="${spec.icon}"/></svg>`;
      btn.addEventListener("click", spec.fn);
      actions.appendChild(btn);
    }

    row.append(idx, name, ping, url, port, actions);
    host.appendChild(row);
  });
}

function addRegion(): void {
  const body = document.createElement("div");
  body.innerHTML = `
    <div class="form-row"><label>Name</label><input class="field" id="rg-name" maxlength="50" placeholder="My Region" /></div>
    <div class="form-row"><label>Ping server</label><input class="field" id="rg-ping" placeholder="ping.example.com" /></div>
    <div class="form-row"><label>Server URL</label><input class="field" id="rg-url" placeholder="https://play.example.com" /></div>
    <div class="form-row"><label>Port</label><input class="field" id="rg-port" type="number" min="1" max="65535" value="443" /></div>
    <p class="muted" style="font-size:12.5px;">The ping server is a bare hostname or IP; the server URL includes the scheme.</p>`;

  openModal({
    title: "Add region",
    body,
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Add",
        variant: "primary",
        onClick: async (close) => {
          const name = (body.querySelector("#rg-name") as HTMLInputElement).value.trim();
          const ping = (body.querySelector("#rg-ping") as HTMLInputElement).value.trim();
          const url = (body.querySelector("#rg-url") as HTMLInputElement).value.trim();
          const port = Number((body.querySelector("#rg-port") as HTMLInputElement).value || 443);
          const res = await api("regions_add", name, ping, url, port);
          if (!res.ok) {
            toast({ title: "Add failed", message: res.error, level: "danger" });
            return;
          }
          close();
          toast({ title: "Region added", message: name, level: "success" });
        },
      },
    ],
  });
}

function resetRegions(): void {
  openModal({
    title: "Reset regions",
    body: "<p>Replace the current list with the five official regions?</p>",
    buttons: [
      { label: "Cancel", variant: "ghost", onClick: (close) => close() },
      {
        label: "Reset",
        variant: "primary",
        onClick: async (close) => {
          const res = await api("regions_reset");
          if (!res.ok) toast({ title: "Reset failed", message: res.error, level: "danger" });
          else close();
        },
      },
    ],
  });
}
