"""Excalidraw generator template. Copy to <WB_DIR>/build-<slug>.py, customize Layout."""
from __future__ import annotations
import itertools
import json
import random
from pathlib import Path

# Resolves relative to this script — works regardless of cwd.
OUT = Path(__file__).resolve().parent / "git-order.excalidraw"

PINK   = "#e03e3e"
INK    = "#1e1e1e"
PURPLE = "#9775fa"
BLUE   = "#1971c2"

# Pure monotonic counter — guarantees uniqueness across both `seed` and
# `versionNonce`. The earlier `count() * 17 + rand(1, 999)` formula collided
# at higher element counts (~60+) and validate.py rejected the file.
_seed = itertools.count(1_000_000)
def seed(): return next(_seed)

UPDATED = 1_700_000_000_000


def _base(elem_id, etype, x, y, w, h, *, stroke=INK, bg="transparent",
          fill="hachure", stroke_width=1, roundness=None, bound_elements=None):
    return {
        "id": elem_id, "type": etype, "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": stroke, "backgroundColor": bg, "fillStyle": fill,
        "strokeWidth": stroke_width, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": roundness,
        "seed": seed(), "version": 1, "versionNonce": seed(),
        "isDeleted": False, "boundElements": bound_elements,
        "updated": UPDATED, "link": None, "locked": False,
    }


def rect(elem_id, x, y, w, h, *, label=None, stroke=INK, bg="transparent",
         fill="hachure", stroke_width=1):
    """Rectangle + optional bound text label. Returns list of elements."""
    text_id = f"{elem_id}-text" if label else None
    bound = [{"id": text_id, "type": "text"}] if text_id else None
    r = _base(elem_id, "rectangle", x, y, w, h,
              stroke=stroke, bg=bg, fill=fill, stroke_width=stroke_width,
              roundness={"type": 3}, bound_elements=bound)
    out = [r]
    if label:
        out.append(text(text_id, x, y, w, h, label, container_id=elem_id, stroke=stroke))
    return out


def text(elem_id, x, y, w, h, body, *, font_size=18, container_id=None, stroke=INK):
    el = _base(elem_id, "text", x, y, w, h, stroke=stroke, roundness=None)
    el.update({
        "text": body, "fontSize": font_size, "fontFamily": 1,
        "textAlign": "center", "verticalAlign": "middle",
        "baseline": int(h * 0.72), "lineHeight": 1.25,
        "containerId": container_id, "originalText": body,
    })
    return el


def arrow(elem_id, x, y, dx, dy, start_id, end_id, *, stroke=INK, stroke_width=1, gap=5):
    a = _base(elem_id, "arrow", x, y, abs(dx) or 1, abs(dy) or 1,
              stroke=stroke, stroke_width=stroke_width,
              roundness={"type": 2})
    a.update({
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": start_id, "focus": 0, "gap": gap},
        "endBinding":   {"elementId": end_id,   "focus": 0, "gap": gap},
        "startArrowhead": None, "endArrowhead": "arrow",
    })
    return a


def add_arrow_binding(rect_element, arrow_id):
    bound = list(rect_element.get("boundElements") or [])
    bound.append({"id": arrow_id, "type": "arrow"})
    rect_element["boundElements"] = bound


elements = []


# ── Layout ──────────────────────────────────────────────────────────────

# Override link() to also register on diamonds (template only handles rectangles).
def link(arrow_id, from_id, to_id, x, y, dx, dy, *, stroke=INK, stroke_width=1):
    a = arrow(arrow_id, x, y, dx, dy, from_id, to_id, stroke=stroke, stroke_width=stroke_width)
    elements.append(a)
    for rect_id in (from_id, to_id):
        for el in elements:
            if el["id"] == rect_id and el["type"] in ("rectangle", "diamond", "ellipse"):
                add_arrow_binding(el, arrow_id)


def diamond(elem_id, x, y, w, h, label, *, stroke=INK, bg="transparent"):
    text_id = f"{elem_id}-t"
    d = _base(elem_id, "diamond", x, y, w, h,
              stroke=stroke, bg=bg, fill="hachure",
              roundness={"type": 2},
              bound_elements=[{"id": text_id, "type": "text"}])
    return [d, text(text_id, x, y, w, h, label, container_id=elem_id, stroke=stroke, font_size=14)]


# ── Title strip ────────────────────────────────────────────────────────
elements.append(text("title", 60, 30, 1500, 40, "git-order  —  any branch state  ⇒  exactly main + dev, both at the same clean tip", font_size=24))
elements.append(text("subtitle", 60, 80, 1500, 28,
    "singular goal: collapse chaos into a 2-branch invariant, salvaging high-signal work onto a fresh dev",
    font_size=14, stroke=PURPLE))

# ── CHAOS panel (input) ───────────────────────────────────────────────
elements.extend(rect("chaos", 60, 140, 280, 540, label="", stroke=PINK))
elements.append(text("chaos-h", 60, 150, 280, 30, "CHAOS  (input)", font_size=18, stroke=PINK))
chips = [
    ("c-main",       "main"),
    ("c-dev",        "dev (stale)"),
    ("c-arch1",      "dev-archive-A"),
    ("c-arch2",      "dev-archive-B"),
    ("c-test1",      "test/X"),
    ("c-test2",      "test/Y-gate"),
    ("c-fork",       "salvage-here"),
    ("c-orphan",     "origin/orphan-ref"),
]
for i, (eid, name) in enumerate(chips):
    cx = 80 + (i % 2) * 130
    cy = 200 + (i // 2) * 110
    elements.extend(rect(eid, cx, cy, 120, 90, label=name))

# ── CLASSIFY panel (decision tree — the heart) ────────────────────────
elements.extend(rect("clf", 380, 140, 700, 540, label="", stroke=INK))
elements.append(text("clf-h", 380, 150, 700, 30, "CLASSIFY  ▸  for each branch B  ≠  {main, dev}", font_size=18))

elements.extend(diamond("d-reach", 470, 210, 280, 110, "tip(B) reachable from main?\n(merge-base --is-ancestor)"))

elements.extend(rect("absorbed", 800, 230, 240, 70, label="ABSORBED → safe -d"))

elements.extend(diamond("d-value", 470, 380, 280, 110, "unique commits have value?\n(inspect main..B content)"))

elements.extend(rect("salvage", 800, 365, 240, 70, label="SALVAGE → onto fresh dev"))
elements.extend(rect("junk",    800, 460, 240, 70, label="JUNK → -D + backup ref"))

# arrows inside CLASSIFY
link("a-reach-yes", "d-reach", "absorbed",   750, 265, 50, 0)
link("a-reach-no",  "d-reach", "d-value",    610, 320, 0, 60)
link("a-value-yes", "d-value", "salvage",    750, 415, 50, -10)
link("a-value-no",  "d-value", "junk",       750, 460, 50, 30)

# Labels on decision arrows
elements.append(text("lbl-yes1", 755, 240, 40, 20, "yes", font_size=12, stroke=BLUE))
elements.append(text("lbl-no1",  615, 325, 40, 20, "no",  font_size=12, stroke=PINK))
elements.append(text("lbl-yes2", 755, 395, 40, 20, "yes", font_size=12, stroke=BLUE))
elements.append(text("lbl-no2",  755, 480, 40, 20, "no",  font_size=12, stroke=PINK))

# Note
elements.append(text("clf-note", 400, 600, 660, 60,
    "verify: every classification cites either an ancestor relation or a content reading.\n"
    "ambiguous → pause, surface to user, do not auto-decide.",
    font_size=12, stroke=PURPLE))

# ── ORDER panel (output) ──────────────────────────────────────────────
elements.extend(rect("order", 1120, 140, 380, 540, label="", stroke=BLUE))
elements.append(text("order-h", 1120, 150, 380, 30, "ORDER  (output)", font_size=18, stroke=BLUE))

elements.extend(rect("o-main", 1160, 220, 140, 100, label="main"))
elements.extend(rect("o-dev",  1320, 220, 140, 100, label="dev"))
link("a-equal", "o-main", "o-dev", 1305, 270, 10, 0, stroke=BLUE)
elements.append(text("o-eq",   1160, 340, 300, 30, "tip(main) == tip(dev)", font_size=16, stroke=BLUE))
elements.append(text("o-diff", 1160, 380, 300, 30, "diff main..dev = ∅", font_size=14))
elements.append(text("o-tree", 1160, 410, 300, 30, "working tree: clean", font_size=14))
elements.append(text("o-orig", 1160, 440, 300, 30, "origin matches local", font_size=14))
elements.append(text("o-only", 1160, 490, 300, 30, "only main + dev exist", font_size=14, stroke=BLUE))

# CHAOS → CLASSIFY → ORDER backbone arrows
link("a-chaos-clf", "chaos", "clf",   343, 410, 32, 0,  stroke=INK, stroke_width=2)
link("a-clf-order", "clf",   "order", 1083, 410, 32, 0, stroke=INK, stroke_width=2)

# ── EXECUTE row (bottom) ──────────────────────────────────────────────
y_ex = 720
elements.append(text("ex-h", 60, y_ex, 1440, 30, "EXECUTE  ▸  deterministic sequence", font_size=18))
exec_steps = [
    ("e1", "1. dev := main\n(ff or fresh-branch)"),
    ("e2", "2. for each SALVAGE\ncherry-pick / file-copy"),
    ("e3", "3. VERIFY\ndiff main..dev matches\nsalvage manifest"),
    ("e4", "4. push origin dev\n(FF only — no force)"),
    ("e5", "5. archive-rename\nthen delete each\nstale branch"),
    ("e6", "6. delete orphan\nremote refs"),
    ("e7", "7. ff dev → main\nso tip(main)==tip(dev)"),
]
for i, (eid, lbl) in enumerate(exec_steps):
    x = 60 + i * 210
    elements.extend(rect(eid, x, y_ex + 50, 190, 110, label=lbl))
    if i > 0:
        prev = exec_steps[i-1][0]
        link(f"a-{prev}-{eid}", prev, eid, x - 20, y_ex + 105, 15, 0)

# ── Callouts (bottom strip) ───────────────────────────────────────────
y_call = 900
elements.extend(rect("cb1", 60,  y_call, 460, 70, label="⏸  PAUSE before destructive op\n(branch -D, push --delete, force ops)", stroke=PINK))
elements.extend(rect("cb2", 540, y_call, 460, 70, label="✓  VERIFY after every step\ndiffstat must match what you intended", stroke=PURPLE))
elements.extend(rect("cb3", 1020, y_call, 480, 70, label="⊕  PRESERVE before delete\nbackup remote ref OR confirm reachability", stroke=BLUE))

# ── Output ──────────────────────────────────────────────────────────────
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "viewBackgroundColor": "#ffffff",
        "currentItemFontFamily": 1,
        "gridSize": None,
    },
    "files": {},
}
OUT.write_text(json.dumps(doc, indent=2))
print(f"Wrote {OUT} ({len(elements)} elements)")
