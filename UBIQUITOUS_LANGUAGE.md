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
| **Graph truth** | The persisted node-state record of evidence Socratink has seen. | What the learner knows |
| **`locked`** | No substantive attempt is on record for the node. | Not known, failed |
| **`primed`** | A substantive cold attempt is on record and study is unlocked. | Learned, partially mastered |
| **`drilled`** | A spaced reconstruction was attempted and was not solid. | Failed, bad, weak learner |
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
| **Imported source** | A normalized text source ready for Gemini extraction. Either fetched from a URL or supplied as raw text by the learner. Carries the canonical (post-redirect) URL when present and a flag indicating remote-attacker-controllability. | "Article", "fetched page", "scraped content" |
| **Threshold chat** | The conversational two-turn surface that captures the learner's concept name and **Starting sketch** at concept creation. Chat is ignition only — it exits into a single handoff card and never grows into a study surface, history thread, or open-ended dialogue. | "AI tutor", "onboarding chat", "knowledge interview", "intake conversation" |
| **Starting sketch** | The learner's verbatim reply to the **Threshold chat** — their rough current model of the concept, captured before any source extraction or graph generation. Remains the baseline against which the **Provisional map** is compared, against which **Targeted study** is scoped, and against which all repair is anchored. | "Notes", "guess", "intro text", "prompt input" |
| **Source-less generation** | Generation of a **Provisional map** from `{concept name, starting sketch}` alone, without an **Imported source**. The resulting graph is hypothesis (per the **Provisional map** definition) — the absence of source raises, not lowers, the hypothesis weighting. | "AI-generated graph", "auto-graph", "source-free extraction" |
| **Grounding context** | Optional curriculum-aligned descriptions (today, from Learning Commons academic standards) passed into the **Source-less generation** prompt as background. Never authoritative; never visible to the learner; never substitutes for an **Imported source** the learner declined to provide. | "Source", "research", "AI knowledge", "curated content" |

## Relationships

- A **Draft map** can become a **Provisional map** without mutating **Graph truth**.
- A **Cold attempt** can move a node from **`locked`** to **`primed`** only when substantive.
- **Targeted study** and **Repair Reps** may help the learner, but neither mutates **Graph truth**.
- A **Spaced re-drill** is the only event that can move **`primed`** or **`drilled`** to **`solidified`**.
- A **Traversal unlock** can happen before **`solidified`** when the product is creating interleaving, but **Mastery-gated progression** requires **`solidified`**.
- An **Imported source** is the input to the **Draft map** extraction pipeline.
- An **Imported source** that is `is_remote_source=True` is treated as untrusted in extraction prompt assembly (per OWASP LLM01).
- A **Threshold chat** captures a **Starting sketch**, which is the canonical concept-creation form of the learner's **Current model**.
- A **Provisional map** may be produced via **Source-less generation** from a **Starting sketch** alone, with no **Imported source** attached. The map is still framed as hypothesis and still mutates no **Graph truth**.
- When both an **Imported source** and a **Starting sketch** are present, extraction runs from the **Imported source** and the **Starting sketch** shapes the result into a **Provisional map**.
- **Grounding context** may augment **Source-less generation** but never substitutes for an **Imported source** the learner declined to provide. The system never silently fetches arbitrary content (Wikipedia, scrape, vendor library) when the learner chose to build without source.

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
- "Actualized" and "hibernating" are legacy concept-shell terms. The live learning-state language is **`locked`**, **`primed`**, **`drilled`**, and **`solidified`**.
- "Diagnostic" implies Socratink knows the learner's mind. Prefer **Routing hint** or **Starting-map anchor**.
