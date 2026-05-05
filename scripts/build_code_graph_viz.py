"""Read .code-review-graph/graph.db and emit docs/code-graph.html.

Renders nodes + edges as a D3 force-directed constellation, colored by community.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / ".code-review-graph" / "graph.db"
OUT = REPO / "docs" / "code-graph.html"


def load_graph() -> dict:
    con = sqlite3.connect(DB)
    try:
        con.row_factory = sqlite3.Row

        communities = {
            row["id"]: {"id": row["id"], "name": row["name"], "size": row["size"]}
            for row in con.execute("SELECT id, name, size FROM communities ORDER BY size DESC")
        }

        nodes_rows = con.execute(
            "SELECT id, kind, name, qualified_name, file_path, line_start, "
            "community_id FROM nodes"
        ).fetchall()

        qn_to_idx = {row["qualified_name"]: i for i, row in enumerate(nodes_rows)}

        nodes = [
            {
                "i": i,
                "id": row["qualified_name"],
                "name": row["name"],
                "kind": row["kind"],
                "file": row["file_path"],
                "line": row["line_start"] or 0,
                "community": row["community_id"],
            }
            for i, row in enumerate(nodes_rows)
        ]

        edges = []
        for row in con.execute(
            "SELECT kind, source_qualified, target_qualified FROM edges"
        ):
            s = qn_to_idx.get(row["source_qualified"])
            t = qn_to_idx.get(row["target_qualified"])
            if s is None or t is None or s == t:
                continue
            edges.append({"s": s, "t": t, "k": row["kind"]})

        meta_rows = list(con.execute("SELECT key, value FROM metadata"))
        meta = {row["key"]: row["value"] for row in meta_rows}
    finally:
        con.close()

    return {
        "communities": list(communities.values()),
        "nodes": nodes,
        "edges": edges,
        "meta": meta,
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>socratink :: code constellation</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<style>
  :root {
    --bg-0: #03060f;
    --bg-1: #070b1c;
    --ink: #e9eefb;
    --ink-dim: #8a93b8;
    --ink-faint: #4d557a;
    --rule: rgba(155, 175, 230, 0.10);
    --accent: #9cc2ff;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; height: 100%;
    background: radial-gradient(1200px 800px at 30% 10%, #0a1230 0%, var(--bg-0) 60%) no-repeat fixed, var(--bg-0);
    color: var(--ink);
    font-family: ui-sans-serif, -apple-system, "SF Pro Text", "Inter", system-ui, sans-serif;
    overflow: hidden;
  }
  header {
    position: fixed; top: 0; left: 0; right: 0;
    padding: 18px 26px 14px;
    display: flex; align-items: baseline; gap: 18px;
    border-bottom: 1px solid var(--rule);
    background: linear-gradient(180deg, rgba(3,6,15,0.92), rgba(3,6,15,0.55) 70%, rgba(3,6,15,0));
    backdrop-filter: blur(6px);
    z-index: 5;
  }
  h1 {
    font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase;
    margin: 0; font-weight: 600; color: var(--ink);
  }
  h1 span.dot { color: var(--accent); margin: 0 6px; }
  .meta { font-size: 12px; color: var(--ink-dim); letter-spacing: 0.04em; }
  .meta b { color: var(--ink); font-weight: 500; }
  aside {
    position: fixed; top: 64px; left: 18px; width: 280px;
    padding: 16px 16px 14px;
    background: rgba(8, 12, 28, 0.72);
    border: 1px solid var(--rule);
    border-radius: 10px;
    backdrop-filter: blur(8px);
    z-index: 4;
    font-size: 12px;
    max-height: calc(100vh - 84px);
    overflow-y: auto;
  }
  aside h2 {
    font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase;
    margin: 0 0 10px; color: var(--ink-dim); font-weight: 600;
  }
  aside .group { margin-bottom: 18px; }
  .chip {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 4px; border-radius: 6px;
    cursor: pointer; user-select: none;
    transition: background 0.12s ease;
  }
  .chip:hover { background: rgba(155,175,230,0.06); }
  .chip .swatch {
    width: 10px; height: 10px; border-radius: 50%;
    box-shadow: 0 0 12px currentColor, 0 0 4px currentColor;
  }
  .chip .label { flex: 1; color: var(--ink); }
  .chip .count { color: var(--ink-faint); font-variant-numeric: tabular-nums; font-size: 11px; }
  .chip.off .label, .chip.off .count { color: var(--ink-faint); text-decoration: line-through; text-decoration-color: rgba(155,175,230,0.2); }
  .chip.off .swatch { opacity: 0.25; box-shadow: none; }
  .edge-toggle {
    display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;
  }
  .edge-toggle button {
    background: transparent; color: var(--ink-dim);
    border: 1px solid var(--rule);
    padding: 4px 8px; border-radius: 999px;
    font: inherit; font-size: 10px; letter-spacing: 0.08em;
    cursor: pointer; text-transform: uppercase;
  }
  .edge-toggle button.on { color: var(--ink); border-color: rgba(156,194,255,0.5); background: rgba(156,194,255,0.08); }
  #stage { position: fixed; inset: 0; z-index: 1; }
  #stage svg { width: 100%; height: 100%; display: block; }
  .link { stroke-linecap: round; }
  .node { cursor: pointer; }
  .node-label {
    fill: var(--ink); font-size: 10px;
    pointer-events: none; text-shadow: 0 1px 4px rgba(0,0,0,0.9);
  }
  .tooltip {
    position: fixed; pointer-events: none; z-index: 6;
    padding: 10px 12px; min-width: 200px; max-width: 320px;
    background: rgba(8,12,28,0.96);
    border: 1px solid rgba(156,194,255,0.35);
    border-radius: 8px;
    font-size: 12px; line-height: 1.45;
    color: var(--ink);
    box-shadow: 0 12px 40px rgba(0,0,0,0.5);
    opacity: 0; transition: opacity 0.1s ease;
  }
  .tooltip .kind {
    font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--ink-dim); margin-bottom: 4px;
  }
  .tooltip .name { font-weight: 600; word-break: break-word; }
  .tooltip .file {
    color: var(--ink-dim); font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; margin-top: 4px; word-break: break-all;
  }
  .tooltip .stats {
    margin-top: 6px; padding-top: 6px;
    border-top: 1px solid var(--rule);
    color: var(--ink-dim);
  }
  .tooltip .stats b { color: var(--ink); font-weight: 500; }
  footer {
    position: fixed; bottom: 14px; right: 18px; z-index: 4;
    font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--ink-faint);
  }
  footer b { color: var(--ink-dim); font-weight: 500; }
  /* faint star backdrop */
  .stars {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
      radial-gradient(1px 1px at 20% 30%, rgba(255,255,255,0.6), transparent 60%),
      radial-gradient(1px 1px at 70% 80%, rgba(255,255,255,0.5), transparent 60%),
      radial-gradient(1.5px 1.5px at 50% 50%, rgba(180,210,255,0.35), transparent 60%),
      radial-gradient(1px 1px at 85% 20%, rgba(255,255,255,0.5), transparent 60%),
      radial-gradient(1px 1px at 10% 75%, rgba(180,210,255,0.45), transparent 60%);
  }
</style>
</head>
<body>
<div class="stars"></div>
<header>
  <h1>socratink<span class="dot">/</span>code constellation</h1>
  <div class="meta">
    <b id="m-nodes">—</b> nodes &nbsp;·&nbsp; <b id="m-edges">—</b> edges &nbsp;·&nbsp; <b id="m-files">—</b> files &nbsp;·&nbsp; built <b id="m-built">—</b>
  </div>
</header>

<aside>
  <div class="group">
    <h2>communities</h2>
    <div id="community-list"></div>
  </div>
  <div class="group">
    <h2>node kind</h2>
    <div id="kind-list"></div>
  </div>
  <div class="group">
    <h2>edges</h2>
    <div class="edge-toggle" id="edge-toggle"></div>
  </div>
  <div class="group">
    <h2>tip</h2>
    <div style="color:var(--ink-dim); line-height:1.5;">
      Hover a node to inspect.<br/>
      Click to lock highlight on its neighborhood.<br/>
      Drag to reposition. Scroll to zoom.
    </div>
  </div>
</aside>

<div id="stage"></div>
<div class="tooltip" id="tip"></div>

<footer><b>graph.db</b> &nbsp;·&nbsp; rendered with d3 force</footer>

<script>
const DATA = __DATA__;

// -------- palette: communities = constellations --------
// chosen for sky/aurora vibe, distinct hues
const PALETTE = [
  "#7ec8ff", // azure (frontend / js-node)
  "#7be0b6", // spring  (tests)
  "#ffd089", // amber   (auth)
  "#c79cff", // violet  (drill)
  "#ff9aa8", // coral   (scripts)
  "#9ee6e0", // teal    (request)
  "#b8c5ff", // periwinkle (overflow)
  "#ffe9a3", // warm ivory (overflow)
];
const KIND_SHAPE = { File: "diamond", Class: "square", Function: "circle", Test: "triangle" };

const communityById = new Map();
DATA.communities.forEach((c, i) => {
  c.color = PALETTE[i % PALETTE.length];
  communityById.set(c.id, c);
});

// degree map for node sizing
const degree = new Array(DATA.nodes.length).fill(0);
DATA.edges.forEach(e => { degree[e.s]++; degree[e.t]++; });

DATA.nodes.forEach((n, i) => {
  n.degree = degree[i];
  const c = communityById.get(n.community);
  n.color = c ? c.color : "#6a7398";
});

// ---- header meta ----
const fileCount = new Set(DATA.nodes.map(n => n.file)).size;
document.getElementById("m-nodes").textContent = DATA.nodes.length.toLocaleString();
document.getElementById("m-edges").textContent = DATA.edges.length.toLocaleString();
document.getElementById("m-files").textContent = fileCount.toLocaleString();
document.getElementById("m-built").textContent = (DATA.meta.last_updated || "—").slice(0, 10);

// ---- legends ----
const enabledCommunities = new Set(DATA.communities.map(c => c.id));
const enabledKinds = new Set(["File", "Class", "Function", "Test"]);
const enabledEdgeKinds = new Set(["CALLS", "IMPORTS_FROM", "INHERITS", "TESTED_BY", "REFERENCES", "CONTAINS"]);

function renderCommunityList() {
  const root = d3.select("#community-list");
  root.selectAll("*").remove();
  DATA.communities.forEach(c => {
    const memberCount = DATA.nodes.filter(n => n.community === c.id).length;
    const chip = root.append("div")
      .attr("class", "chip" + (enabledCommunities.has(c.id) ? "" : " off"))
      .on("click", () => {
        if (enabledCommunities.has(c.id)) enabledCommunities.delete(c.id);
        else enabledCommunities.add(c.id);
        renderCommunityList();
        applyFilters();
      });
    chip.append("span").attr("class", "swatch").style("color", c.color).style("background", c.color);
    chip.append("span").attr("class", "label").text(c.name);
    chip.append("span").attr("class", "count").text(memberCount);
  });
}

function renderKindList() {
  const root = d3.select("#kind-list");
  root.selectAll("*").remove();
  ["File", "Class", "Function", "Test"].forEach(k => {
    const count = DATA.nodes.filter(n => n.kind === k).length;
    const chip = root.append("div")
      .attr("class", "chip" + (enabledKinds.has(k) ? "" : " off"))
      .on("click", () => {
        if (enabledKinds.has(k)) enabledKinds.delete(k);
        else enabledKinds.add(k);
        renderKindList();
        applyFilters();
      });
    chip.append("span").attr("class", "swatch").style("color", "#9cc2ff").style("background", "#9cc2ff");
    chip.append("span").attr("class", "label").text(k);
    chip.append("span").attr("class", "count").text(count);
  });
}

function renderEdgeToggle() {
  const root = d3.select("#edge-toggle");
  root.selectAll("*").remove();
  ["CALLS", "IMPORTS_FROM", "INHERITS", "TESTED_BY", "REFERENCES", "CONTAINS"].forEach(k => {
    root.append("button")
      .attr("class", enabledEdgeKinds.has(k) ? "on" : "")
      .text(k.replace(/_/g, " ").toLowerCase())
      .on("click", function() {
        if (enabledEdgeKinds.has(k)) enabledEdgeKinds.delete(k);
        else enabledEdgeKinds.add(k);
        renderEdgeToggle();
        applyFilters();
      });
  });
}

renderCommunityList();
renderKindList();
renderEdgeToggle();

// ---- svg + zoom ----
const stage = d3.select("#stage");
const svg = stage.append("svg");

const defs = svg.append("defs");
// soft glow filter
const glow = defs.append("filter").attr("id", "glow").attr("x", "-50%").attr("y", "-50%").attr("width", "200%").attr("height", "200%");
glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
const merge = glow.append("feMerge");
merge.append("feMergeNode").attr("in", "blur");
merge.append("feMergeNode").attr("in", "SourceGraphic");

const root = svg.append("g");
const linkLayer = root.append("g").attr("class", "links");
const nodeLayer = root.append("g").attr("class", "nodes");

const zoom = d3.zoom()
  .scaleExtent([0.1, 6])
  .on("zoom", (e) => root.attr("transform", e.transform));
svg.call(zoom);

// initial center
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  svg.attr("viewBox", `${-w/2} ${-h/2} ${w} ${h}`);
}
resize();
window.addEventListener("resize", resize);

// ---- d3 force layout ----
const nodes = DATA.nodes.map(n => ({ ...n }));
const links = DATA.edges.map(e => ({ source: e.s, target: e.t, kind: e.k }));

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id((_, i) => i).distance(d => d.kind === "TESTED_BY" ? 60 : 35).strength(0.25))
  .force("charge", d3.forceManyBody().strength(-32).distanceMax(380))
  .force("center", d3.forceCenter(0, 0))
  .force("collide", d3.forceCollide().radius(d => 4 + Math.sqrt(d.degree)));

let link = linkLayer.selectAll("line").data(links).enter().append("line")
  .attr("class", d => "link link-" + d.kind)
  .attr("stroke", d => {
    if (d.kind === "TESTED_BY") return "rgba(123,224,182,0.18)";
    if (d.kind === "INHERITS") return "rgba(199,156,255,0.35)";
    if (d.kind === "IMPORTS_FROM") return "rgba(255,208,137,0.22)";
    if (d.kind === "CONTAINS") return "rgba(155,175,230,0.10)";
    return "rgba(126,200,255,0.16)";
  })
  .attr("stroke-width", d => d.kind === "INHERITS" ? 1.1 : 0.6);

let node = nodeLayer.selectAll("circle").data(nodes).enter().append("circle")
  .attr("class", "node")
  .attr("r", d => 2.5 + Math.sqrt(d.degree))
  .attr("fill", d => d.color)
  .attr("filter", "url(#glow)")
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
  .on("mouseover", showTip)
  .on("mousemove", moveTip)
  .on("mouseout", hideTip)
  .on("click", lockNode);

sim.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
});

// ---- filters ----
function applyFilters() {
  node.style("display", d => (enabledCommunities.has(d.community) && enabledKinds.has(d.kind)) ? null : "none");
  link.style("display", d => {
    if (!enabledEdgeKinds.has(d.kind)) return "none";
    const sOk = enabledCommunities.has(d.source.community) && enabledKinds.has(d.source.kind);
    const tOk = enabledCommunities.has(d.target.community) && enabledKinds.has(d.target.kind);
    return (sOk && tOk) ? null : "none";
  });
}

// ---- tooltip + neighborhood highlight ----
const tip = document.getElementById("tip");
let lockedId = null;

function neighborsOf(d) {
  const set = new Set([d.index]);
  links.forEach(l => {
    if (l.source.index === d.index) set.add(l.target.index);
    if (l.target.index === d.index) set.add(l.source.index);
  });
  return set;
}

function highlight(d) {
  const ns = neighborsOf(d);
  node.attr("opacity", n => ns.has(n.index) ? 1 : 0.15);
  link.attr("opacity", l => (l.source.index === d.index || l.target.index === d.index) ? 0.8 : 0.05);
}
function clearHighlight() {
  node.attr("opacity", 1);
  link.attr("opacity", 1);
}

function showTip(e, d) {
  if (lockedId !== null && lockedId !== d.index) return;
  if (lockedId === null) highlight(d);
  const c = communityById.get(d.community);
  tip.innerHTML = `
    <div class="kind">${d.kind}</div>
    <div class="name">${escapeHtml(d.name)}</div>
    <div class="file">${escapeHtml(d.file)}${d.line ? ":" + d.line : ""}</div>
    <div class="stats">
      degree <b>${d.degree}</b> &nbsp;·&nbsp; community <b>${c ? c.name : "—"}</b>
    </div>`;
  tip.style.opacity = 1;
  moveTip(e);
}
function moveTip(e) {
  const pad = 14;
  let x = e.clientX + pad, y = e.clientY + pad;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  if (x + w > window.innerWidth - 10) x = e.clientX - w - pad;
  if (y + h > window.innerHeight - 10) y = e.clientY - h - pad;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() {
  if (lockedId !== null) return;
  tip.style.opacity = 0;
  clearHighlight();
}
function lockNode(e, d) {
  e.stopPropagation();
  if (lockedId === d.index) {
    lockedId = null;
    hideTip();
  } else {
    lockedId = d.index;
    highlight(d);
    showTip(e, d);
  }
}
svg.on("click", () => {
  if (lockedId !== null) {
    lockedId = null;
    clearHighlight();
    tip.style.opacity = 0;
  }
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c]));
}
</script>
</body>
</html>
"""


def main() -> None:
    data = load_graph()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
