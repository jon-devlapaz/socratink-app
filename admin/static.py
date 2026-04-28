"""Inlined HTML+CSS+JS for the admin Tink TODO dashboard.

Served by `admin_todo_page` as a single HTMLResponse. Inlining keeps the
page eligible for the handler-level Admin Gate; a guest user fetching it
gets 404 from the server, never the shell.

Honors `DESIGN.md` (socratink design system):
    - cream paper, never white; ink, never true black; one violet accent
    - crystal-state badge palette (locked / drilled / solidified) for items
    - violet-tinted shadows; inset 1px paper-edge highlight on cards
    - lowercase brand/state tokens; Title Case for section headings
    - no exclamation marks, no emoji, no left-border-accent cards
    - motion at 140 / 220 / 320ms; spring only on solidified
    - theme propagation via localStorage["learnops-theme"]
"""

ADMIN_TODO_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>tink todo</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
  // Theme propagation: respect the main app's stored preference.
  (function () {
    try {
      var t = localStorage.getItem('learnops-theme');
      if (t === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
      }
    } catch (e) { /* private browsing, etc. */ }
  })();
</script>
<style>
  :root {
    --ink-900: #242038;
    --ink-900-rgb: 36, 32, 56;
    --violet-600: #9067c6;
    --violet-600-rgb: 144, 103, 198;
    --lavender-500: #8d86c9;
    --lavender-500-rgb: 141, 134, 201;
    --mauve-200: #cac4ce;
    --mauve-200-rgb: 202, 196, 206;
    --cream-50: #f7ece1;
    --cream-50-rgb: 247, 236, 225;

    --surface-page: var(--cream-50);
    --surface-card: #ffffff;
    --surface-nested: rgba(var(--mauve-200-rgb), 0.32);
    --surface-rail: rgba(var(--mauve-200-rgb), 0.18);

    --text-strong: var(--ink-900);
    --text-body: rgba(var(--ink-900-rgb), 0.84);
    --text-muted: rgba(var(--ink-900-rgb), 0.62);
    --text-dim: rgba(var(--ink-900-rgb), 0.42);

    --accent: var(--violet-600);
    --accent-soft: rgba(var(--violet-600-rgb), 0.10);
    --accent-border: rgba(var(--violet-600-rgb), 0.20);
    --accent-border-strong: rgba(var(--violet-600-rgb), 0.32);
    --accent-ring: 0 0 0 3px rgba(var(--violet-600-rgb), 0.16);

    --border-subtle: rgba(var(--ink-900-rgb), 0.10);
    --border-strong: rgba(var(--ink-900-rgb), 0.16);

    --shadow-card: 0 8px 32px rgba(var(--violet-600-rgb), 0.10), 0 1px 4px rgba(0, 0, 0, 0.04);
    --shadow-soft: 0 10px 30px rgba(var(--ink-900-rgb), 0.05);
    --shadow-hover: 0 16px 32px rgba(var(--ink-900-rgb), 0.10);
    --paper-edge: inset 0 1px 0 rgba(255, 255, 255, 0.6);

    --node-locked: var(--mauve-200);
    --node-drilled: #d8a867;
    --node-solidified: #4dba8a;
    --crystal-fractured: #b77b90;

    --font-display: 'Manrope', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    --font-body: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    --font-mono: ui-monospace, 'SF Mono', monospace;

    --tracking-kicker: 0.18em;
    --tracking-tight: -0.02em;

    --duration-micro: 140ms;
    --duration-quick: 220ms;
    --duration-cozy: 320ms;
    --ease-standard: cubic-bezier(0.2, 0.8, 0.2, 1);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

    --page-background:
      radial-gradient(circle at 14% 12%, rgba(255, 255, 255, 0.56), transparent 28%),
      radial-gradient(circle at 88% 18%, rgba(var(--lavender-500-rgb), 0.12), transparent 24%),
      radial-gradient(circle at 52% 100%, rgba(212, 179, 131, 0.09), transparent 30%),
      linear-gradient(180deg, rgba(255, 251, 247, 0.76), rgba(var(--cream-50-rgb), 0.96) 26%, var(--cream-50) 100%);
  }
  [data-theme="dark"] {
    --surface-page: #1f1b31;
    --surface-card: #302b49;
    --surface-nested: rgba(var(--lavender-500-rgb), 0.22);
    --surface-rail: rgba(var(--lavender-500-rgb), 0.10);

    --text-strong: var(--cream-50);
    --text-body: rgba(var(--cream-50-rgb), 0.86);
    --text-muted: rgba(var(--cream-50-rgb), 0.66);
    --text-dim: rgba(var(--cream-50-rgb), 0.42);

    --accent: var(--lavender-500);
    --accent-soft: rgba(var(--lavender-500-rgb), 0.20);
    --accent-border: rgba(var(--lavender-500-rgb), 0.34);
    --accent-border-strong: rgba(var(--lavender-500-rgb), 0.50);
    --accent-ring: 0 0 0 3px rgba(var(--lavender-500-rgb), 0.22);

    --border-subtle: rgba(var(--cream-50-rgb), 0.12);
    --border-strong: rgba(var(--cream-50-rgb), 0.20);

    --shadow-card: 0 14px 44px rgba(11, 9, 24, 0.34), 0 1px 0 rgba(var(--cream-50-rgb), 0.04);
    --shadow-soft: 0 16px 44px rgba(11, 9, 24, 0.24);
    --shadow-hover: 0 24px 60px rgba(11, 9, 24, 0.36);
    --paper-edge: inset 0 1px 0 rgba(var(--cream-50-rgb), 0.06);

    --page-background:
      radial-gradient(circle at 14% 14%, rgba(var(--lavender-500-rgb), 0.26), transparent 28%),
      radial-gradient(circle at 82% 16%, rgba(var(--violet-600-rgb), 0.22), transparent 24%),
      radial-gradient(circle at 50% 100%, rgba(66, 59, 101, 0.22), transparent 38%),
      linear-gradient(180deg, #241f39 0%, #1f1b31 100%);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; min-height: 100vh; }
  body {
    background: var(--page-background);
    color: var(--text-body);
    font: 15px/1.55 var(--font-body);
    font-feature-settings: "ss01", "cv05";
    letter-spacing: -0.005em;
    min-height: 100vh;
  }

  header {
    padding: 28px 36px 8px;
    max-width: 1240px; margin: 0 auto;
    display: grid;
    grid-template-columns: auto 1fr auto auto auto;
    align-items: center;
    column-gap: 16px;
    row-gap: 4px;
  }
  header .kicker {
    grid-column: 1 / 2;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: var(--tracking-kicker);
    color: var(--accent);
  }
  header .path {
    grid-column: 2 / 3;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-dim);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  header .mtime {
    grid-column: 3 / 4;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
  }
  header .status {
    grid-column: 4 / 5;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-dim);
    padding: 4px 10px; border-radius: 999px;
    border: 1px solid transparent;
    transition: color var(--duration-quick) var(--ease-standard),
                border-color var(--duration-quick) var(--ease-standard),
                background-color var(--duration-quick) var(--ease-standard);
  }
  header .status.ok { color: var(--node-solidified); }
  header .status.err { color: var(--crystal-fractured); border-color: var(--crystal-fractured); background: rgba(183, 123, 144, 0.08); }
  header button {
    grid-column: 5 / 6;
    appearance: none;
    border: 1px solid var(--border-subtle);
    background: var(--surface-card);
    box-shadow: var(--paper-edge);
    color: var(--text-body);
    padding: 7px 14px;
    font: inherit; font-size: 12px; font-weight: 600;
    border-radius: 999px;
    cursor: pointer;
    transition: transform var(--duration-micro) var(--ease-standard),
                border-color var(--duration-micro) var(--ease-standard),
                box-shadow var(--duration-quick) var(--ease-standard);
  }
  header button:hover:not(:disabled) {
    transform: translateY(-1px);
    border-color: var(--accent-border-strong);
    box-shadow: var(--paper-edge), var(--shadow-hover);
  }
  header button:active { transform: scale(0.97); }
  header button:focus-visible { outline: none; box-shadow: var(--paper-edge), var(--accent-ring); }
  header button:disabled { opacity: 0.45; cursor: progress; }
  header h1 {
    grid-column: 1 / -1;
    margin: 6px 0 0;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 28px;
    letter-spacing: var(--tracking-tight);
    color: var(--text-strong);
  }
  header .subhead {
    grid-column: 1 / -1;
    margin-bottom: 18px;
    font-size: 13px;
    color: var(--text-muted);
    max-width: 64ch;
  }

  .filter-rail {
    display: flex; flex-wrap: wrap; gap: 6px;
    padding: 0 36px;
    max-width: 1240px; margin: 0 auto 8px;
  }
  .filter {
    appearance: none;
    border: 1px solid var(--border-subtle);
    background: var(--surface-card);
    box-shadow: var(--paper-edge);
    color: var(--text-muted);
    padding: 6px 14px;
    font: inherit;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    border-radius: 999px;
    cursor: pointer;
    transition: transform var(--duration-micro) var(--ease-standard),
                color var(--duration-micro) var(--ease-standard),
                border-color var(--duration-micro) var(--ease-standard),
                background-color var(--duration-micro) var(--ease-standard);
  }
  .filter:hover { transform: translateY(-1px); border-color: var(--accent-border-strong); color: var(--text-strong); }
  .filter:focus-visible { outline: none; box-shadow: var(--paper-edge), var(--accent-ring); }
  .filter.active {
    color: var(--accent);
    border-color: var(--accent-border-strong);
    background: var(--accent-soft);
  }
  .filter .count { color: var(--text-dim); margin-left: 6px; font-weight: 500; }
  .filter.active .count { color: var(--accent); }

  main { padding: 8px 36px 96px; max-width: 1240px; margin: 0 auto; }

  .session {
    margin-top: 36px;
    padding: 22px 22px 24px;
    background: var(--surface-card);
    border: 1px solid var(--border-subtle);
    border-radius: 18px;
    box-shadow: var(--paper-edge), var(--shadow-soft);
  }
  .session:first-of-type { margin-top: 16px; }
  .session.toplevel { background: transparent; box-shadow: none; border-style: dashed; }
  .session h2 {
    margin: 0 0 14px;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 17px;
    letter-spacing: var(--tracking-tight);
    color: var(--text-strong);
  }
  .session.toplevel h2 {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: var(--tracking-kicker);
    font-weight: 700;
  }

  .buckets {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 14px;
    align-items: start;
  }
  .bucket {
    padding: 14px 16px 18px;
    background: var(--surface-nested);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    min-height: 64px;
    transition: background-color var(--duration-quick) var(--ease-standard),
                border-color var(--duration-quick) var(--ease-standard);
  }
  .bucket.toplevel {
    background: transparent;
    border-style: dashed;
  }
  .bucket h3 {
    margin: 0 0 10px;
    font-family: var(--font-display);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: var(--tracking-kicker);
    color: var(--accent);
  }
  .bucket.dragover {
    background: var(--accent-soft);
    border-color: var(--accent-border-strong);
  }

  ul.items { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }

  li.item {
    position: relative;
    display: flex; align-items: flex-start; gap: 10px;
    padding: 7px 9px 7px 7px;
    border-radius: 8px;
    cursor: grab;
    border: 1px solid transparent;
    transition: background-color var(--duration-micro) var(--ease-standard),
                border-color var(--duration-micro) var(--ease-standard),
                opacity var(--duration-quick) var(--ease-standard);
  }
  li.item:hover { background: var(--surface-card); border-color: var(--border-subtle); }
  li.item.dragging { opacity: 0.4; cursor: grabbing; }
  li.item.dragover-after { box-shadow: 0 1px 0 var(--accent); }
  li.item.deprecated .body { color: var(--text-dim); text-decoration: line-through; text-decoration-thickness: 1px; }
  li.item.resolved .body { color: var(--text-muted); }

  li.item input[type="checkbox"] {
    flex: 0 0 auto;
    margin: 4px 2px 0 0;
    appearance: none;
    width: 14px; height: 14px;
    border: 1px solid var(--accent-border-strong);
    border-radius: 4px;
    cursor: pointer;
    background: var(--surface-card);
    box-shadow: var(--paper-edge);
    transition: background-color var(--duration-cozy) var(--ease-spring),
                border-color var(--duration-quick) var(--ease-standard);
  }
  li.item input[type="checkbox"]:hover { border-color: var(--accent); }
  li.item input[type="checkbox"]:checked {
    background: var(--node-solidified);
    border-color: var(--node-solidified);
  }
  li.item input[type="checkbox"]:checked::after {
    content: "";
    display: block;
    width: 4px; height: 8px;
    margin: 0 auto;
    margin-top: -1px;
    border: solid var(--cream-50);
    border-width: 0 1.5px 1.5px 0;
    transform: rotate(45deg);
  }
  li.item input[type="checkbox"]:focus-visible { outline: none; box-shadow: var(--paper-edge), var(--accent-ring); }

  li.item .body {
    flex: 1; min-width: 0;
    word-break: break-word;
    color: var(--text-body);
    font-size: 14px;
    line-height: 1.5;
  }
  li.item .body:hover { cursor: text; }
  .body-edit {
    display: block;
    width: 100%;
    resize: none;
    overflow: hidden;
    min-height: 32px;
    appearance: none;
    border: 1px solid var(--accent-border-strong);
    background: var(--surface-card);
    color: var(--text-strong);
    font: inherit;
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.5;
    padding: 6px 8px;
    border-radius: 6px;
    box-shadow: var(--paper-edge), var(--accent-ring);
    outline: none;
  }
  li.item .body code {
    font-family: var(--font-mono);
    font-size: 12px;
    background: var(--surface-rail);
    color: var(--text-strong);
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid var(--border-subtle);
  }
  li.item .meta { margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px; }
  li.item .badge {
    font-family: var(--font-mono);
    font-size: 10px; font-weight: 600;
    padding: 1px 7px;
    border-radius: 999px;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
  }
  /* Builder's Trap: drilled-warm halo, never red, returnable. */
  .badge.bt {
    background: rgba(216, 168, 103, 0.14);
    color: var(--node-drilled);
    border-color: rgba(216, 168, 103, 0.32);
  }
  .badge.resolved {
    background: rgba(77, 186, 138, 0.10);
    color: var(--node-solidified);
    border-color: rgba(77, 186, 138, 0.26);
  }
  .badge.deprecated {
    background: var(--surface-rail);
    color: var(--text-dim);
    border-color: var(--border-subtle);
  }

  .empty {
    color: var(--text-dim);
    font-size: 12px;
    font-style: italic;
    padding: 6px 4px;
  }

  .conflict {
    margin: 16px 0;
    padding: 14px 18px;
    background: rgba(183, 123, 144, 0.10);
    border: 1px solid var(--crystal-fractured);
    border-radius: 12px;
    font-size: 13px;
    color: var(--text-strong);
    box-shadow: var(--paper-edge);
  }
  .conflict button {
    margin-left: 12px;
    appearance: none;
    border: 1px solid var(--border-subtle);
    background: var(--surface-card);
    color: var(--text-strong);
    padding: 5px 12px;
    font: inherit; font-size: 12px; font-weight: 600;
    border-radius: 999px;
    cursor: pointer;
  }
  .conflict button:hover { border-color: var(--accent-border-strong); }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition-duration: 0ms !important; animation-duration: 0ms !important; }
  }
</style>
</head>
<body>
<header>
  <span class="kicker">tink todo</span>
  <span class="path">/Users/jondev/dev/socratink/todo.md</span>
  <span class="mtime" id="mtime"></span>
  <span class="status" id="status"></span>
  <button id="reload" title="Re-read the file from disk">reload</button>
  <h1>Field Journal</h1>
  <p class="subhead">Sessions, buckets, items. Toggle a checkbox to resolve. Double-click the body to edit. Drag within a session to rebucket. Cross-session moves are not permitted.</p>
</header>
<div class="filter-rail" id="filter-rail"></div>
<main id="root">
  <div class="empty" id="loading">loading</div>
</main>
<script>
(() => {
  "use strict";
  let CURRENT_MTIME = null;
  let LAST_DATA = null;

  const FILTER_KEY = "tink-todo-filter";
  const FILTERS = [
    { key: "open",     label: "open" },
    { key: "all",      label: "all" },
    { key: "bt",       label: "builders trap" },
    { key: "resolved", label: "resolved" },
  ];
  let currentFilter = (() => {
    try { return localStorage.getItem(FILTER_KEY) || "open"; }
    catch (e) { return "open"; }
  })();

  const root = document.getElementById("root");
  const mtimeEl = document.getElementById("mtime");
  const statusEl = document.getElementById("status");
  const reloadBtn = document.getElementById("reload");
  const railEl = document.getElementById("filter-rail");

  function passesFilter(item) {
    switch (currentFilter) {
      case "open":     return item.is_open;
      case "bt":       return item.is_builders_trap;
      case "resolved": return item.is_resolved;
      case "all":
      default:         return true;
    }
  }

  function computeCounts(data) {
    const c = { open: 0, all: 0, bt: 0, resolved: 0 };
    for (const s of data.sessions) {
      for (const b of s.buckets) {
        for (const i of b.items) {
          c.all++;
          if (i.is_open) c.open++;
          if (i.is_builders_trap) c.bt++;
          if (i.is_resolved) c.resolved++;
        }
      }
    }
    return c;
  }

  function renderFilters(data) {
    const counts = computeCounts(data);
    railEl.innerHTML = "";
    for (const f of FILTERS) {
      const btn = document.createElement("button");
      btn.className = "filter" + (f.key === currentFilter ? " active" : "");
      btn.type = "button";
      const label = document.createTextNode(f.label);
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = String(counts[f.key]);
      btn.appendChild(label);
      btn.appendChild(count);
      btn.addEventListener("click", () => {
        currentFilter = f.key;
        try { localStorage.setItem(FILTER_KEY, f.key); } catch (e) { /* private mode */ }
        if (LAST_DATA) render(LAST_DATA);
      });
      railEl.appendChild(btn);
    }
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.className = "status " + (kind || "");
  }

  function fmtMtime(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
      + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  async function load() {
    setStatus("reading", "");
    reloadBtn.disabled = true;
    try {
      const r = await fetch("/api/admin/todo", { credentials: "same-origin" });
      if (!r.ok) {
        setStatus("error " + r.status, "err");
        return;
      }
      const data = await r.json();
      CURRENT_MTIME = data.mtime;
      LAST_DATA = data;
      mtimeEl.textContent = "mtime " + fmtMtime(data.mtime);
      renderFilters(data);
      render(data);
      setStatus("current", "ok");
    } catch (e) {
      console.error(e);
      setStatus("network error", "err");
    } finally {
      reloadBtn.disabled = false;
    }
  }

  function render(data) {
    LAST_DATA = data;
    renderFilters(data);
    root.innerHTML = "";
    let visibleSessions = 0;
    for (const session of data.sessions) {
      if (!session.buckets.length) continue;
      const sectionEl = renderSession(session);
      if (sectionEl) {
        root.appendChild(sectionEl);
        visibleSessions++;
      }
    }
    if (!visibleSessions) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.style.padding = "32px 8px";
      empty.textContent = "no items match this filter.";
      root.appendChild(empty);
    }
  }

  function renderSession(session) {
    const visibleBuckets = [];
    for (const bucket of session.buckets) {
      const visibleItems = bucket.items.filter(passesFilter);
      if (visibleItems.length) {
        visibleBuckets.push([bucket, visibleItems]);
      }
    }
    if (!visibleBuckets.length) return null;
    const sec = document.createElement("section");
    sec.className = "session" + (session.line_index < 0 ? " toplevel" : "");
    const h2 = document.createElement("h2");
    h2.textContent = session.line_index < 0 ? "loose items" : session.title;
    sec.appendChild(h2);
    const bucketsEl = document.createElement("div");
    bucketsEl.className = "buckets";
    for (const [bucket, items] of visibleBuckets) {
      bucketsEl.appendChild(renderBucket(bucket, items));
    }
    sec.appendChild(bucketsEl);
    return sec;
  }

  function renderBucket(bucket, items) {
    const wrap = document.createElement("div");
    wrap.className = "bucket" + (bucket.line_index < 0 ? " toplevel" : "");
    wrap.dataset.bucketLine = String(bucket.line_index);
    const h3 = document.createElement("h3");
    h3.textContent = bucket.line_index < 0 ? "(top)" : bucket.name;
    wrap.appendChild(h3);
    const ul = document.createElement("ul");
    ul.className = "items";
    for (const item of items) {
      ul.appendChild(renderItem(item));
    }
    wireBucketDropTarget(wrap);
    wrap.appendChild(ul);
    return wrap;
  }

  function renderItem(item) {
    const li = document.createElement("li");
    li.className = "item";
    if (item.is_deprecated) li.classList.add("deprecated");
    else if (item.is_resolved) li.classList.add("resolved");
    li.dataset.lineIndex = String(item.line_index);
    li.draggable = true;

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !item.is_open;
    cb.addEventListener("change", () => toggleItem(item.line_index, cb));
    li.appendChild(cb);

    const bodyWrap = document.createElement("div");
    bodyWrap.style.flex = "1";
    bodyWrap.style.minWidth = "0";
    const body = document.createElement("div");
    body.className = "body";
    body.appendChild(renderInline(stripMetaForDisplay(item.body_plain)));
    body.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      enterEdit(li, item, body);
    });
    bodyWrap.appendChild(body);
    const meta = renderBadges(item);
    if (meta) bodyWrap.appendChild(meta);
    li.appendChild(bodyWrap);

    wireItemDrag(li);
    return li;
  }

  function enterEdit(li, item, bodyEl) {
    li.draggable = false;
    const oldDraggable = true;
    const input = document.createElement("textarea");
    input.className = "body-edit";
    input.rows = 1;
    input.value = item.body;
    input.spellcheck = false;
    bodyEl.replaceWith(input);
    const autoGrow = () => {
      input.style.height = "auto";
      input.style.height = input.scrollHeight + "px";
    };
    input.addEventListener("input", () => {
      if (/[\r\n]/.test(input.value)) {
        const pos = input.selectionStart;
        input.value = input.value.replace(/[\r\n]+/g, " ");
        input.setSelectionRange(pos, pos);
      }
      autoGrow();
    });
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
    autoGrow();
    let done = false;
    const cancel = () => {
      if (done) return;
      done = true;
      li.draggable = oldDraggable;
      input.replaceWith(bodyEl);
    };
    const commit = async () => {
      if (done) return;
      const newBody = input.value;
      if (newBody === item.body || !newBody.trim()) { cancel(); return; }
      done = true;
      input.disabled = true;
      setStatus("writing", "");
      try {
        const r = await fetch("/api/admin/todo/edit", {
          method: "PATCH",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            line_index: item.line_index,
            new_body: newBody,
            expected_mtime: CURRENT_MTIME
          })
        });
        if (r.status === 409) { showConflict(); return; }
        if (r.status === 422) {
          const j = await r.json().catch(() => ({}));
          setStatus("rejected: " + (j.detail || ""), "err");
          done = false;  // let user retry
          input.disabled = false;
          input.focus();
          return;
        }
        if (!r.ok) {
          setStatus("write failed " + r.status, "err");
          done = false;
          input.disabled = false;
          return;
        }
        const data = await r.json();
        CURRENT_MTIME = data.mtime;
        mtimeEl.textContent = "mtime " + fmtMtime(data.mtime);
        render(data);
        setStatus("applied", "ok");
      } catch (e) {
        console.error(e);
        setStatus("network error", "err");
        done = false;
        input.disabled = false;
      }
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); commit(); }
      else if (e.key === "Escape") { e.preventDefault(); cancel(); }
    });
    input.addEventListener("blur", () => { if (!done) commit(); });
  }

  function stripMetaForDisplay(body) {
    return body
      .replace(/\s*\*\(resolved \d{4}-\d{2}-\d{2}[^)]*\)\*/, "")
      .replace(/\s*\*\(deprecated \d{4}-\d{2}-\d{2}[^)]*\)\*/, "")
      .replace(/\s*\*\(Builder's Trap\? → [^)]*\)\*/, "")
      .trim();
  }

  function renderInline(text) {
    const frag = document.createDocumentFragment();
    const re = /`([^`]+)`/g;
    let last = 0;
    let m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const code = document.createElement("code");
      code.textContent = m[1];
      frag.appendChild(code);
      last = m.index + m[0].length;
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    return frag;
  }

  function renderBadges(item) {
    const tags = [];
    if (item.is_builders_trap) tags.push(["bt", "builders trap"]);
    if (item.is_resolved) tags.push(["resolved", "resolved"]);
    if (item.is_deprecated) tags.push(["deprecated", "deprecated"]);
    if (!tags.length) return null;
    const wrap = document.createElement("div");
    wrap.className = "meta";
    for (const [cls, label] of tags) {
      const b = document.createElement("span");
      b.className = "badge " + cls;
      b.textContent = label;
      wrap.appendChild(b);
    }
    return wrap;
  }

  async function toggleItem(lineIndex, cbEl) {
    cbEl.disabled = true;
    setStatus("writing", "");
    try {
      const r = await fetch("/api/admin/todo/toggle", {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line_index: lineIndex, expected_mtime: CURRENT_MTIME })
      });
      if (r.status === 409) { showConflict(); return; }
      if (!r.ok) {
        setStatus("write failed " + r.status, "err");
        cbEl.checked = !cbEl.checked;
        return;
      }
      const data = await r.json();
      CURRENT_MTIME = data.mtime;
      mtimeEl.textContent = "mtime " + fmtMtime(data.mtime);
      render(data);
      setStatus("applied", "ok");
    } catch (e) {
      console.error(e);
      cbEl.checked = !cbEl.checked;
      setStatus("network error", "err");
    } finally {
      cbEl.disabled = false;
    }
  }

  let DRAG_LINE = null;

  function wireItemDrag(li) {
    li.addEventListener("dragstart", (e) => {
      DRAG_LINE = parseInt(li.dataset.lineIndex, 10);
      li.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", li.dataset.lineIndex);
    });
    li.addEventListener("dragend", () => {
      li.classList.remove("dragging");
      DRAG_LINE = null;
      document.querySelectorAll(".dragover-after, .dragover").forEach(n => {
        n.classList.remove("dragover-after");
        n.classList.remove("dragover");
      });
    });
    li.addEventListener("dragover", (e) => {
      if (DRAG_LINE === null) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      li.classList.add("dragover-after");
    });
    li.addEventListener("dragleave", () => li.classList.remove("dragover-after"));
    li.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const dropAfter = parseInt(li.dataset.lineIndex, 10);
      const bucketEl = li.closest(".bucket");
      if (!bucketEl) return;
      const bucketLine = parseInt(bucketEl.dataset.bucketLine, 10);
      submitMove(DRAG_LINE, bucketLine, dropAfter);
    });
  }

  function wireBucketDropTarget(bucketEl) {
    bucketEl.addEventListener("dragover", (e) => {
      if (DRAG_LINE === null) return;
      e.preventDefault();
      bucketEl.classList.add("dragover");
    });
    bucketEl.addEventListener("dragleave", (e) => {
      if (e.target === bucketEl) bucketEl.classList.remove("dragover");
    });
    bucketEl.addEventListener("drop", (e) => {
      if (DRAG_LINE === null) return;
      e.preventDefault();
      bucketEl.classList.remove("dragover");
      const bucketLine = parseInt(bucketEl.dataset.bucketLine, 10);
      submitMove(DRAG_LINE, bucketLine, null);
    });
  }

  async function submitMove(lineIndex, bucketLine, afterLine) {
    setStatus("moving", "");
    try {
      const r = await fetch("/api/admin/todo/move", {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          line_index: lineIndex,
          target_bucket_line: bucketLine,
          after_item_line: afterLine,
          expected_mtime: CURRENT_MTIME
        })
      });
      if (r.status === 409) { showConflict(); return; }
      if (r.status === 422) {
        const j = await r.json().catch(() => ({}));
        setStatus("not allowed: " + (j.detail || "rejected"), "err");
        return;
      }
      if (!r.ok) { setStatus("write failed " + r.status, "err"); return; }
      const data = await r.json();
      CURRENT_MTIME = data.mtime;
      mtimeEl.textContent = "mtime " + fmtMtime(data.mtime);
      render(data);
      setStatus("applied", "ok");
    } catch (e) {
      console.error(e);
      setStatus("network error", "err");
    }
  }

  function showConflict() {
    const banner = document.createElement("div");
    banner.className = "conflict";
    banner.innerHTML = "this page is out of date. the file changed on disk since you opened it. ";
    const btn = document.createElement("button");
    btn.textContent = "reload";
    btn.addEventListener("click", () => { banner.remove(); load(); });
    banner.appendChild(btn);
    root.prepend(banner);
    setStatus("out of date", "err");
  }

  reloadBtn.addEventListener("click", load);
  window.addEventListener("focus", () => {
    fetch("/api/admin/todo/mtime", { credentials: "same-origin" })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && d.mtime !== CURRENT_MTIME) load(); })
      .catch(() => {});
  });
  load();
})();
</script>
</body>
</html>
"""
