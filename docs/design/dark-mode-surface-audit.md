# Dark-Mode Surface Audit

Audit only — no fixes. Dashboard fix deferred behind funnel work.

## Method

Port 8000 was occupied by an external uvicorn and the preview launcher
reserves its own port, so browser-based capture was blocked. Audit was
done by reading the token flip in `public/css/variables.css` (lines
274–344) and tracing every top-level view's surface stack through
`public/css/*.css` + `public/index.html` + `public/login.html`.

The reading is deterministic: failure modes are derivable from the
token values (e.g. card `#302b49` on page `#1f1b31` = ~8 L* delta →
cards vanish into page). Screenshots would only confirm what the
token math already says.

### Dark-mode primitives (from `variables.css:274–344`)

| Token                    | Dark value                         | Used for                         |
|--------------------------|------------------------------------|----------------------------------|
| `--surface-page-theme`   | `#1f1b31` (mid indigo, L* ≈ 17)    | `--surface`, `--bg`              |
| `--surface-card-theme`   | `#302b49` (L* ≈ 25)                | `--surface-card`, `--card-bg`    |
| `--surface-panel-theme`  | `rgba(lavender, 0.18)`             | drawer, nested panels            |
| `--surface-nested-theme` | `rgba(lavender, 0.24)`             | chat bubble AI, map nested       |
| `--surface-high`         | `#3b3658` (L* ≈ 28)                | analytics hover, sidebar hover   |
| `--surface-highest`      | `#2d2846` (L* ≈ 23) — **below** `--surface-card` | unused consistently |
| `--gradient-card-start`  | `rgba(66, 59, 101, 0.96)` ≈ `#423b65` | settings/analytics cards       |
| `--gradient-card-end`    | `rgba(47, 42, 74, 0.98)` ≈ `#2f2a4a`  | "                              |
| `--graph-tile-top/-left/-right` | `#554f7b` / `#3b3658` / `#443e67` | isometric tiles in graph mode |
| Page gradient            | `#241f39 → #1f1b31` (linear) + two violet radials | body background      |

**Structural diagnosis.** The page/card delta is ~8 L*, and
`--surface-highest` is numerically *below* `--surface-card`, so the
"higher" surface is actually darker — the elevation ladder is broken.
Hypothesis in the task brief is correct: `#1f1b31` is a mid-saturation
indigo, not a near-black ground. Everything violet the design puts on
top of it (radial blooms, accent pills, lavender-500 rgba fills) has
no room to read as *accent* because the base is already that hue.

---

## (1) Surface classification

| View                 | Status           | Evidence                                                                 |
|----------------------|------------------|---------------------------------------------------------------------------|
| **Graph-mode map**   | Dark-native      | Dedicated `--graph-tile-*` token family with hex dark greys (#554f7b/#3b3658/#443e67), stage gradients `--gradient-stage-*` flip. Tuned per `dark-mode-graph-patch.md` (referenced by brief). |
| **Crystal tiles (hero + map grid)** | Partly dark-native | `crystal.css:90–121` has `body[data-theme="dark"]` overrides for opacity, drop-shadow, `top-empty` fill, selection highlight. Empty-slot dashed outline tuned for dark. Tile fills themselves consume `--tile-*` tokens that flip. |
| **Drill chat AI bubble** | Dark-native-ish | `--surface-nested` (lavender-alpha) composites OK on card; no hardcoded light fills. |
| **Tooltip / creation scrim** | Dark-native | Consumes `--tooltip-bg`/`--tooltip-border` and `--overlay-backdrop`, which have dedicated dark values. |
| **Dashboard hero card**  | Inverted        | `layout.css:125–138` — `background: var(--surface-card)` on a page that's only 8 L* darker. No dark-specific override (removed at `layout.css:177`). |
| **Isometric grid in hero (empty + populated)** | Inverted | Tiles consume `--tile-*` tokens which in dark map to `--graph-tile-*` greys (#554f7b/#3b3658/#443e67) — but those were designed to sit on the graph-mode stage gradient, not on the dashboard's flat mid-indigo page. Tile-top #554f7b is close to page #1f1b31 in hue and only +~15 L, and `::before` bloom at opacity 0.7 washes it further. |
| **Library view**     | Inverted         | `.library-view` uses `var(--surface)`; `.library-card` uses `--gradient-panel-start/-end`. Gradient flips, but chips (`.library-card-pill`, `--accent-soft`) and `--accent-border` read as muddy violet-on-violet. Card has no meaningful elevation over page. |
| **Analytics / Your Progress** | Inverted   | `ai-runs-dashboard.css:559–562` explicitly relies on token flip. Hardcoded `.bar-track { background: rgba(ink-900, 0.08) }` (line 354) — ink-900 is the *dark* primitive, so bar track = near-invisible on dark card. Stat tiles consume `--surface-card` *inside* a `.analytics-panel` that also consumes `--gradient-card-*` — identical fill, nested cards vanish. |
| **Settings page**    | Inverted         | `.settings-page-card` uses `--gradient-card-*` on `--surface` page. Same low elevation as analytics. Inputs use `--card-bg` (= `--surface-card-theme`) which now equals the card's own fill — field/container boundary lost. |
| **Map view (study mode)** | Inverted      | `.graph-detail` + `.graph-stage-wrap` both `var(--surface-card)` on `var(--surface)`. `.graph-study-reference { background: rgba(lavender, 0.04) }` — effectively zero contrast in dark. `.graph-detail-surface` / `.graph-detail-disclosure` use `rgba(white, 0.62)` / `rgba(white, 0.45)` which are designed for light ground; become milky smears over the card. |
| **Drill chat container** | Inverted (inherits map) | `.drill-ui-embedded` sits inside `.graph-detail` in the same surface stack. Ai bubble compositing is fine; the container around it is the problem. Mobile sticky `.chat-input-area` (layout.css:1738) uses `--surface-card` — pinned to bottom with no distinguishable elevation. |
| **Bottom nav (mobile)** | Inverted       | `layout.css:361` — `background: var(--surface-card)`, same as page body at bottom, only a `border-top: var(--border)` hairline separates them. Shadow rgba(ink, 0.08) disappears on dark ground. |
| **Drawer footer (mobile)** | Dark-native | Has `[data-theme="dark"] .drawer-footer` override at `layout.css:208–210`. |
| **Auth/login page**  | Broken (no dark) | `login.html:2` ships `<html lang="en" class="light">` hardcoded. `login.css:1–17` defines its own `:root` with hex primitives (`--surface: #fdf9f5` etc.) and does not import `variables.css`. No `[data-theme="dark"]` block anywhere in `login.css`. The page ignores user theme preference entirely. Not "inverted muddy" — it's a light page regardless of toggle. |

---

## (2) Specific failures per inverted surface

Ordered by the token anti-pattern they instantiate.

### A. Hero card (dashboard)
- **Bg/card contrast**: page `#1f1b31` vs card `#302b49`, ΔL ≈ 8. Card perimeter relies on `--shadow-ambient` = `0 40px 100px rgba(44,51,62,0.05)` — inherited from light mode, near-invisible on dark. `--shadow-card` is correctly re-tokened for dark but hero uses `--shadow-ambient`, not `--shadow-card`.
- **Hero empty state (single-column collapse)**: the recent 3d29229/750ccbf/32208d2 empty-state work tightened the light-mode design; in dark the hero card becomes an unbordered blob roughly the shape of the page.
- **Hero eyebrow / chip**: `--accent-soft` = `rgba(lavender, 0.22)` on card `#302b49` reads as a faint lavender patch, not a chip. Border `--accent-border` `rgba(lavender, 0.34)` is the only thing defining the chip's edge.

### B. Isometric grid (hero + mobile hero)
- `--tile-top` in dark = `#554f7b`, `--tile-left` = `#3b3658`, `--tile-right` = `#443e67`. Inter-tile ΔL ≈ 5–8. On a page that is *already* #1f1b31, the full structure reads as a single indigo mass.
- Empty-tile dash at `--locked` = `rgba(lavender, 0.52)` — the strongest element in the illustration after the crystal, which inverts the intended visual hierarchy (crystal should dominate, dashes should recede).
- `#grid-container::before` bloom at opacity 0.7 (crystal.css:101) adds a violet wash exactly where the tiles need the most separation.
- Consequence: tile/pin definition gone, crystal no longer reads as occupying a tile.

### C. Library
- Card gradient `#3b355b → #2d2846` against page `#1f1b31` — the bottom half of the gradient (`#2d2846`) is *lighter than `--surface-card-theme` by only 2 L* but darker than the gradient top*. Cards look like gradients without an enclosing form.
- `.library-card-pill` uses `--accent-soft` + `--accent-soft-strong` border — the pill has almost no fill in dark, only a 1px lavender edge.
- `.library-card-vault:hover` relies on `--shadow-raised` (re-tokened but weak) and `--accent-border-strong` — hover state barely registers.

### D. Analytics
- `.bar-track { background: rgba(var(--ink-900-rgb), 0.08) }` (**hardcoded**, `ai-runs-dashboard.css:354`). `ink-900` is the *dark* primitive, so on a dark card the track is 8% dark-on-dark — effectively invisible. Bars float with no channel.
- `.stat-tile` and `.list-card` and `.event-item` all use `--surface-card` nested inside `.analytics-panel` (which uses `--gradient-card-*`, average L* ≈ 23–27). Inner tile ≈ outer panel — three levels of nesting become one flat plane.
- `.empty-state { background: rgba(var(--mauve-200-rgb), 0.24) }` — mauve alpha over dark card reads as violet haze, not a state surface.
- `.callout-card { radial(rgba(lavender, 0.16)) + var(--surface-card) }` — radial accent barely lifts off card.

### E. Settings
- `.settings-page-card` uses `--gradient-card-*` on `--surface` — same elevation problem as analytics panels.
- `.settings-input { background: var(--card-bg); border: 1px solid var(--border) }`. `--card-bg` aliases to `--surface-card-theme` which *equals the page card it sits in*. The input border is `rgba(cream, 0.14)` — readable but the input fill is ambient with its container.
- `.settings-badge.success { background: var(--accent-soft); color: var(--primary) }` — accent-soft on card is ~3% effective contrast.
- `.settings-box { background: var(--surface-nested) }` — lavender alpha on card, mildly distinguishable.

### F. Map view — study mode
- `.graph-detail` + `.graph-stage-wrap` both `var(--surface-card)` on `var(--surface)`. Two primary columns with identical fill, identical border `var(--border)`.
- `.graph-study-reference { background: rgba(lavender, 0.04); border: rgba(lavender, 0.1) }` — 4% lavender alpha is noise, not a surface.
- `.graph-detail-disclosure` and `.graph-detail-surface` use `rgba(white, 0.45–0.62) → rgba(cream, 0.22–0.34)` gradients: **designed for light ground**. On dark they become a milky veil that reads as a rendering bug.
- Repair-reps animations (graphPrimedGlow, graphSolidGlow) use `rgba(110, 174, 209, *)` — a cyan blue appearing nowhere else in the dark palette, jarring.

### G. Drill chat container (inherits from map)
- Container surfaces same as F. Chat bubbles themselves read OK (AI = `--surface-nested` alpha; user = `--primary-fill` unchanged). But the rail around them collapses.
- Mobile: `body.is-drilling .chat-input-area { background: var(--surface-card) }` pinned bottom — identical to `.graph-detail` that wraps it; no visual division from keyboard area.

### H. Bottom nav (mobile)
- `.bottom-nav { background: var(--surface-card); box-shadow: 0 -2px 10px rgba(ink-900, 0.08); border-top: 1px solid var(--border) }`. On dark ground: bg same as enclosing `#card`, shadow zero-effective, only a 14% cream hairline separates the nav from content. In graph mode (dark-native ground) the hairline is enough; in dashboard mode it floats.

### I. Auth/login page
- Not inverted — **ignores theme entirely.** Hardcoded light palette in `login.css:1–17`. `<html class="light">` fixed at `login.html:2`. If user toggles dark elsewhere then navigates to /login, they hit an unexpected light flash.
- Separate issue from the others; needs its own decision (wire up to variables.css vs. keep deliberately light brand page).

---

## (3) Ranked fix order — user-facing impact

1. **Dashboard hero + isometric grid** (deferred per brief, but remains #1). First surface on load; confirmed bad; isometric illustration losing tile definition breaks the signature visual. Every new user lands here.
2. **Analytics bars + nested tiles.** Second-most-visited signal surface. Hardcoded `rgba(ink-900, 0.08)` bar track is a one-line outright bug; nested-tile flattening undermines the whole "Your Progress" read.
3. **Settings page.** Medium traffic, but input fields being fill-identical to their container is a functional (not only aesthetic) problem — users can't see the field boundary.
4. **Map view study mode.** Regular-use surface. The `rgba(white, *)` gradient smears on `graph-detail-disclosure`/`-surface` read as broken rendering, which is worse than flat.
5. **Library.** Medium traffic. Pill/card affordance erosion but content is still scannable.
6. **Drill chat container.** Bubbles are fine; container problem is mostly noticed on mobile during drill.
7. **Bottom nav (mobile).** Edge-case: only noticeable on dashboard/library in dark on mobile. Graph mode is fine.
8. **Auth/login.** Separate track — decide whether login should be dark-aware at all before fixing. Low impact (one-shot screen, clearly brand-styled).

---

## (4) Recommendation — systemic vs per-surface

**Do a systemic token-layer fix, then per-surface touch-ups — not the other way around.**

### Why systemic first

Every failure above except (I/login) traces to the same two root causes:

1. **Page is too light.** `#1f1b31` is a mid-saturation indigo ~L* 17. The graph mode works because it *adds* a gradient stage on top; the signal surfaces don't, and expect the page to be near-black the way a graph stage's top layer expects the page to be indigo. If the page were `#0e0b1a`-ish (near-black, low saturation) the existing card values would gain 6–8 L* of breathing room for free.
2. **Elevation ladder is broken.** `--surface-highest` (#2d2846) < `--surface-card` (#302b49) < `--surface-high` (#3b3658). The "highest" token is darker than plain card — wrong direction. Gradient-card-end `#2f2a4a` ≈ surface-highest — redundant.

Patching these two numerically would lift dashboard hero, library, analytics panels, settings cards, study-mode detail panels, and bottom nav simultaneously. No per-component rules needed for the contrast complaint itself.

### Proposed systemic shape

Not implementing, but for orientation:

```css
[data-theme="dark"] {
  /* Near-black signal ground */
  --surface-page-theme: #0e0b1a;     /* was #1f1b31 */
  --surface-card-theme: #1a1730;     /* was #302b49  — was too light, now restored delta ~10 L* */
  --surface-high:       #2d2846;     /* was #3b3658 — repurposed */
  --surface-highest:    #3b3658;     /* was #2d2846 — restored ladder direction */
  /* Gradient card pair regenerated against new ground */
  --gradient-card-start: rgba(40, 35, 70, 0.96);
  --gradient-card-end:   rgba(22, 19, 44, 0.98);
  /* Page gradient restated with violet as accent, not ground */
  --page-background:
    radial-gradient(circle at 14% 14%, rgba(var(--lavender-500-rgb), 0.20), transparent 32%),
    radial-gradient(circle at 82% 16%, rgba(var(--violet-600-rgb),   0.18), transparent 28%),
    linear-gradient(180deg, #120e22 0%, #0e0b1a 100%);
}
```

After this, graph mode needs verification — the graph-mode design currently reads well against `#1f1b31` because its own stage gradient is tuned for that ground. Two options:

- **Option A (preferred):** graph mode re-tunes `--gradient-stage-*` for the new darker ground. Brief edit; graph stage already uses its own gradient stack.
- **Option B:** introduce a scoped override on `.map-view` (or `body[data-map-open="true"]`) that restores the old page value locally. Works but multiplies sources of truth and re-introduces exactly the kind of state-split the user has feedback against (see `feedback_product_principles_to_engineering`).

### Per-surface patches still needed after

A systemic fix does not remove these:

- `ai-runs-dashboard.css:354` — replace `rgba(ink-900, 0.08)` bar track with a `--track-neutral` token (or `rgba(cream, 0.10)` in dark). Always broken regardless of page ground.
- `graph-detail-disclosure` / `graph-detail-surface` `rgba(white, *)` gradients — these are light-mode-only compositions and need dark counterparts or a token (`--graph-accent-surface-grad-*`).
- `graph-repair-*` cyan `rgba(110, 174, 209, *)` — off-palette, probably wants to flow from `--accent-*` or get an explicit `--repair-*` token.
- `login.html` / `login.css` — separate decision: wire into `variables.css` and respect `[data-theme]`, or keep deliberately brand-light.

### Risk summary

- **Hard-to-reverse:** none — token values are a single file.
- **Needs before shipping:** graph-mode verification (option A or B decision), and a read-through of dashboard + analytics + settings in the new palette. Bar-track hex fix is a separate one-line follow-up.
- **Safe to ship behind the deferred dashboard fix:** yes — the token change is the dashboard fix, and cascades to everything else for free.
