# Handoff — Extraction evals + rubric (make `ProvisionalMap` golden)

**Date drafted:** 2026-05-02
**Status:** Ready for pickup — brainstorm-first workstream
**Drafted by:** Claude Opus 4.7 (1M context), in conversation with jon-devlapaz
**Founder's stated goal (verbatim):** *"I want to make this extraction thing GOLDEN. like unbreakable like also think about rubricing and what not."*

**Skills the next agent must invoke (IN ORDER):**

1. `superpowers:brainstorming` — **first**, mandatory. This is a creative-work task with a wide design space (rubric dimensions, eval-harness shape, fixture lifecycle). Brainstorm with the founder before producing a spec. The HARD-GATE in that skill applies: do not write code or invoke implementation skills until a design is presented and approved.
2. `superpowers:writing-plans` — **after brainstorming approves a spec**, write the bite-sized implementation plan.
3. `superpowers:test-driven-development` — **during execution**, write failing tests first, then the eval-harness code.

**Optional / situational:**
- `improve-codebase-architecture` — useful if the eval-harness module surface starts feeling shallow or fused with extraction itself.
- `episodic-memory:remembering-conversations` — useful for retrieving the 2026-05-01 foundation-design conversation context (where this workstream was originally surfaced as Spec §5.6).
- `convergence-investigation-2.skill` — possibly applicable for the rubric design (cross-investigation parallels), only if the rubric grows beyond pass/fail into quality-tier classification.

**Do not skip the brainstorming step.** This is not a mechanical task. The shape of "golden, unbreakable" is a design decision the founder must shape, not the agent.

---

## What this handoff is

The first execution sweep of the LLM seam (PR #76, merged 2026-05-01) shipped `extract_knowledge_map` returning a typed `ProvisionalMap` with closure validators. That gives us **structural correctness**. It does NOT give us **quality assurance**.

This handoff is the work order to build the eval layer that turns "extraction passes parsing" into "extraction is empirically golden against a rubric the founder can defend."

The original foundation-design spec (`docs/superpowers/specs/2026-05-01-foundation-design.md` §5.6) explicitly deferred this work to a follow-up sweep. This is that sweep.

---

## Goals (verbatim from founder)

1. **GOLDEN** — extraction output should pass not just structural integrity but a meaningful quality bar.
2. **Unbreakable** — regression-safe; prompt edits and model swaps must surface quality changes immediately.
3. **Rubric-backed** — the quality bar is articulated, not vibes; reviewable; defensible.

The goals are deliberately ambitious. The brainstorm should sharpen them into a concrete first cut that ships, and a longer roadmap for the rest.

---

## What is already in place (foundation work, merged)

- `models.ProvisionalMap` — Pydantic typed contract enforcing closure rules from `app_prompts/extract-system-v1.txt`. **Structural correctness only.** Lives in `models/provisional_map.py`.
- Closure validators (already pass-or-fail):
  - identifier grammar (`b<N>`, `c<N>`, `c<N>_s<M>`, `core-thesis`)
  - every backbone `dependent_clusters` references existing cluster
  - every cluster covered by ≥ 1 backbone
  - every cluster has ≥ 1 subnode
  - every subnode lives in its declared cluster
  - learning prerequisites form a DAG (no self-loops, no reciprocals, no cycles)
  - framework `source_clusters` reference existing clusters
- Live smoke script — `tmp/smoke_extract.py` (in the worktree) — runs extraction live, prints success or normalized-error path. **Not committed**, lives in `.gitignore`'d `tmp/`. Useful pattern but not a permanent eval.
- Architectural seam — `extract_knowledge_map(text, *, llm=None, api_key=None)` accepts a fake `LLMClient` for tests, so eval harness can run offline against recorded responses.
- LLM-client telemetry — every call emits structured success/failure logs (`task_name`, `prompt_version`, `provider`, `model`, `input_tokens`, `output_tokens`, `latency_ms`). Useful as evaluation signals.
- ADR-0001 (`docs/adr/0001-provisional-map-typed-contract.md`) — records the structural-only validation policy and explicitly notes that quality minimums are the prompt's job, not the schema's. This handoff is consistent with that policy: *the rubric does not move into Pydantic; the rubric is its own layer.*

## What is not in place (this is the gap)

- No golden fixtures — there is zero recorded "good output" to compare against.
- No rubric — no articulated quality bar beyond closure rules.
- No eval harness — no pytest test, CLI tool, or scheduled job that runs ProvisionalMaps through quality checks.
- No regression baseline — when the extract prompt changes, we have no signal "did quality go up or down?"
- No adversarial coverage — the structural validators have not been stress-tested with edge inputs.

---

## Source artifacts

- **The function under test:** `ai_service.extract_knowledge_map` (lives in `ai_service.py`)
- **The prompt that drives it:** `app_prompts/extract-system-v1.txt` — read this end-to-end, especially:
  - The processing pipeline (Steps 1-6) — each step is a potential rubric dimension
  - The OUTPUT SCHEMA section
  - The OUTPUT RULES list (around line 240)
  - The QUALITY GATE for frameworks (3 tests: decision, abstraction, mechanism)
- **The typed contract:** `models/provisional_map.py` — structural baseline you build on top of
- **The LLM seam:** `llm/` package — the eval harness should use `LLMClient` like production code does (no patching private names)
- **Foundation spec §5.6:** `docs/superpowers/specs/2026-05-01-foundation-design.md` — the original (deliberately under-specified) section on golden fixtures
- **PRODUCT.md** — describes the user as arriving with *"source material, a concept name, notes, transcripts, articles, or a rough starting model"* — this is the input variety the eval set must cover
- **DESIGN.md §5** (state model) — describes which graph mutations are allowed when. Extraction does NOT mutate graph truth, but the OUTPUT shape feeds every later state transition.
- **UBIQUITOUS_LANGUAGE.md** — every term used in the rubric must come from this glossary (or be added to it)

## Binding docs (must respect)

- `AGENTS.md` — execution discipline (surgical changes, no abstractions for single-use, every changed line traces to the request)
- `app_prompts/extract-system-v1.txt` — the prompt's own quality gates and output rules ARE rubric dimensions
- `docs/adr/0001-provisional-map-typed-contract.md` — *quality minimums are not enforced in the schema; that is the rubric's job. Don't blur the layers.*

---

## Suggested rubric framework — STARTER (for brainstorm input only)

This is **input to the brainstorm, not a decided design**. The founder may keep, cut, reshape, or replace any of this.

### Layered eval architecture (one possible shape)

| Layer | Purpose | Cost | Frequency |
|---|---|---|---|
| **L1 — Structural** (already exists) | Pydantic closure validators in `ProvisionalMap` | free | every CI run, every commit |
| **L2 — Auto-rubric** | Programmatic checks beyond structure: label length budgets, identifier sequentiality, DAG sanity, framework-quality-gate tests, no editorialize markers in `description`, prerequisite-edge minimality | free | every PR touching extraction |
| **L3 — LLM-judge rubric** | LLM evaluates quality dimensions humans can't auto-check: "is this label a mechanism or a topic?", "is this framework decision-changing or a truism?", "does the cluster boundary preserve interdependence?" | money + time | weekly, fixture refresh, prompt-version PRs |
| **L4 — Human review** | Periodic founder-led qualitative review of a fixture batch | high | quarterly or on major prompt changes |

### Candidate rubric dimensions (each scored: pass/fail or 0-1)

Drawn from `app_prompts/extract-system-v1.txt`. Brainstorm should refine, drop, or add:

**Macrostructure (Step 1):**
- Output is structural skeleton, not a summary (no narrative reconstruction)
- No conversational filler / verbal tics in `description`
- Examples / anecdotes generalized into mechanisms
- Only constructed claims that are strongly entailed

**Knowledge architecture (Step 2):**
- `core_thesis` is one sentence, not a paragraph
- `architecture_type` matches the underlying logic, not the source's presentation order
- `governing_assumptions` are unstated premises, not stated claims
- `difficulty` aligns with cluster count and complexity

**Functional clustering (Step 3):**
- Clusters group by **shared causal mechanism**, not by **shared vocabulary** (the critical constraint)
- Cluster labels are concise mechanism statements, not topic labels
- Cluster labels are not full answer-key sentences
- Each cluster passes the NUCLEUS TEST (deletion of any node breaks coherence)
- Cluster count is in valid range (1-7)

**Sub-node decomposition (Step 3b):**
- Sub-nodes pass the INTERDEPENDENCE TEST (independent → decompose; interdependent → keep unified)
- Every cluster has ≥ 1 sub-node (already enforced structurally)
- Sub-node IDs are sequential within their cluster
- Each sub-node has a non-empty `mechanism` field
- Sub-node `mechanism` is causal (how/why), not definitional (what)

**Backbone (Step 4):**
- Backbone count is 1-4
- Each backbone passes the VALIDATION TEST (removal affects multiple clusters)
- Every cluster appears in some backbone's `dependent_clusters` (already enforced structurally)

**Relationships (Step 5):**
- `domain_mechanics` propositions have active linking verbs (not bare arrows)
- `learning_prerequisites` form a sparse DAG (already enforced structurally)
- No prerequisite edges added on uncertain reasoning

**Frameworks (Step 6):**
- Each framework passes all THREE quality gate tests:
  - DECISION TEST — names a specific decision type + external domain
  - ABSTRACTION TEST — survives noun-stripping
  - MECHANISM TEST — states a causal relationship, not a category
- Zero frameworks is a valid output (do not force)

**Output discipline:**
- `drill_status`, `gap_type`, `gap_description`, `last_drilled` all `null` on extraction (already structural)
- Total node count in 5-30 range (or `low_density: true` flagged)
- No editorialize markers (`!`, "remember to", "key takeaway", "in summary")
- No emoji, no exclamation marks
- Mechanism strings prefer abstraction over repetition

**Safety (extraction-specific):**
- For Imported Sources with `is_remote_source=True`, no instructions from the source content leaked into the output as if they were extracted mechanisms (prompt-injection resistance, OWASP LLM01)

### Candidate fixture set

Cover the input variety described in PRODUCT.md:

1. `short_concept_only` — just a concept name (e.g., "Entropy") → should produce thin map or `low_density: true`
2. `pasted_passage_clean` — 2-3 paragraphs of clean expository text, single domain
3. `pasted_passage_messy` — same passage with conversational filler, false starts, repetition
4. `lecture_transcript` — long transcript, multi-mechanism, includes off-topic asides
5. `textbook_chapter_excerpt` — dense, formal, nested
6. `student_notes_fragmented` — bullet-style, incomplete sentences, shorthand
7. `multi_domain` — passage that spans 2+ domains (rubric for cross-cluster mechanism vs. silo)
8. **Adversarial fixtures:**
   - `prompt_injection_attempt` — Imported Source containing fake "instructions" addressed to the LLM
   - `low_density_input` — input with < 5 substantive claims (should flag `low_density: true`)
   - `pure_taxonomy` — input that is structurally a list (should NOT produce frameworks per the MECHANISM TEST)
   - `no_unifying_thesis` — input where `core_thesis` should fall back to "organizing question"

Each fixture stores the input + a recorded LLM response + the expected rubric scores.

### Candidate harness shape (one option)

- `tools/extract_eval/` — package with the rubric, fixtures, scoring logic, CLI entrypoint
- Reads fixtures from `tests/fixtures/extraction_eval/`
- Two run modes:
  - `--mode replay` (default, fast, free, runs in CI) — feeds recorded LLM responses through the rubric
  - `--mode live` (manual, costs money, refreshes fixtures) — calls real Gemini, records the response, optionally re-scores
- Output: per-fixture rubric report (Markdown table), aggregate pass-rate summary
- Pytest integration: `tests/test_extraction_rubric.py` runs replay mode in CI; per-fixture failures surface specific dimensions that broke

### Open questions for the brainstorm

The agent picking this up MUST raise these with the founder before writing a spec:

1. **Scope of the first cut** — ship just L1+L2 (free, fast) and defer L3+L4? Or ship a thin slice of L3 from day one (one LLM-judge dimension to prove the pattern)?
2. **Pass/fail vs scored** — is each rubric dimension binary, or scored 0-1? Mixed? What is the aggregate?
3. **Fixture lifecycle** — when a prompt version changes intentionally, what is the workflow to refresh fixtures? Approve old vs new shape diff manually?
4. **LLM-judge bias** — if the same model that produced the output also judges it, the eval is suspect. Cross-model judging (Gemini extracts, Claude judges) is more rigorous. Which provider for the judge? Is the budget for a second provider in scope yet?
5. **Adversarial scope** — how many adversarial fixtures are required for v1? The list above has 4; the founder may want more or less.
6. **Surfacing in dev workflow** — should the rubric run on every commit (pre-commit hook), every PR (GitHub Actions), or only on demand (`make eval`)?
7. **Rubric vs prompt drift** — when a rubric dimension fails repeatedly, do we tighten the prompt or loosen the rubric? Who decides?
8. **Versioning** — does the rubric itself version (rubric v1 vs v2)? Yes, almost certainly. How does that interact with prompt versioning?
9. **L3 cost ceiling** — running an LLM-judge on every fixture, every PR is expensive. What is the founder's per-week eval budget?
10. **Coverage vs depth** — 8 fixtures with 30 dimensions each (deep), or 30 fixtures with 8 dimensions each (broad)?

---

## Deliverables (what the next agent should produce)

The brainstorm phase shapes the spec; the spec drives the plan; the plan drives the deliverables. Likely shape:

- **Spec doc:** `docs/superpowers/specs/<date>-extraction-evals-design.md`
- **Plan doc:** `docs/superpowers/plans/<date>-extraction-evals.md`
- **New package(s):** likely `tools/extract_eval/` with submodules for rubric / scoring / fixtures
- **Test fixtures:** `tests/fixtures/extraction_eval/<slug>.json` (input + recorded response + expected rubric)
- **Pytest test:** `tests/test_extraction_rubric.py`
- **CI / dev workflow integration:** TBD per brainstorm answer to question #6
- **ADR:** likely **ADR-0004** recording the rubric architecture (layered, structural ≠ rubric, fixture-replay default)
- **Documentation:** `docs/design/extraction-rubric.md` for ongoing reference of dimensions and scoring policy

## Out of scope (deliberately deferred)

- **Drill / repair / re-drill evals** — different artifacts, different prompts. The next migration sweep (drill_chat / generate_repair_reps through the seam) sets up the structural baseline; quality evals on those come later.
- **End-to-end product evals** — does the learner reconstruct the mechanism better after socratink than after just reading? That is a research question, not a foundation question. Out of scope here.
- **Cost dashboarding / token-usage analytics** — the LLM client emits structured logs (`input_tokens`, `output_tokens`, `latency_ms`); piping those into a dashboard is a separate ops concern.
- **Multi-language / non-English source material** — defer until the English path is empirically golden.
- **Live A/B testing of prompt variants on real learner traffic** — needs the prompt registry shipped first (foundation spec §5.4, also deferred).

## Success criteria (for the workstream as a whole)

The workstream is "done" when:

- A rubric is articulated, reviewed by the founder, and committed as `docs/design/extraction-rubric.md`
- An eval harness exists, runs offline in CI on a fixture set, and produces a per-dimension pass-rate report
- A fixture refresh path exists and is documented (the founder can re-record fixtures against current Gemini output without ad-hoc tooling)
- A regression baseline is captured: the current prompt version's rubric scores are the floor; future prompt changes must equal or exceed
- ADR-0004 is committed
- The founder has tested the harness end-to-end at least once (fixture run → report → spotted regression OR confirmed quality)

The workstream is "golden" when:

- All current fixtures pass at the founder's chosen aggregate threshold
- Adversarial fixtures (prompt injection, low-density, pure-taxonomy) behave as the rubric predicts
- The next prompt version that ships measurably moves a rubric dimension in a direction the founder is willing to defend in writing

## How to start

1. **Read the foundation context first**, in this order:
   - This handoff (you're here)
   - `docs/adr/0001-provisional-map-typed-contract.md`
   - `app_prompts/extract-system-v1.txt` (the prompt itself)
   - `docs/superpowers/specs/2026-05-01-foundation-design.md` §5.6 (the original deferral)
   - `models/provisional_map.py` (the structural baseline)
2. **Invoke `superpowers:brainstorming`** — establish design intent with the founder. Do NOT skip this. Walk through the 10 open questions above. Decide what's in v1 vs. later.
3. After brainstorming approves a spec, **invoke `superpowers:writing-plans`** — produce a TDD-style step-by-step plan.
4. **Set up an isolated worktree before any code:**
   ```bash
   git worktree add .worktrees/extract-evals -b feat/extraction-evals dev
   ```
   The post-checkout hook (`scripts/git-hooks/post-checkout`) will auto-link `.env` and `.env.local`. Verified working as of 2026-05-01.
5. Execute via `superpowers:test-driven-development`. Commit small, commit often.
6. Open a PR against `dev` titled `feat(eval): extraction rubric + harness — <one-line summary of v1 scope>`.

## A note on tone

The founder's wording was *"GOLDEN. like unbreakable like also think about rubricing."* That is ambition, not a brief. The brainstorm's first job is to translate ambition into a v1 scope that ships, not to chase the full ideal in one sweep. **The rubric is a forever artifact** — it will accrete dimensions as the product matures. The eval harness is a forever artifact. Get a thin, defensible slice in CI; iterate from there.

Per AGENTS.md execution discipline: *no abstractions, configurability, or generic frameworks for single-use code; match existing style; every changed line should trace back to the user request.*

The eval framework IS likely to be reused (drill, repair-reps, future stages will want analogous evals), so some abstraction is justified — but not preemptively. Build for the extraction case first; abstract on the second use, not before.
