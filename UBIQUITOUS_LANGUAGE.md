# Ubiquitous Language

## Learning Loop

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Evidence-weighted map** | The graph projection of proposed domain structure plus learner-generated evidence Socratink has recorded. | Knowledge map as diagnosis, mastery map |
| **Draft map** | A newly extracted map with no learner evidence attached. | Diagnosis, understanding map |
| **Provisional map** | A map shaped by starting-map input but still carrying no graph-truth mutation. | Evaluated map, personalized mastery map |
| **Cold attempt** | An unscored first generation attempt on a local node before explanatory content appears. | Quiz, test, assessment |
| **Targeted study** | Attempt-scoped corrective study unlocked by a substantive cold attempt. | Proof, mastery, completion |
| **Repair Reps** | Optional typed micro-practice for causal bridges that never mutates graph truth. | Drill shortcut, mastery practice |
| **Spaced re-drill** | A later reconstruction attempt after spacing/interleaving that can record `solidified` if solid. | Review, immediate retry, final test |

## Graph Truth

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Graph truth** | The derived projection of training evidence Socratink has seen. The provisional graph stays a hypothesis; learner evidence lives in the training store. | What the learner knows |
| **Training record** | Browser-local evidence record keyed as `socratink:training:v1:<conceptId>`; contains learner sketch, attempts, study reveal timestamps, and repair text. | Graph summary, mastery record |
| **`null` training state** | No learner reconstruction attempt is on record for the node. Usually rendered silently or as "ready to reconstruct", not as a badge. | Locked knowledge, failed |
| **`primed`** | Learner reconstruction evidence is on record; study, repair, review, or spaced-attempt routing is derived from the latest attempt. Legacy `primed`/`study` graph nodes with no attempt record may reveal study with `attempts: []` as compatibility only; that is not reconstruction evidence. | Learned, partially mastered |
| **`needs repair`** | Current evidence contains named gaps that need repair before the next reconstruction can honestly advance. | Failed, bad, weak learner |
| **`solidified`** | At least one solid spaced reconstruction is on record. | Mastered forever, actualized, cleared as knowledge |
| **Traversal unlock** | Permission to move through the map based on engagement evidence. | Mastery unlock |
| **Mastery-gated progression** | Progression that requires `solidified` evidence. | Basic branch opening |

## Product Claims

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Recorded evidence** | A machine-checkable event from learner action, such as an attempt or reconstruction result. | Proof of knowledge |
| **Current model** | The learner's expressed starting point or attempted explanation. | Understanding, ability level |
| **Routing hint** | Internal signal used to shape the path or prompt emphasis. | Diagnostic label |
| **Reconstruction evidence** | Evidence from the learner rebuilding a mechanism in their own words. | Real learning, proved it |
| **Gap** | A missing or incorrect causal bridge in an attempt. | Misconception detected, weakness |

## Content Intake

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Grounding context** | Optional curriculum-aligned descriptions (today, from Learning Commons academic standards) passed into the **Source-less generation** prompt as background. Never authoritative; never visible to the learner; never substitutes for an **Imported source** the learner declined to provide. | "Source", "research", "AI knowledge", "curated content" |
| **Ignition** | The first-class IA route that hosts the **Door** (C-prime: concept-name-only form) and the **Threshold composer** (deprecated). Peer of Desk / Library / Settings in the sidebar and bottom nav, and the first-run landing surface for a learner with no concepts. Board-cap gated: when the learner is at the 9-concept board cap the composer is hidden and a retire-one CTA takes its place ("The board holds nine concepts. Retire one to start another."). | "New tink", "create concept", "onboarding screen", "intake page" |
| **Imported source** | A normalized text source ready for Gemini extraction. Either fetched from a URL or supplied as raw text by the learner. Carries the canonical (post-redirect) URL when present and a flag indicating remote-attacker-controllability. | "Article", "fetched page", "scraped content" |
| **Launch attempt** | The learner's threshold submission on the **Launch pad**. Captures the rough whole-concept model (global **Current model**). Mutates no node state. Seeds the **Smallest actionable route** generation. (C-prime, 2026-05-07.) | "Threshold input", "draft map input" |
| **Launch pad** | The post-door surface (C-prime, 2026-05-07) where the learner enters the **Launch attempt** for a source-less concept. Only reached when no **Imported source** was attached at the door. Replaces the previous in-form "Starting sketch" textarea. | "Threshold surface", "second screen" |
| **Pending shell** | An in-flight concept name committed at the door but not yet built. Lives only in `sessionStorage`. Evaporates on tab close or after successful **Launch attempt** → route build. (C-prime, 2026-05-07.) | "In-flight concept", "unsaved entry" |
| **Smallest actionable route** | A **ProvisionalMap** with ≤4 drillable nodes (1 suggested first target carrying the core thesis + ≤3 backbone hints). The output of **Source-less generation** in C-prime. (C-prime, 2026-05-07.) | "Minimal map", "skeleton route" |
| **Source-less generation** | Generation of a **Provisional map** from `{concept name, launch attempt}` alone, without an **Imported source**. The resulting graph is hypothesis (per the **Provisional map** definition) — the absence of source raises, not lowers, the hypothesis weighting. In C-prime, returns a **Smallest actionable route** (≤4 drillable nodes). | "AI-generated graph", "auto-graph", "source-free extraction" |
| **Starting sketch** | The concept-page display label for the preserved learner **Launch attempt** ("Your starting sketch:"). The original "starting sketch" form field on the door is deprecated (2026-05-07) and replaced by **Launch attempt** captured on the **Launch pad** post-door. See `docs/product/spec.md` for the current contract. | "Threshold input", "rough model" |
| **Threshold composer** | *Deprecated (2026-05-07).* Under C-prime, split into: (a) the **Door** (captures concept name only, optionally **Imported source**), and (b) the **Launch pad** (captures **Launch attempt** for source-less concepts). The original two-field form on **Ignition** no longer exists. See `docs/product/spec.md` for the current contract. | "AI tutor", "onboarding chat", "threshold chat", "knowledge interview", "intake conversation" |
| **Confusion artifact** | A concrete piece of material the user already has in hand that represents their own confusion or incompleteness — a textbook paragraph re-read three times, a practice question missed, a lecture note that didn't land, a code snippet they couldn't write. socratink extracts the principle the confusion is pointing at; the user cold-attempts that principle. *Internal-team term*: user-facing copy should use the concrete form ("paste something that confused you", "a question you missed"), not the abstract noun. Resolved 2026-05-10. | "Content to consume", "study material", "the material" |
| **Library** | The surface where a user sees their **own** reconstructed work — concepts they have authored (or imported) and put their own evidence into through the reconstruction loop. The visible record of what this user can reconstruct from memory under spacing. Not a content catalog, sample shelf, or browseable archive of pre-made material. The trust signal of Library is preserved by deletion, not relocation, of curated content. See [ADR-0004](docs/adr/0004-library-is-users-work-only.md). | "Saved articles", "content shelf", "concept catalog", "browseable archive" |
| **Draft path** | *Deprecated (2026-05-09).* A card-state label that used to appear on `Reference Concepts` cards meaning "this pre-prepared seed hasn't been imported into your library yet." Removed along with the seeding mechanism in [ADR-0004](docs/adr/0004-library-is-users-work-only.md). The phrase has no referent in the current product and should not be reintroduced. | — |

## Relationships

- A **Draft map** can become a **Provisional map** without mutating **Graph truth**.
- A **Cold attempt** can create a **Training record** attempt; the derived state becomes **`primed`** or **`needs repair`** depending on the recorded classification and prior evidence.
- **Targeted study** and **Repair Reps** may help the learner, but neither directly produces **`solidified`** evidence.
- A spaced strong reconstruction is required before a node can derive **`solidified`**.
- A **Traversal unlock** can happen before **`solidified`** when the product is creating interleaving, but **Mastery-gated progression** requires **`solidified`**.
- An **Imported source** is the input to the **Draft map** extraction pipeline.
- An **Imported source** that is `is_remote_source=True` is treated as untrusted in extraction prompt assembly (per OWASP LLM01).
- Under C-prime: the **Door** on **Ignition** captures a concept name and optionally an **Imported source**. If no source is attached, a **Pending shell** is written to `sessionStorage` and the learner navigates to the **Launch pad**.
- The **Launch pad** reads the **Pending shell** and captures the **Launch attempt**, which is the learner's **Current model** (global rough understanding). Only after the learner submits does **Source-less generation** run.
- A **Provisional map** may be produced via **Source-less generation** from a **Launch attempt** alone, with no **Imported source** attached. In C-prime, this returns a **Smallest actionable route** (≤4 nodes). The map is framed as hypothesis and mutates no **Graph truth** until a **Cold attempt** produces substantive evidence.
- When an **Imported source** is present at the door, the existing extraction pipeline runs (full **Provisional map**). The door submit completes immediately; no **Launch pad** is shown.
- **Grounding context** may augment **Source-less generation** but never substitutes for an **Imported source** the learner declined to provide. The system never silently fetches arbitrary content (Wikipedia, scrape, vendor library) when the learner chose to build without source.
- A **Pending shell** is cleared when: (a) the **Launch attempt** succeeds and the resulting route is persisted locally, or (b) the learner closes the tab / explicitly cancels. The shell is terminal per-tab and per-session.

## Example Dialogue

> **Dev:** "Can this screen say the learner mastered the room?"
>
> **Domain expert:** "Only if the room is **`solidified`**, and even then say Socratink has a solid spaced reconstruction on record."
>
> **Dev:** "What about after study?"
>
> **Domain expert:** "That is **Targeted study**. It is a repair opportunity, not **Graph truth**."
>
> **Dev:** "So the graph can open the next room after **`primed`**?"
>
> **Domain expert:** "Yes, as a **Traversal unlock** for interleaving. Do not call it mastery."

## Flagged Ambiguities

- "Mastery" is overloaded between product shorthand and evidence claims. Prefer **`solidified`** or "solid spaced reconstruction on record" when referring to a node.
- "Cleared" can work as visual shorthand, but it must not imply knowledge. Prefer **`solidified`** in product copy unless a local UI spec explicitly frames "cleared" as display shorthand.
- "Actualized", "hibernating", `locked`, and `drilled` are legacy concept-shell or prior drill terms. The live training-state language is **`null`**, **`primed`**, **`needs repair`**, and **`solidified`**.
- "Diagnostic" implies Socratink knows the learner's mind. Prefer **Routing hint** or **Starting-map anchor**.

## Historical drift report 2026-05-12

This snapshot predates the 2026-05-15 training-record implementation and is kept
only as historical evidence. Do not treat these match counts as current code
truth; the live training-state vocabulary now appears in the JavaScript training
store and derivation modules.

- Evidence-weighted map — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Draft map — 2 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Provisional map — 1 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Cold attempt — 1 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Targeted study — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Spaced re-drill — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Graph truth — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- `locked` — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- `primed` — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- `drilled` — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- `solidified` — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Traversal unlock — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Mastery-gated progression — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Recorded evidence — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Current model — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Routing hint — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Reconstruction evidence — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Gap — 2 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Grounding context — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Imported source — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Launch attempt — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Launch pad — 1 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Pending shell — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Smallest actionable route — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Source-less generation — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Starting sketch — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
- Threshold composer — 0 verbatim `.py`/`.js` matches; documentation-only or sparse code usage.
