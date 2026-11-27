/* News view: live announcements with offline cache ------------------------- */

import { api } from "../bridge";
import { on } from "../events";
import { toast } from "../toast";
import { renderMarkdown } from "../markdown";

const $ = <T extends HTMLElement = HTMLElement>(id: string): T =>
  document.getElementById(id) as T;

let identity = "";
let unseen = false;
let loaded = false;

export function initNews(): void {
  $("news-refresh").addEventListener("click", () => void loadNews(true));
  on("news_result", (data) => applyNews(data));
}

export async function loadNews(force = false): Promise<void> {
  if (loaded && !force) return;
  const cached = await api<any>("news_cached");
  if (cached.ok && cached.data?.posts?.length) applyNews(cached.data);
  const res = await api("news_load", force);
  if (!res.ok) toast({ title: "News failed", message: res.error, level: "danger" });
}

function applyNews(data: any): void {
  if (!data) return;
  loaded = true;
  const posts: string[] = data.posts ?? [];
  identity = data.identity ?? "";
  unseen = Boolean(data.unseen);

  const status = $("news-status");
  status.textContent = data.offline ? "Cached" : "Live";
  status.className = `pill${data.offline ? " warning" : " success"}`;

  const notice = $("news-notice");
  if (data.error) {
    $("news-notice-text").textContent = data.error;
    notice.classList.add("show");
  } else {
    notice.classList.remove("show");
  }

  $("news-cache-state").textContent = data.offline ? "In use" : "Updated";
  $("news-identity").textContent = identity
    ? identity.replace(/^(sha256:|id:)/, "").slice(0, 16)
    : "—";

  const host = $("news-list");
  host.replaceChildren();
  if (!posts.length) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="empty">
        <span class="badge-icon"><svg class="icon lg"><use href="#i-news" /></svg></span>
        <h3>No announcements yet</h3>
        <p>Published notes will appear here as soon as they are available.</p>
      </div>`;
    host.appendChild(card);
    return;
  }

  for (const post of posts) {
    const article = document.createElement("article");
    article.className = "news-post";
    const body = document.createElement("div");
    body.className = "md";
    renderMarkdown(body, post);
    article.appendChild(body);
    host.appendChild(article);
  }

  if (unseen) {
    unseen = false;
    void api("news_mark_seen");
  }
}
