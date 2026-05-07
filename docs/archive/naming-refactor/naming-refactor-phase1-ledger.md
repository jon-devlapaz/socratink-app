# Phase 1 ledger — socratink vernacular revamp · motif: Reading Room and Field Journal

> Phase 1 deliverable for `naming-refactor-prompt.md`. Output only — no code edits.
> User-locked decisions (this turn): motif = Candidate A; (1) dungeon-map stays designer-only; (2) `ignition` keeps code-side route id, display label only is in scope; (3) all four state-token display labels open per-row; (4) chip max 12 chars, nav max 24, ARIA max 42; (5) drop login tagline; (6) `tink it` in scope as a CTA candidate; (7) dark-mode visuals stay, labels adopt the motif.
> Two slots are blocked pending the user's pick from the alternatives below: the **`Ignition`** display label and the **`Start Cold Attempt`** primary action. Body rows for those two strings carry `[blocked — pick alternative]` and the per-row recommendation.

---

## Disputed slots — pick before applying

### 1. `Ignition` (top-nav display label) · Phase 0 candidate `Intake` blocked as clinical

Three motif-aligned alternatives, all ≤ 24 chars:

| Alt | Form | Why it works | Why it might not |
| --- | --- | --- | --- |
| **`New Entry`** *(recommended)* | journal-coherent; extends the Repair-History `field journal` vocabulary used at Screen 7 | reads as "add an entry to your journal" — coherent with the motif anchor; 9 chars; survives ARIA cleanly (`Begin a new entry`) | reads as data-entry / form-tool register if a first-time visitor maps it to spreadsheets |
| **`Sketch`** | directly names the route's artifact (`Starting Sketch` is a defined domain noun in `UBIQUITOUS_LANGUAGE.md`) | unambiguous tie to the route's actual purpose; 6 chars; pairs perfectly with the `Starting Sketch` field heading | verb/noun ambiguity in nav; siblings `Desk / Library / Settings` are nouns, `Sketch` reads as a verb |
| **`Inkwell`** | atmospheric reading-room object; resonates with the `socratink` brand syllable | strongest motif voice; 7 chars; the implement you reach for when starting a study | first-time visitors need onboarding to parse "Inkwell" as "where you start a new concept"; not literal |

**Recommendation: `New Entry`.** Lowest first-time-visitor cost; strongest cross-surface coherence (the field journal in Repair History becomes the running ledger of which entries you've started and which you've recorded).

### 2. `Start Cold Attempt` (primary action) · Phase 0 candidate `First Pass` blocked as graded

Three alternatives that preserve "unscored, from your own model":

| Alt | Form | Why it works | Why it might not |
| --- | --- | --- | --- |
| **`Try Cold`** *(recommended)* | preserves the existing `cold` register the product already speaks; verb-led | 8 chars; unambiguously ungraded ("try" ≠ pass); pairs with screen title `First Cold Attempt` cleanly | "cold" needs the `Cold Attempt` screen above it to define the term; standalone the word reads sparse |
| **`Sketch From Memory`** | names the act; reading-room sketch metaphor; "from memory" makes "no scoring" structural | maximally explicit about what the button does without using the cold-attempt jargon at all | 18 chars — fine on desktop, tight at 320px; shifts the noun the screen owns from `Cold Attempt` to `Sketch From Memory` |
| **`tink it`** | brand-sanctioned lowercase verb per `brand-reference.md`; tests motif flexibility (the lowercase brand-as-verb folds cleanly into reading-room quiet) | strongest brand identity; 7 chars; `tink` is the syllable everything else echoes from | first-time users can't parse the verb without onboarding copy; brand-as-verb requires a one-line "what does *tink* mean" explainer somewhere |

**Recommendation: `Try Cold`.** It is the smallest possible motif move — preserves the canonical `cold attempt` domain noun, keeps muscle memory, and reads ungraded by construction. Reserve `tink it` for a later motif-confidence pass once the rest of the vernacular is locked.

---

## Pre-discovered findings — locked rows, ship regardless of motif

These seven rows hand-confirmed at their cited locations. Apply in Phase 2 batch 0 (independent of all other rows below).

| Surface (file:line) | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `public/login.html:28` (alt) | `Socratink brand mark` | `socratink mark` | brand-rule (lowercase); 14 chars; ARIA cleanly | none — `mark` is the canonical brand term |
| `public/index.html:77` (alt) | `Socratink brand mark` | `socratink mark` | same | same |
| `public/login.html:11` (`<title>`) | `socratink — the Socratic Canvas` | `socratink — sign in` | user directive (5); "Socratic Canvas" is not in canonical vocabulary | none |
| `public/index.html:8,11` (meta `apple-mobile-web-app-title`) | `Socratink` | `socratink` | brand-rule; iOS may force-capitalize the home-screen badge regardless, but the meta value stays canonical | iOS rendering may title-case anyway; cosmetic |
| `public/login.html:7,10` (meta) | `Socratink` | `socratink` | same | same |
| `public/js/app.js:299` | `Spaced evidence is on record. Re-drill later if you want to challenge it.` | `Spaced evidence is on record. Re-drill later to keep this one in shape.` | "challenge" is on the avoid-list (DESIGN.md, prompt §forbidden-vocabulary) | new copy must remain quiet — no triumphal register |
| `public/js/graph-view.js:69` | `Needs correction` | `Needs a different causal link` | "correction" reads as defect/diagnostic framing | 30 chars — fits badge; verify against `getGapLabel()` callers |
| `public/js/graph-view.js:832` | renders `data.reDrillBand` (one of `spark/link/chain/clear/tetris`) directly to the learner | **remove the visible band entirely**. Replace the trajectory paragraph with: `Cold attempt: exploratory guess. Spaced re-drill: solid. The change is the evidence on record.` | trajectory bands are post-attempt internal-only telemetry per DESIGN.md §11 — `tetris` reaching learner copy is a hard voice violation. **Most urgent row in this ledger.** | the paragraph must still distinguish solid vs. non-solid spaced re-drill outcomes — the existing `isSolid` ternary handles it; the band literal is what comes out |
| `public/js/graph-view.js:391` (cluster `teaserLabel`) | `Locked container` | `Locked section` | "container" is implementation jargon; `section` is the motif-aligned term for cluster | propagates to all cluster placeholders |
| `public/js/graph-view.js:906` (`graph-detail-kicker`) | `Cluster` | `Section` | same | kicker capitalization |
| `public/js/graph-view.js:910`, `app.js:2378` (template) | `${data.subnodeCount \|\| 0} drill nodes` / `${meta.subnodeCount} drill nodes` | `${n} entries` (or `1 entry` / `${n} entries` with a small plural helper) | "drill nodes" is implementation jargon; `entries` is the motif-aligned word for `subnode` (see motif glossary) | pluralization helper required; `0 entries` is acceptable |
| `app.js:2377` | `${meta.clusterCount} clusters` | `${n} sections` | same family | same plural-helper note |

**ARIA scan:** the prior-run scan found no missing `aria-label` on icon-only buttons. Re-confirmed in this inventory: `aria-label`s exist on `#drawer-toggle`, drawer close, account actions, theme toggle, sidebar toggle, concept-create close, modal close, repair-reps steps, edge labels, and node labels. **Confirmed clean.**

---

## Motif glossary (lock these before applying body rows)

These 5–8 anchors are the load-bearing vocabulary of the chosen motif. Every body row below derives from this glossary.

| Anchor | Singular | Plural | Replaces (in copy only) | Notes |
| --- | --- | --- | --- | --- |
| **journal entry** | `entry` | `entries` | `room`, `drill node`, `subnode` (in learner copy only — code identifiers stay) | the basic unit of work; what was a "room" becomes "an entry in your journal" |
| **section** | `section` | `sections` | `cluster`, `container` (in learner copy) | cluster-level grouping under a backbone branch |
| **backbone principle** | `backbone principle` | `backbone principles` | — | already on motif; kept verbatim |
| **core thesis** | `core thesis` | — | — | already on motif; kept verbatim |
| **field journal** | `field journal` | — | "Repair History" screen | Screen 7's display label; existing canonical motif anchor (DESIGN.md §3) |
| **starting sketch** | `starting sketch` | `starting sketches` | — | already on motif (UBIQUITOUS_LANGUAGE.md domain noun); kept verbatim |
| **draft path / draft route** | `draft path` | `draft paths` | — | already on motif; kept verbatim |
| **cold attempt / spaced re-drill** | (domain nouns) | — | — | display labels stay; only re-casings allowed |

**Banned from learner copy under this motif (in addition to the prompt's forbidden vocabulary):**
- `cluster` (use `section`)
- `container` (use `section`)
- `drill node` / `subnode` (use `entry`)
- `room` (use `entry`)
- `Cluster Result` / `Drill Result` (use `Section result` / `Entry result`)
- `boss fight` (designer-only per user lock; should not appear in copy)

---

## Body ledger

Format: `Surface (file:line) | Current | Proposed | Rationale | Risk`. Where many rows share a fix, they appear as a single grouped row with all locations listed.

### A. Top-level navigation (≤ 24 chars)

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:58, 83` (sidebar + bottom nav) | `Ignition` | `[blocked — pick alternative; recommended: New Entry]` | route id `ignition` stays per user lock (2); display only | low — only display label moves |
| `index.html:62, 85` | `Desk` | `Desk` `[no change — motif keeps the term]` | the desk *is* the reading room; canonical | — |
| `index.html:66, 87` | `Library` | `Library` `[no change — motif keeps the term]` | reading-room canonical | — |
| `index.html:70, 89` | `Settings` | `Settings` `[no change — motif keeps the term]` | utility nav; cross-product convention; "Your reading room" subtitle (`app.js:3743`) carries the motif | — |
| `index.html:91` (bottom-nav-only) | `Send Feedback` | `Send Feedback` `[no change — voice rule already satisfied]` | utility | — |
| `index.html:212` (Desk kicker) | `Desk` | `Desk` `[no change]` | matches nav | — |
| `app.js:3741` (Settings kicker) | `Settings` | `Settings` `[no change]` | matches nav | — |
| `app.js:2325` (Library kicker) | `Library` | `Library` `[no change]` | matches nav | — |
| Map-mode toggle: `index.html:351, 352` | `Route` / `Graph` | `Route` / `Graph` `[no change — domain nouns; see open question 8 below]` | "graph" is a learner-visible code term; renaming would propagate widely with little voice gain | — |

### B. Screen titles and section headings

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:285`, `app.js:335`, `concept-create.js:33` | `What do you want to understand?` | `What do you want to understand?` `[no change — voice rule already satisfied]` | invitation register; on-motif | — |
| `index.html:307` | `Starting map` (field heading) | `Starting sketch` | aligns to the canonical `Starting Sketch` domain noun (UBIQUITOUS_LANGUAGE.md); the heading and the field name should agree | propagates with the change at `index.html:307` and `concept-create.js:283` (kicker `STARTING MAP`) |
| `concept-create.js:283` (kicker) | `STARTING MAP` | `STARTING SKETCH` | same | uppercase variant of above |
| `index.html:366` | `Evidence Map` | `Evidence Map` `[no change — already on motif]` | "evidence map" is product creed; reading-room compatible | — |
| `index.html:376`, `app.js:1995` | `Cold Attempt` / `First Cold Attempt` | `Cold Attempt` / `First Cold Attempt` `[no change — domain noun, unchanged in this naming pass]` | UBIQUITOUS_LANGUAGE.md term; display title kept; only the action-button label is in scope | rename only if action label moves to `tink it`; otherwise hold |
| `app.js:1974` | `Concept Threshold` | `Starting Sketch` | reuses the canonical artifact name; the screen *is* the place that captures the starting sketch | re-frames a screen-title noun → confirm with user before applying |
| `app.js:1981` | `Provisional Graph` | `Provisional Graph` `[no change — domain noun]` | UBIQUITOUS_LANGUAGE.md term; visible label and domain noun coincide | — |
| `app.js:2009` | `Draft Route` | `Draft Route` `[no change — already on motif]` | DESIGN.md allowed graph-claim vocabulary | — |
| `app.js:2026` | `Nearby Rooms` | `Nearby Entries` | room → entry per glossary; pluralization regular | re-keyword for any callers expecting "Rooms" |
| `app.js:2065` | `Connection Hints` | `Connection Hints` `[no change]` | reading-room canonical | — |
| `app.js:2074` | `Locked Study Silhouette` | `Locked Study Silhouette` `[no change — domain noun, screen title]` | DESIGN.md screen 4 name; legible silhouette metaphor is on motif | — |
| `app.js:2082` | `Framework Notes` | `Framework Notes` `[no change — already on motif]` | scholarly | — |
| `app.js:2328` | `Documentation Concepts` | `Reference Concepts` | "Documentation" is implementation register; `Reference` is reading-room canonical (a reference shelf) | low |
| `app.js:2355` | `Your Library` | `Your Library` `[no change]` | matches nav | — |
| `app.js:3743` | `Your reading room` | `Your reading room` `[no change — motif voice line]` | already on motif | — |
| `app.js:3757` | `Display` | `Display` `[no change]` | utility heading | — |
| `app.js:886` | `Start a concept` | `Start a concept` `[no change]` | voice rule satisfied | — |
| `index.html:409` | `Send Feedback` | `Send Feedback` `[no change]` | utility | — |
| `graph-view.js:639` | `Reps did not load` | `Reps did not load` `[no change]` | acceptable | — |
| `graph-view.js:667` | `Practice logged` | `Practice logged` `[no change]` | on motif | — |
| `graph-view.js:760` | `Enough for this pass` | `Enough for this pass` `[no change — already on motif]` | reading-room | — |
| `graph-view.js:761` | `This session has enough retrieval on record. Return later so spaced reconstruction can carry the evidence.` | `[no change — voice rule already satisfied]` | scholarly cadence | — |
| `graph-view.js:966` | `One node at a time` | `One entry at a time` | node → entry per glossary | propagation |
| `graph-view.js:972`, `app.js:1944, 3505`, `graph-view.js:309, 798, 872` (`Core Thesis`) | `Core Thesis` (kicker / heading) | `Core Thesis` `[no change — already on motif]` | scholarly canonical | — |
| `graph-view.js:976`, `app.js:1998` | `Starting Room` | `Starting Entry` | room → entry per glossary | check kicker styling — uppercase variant should also be `STARTING ENTRY` |

### C. Action labels (button text)

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:355`, `app.js:1920, 2874`, `graph-view.js:895` | `Start Cold Attempt` | `[blocked — pick alternative; recommended: Try Cold]` | primary user-locked alternative slot | — |
| `app.js:2874` (alt branch) | `Start With Core Thesis` | `Start With Core Thesis` `[no change]` | already on motif | — |
| `index.html:319`, `app.js:451 (title)` | `Create draft path` | `Create draft path` `[no change — already on motif]` | DESIGN.md allowed vocabulary | — |
| `index.html:219` | `Begin at Ignition` | `Begin at New Entry` (or whichever wins for `Ignition`) | propagates the disputed-slot choice | applies only after slot 1 resolves |
| `index.html:231`, `app.js:1635` | `Start room` | `Open entry` | room → entry; "Start" overstates ("start" the entry implies grading); "Open" is reading-room precise | low; appears on Desk hero |
| `index.html:234` | `Needs repair` | `Needs repair` `[no change — already on motif]` | scholarly, ungraded | — |
| `index.html:235` | `Attempt recorded` | `Attempt recorded` `[no change — already on motif]` | DESIGN.md allowed vocabulary | — |
| `index.html:238, 246`, `app.js:1638` | `Spacing gate unavailable` | `Spacing gate unavailable` `[no change]` | precise; not punitive | — |
| `index.html:290`, `app.js:2347` | `Open Library` / `Open concept` | `Open Library` / `Open concept` `[no change]` | reading-room verb | — |
| `app.js:307, 329` | `Begin` | `Begin` `[no change]` | voice rule satisfied | — |
| `app.js:312, 316` | `Open Draft Path` | `Open Draft Path` `[no change]` | already on motif | — |
| `app.js:313, 317` | `Draft Map` | `Draft Map` `[no change]` | — | — |
| `app.js:319, 1920` | `Repair Gap` | `Repair Gap` `[no change — already on motif]` | scholarly | — |
| `app.js:322, 326` | `Open Evidence Map` | `Open Evidence Map` `[no change]` | — | — |
| `app.js:323` | `Return Later` | `Return Later` `[no change]` | reading-room canonical | — |
| `app.js:327` | `Open Desk` | `Open Desk` `[no change]` | matches nav | — |
| `app.js:1655` | `Start repair` | `Start repair` `[no change]` | scholarly | — |
| `app.js:2002`, `graph-view.js:993` | `Start first room` | `Open first entry` | room → entry; "Open" not "Start" (verb-tone fix) | low |
| `app.js:1693` | `Add Another Concept` | `Add Another Concept` `[no change]` | utility | — |
| `app.js:2347` | `Add concept` | `Add concept` `[no change — voice rule satisfied]` | per UBIQUITOUS_LANGUAGE.md / DESIGN.md examples | — |
| `app.js:2818, 2845` | `Reopen Study` / `Resume Study` | `Reopen Study` / `Resume Study` `[no change]` | scholarly | — |
| `app.js:2821, 2852, 2865` | `Start Repair Reps` | `Start Repair Reps` `[no change — domain noun, display matches]` | UBIQUITOUS_LANGUAGE.md term | — |
| `app.js:2850, 2863` | `Start Spaced Re-Drill` | `Start Spaced Re-Drill` `[no change — domain noun]` | UBIQUITOUS_LANGUAGE.md term | — |
| `app.js:2817` | `Go to next reachable branch` / `Go to next reachable node` | `Go to next reachable branch` / `Go to next reachable entry` | node → entry where node = subnode; if "node" refers to the cluster level here, use `section` | confirm code path before applying |
| `app.js:1446` | `Try again` | `Try again` `[no change]` | utility | — |
| `app.js:1041` | `Continue with Google` | `Continue with Google` `[no change]` | OAuth standard | — |
| `app.js:1040` | `Browse starter maps` | `Browse starter maps` `[no change — already on motif]` | reading-room | — |
| `app.js:1826`, `concept-create.js:288, 296` | `edit` | `edit` `[no change]` | utility | — |
| `concept-create.js:121, 122` | `Cancel` / `Continue` | `Cancel` / `Continue` `[no change]` | utility | — |
| `concept-create.js:231–237` | `Build from my map and source` / `Build from source` / `Build from my starting map` | `Build from my starting sketch and source` / `Build from source` / `Build from my starting sketch` | aligns to canonical `Starting Sketch` term | length grows by ~6 chars; verify mobile fit |
| `concept-create.js:307–308` | `replace` / `Add source` | `replace` / `Add source` `[no change]` | utility | — |
| `concept-create.js:609–611, 687–689` | `Text` / `URL` / `File` and `Paste` / `URL` / `Upload` | `[no change]` (utility tabs) | — | — |
| `concept-create.js:629, 709` | `Attach` / `Extract` | `Attach` / `Extract` `[no change]` | utility | — |
| `graph-view.js:556–558, 589–591` | `Same bridge` / `Partly linked` / `Different link` and `Guessing` / `Have a hunch` / `Can trace it` | `[no change — voice rule already satisfied; on motif]` | scholarly self-rating language | — |
| `graph-view.js:641, 685, 854` | `Reopen Study` | `Reopen Study` `[no change]` | scholarly | — |
| `graph-view.js:642, 671, 685, 762, 790, 858` | `Back to graph` / `Return to Map` | `Back to map` / `Return to Map` `[no change for "Return to Map"]`; **`Back to graph` → `Back to map`** | "graph" is implementation register surfacing; "map" is the canonical motif term | low; route still uses `graph` mode internally |
| `graph-view.js:721` | `Log Reps` / `Next Rep` | `Log Reps` / `Next Rep` `[no change — domain noun]` | UBIQUITOUS_LANGUAGE.md (`Repair Reps`) | — |
| `graph-view.js:724` | `Lock in and show reference bridge` | `[no change — already on motif]` | scholarly | — |
| `app.js:1826`, `app.js:3826, 3838` | `Sign in` / `Log out` | `[no change]` | utility | — |
| `welcome.js:11` | `enter the first room` | `open the first entry` | room → entry; "open" replaces "enter" to match motif (you open a journal entry, not a dungeon door) | welcome surface — apply with care; very visible |
| `welcome.js:100` | `skip` | `skip` `[no change]` | utility | — |
| `concept-create.js:288, 296, 307, 319, 628` (Cancel/edit) | `[no change]` | — | utility | — |
| `index.html:153` | `Save & Sync` | `Save & Sync` `[no change]` | utility | — |
| `index.html:154` | `Log Out` | `Log Out` `[no change]` | utility | — |
| `index.html:156` | `[skip 24h]` | `[skip 24h]` `[no change — dev-only debug button; check whether it should be hidden in prod]` | flagged in open questions | — |
| `app.js:130` | `return to app` (login.js:130) | `return to app` `[no change]` | utility | — |
| `login.html:50` | `continue as guest` | `continue as guest` `[no change]` | utility | — |
| `login.html:47`, `index.html:113` | `Continue with Google` | `Continue with Google` `[no change]` | OAuth standard | — |

### D. State-display chips (≤ 12 chars target; current vs proposal)

The state-machine display strings. Code tokens (`locked`, `primed`, `drilled`, `solidified`) stay; only the rendered label changes.

| Surface | Current chip | Proposed chip | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `app.js:274` | `source captured` | `source captured` `[no change — already on motif]` | scholarly | 15 chars — over 12-char target; flag for chip-component check |
| `app.js:275` | `draft path` | `draft path` `[no change]` | DESIGN.md allowed | — |
| `app.js:276`, `graph-view.js:62, 84, 1801` | `worth revisiting` | `worth revisiting` `[no change — load-bearing brand line per DESIGN.md §10]` | tone-by-surface canon | 16 chars — over 12 target; verify chip; this is a load-bearing voice line, do not shorten |
| `app.js:277` | `spacing` | `spacing` `[no change]` | scholarly | — |
| `app.js:278` | `spaced evidence` | `spaced evidence` `[no change — already on motif]` | DESIGN.md vocabulary | 15 chars — flag chip width |
| `app.js:279, 338`, `index.html:208` | `no map yet` | `no map yet` `[no change — voice rule satisfied]` | quiet | — |
| `app.js:1914` | `lightweight draft` | `lightweight draft` `[no change]` | scholarly | 17 chars — flag chip width |
| `app.js:1926`, `graph-view.js:60, 843, 1799` | `solidified through spaced reconstruction` | `solidified` *(chip)* / keep full phrase in detail panel and screen-reader announcements | full phrase >12 chars by far; truncate to motif anchor for chip; full phrase remains in long-form contexts | requires per-callsite split between chip surface and detail-panel surface — verify each location |
| `app.js:1927` | `worth revisiting` | as row above | — | — |
| `app.js:1928`, `graph-view.js:61, 82, 784, 1803` | `primed for study` | `primed for study` `[no change — load-bearing brand line per DESIGN.md §10]` | DESIGN.md allowed; voice canon | 16 chars — flag chip width |
| `app.js:1929`, `graph-view.js:104, 1805` | `ready for first attempt` | `ready for first attempt` `[no change — DESIGN.md allowed graph-claim vocabulary]` | canon | 23 chars — almost certainly does not fit a 12-char chip; this string belongs to legend / tooltip surfaces, not chips. Verify per callsite. |
| `app.js:1985`, `graph-view.js:989` | `draft route` | `draft route` `[no change]` | DESIGN.md allowed | — |
| `app.js:1986` | `ready for first attempt` | as row above | — | — |
| `app.js:1987`, `app.js:2012`, `graph-view.js:1806` | `locked` | `locked` `[no change — token = display label]` | brevity matches token | — |
| `app.js:2012` | `primed for study` | as row above | — | — |
| `app.js:2340` | `in library` / `draft path` | `in library` / `draft path` `[no change]` | utility | — |
| `app.js:1122` | `Analyzing` | `Drafting` (or `Drafting…`) | "Analyzing" reads as diagnostic register — DESIGN.md forbidden adjacent | small — nearby `app.js:1137` already uses `Drafting` |
| `app.js:1315` | `Draft ready` | `Draft ready` `[no change — already on motif]` | reading-room | — |
| `graph-view.js:67` | `Needs one more clean pass` | `Needs one more clean pass` `[no change — already on motif]` | scholarly self-strategy | — |
| `graph-view.js:68` | `Needs a fuller mechanism` | `Needs a fuller mechanism` `[no change — already on motif]` | scholarly | — |
| `graph-view.js:69` | `Needs correction` | `Needs a different causal link` | (locked above in pre-discovered findings) | — |
| `graph-view.js:531–534` | `Bridge` / `Next Step` / `Cause -> Effect` / `Repair` | `[no change — domain nouns; on motif]` | rep-scaffold language | "Cause -> Effect" is an arrow glyph — confirm rendering on dark mode |
| `graph-view.js:538–541, 565–567, 571–573` | `Same bridge` / `Partly linked` / `Different link` / `Not rated`; `Guessing` / `Have a hunch` / `Can trace it` | `[no change — already on motif]` | scholarly | — |
| `graph-view.js:912` | `attempts recorded` | `attempts recorded` `[no change]` | scholarly, on motif | — |
| `graph-view.js:989–991` | `core thesis first` / `bright means ready` / `ghosted means locked` | `[no change — already on motif]` | quiet, instructive | — |
| `index.html:104` | `unsaved` | `unsaved` `[no change — utility]` | — | — |

### E. Empty states, errors, validation (sentence-form copy)

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:215`, `app.js:284, 301` | `Pick a tile to enter a room, or start a new draft path at Ignition.` | `Pick a tile to open an entry, or start a new draft path at New Entry.` (cascades on disputed slot 1) | room → entry; "enter" → "open"; nav-label propagation | propagates with disputed-slot pick |
| `index.html:216` | `The map stays honest because evidence comes from your reconstruction.` | `[no change — motif voice line]` | foundational creed; do not paraphrase | — |
| `index.html:289`, `app.js:1499` | `The board holds nine concepts. Retire one to start another.` | `[no change — already on motif]` | scholarly imperative | — |
| `index.html:312` | `Parts, guesses, examples, confusions. No polished answer needed.` | `[no change — motif voice line]` | scholarly invitation | — |
| `index.html:380`, `app.js:692, 1823` | `Write what you can reconstruct from memory.` / `Paste source material here.` / `Explain this core idea in your own words.` | `[no change]` | on motif | — |
| `index.html:418` | `Experiencing an issue? Have an idea? Your feedback goes directly to my local TODO list.` | `Have feedback? It goes straight to the build's local TODO list.` | "my local TODO" reveals that feedback is one developer's; could read as unscaled or jokey. Tighter reading-room register. | optional — flag as a polish row, low priority |
| `index.html:420` | `Tell me what's on your mind...` | `Tell me what's on your mind` (drop the ellipsis, drop the period — placeholder convention in the rest of the file) | placeholder convention | low |
| `app.js:284, 301`, see row above | duplicate of above | — | — | — |
| `app.js:288–293` | various draft-path guidance lines | `[no change — already on motif]` | scholarly | — |
| `app.js:295` | `A spaced re-drill found a gap worth repairing. Revisit the mechanism, then return under spacing.` | `[no change — voice rule already satisfied]` | tone-by-surface canon | — |
| `app.js:297` | `This room is spacing. Work elsewhere or return when re-drill is eligible.` | `This entry is spacing. Work elsewhere or return when re-drill is eligible.` | room → entry | — |
| `app.js:299` | `…Re-drill later if you want to challenge it.` | (locked in pre-discovered findings) | — | — |
| `app.js:379, 452, 456` | `Add one concept and one guess, example, or confusion before socratink builds the draft path.` / `Add a few words about how you think it works before socratink builds the draft path.` | `[no change — already on motif]` | scholarly | — |
| `app.js:889` | `Study content stays locked until the cold attempt.` | `[no change — motif creed line]` | foundational | — |
| `app.js:980, 981` | `Guest mode uses sample maps.` / `Sign in to extract your own content into a draft map.` | `[no change]` | utility, on motif | — |
| `app.js:1000–1015` (extraction errors) | various `Try again when ready.` | `[no change — voice rule already satisfied]` | scholarly | — |
| `app.js:1064–1070` (overlay tips) | various tooltip strings | `[no change — already on motif]` | scholarly | "structuring the rooms" → see `app.js:1066` row in §G below |
| `app.js:1066` | `socratink is structuring the rooms.` | `socratink is structuring the entries.` | room → entry | propagation; flag — this is overlay tooltip text |
| `app.js:1438` | `socratink couldn't draft from this seed. You can try again, or attach source material for a different draft path.` | `[no change]` | scholarly | — |
| `app.js:1521` | `Delete "${conceptName}"? This removes its draft path and recorded evidence from this browser.` | `[no change]` | utility / scholarly | — |
| `app.js:1709, 1712, 1718, 1736, 1740` | file-error messages | `[no change]` | utility | — |
| `app.js:1976` | `This is global context. The first room will ask one smaller question.` | `This is global context. The first entry will ask one smaller question.` | room → entry | screen-3 voice row |
| `app.js:1977` | `No threshold context was captured for this concept.` | `No starting sketch was captured for this concept.` | aligns to canonical name | — |
| `app.js:1983` | `The route below is a hypothesis from the source and your threshold. It has not changed graph truth.` | `…from the source and your starting sketch.` | aligns to canonical name | — |
| `app.js:1990` | `Drafted from a thin sketch. The route is intentionally sparse — your first cold attempt will fill in what the sketch left out.` | `[no change — already on motif]` | scholarly | — |
| `app.js:2000` | `The first room asks for the governing idea, not the whole source.` | `The first entry asks for the governing idea, not the whole source.` | room → entry | — |
| `app.js:2030` | `Nearby room set ${idx + 1}` | `Nearby section ${idx + 1}` | cluster level → section per glossary | — |
| `app.js:2038` | `Purpose only for now. Study content stays locked until a cold attempt creates something to repair.` | `[no change — motif voice line]` | — | — |
| `app.js:2044` | `Room ${subIdx + 1}` / `Locked room ${subIdx + 1}` | `Entry ${i + 1}` / `Locked entry ${i + 1}` | room → entry | — |
| `app.js:2046, 2047` | `Study material available after the recorded attempt.` / `locked study silhouette. Enter the room before the mechanism appears.` | `Study material available after the recorded attempt.` / `locked study silhouette. Open the entry before the mechanism appears.` | room → entry; "Enter" → "Open" | — |
| `app.js:2066, 2067` | `Domain links: ${n} proposed source relationships.` / `Prerequisite links: ${n} proposed route constraints.` | `[no change]` | scholarly | — |
| `app.js:2075` | `Connections, frameworks, and solved mechanisms stay hidden until at least one room has a cold attempt on record.` | `…until at least one entry has a cold attempt on record.` | room → entry | — |
| `app.js:2228` | `Library full. Retire a concept to add another.` | `[no change]` | scholarly | — |
| `app.js:2236–2240, 2265` | Hermes Agent bundled-content sample copy | `[deferred — out of scope: bundled sample concept content, distinct from chrome]` | example/seed content, not chrome | — |
| `app.js:2281` | `Failed to load this library concept.` | `[no change]` | utility | — |
| `app.js:2296` | `No summary available yet.` | `[no change]` | utility | — |
| `app.js:2298–2301` | `Source: ${concept.contentFilename}` etc. | `[no change]` | utility | — |
| `app.js:2329` | `Curated draft paths you can enter without treating the map as learner evidence.` | `Curated draft paths you can open without treating the map as learner evidence.` | "enter" → "open" (door-metaphor → book-metaphor) | minor |
| `app.js:2356` | `Draft paths and evidence maps you can reopen.` | `[no change — already on motif]` | reading-room | — |
| `app.js:2360` | `No draft paths yet. Begin one at <a …>Ignition</a>.` | `No draft paths yet. Begin one at <a …>New Entry</a>.` (cascades) | propagates disputed-slot pick | — |
| `app.js:2722` | `Study this node first` | `Study this entry first` | node → entry | — |
| `app.js:2723` | `Finish the study step before you try a spaced re-drill.` | `[no change — voice rule satisfied]` | — | — |
| `app.js:2729` | `Work on another node first` | `Work on another entry first` | node → entry | — |
| `app.js:2730` | `This re-drill needs a short buffer before it counts. Work another node, then come back.` | `…Work another entry, then come back.` | node → entry | — |
| `app.js:2735` | `Interleave one more node first` | `Interleave one more entry first` | node → entry | — |
| `app.js:2736` | `Finish one other cold attempt or study step before returning here. That buffer helps the graph tell the truth.` | `[no change — already on motif]` | scholarly | — |
| `app.js:2807` | `Let this one incubate` | `[no change — already on motif]` | reading-room ("let it cool" register) | — |
| `app.js:2809, 2810` | `This idea is primed. Shift to ${nextTarget.label} while this one settles, then come back for spaced re-drill.` | `[no change — already on motif]` | — | — |
| `app.js:2927, 2928` | `Repair Reps are not ready` / `Finish targeted study first…` | `[no change — already on motif]` | — | — |
| `app.js:3018, 2974` | repair-rep error states | `[no change]` | utility | — |
| `app.js:3467–3470` (set of four post-attempt strings) | `You made the first mark. Now the room can show the gap.` etc. | replace `room` with `entry`: `You made the first mark. Now the entry can show the gap.` etc. across all four | room → entry | — |
| `app.js:3506` | `Explain this core idea in your own words.` | `[no change — motif voice line]` | — | — |
| `app.js:3513–3514` | `Solid evidence already recorded` / `This room already has a solid spaced reconstruction on record. Pick a node without that record to keep the graph truthful.` | `…This entry already has a solid spaced reconstruction…Pick an entry without that record…` | room/node → entry | — |
| `app.js:3537–3538, 3550–3551` | session-cap / retrieval-ceiling messages | `[no change — already on motif]` | scholarly | — |
| `app.js:3581` | `Active room: ${label}` | `Active entry: ${label}` | room → entry | accessible-status announcer |
| `app.js:3598, 3725` | `The drill service failed to respond. Check the backend or API key and try again.` | `The drill service failed to respond. Try again when ready.` | "API key" leaks dev language; mention is gratuitous to learners | small; verify nothing relies on the exact wording |
| `app.js:3690` | `what you just did` (kicker) | `[no change — already on motif]` | — | — |
| `app.js:3694` | `You tried first. The room stayed quiet until your guess existed.` | `You tried first. The entry stayed quiet until your guess existed.` | room → entry | — |
| `app.js:3698` | `Study has a target now. Repair the gap this room exposed.` | `…this entry exposed.` | room → entry | — |
| `app.js:3702` | `Return later. Only spaced re-drill can change the record.` | `[no change — motif creed line]` | — | — |
| `app.js:3744` | `Quiet preferences for how socratink looks and sounds. Saved to this browser.` | `[no change — already on motif]` | — | — |
| `app.js:3762, 3773, 3782` | settings sub-labels | `[no change]` | — | — |
| `concept-create.js:38` | `Try this: give one example. Anywhere this concept shows up in something you've read or experienced — a small detail will do.` | `[no change — already on motif]` | invitation register | — |
| `concept-create.js:43` | `A few words about how you think it works will give socratink something to draft from. Or attach source material — either path opens the build.` | `[no change — already on motif]` | — | — |
| `concept-create.js:314` | `None added — socratink will draft from your sketch alone. The graph stays hypothesis until your reconstruction.` | `[no change — already on motif]` | — | — |
| `concept-create.js:621–622, 718, 728, 733, 754, 758` | file-attachment scaffolding | `[no change]` | utility | — |
| `graph-view.js:21` | `Untitled` | `[no change]` | utility | — |
| `graph-view.js:45` | `This node anchors the extracted concept map.` | `This entry anchors the extracted concept map.` | node → entry | — |
| `graph-view.js:110` | `Start here and rebuild the mechanism from memory.` | `[no change — motif voice line]` | — | — |
| `graph-view.js:113` | `Targeted study is open for this node. Re-enter the mechanism view, then return to the map when you are ready to let it incubate.` | `…open for this entry. Re-enter…` | node → entry | — |
| `graph-view.js:118` | `Study is on record. Let this idea incubate while you work another reachable branch, then return for spaced re-drill.` | `[no change]` | — | — |
| `graph-view.js:119` | `This room is primed. Work another reachable node before coming back for spaced re-drill.` | `This entry is primed. Work another reachable entry before coming back for spaced re-drill.` | room/node → entry | — |
| `graph-view.js:124` | `This idea is still settling. Shift outward to another branch, then come back for a cleaner reconstruction.` | `[no change]` | — | — |
| `graph-view.js:125` | `This room still needs another pass. Interleave a different node, then come back for the next re-drill.` | `This entry still needs another pass. Interleave a different entry, then come back for the next re-drill.` | room/node → entry | — |
| `graph-view.js:129, 974` | `What governing idea explains how this whole system behaves? Start here, then take your best guess.` | `[no change — motif voice line]` | — | — |
| `graph-view.js:134` | `What principle governs this branch, and why does the rest of this territory depend on it?` | `[no change]` | — | — |
| `graph-view.js:135` | `Engage the core thesis first to reveal this backbone branch.` | `[no change]` | — | — |
| `graph-view.js:140` | `This branch is open. The drill happens inside its rooms, not in the container itself.` | `This branch is open. The drill happens inside its entries, not in the section itself.` | room → entry; container → section | — |
| `graph-view.js:141` | `Work the prerequisite rooms to reveal this branch.` | `Work the prerequisite entries to reveal this branch.` | room → entry | — |
| `graph-view.js:146` | `This room is available. Enter with your current model. Study stays hidden until you attempt.` | `This entry is available. Open with your current model. Study stays hidden until you attempt.` | room → entry; "Enter" → "Open" | — |
| `graph-view.js:147` | `Work the branch before drilling this room.` | `Work the branch before drilling this entry.` | room → entry | — |
| `graph-view.js:150` | `Choose a reachable room and make the next attempt.` | `Choose a reachable entry and make the next attempt.` | room → entry | — |
| `graph-view.js:156–158, 1790–1792, 340, 441` | `Locked branch` / `Locked room set` / `Locked room` | `Locked branch` / `Locked section` / `Locked entry` | room → entry; room set → section | — |
| `graph-view.js:174, 195` | `Reference Statement` (heading + kicker) | `[no change — already on motif]` | scholarly | — |
| `graph-view.js:187, 852` | `Mechanism not specified.` | `[no change]` | utility | — |
| `graph-view.js:309, 798, 872, 972, app.js:1944, 3505` | `Core Thesis` (kickers/headings) | `[no change]` | scholarly canonical | — |
| `graph-view.js:341` | `Backbone Principle ${index + 1}` | `[no change]` | — | — |
| `graph-view.js:364–365, 409–410, 423–424, 465–466` | `Backbone branch` / `Drill branch` / `This cluster…` | `Backbone branch` / `Section branch` / `This section…` | cluster → section in copy | propagation row |
| `graph-view.js:442` | `Drill Node ${subIndex + 1}` | `Entry ${i + 1}` | drill node → entry | — |
| `graph-view.js:482, 498` | `Prerequisite` / `Domain mechanic` | `[no change]` | scholarly | — |
| `graph-view.js:520, 620` | `this node` (literal substring used inside larger sentences) | `this entry` | node → entry | — |
| `graph-view.js:525` | `Practice only` | `[no change]` | scholarly | — |
| `graph-view.js:554, 587, 625, 627, 638, 663, 665, 682, 702, 705, 710, 751, 759, 780, 788, 802, 803, 826, 828, 830, 831, 850, 866, 902, 906, 918, 952, 965, 976, 2724` (kicker uses) | various — see specific rows above | mostly `[no change]`; the room/cluster→entry/section substitutions covered above | — | — |
| `graph-view.js:608, 609, 610` | `Rep ${i + 1}` / `Predicted:` / `Rated:` | `[no change — domain noun + utility]` | — | — |
| `graph-view.js:630` | `Building three causal reps for this node. This is practice, not graph-truth evidence.` | `Building three causal reps for this entry. This is practice, not graph-truth evidence.` | node → entry | — |
| `graph-view.js:668, 670` | `Three bridge reps saved on ${nodeLabel}.` / `These reps are saved. Graph truth comes from the next spaced re-drill.` | `[no change]` | scholarly | — |
| `graph-view.js:684` | `Repair Reps are not ready for this node yet.` | `Repair Reps are not ready for this entry yet.` | node → entry | — |
| `graph-view.js:707, 712, 718, 722, 725` | rep-scaffold sentences | `[no change — already on motif]` | — | — |
| `graph-view.js:774–776` | `Next evidence move: spaced re-drill ${label}.` / `Next spacing move: enter ${label}.` / `Leave this node to incubate. Work on other nodes before returning to spaced re-drill.` | `…Leave this entry to incubate. Work on other entries before returning to spaced re-drill.` | node → entry | — |
| `graph-view.js:840` | `Solidified through spaced reconstruction. This is evidence, not a permanent claim.` / `Attempt logged. This room is worth revisiting.` | `…This entry is worth revisiting.` | room → entry | — |
| `graph-view.js:942, 945, 948–949, 952` | edge-detail copy: `Draft connection` / `held until attempt` / `This connection is part of the proposed route. Its mechanism stays out of view until the adjacent rooms have learner evidence.` | `…until the adjacent entries have learner evidence.` | room → entry | — |
| `graph-view.js:967` | `Use the chat to reconstruct the active node from memory…` | `Use the chat to reconstruct the active entry from memory…` | node → entry | — |
| `graph-view.js:985, 986` | `This is the first room. It asks one smaller question…` | `This is the first entry. It asks one smaller question…` | room → entry | — |
| `graph-view.js:1333` | `No extracted graph data is available yet.` | `[no change]` | utility | — |
| `graph-view.js:1851` | `Graph renderer failed to mount. Draft view is still available.` | `[no change]` | utility | — |

### F. ARIA labels, alt text, title attributes, sr-only (≤ 42 chars target)

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:75` | `Sidebar` | `Sidebar` `[no change]` | utility | — |
| `index.html:101` | `Account actions` | `Account actions` `[no change]` | utility | — |
| `index.html:120` | `Close sidebar` | `Close sidebar` `[no change]` | utility | — |
| `index.html:130` | `socratink` (sr-only h1) | `socratink` `[no change]` | brand | — |
| `index.html:135, 136` | `Toggle sidebar` (aria + title) | `Toggle sidebar` `[no change]` | utility | — |
| `index.html:157` | `Close concept map` | `Close concept map` `[no change]` | utility | — |
| `index.html:169` | `Switch to dark mode` (aria + title) | `Switch to dark mode` `[no change]` | utility | — |
| `index.html:303` | `What do you want to understand?` (aria) | `[no change]` | scholarly | — |
| `index.html:350` | `Map display mode` | `Map display mode` `[no change]` | utility | — |
| `app.js:159, 163` | `Switch to light mode` / `Switch to dark mode` | `[no change]` | utility | — |
| `app.js:577` | `Begin a concept` / `Open ${concept.name}` | `[no change]` | utility | — |
| `app.js:631` | `Delete concept ${name}` | `[no change]` | utility | — |
| `app.js:879` | `Close` (concept-create modal) | `Close` `[no change]` | utility | — |
| `app.js:1984` | `Provisional graph legend` | `Provisional graph legend` `[no change]` | utility | — |
| `app.js:3764, 3776, 3785` | `Theme` / `Reduced motion` / `Threshold sounds` | `Theme` / `Reduced motion` / `Threshold sounds` `[no change]`; **but** if `Concept Threshold` screen renames to `Starting Sketch`, retire `Threshold sounds` to `Sketch sounds` | utility; one cascade | flag |
| `concept-create.js:518` | `Concept name` | `Concept name` `[no change]` | utility | — |
| `concept-create.js:564` | `Your sketch` | `Your sketch` `[no change — on motif]` | — | — |
| `graph-view.js:512` | `Repair Reps steps` | `[no change — domain noun]` | — | — |
| `graph-view.js:588` | `Stance before revealing reference` | `[no change]` | utility | — |
| `graph-view.js:2322, 2328` | `${edge.label \|\| edge.type \|\| 'Connection'}` | `[no change]` | code-derived label, defaulting on motif | — |
| `graph-view.js:2419, 2420` | aria-label / title built by `buildNodeAriaLabel()` | `[no change — derived from node-state copy already in this ledger]` | propagates with state-chip rows | — |
| `tooltips.js:46` | `Close` | `[no change]` | utility | — |
| `login.html:35` | `Login` (sr-only) | `Login` `[no change]` | utility | — |
| `login.html:53` | `Support the build on Buy Me a Coffee` | `[no change]` | utility | — |
| `login.html:61` | `Join the socratink Discord` | `[no change]` | utility | — |

### G. Tooltips and overlay tips

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `app.js:1064` | `socratink is drafting your starting map.` | `socratink is drafting your starting sketch.` | "Starting Sketch" canonical | propagates from §B "Starting map" → "Starting sketch" decision |
| `app.js:1065` | `Spacing retrieval over time helps short-term recall become more durable.` | `[no change — already on motif]` | — | — |
| `app.js:1066` | `socratink is structuring the rooms.` | `socratink is structuring the entries.` | room → entry | — |
| `app.js:1067, 1069, 1070` | overlay tips | `[no change — motif voice]` | — | — |
| `app.js:1133` | `socratink is drafting your starting map.` (duplicate string in different code path) | `socratink is drafting your starting sketch.` | same | — |
| `floating-room-label.js:47, 113, 114` | `Open room` (button + tooltip) / `Begin a concept` | `Open entry` / `Begin a concept` | room → entry | a11y-visible — verify floating label callers |

### H. Misc placeholders, kickers, and small strings

| Surface | Current | Proposed | Rationale | Risk |
| --- | --- | --- | --- | --- |
| `index.html:284` | `Start here` (kicker) | `[no change]` | utility | — |
| `app.js:284` (kicker), `concept-create.js:110, 287` | `CONCEPT` (kicker) | `[no change]` | utility | — |
| `app.js:878` | `NEW CONCEPT` (kicker) | `[no change]` | utility | — |
| `app.js:3690` | `what you just did` (kicker) | `[no change]` | already on motif | — |
| `concept-create.js:295` | `YOUR SKETCH` (kicker) | `[no change]` | already on motif | — |
| `concept-create.js:306` | `SOURCE MATERIAL` (kicker) | `[no change]` | utility | — |
| `concept-create.js:613` | `Paste source material here.` (placeholder) | `[no change]` | utility | — |
| `concept-create.js:616` | `https://example.com/article` (placeholder) | `[no change]` | utility | — |
| `app.js:485, 488` | `Photosynthesis` / `Entropy` / `Transformers` / `Attention` (rotating placeholder examples) | `[no change]` | scholarly canonical | — |
| `welcome.js:8` | `welcome` (kicker) | `[no change]` | — | — |
| `welcome.js:9, 10` | `socratink is a reading room, not a dashboard.` / `Bring what you have. The first room stays quiet until you begin.` | `…The first entry stays quiet until you begin.` (line 10) | room → entry; the line 9 motif anchor stays verbatim | — |

---

## Already-on-motif appendix (rows the inventory found that need no work)

Listed for the user to spot-check; each appears in the body ledger with `[no change]`. ~25 lines representing the load-bearing voice canon:

- `socratink is a reading room, not a dashboard.` (welcome.js:9) — the motif anchor.
- `Bring what you have. The first room stays quiet until you begin.` (welcome.js:10) — *room → entry above.*
- `The map stays honest because evidence comes from your reconstruction.` (index.html:216).
- `Reading is exposure. Reconstruction is evidence.` (app.js:1070).
- `Study content stays locked until the cold attempt.` (app.js:889).
- `This is global context. The first room will ask one smaller question.` (app.js:1976) — *room → entry above.*
- `What governing idea explains how this whole system behaves? Start here, then take your best guess.` (app.js:1995 / graph-view.js:129, 974).
- `Worth revisiting.` (state) — load-bearing per DESIGN.md tone-by-surface.
- `Solidified. Spaced reconstruction recorded.` (state).
- `Evidence recorded. Let spacing do its work while you're away.` (session cap).
- `Quiet preferences for how socratink looks and sounds. Saved to this browser.` (settings).
- `Your reading room` (settings heading).
- `Cream paper or obsidian sky` (theme subtitle).
- `Calm transitions, no settle bloom` (motion subtitle).
- `Soft cues at focus and submit` (sound subtitle).
- `You tried first. The room stayed quiet until your guess existed.` (post-attempt) — *room → entry above.*
- `Return later. Only spaced re-drill can change the record.` (post-attempt).
- `None added — socratink will draft from your sketch alone. The graph stays hypothesis until your reconstruction.` (concept-create empty).
- `Practice only. Graph truth comes from spaced re-drill.` (rep practice).
- `Three bridge reps saved on ${nodeLabel}. These reps are saved. Graph truth comes from the next spaced re-drill.` (rep success).
- `Use the chat to reconstruct the active node from memory. The graph updates only when the outcome provides evidence.` (graph-view) — *node → entry above.*

---

## Deferred / rejected appendix

| Item | Reason |
| --- | --- |
| `Repair Reps`, `Cold Attempt`, `Spaced Re-Drill`, `Provisional Graph` (display-= domain) | `[no change — domain nouns from UBIQUITOUS_LANGUAGE.md]`. Underlying domain rename would be a separate, larger refactor. |
| `Cluster` / `Section` rename of code identifiers (`subnodeCount`, `clusterCount`, `cluster_id`, etc.) | `[deferred — out of scope: code identifier rename, not naming pass]`. Display-only swap covered above. |
| `room` / `entry` rename of code identifiers (e.g., `floating-room-label.js` filename, `room-vocab` discriminators) | `[deferred — out of scope: code identifier]`. Display-only swap covered above. |
| `data-state="growing" \| "instantiated" \| "actualized" \| "hibernating"` legacy crystal-shell display tokens (`colors_and_type.css:174–211`) | `[deferred — feature/legacy: these are CSS/data tokens, not learner-visible chips]`. Confirmed not user-facing at build time. |
| `data.reDrillBand` band literals (`spark/link/chain/clear/tetris`) | Removed from learner-visible copy entirely (locked in pre-discovered findings). The internal use as telemetry stays. |
| Hermes Agent sample-content seed strings (`app.js:2236–2265`) | `[deferred — out of scope: bundled sample concept content, not chrome]`. Would be re-authored during a content pass, not a chrome rename. |
| `[skip 24h]` button (`index.html:156`) | `[uncategorized — propose category]`. Looks like a dev convenience left visible — flag in open questions whether it ships or hides in prod. |
| `Cause -> Effect` chip (`graph-view.js:533`) | `[no change — motif keeps the term]`, but the arrow glyph rendering needs verification on dark mode. |

---

## Open questions before applying Phase 2

1. **Pick the `Ignition` display-label alternative** (`New Entry` / `Sketch` / `Inkwell`). Recommendation: `New Entry`.
2. **Pick the `Start Cold Attempt` action alternative** (`Try Cold` / `Sketch From Memory` / `tink it`). Recommendation: `Try Cold`.
3. **`Concept Threshold` screen title rename to `Starting Sketch`.** This was proposed as a coherence move with the `Starting map` → `Starting sketch` field rename. Two screen titles share the same artifact (`Concept Threshold` and the form heading) — should they fully agree, or do you want the screen title to stay `Concept Threshold` and only the field heading change? Default in this ledger: rename the screen title too.
4. **Chip-width policy for "load-bearing" voice strings.** The chips `worth revisiting` (16), `primed for study` (16), `spaced evidence` (15), `source captured` (15), `lightweight draft` (17), and `solidified through spaced reconstruction` (40) all exceed the 12-char ceiling. Two options: (a) shorten the chips and keep the long phrasings in detail-panel / aria contexts; (b) raise the chip ceiling for these specific strings. Default in this ledger: keep the strings (they are voice-canonical) and verify per chip component that they actually wrap or fit. Confirm.
5. **`Map` / `Graph` mode-toggle labels (`index.html:351, 352`).** Should these stay as-is (they're domain shortcuts) or move to the motif (e.g., `Route` / `Map`)? Default: no change.
6. **`[skip 24h]` debug button (`index.html:156`).** Flagged as ambiguous — does this ship in production, or is it dev-only? If dev-only, hide rather than rename.
7. **`Threshold sounds` (`app.js:3782, 3785`).** If the screen title `Concept Threshold` renames to `Starting Sketch`, the settings sub-label becomes inconsistent. Rename to `Sketch sounds` or keep `Threshold sounds` because the audio cue actually fires at the threshold composer's ignition moment? Default: rename to `Sketch sounds`.
8. **Dark-mode-graph copy alignment (per user lock 7).** Visual idioms stay, labels adopt the motif. Is there a separate file (e.g., `docs/design/dark-mode-graph-patch.md`) whose copy callouts should be cross-checked against this ledger? Confirm scope.
