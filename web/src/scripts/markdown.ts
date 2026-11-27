/* Tiny, safe Markdown renderer for release announcements -------------------
 * Supports headings, lists, emphasis, inline code, links and images. All text
 * goes through textContent; only validated https? URLs become href/src.
 */

const INLINE = /(!?\[([^\]]*)\]\((https?:\/\/[^\s)]+)\))|(\*\*([^*]+)\*\*)|(`([^`]+)`)/g;

function fragment(text: string): DocumentFragment {
  const out = document.createDocumentFragment();
  let last = 0;
  INLINE.lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > last) {
      out.appendChild(document.createTextNode(text.slice(last, match.index)));
    }
    if (match[1]) {
      const label = match[2] || "";
      const url = match[3];
      if (match[1].startsWith("!")) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = label;
        img.loading = "lazy";
        out.appendChild(img);
      } else {
        const a = document.createElement("a");
        a.href = url;
        a.textContent = label;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        out.appendChild(a);
      }
    } else if (match[4]) {
      const strong = document.createElement("strong");
      strong.textContent = match[5];
      out.appendChild(strong);
    } else if (match[6]) {
      const code = document.createElement("code");
      code.textContent = match[7];
      out.appendChild(code);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) out.appendChild(document.createTextNode(text.slice(last)));
  return out;
}

function block(host: HTMLElement, tag: string, text: string): void {
  const el = document.createElement(tag);
  el.appendChild(fragment(text));
  host.appendChild(el);
}

/** Render a Markdown post into a container, replacing its contents. */
export function renderMarkdown(host: HTMLElement, raw: string): void {
  host.replaceChildren();
  const clean = (raw || "").replace(/<!--[\s\S]*?-->/g, "").trim();
  if (!clean) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "This announcement is empty.";
    host.appendChild(p);
    return;
  }

  const lines = clean.split(/\r?\n/);
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      block(host, "p", paragraph.join(" "));
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list) {
      const el = document.createElement(list.ordered ? "ol" : "ul");
      for (const item of list.items) {
        const li = document.createElement("li");
        li.appendChild(fragment(item));
        el.appendChild(li);
      }
      host.appendChild(el);
      list = null;
    }
  };
  const flush = () => { flushParagraph(); flushList(); };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flush();
      continue;
    }
    const heading = /^(#{1,4})\s+(.*)$/.exec(trimmed);
    if (heading) {
      flush();
      block(host, `h${heading[1].length}`, heading[2]);
      continue;
    }
    if (/^-{3,}$/.test(trimmed)) {
      flush();
      host.appendChild(document.createElement("hr"));
      continue;
    }
    const bullet = /^[-*+]\s+(.*)$/.exec(trimmed);
    const numbered = /^\d+\.\s+(.*)$/.exec(trimmed);
    if (bullet || numbered) {
      flushParagraph();
      const ordered = Boolean(numbered);
      if (!list || list.ordered !== ordered) {
        flushList();
        list = { ordered, items: [] };
      }
      list.items.push((bullet || numbered)![1]);
      continue;
    }
    flushList();
    paragraph.push(trimmed);
  }
  flush();
}
