# Codebase AI-Readiness Rubric (socratink-app)

A measurement instrument for how well an AI coding agent can ingest, navigate, verify, and modify this codebase. Each criterion declares the **evidence tier** behind it so reviewers know which scores carry research weight and which are heuristic.

## Why this rubric exists

A rubric is only useful if (a) two reviewers score the same repo the same way, and (b) the score correlates with something real (agent task success). Most "AI-readiness" rubrics fail both tests. This one:

- Cites research where it exists; labels criteria **`[heuristic]`** where it doesn't.
- Gives a **measurement protocol** per criterion — usually a single shell command — so scoring is reproducible.
- Drops folklore axes (vertical-slice supremacy, raw file length, codebase-level OpenAPI) that have no empirical backing.
- Adds the axes the original draft missed: type coverage, test runnability, verification gates, lockfile/build reproducibility.

## Evidence tiers used in this rubric

| Tier | Meaning |
| :--- | :--- |
| `[evidence: high]` | Backed by a controlled study, benchmark ablation, or multiple independent sources. |
| `[evidence: medium]` | One credible study or a strong industry-wide consensus with measurable claims. |
| `[heuristic]` | Plausible practitioner intuition; no published study isolates the effect. Use the criterion if it helps your team align, but do not treat the score as predictive. |

## Scoring scale (per criterion)

- **0 — Hostile:** Actively prevents agent work.
- **1 — Resistant:** Forces excessive token use or multi-hop searches.
- **2 — Friendly:** Follows reasonable practice; agent navigates with moderate prompting.
- **3 — Optimized:** Intentionally designed for machine ingestion and reproducible verification.

12 criteria × 3 = **36 points max**. No category weights — weights in the previous draft were declared at 40/30/30 but never applied in the score arithmetic. Equal-weight raw points are honest.

---

## Category A — Retrieval & Parseability

The agent's ability to find and ingest the right code chunk.

### A1. AST-chunk compatibility `[evidence: high]`
*Can the repo be cleanly chunked by an AST-aware retriever (tree-sitter/cAST)? Tree-sitter has documented failure modes — incomplete syntax, deeply nested unclosed braces, exotic templating — that degrade retrieval.*

**Source:** cAST shows AST-aware chunking improves Pass@1 on SWE-bench by 2.6pp (Claude) and 5.6pp (CodeLlama-7B) vs line-based chunking. <https://arxiv.org/html/2506.15655v1>. Tree-sitter limitations documented at <https://blog.jez.io/tree-sitter-limitations/>.

**Measure:**
```bash
# Count source files; flag any that exceed 800 LOC (cAST's reference chunk
# budget at 4000 chars ≈ 80-150 LOC of typical code — one logical unit per
# chunk needs files small enough to chunk at AST-leaf boundaries).
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' \) \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' \
  -not -path '*/.code-review-graph/*' -not -path '*/.vercel/*' \
  -not -path '*/.claude/*' -not -path '*/.agents/*' \
  -exec wc -l {} + | awk '$1 > 800 {print}'
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Files use bespoke templating or string-built code blocks that tree-sitter cannot parse. | 5+ files > 800 LOC OR any source file > 2000 LOC. | 1–4 files > 800 LOC, none > 2000 LOC. | All source files ≤ 800 LOC; tree-sitter parses without ERROR nodes on any file. |

**socratink-app baseline:** `public/js/app.js` (3,542), `ai_service.py` (1,069), `auth/router.py` (996), `main.py` (872) — scoring **1**.

---

### A2. Lexical specificity & search recall `[evidence: medium]`
*BM25 / keyword retrieval is the cheap-and-fast fallback even in vector-RAG stacks. Inconsistent naming and abbreviations destroy keyword recall.*

**Source:** Ubiquitous-language consistency is heuristic on its own but compounds with retrieval — cAST results assume terms appear consistently in both index and query.

**Measure:**
```bash
# Compare domain terms in UBIQUITOUS_LANGUAGE.md against grep occurrences.
# Each canonical term should appear at the names it's documented under, not
# via abbreviation drift.
grep -E '^\s*[-*]\s+\*\*[A-Z]' UBIQUITOUS_LANGUAGE.md | head -20
# Then spot-check 5 terms via ripgrep.
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Cryptic abbreviations dominate (`chk_usr_auth_v2`). | Naming drifts across modules; same concept named 3+ ways. | Descriptive, intent-revealing names; no glossary. | Glossary (`UBIQUITOUS_LANGUAGE.md` or equivalent) exists and ≥80% of its terms appear verbatim in code. |

**socratink-app baseline:** `UBIQUITOUS_LANGUAGE.md` exists (87 LOC). Spot-check before scoring.

---

### A3. Cohesive logical units per file `[heuristic]`
*Intuitively: one file = one concept makes retrieval chunks meaningful. Empirically: SWE-bench gold patches average 1.7 files / 32.8 lines, but no controlled study isolates "files-per-concept" as a predictor. Score conservatively.*

**Source:** SWE-bench patch-scope stats <https://arxiv.org/pdf/2310.06770>. No study isolates this axis from confounds.

**Measure:** Manual — pick 5 random files, ask: "does this file contain one bounded responsibility?" Count files with multiple unrelated responsibilities.

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Most files mix unrelated responsibilities. | 30%+ of sampled files mix concepts. | Most files have one clear responsibility; a few god-files. | Strict one-concept-per-file; god-files explicitly refactored or annotated as known exceptions. |

**socratink-app baseline:** `ai_service.py` (extraction + drill + repair-reps in one file) is the canonical god-file to flag. Score **1–2** pending review.

---

## Category B — Static Verification Signal

The agent's ability to get fast, accurate feedback on its own edits.

### B1. Type-hint coverage `[evidence: high]`
*Type errors cause 24–34% of LLM code-gen compile failures. Hand-written hints help the type-checker, which then gives the agent verification signal.*

**Source:** Type-constrained decoding study, 24% Copilot compilation failures attributed mainly to type errors. <https://arxiv.org/pdf/2504.09246>, <https://arxiv.org/html/2507.22086v1>.

**Caveat:** Evidence is strongest for *generation* (type-constrained decoding). The mechanism for *agent navigation* (reading a hint to predict shape) is weaker — keep this in mind when scoring.

**Measure:**
```bash
# Python annotated-return ratio.
TOTAL=$(rg -t py 'def \w+\(' --no-heading | wc -l)
ANNOTATED=$(rg -t py 'def \w+\([^)]*\)\s*->' --no-heading | wc -l)
echo "scale=2; $ANNOTATED * 100 / $TOTAL" | bc
# Mypy strict run on changed paths.
mypy --strict path/to/changed/  # should exit 0
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Dynamically typed with `**kwargs: Any` patterns; no `pyproject.toml`/`mypy.ini`. | < 40% annotated returns OR mypy never runs cleanly. | 40–80% annotated returns; mypy installed; runs cleanly on most modules. | ≥ 80% annotated returns; mypy strict config exists and CI/pre-deploy enforces zero new errors. |

**socratink-app baseline:** 232 annotated returns; **pyrefly is the primary type-check gate** (config in `pyrefly.toml`, `preset = "legacy"`, `check-unannotated-defs = true`, version pinned in `scripts/doctor.sh`) with mypy retained as a cross-check (`mypy.ini` at the repo root: Python 3.13, `warn_unreachable`, `strict_optional`, `check_untyped_defs`, `warn_return_any`). Both checkers run cleanly under `scripts/doctor.sh` and the preflight CI workflow. Pyrefly's `check-unannotated-defs = true` means unannotated defs are now inferred and checked through, partially substituting for mypy's `disallow_untyped_defs` — currently scoring **2**, on the cusp of **3** pending annotated-return ratio ≥ 80% and tightened per-module overrides.

---

### B2. Test discoverability & runnability `[evidence: high — necessity]; [evidence: high — insufficiency]`
*Tests are the agent's primary feedback loop. They are necessary but not sufficient: 29.6–47.9% of "resolved" SWE-bench patches are behaviorally divergent from ground truth — tests pass while behavior is wrong.*

**Source:** SWE-bench, PatchDiff (29.6%) <https://arxiv.org/abs/2503.15223>, SWE-Bench+ (47.9%) <https://openreview.net/forum?id=R40rS2afQ3>.

**Measure:**
```bash
# Test:source ratio.
TESTS=$(find tests -name 'test_*.py' | wc -l)
SOURCES=$(find . -name '*.py' -not -path '*/tests/*' -not -path '*/.venv/*' \
  -not -path '*/node_modules/*' | wc -l)
echo "scale=2; $TESTS / $SOURCES" | bc
# Time to first test result.
time pytest --co -q | tail -3
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No tests or tests cannot be discovered by the framework's default runner. | Tests exist but require manual env setup; long boot; flaky. | One-command run; test:source ratio ≥ 0.5; clear which tests cover which module. | One-command run; test:source ≥ 1.0; collocation/naming makes coverage of a unit obvious; smoke tests subsettable (`-m smoke`). |

**socratink-app baseline:** 68 test files, 1.74:1 ratio, `pytest.ini` works, Playwright e2e present — currently scoring **3** *if* the runner is one-command from a clean checkout (verify with `scripts/bootstrap-python.sh && pytest -q`).

---

### B3. Verification gate (CI or pre-deploy automation) `[evidence: high]`
*An agent that can't run the linter/typechecker/tests in CI is operating blind on its own diffs. Local-only gates are fragile.*

**Source:** SWE-bench's evaluation harness assumes tests run automatically; agents like SWE-agent and Aider depend on programmatic test feedback. <https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf>.

**Measure:**
```bash
ls -la .github/workflows/ 2>/dev/null || echo "no CI"
# Or any equivalent automation:
ls scripts/preflight-deploy.sh scripts/doctor.sh scripts/verify-deploy.sh
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No automated check before merge or deploy. | Manual scripts exist but rely on developer remembering to run them. | Pre-commit hook OR local pre-deploy script that runs tests + typecheck + lint and blocks on failure. | CI on push/PR + diff-coverage threshold + typecheck + lint, mirrored locally by a single script. |

**socratink-app baseline:** `scripts/preflight-deploy.sh` + `scripts/doctor.sh` exist; `.github/workflows/preflight.yml` invokes `bash scripts/doctor.sh` (which runs **both `pyrefly check` and `mypy .`** as parallel type-check gates) plus `pytest -q --ignore=tests/e2e` on every `pull_request` and on pushes to `main`/`dev`; its `coverage` job starts a loopback app, selects `COMPARE_BRANCH`, and runs `scripts/check-coverage.sh` for strict diff coverage. The same gates are mirrored locally by `scripts/doctor.sh` and `scripts/check-coverage.sh`. Currently **3**.

---

## Category C — Instruction & Context Files

How the repo tells the agent its own rules.

### C1. Active AI directive file (AGENTS.md / CLAUDE.md) `[evidence: medium]`
*Rule files yield small, real, model-dependent gains — Arize's Prompt Learning on `.clinerules` showed +0.67–6% test gains for Claude Sonnet 4-5, ~10–15% overall for GPT-4.1. Marketing claims of larger jumps (65→94%) have no paper backing.*

**Source:** <https://arize.com/blog/optimizing-coding-agent-rules-claude-md-agents-md-clinerules-cursor-rules-for-improved-accuracy/>.

**Measure:**
```bash
# Presence, size, age.
for f in AGENTS.md CLAUDE.md GEMINI.md .cursorrules; do
  [ -f $f ] && echo "$f: $(wc -l < $f) lines, modified $(stat -f %Sm $f)"
done
# Are claims in it falsifiable from current code?
# Manual spot-check: pick 3 architectural claims; grep to verify they're still true.
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No directive file. | Exists but is stale, vague ("write clean code"), or unverifiable. | Substantive file with concrete architecture and convention claims; ≥80% still match the codebase. | C2 conditions met **and** the file includes anti-patterns/known footguns specific to this repo, with bootstrap order, file map, and verification commands. |

**socratink-app baseline:** `AGENTS.md` substantive (307 LOC), `CLAUDE.md` is a 5-line pointer. Verify the AGENTS.md claims grep-match the code, then likely score **2–3**.

---

### C2. Domain language consistency `[heuristic]`
*Captures whether the repo's terminology is centralized and applied. Compounds with A2.*

**Measure:**
```bash
ls UBIQUITOUS_LANGUAGE.md docs/glossary.md 2>/dev/null
# Spot-check 5 terms from the glossary against ripgrep matches.
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No glossary; terms drift module-by-module. | Glossary exists but is out of date. | Glossary current; most key terms used consistently. | Glossary current and *referenced from AGENTS.md*; CI lint or doc check catches drift. |

**socratink-app baseline:** `UBIQUITOUS_LANGUAGE.md` (120 LOC) — pointed-to from `DESIGN.md` §2 — likely **2** pending freshness check.

---

### C3. Directory-level READMEs / ADRs `[heuristic]`
*Enables hierarchical retrieval: agent reads the directory's README before grepping files.*

**Measure:**
```bash
find . -maxdepth 3 -name 'README.md' -not -path '*/node_modules/*'
ls docs/adr/ 2>/dev/null
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Root README only. | Root README + a handful of stale folder READMEs. | Root + ≥3 directory READMEs covering main bounded contexts; ADRs exist. | Every top-level source directory has a README that states purpose, public surface, and known footguns; ADRs cover non-obvious decisions. |

**socratink-app baseline:** `docs/adr/` exists with 4 ADRs; `tests/e2e/README.md`, `docs/founder/README.md`, `docs/adr/README.md` plus per-directory READMEs for `auth/`, `llm/`, `source_intake/`, `models/`, and `app_prompts/` are now checked in. Currently **3**; keep new top-level source directories under the same convention to hold the score.

---

## Category D — Reproducibility & Feedback Loops

The agent's ability to run the system at all.

### D1. Single-command dev start `[evidence: medium]`
*If the agent can't boot the app, it can't verify UI / integration changes empirically — and global CSS regressions, route mismatches, and runtime config errors won't surface until production.*

**Measure:**
```bash
# Either a documented one-liner or a Makefile target.
ls Makefile justfile 2>/dev/null
grep -E '"(dev|start)":' package.json 2>/dev/null
ls scripts/dev.sh 2>/dev/null
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Boot requires multiple undocumented steps. | Documented but takes >5min from clean checkout. | One command, ≤5min, prerequisites documented in README. | One command, lockfiles + bootstrap script make it idempotent; devcontainer or equivalent for parity with prod. |

**socratink-app baseline:** `scripts/bootstrap-python.sh` + `scripts/dev.sh` + lockfiles present — **3**.

---

### D2. Build/run reproducibility `[evidence: medium]`
*Lockfiles, pinned versions, and reproducible local→prod parity. Without these, an agent's fix passes locally and breaks in deploy.*

**Measure:**
```bash
ls package-lock.json pnpm-lock.yaml poetry.lock requirements.txt 2>/dev/null
grep -c '==' requirements.txt 2>/dev/null  # pin count
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No lockfile; floating versions. | Lockfile exists but is regularly out of sync. | Lockfiles present and current; CI/preflight validates them. | D2's level-2 plus deploy uses the same lockfile-resolved versions as local (Vercel build pinned, image digests, etc.). |

**socratink-app baseline:** `requirements.txt` (pinned), `requirements-dev.txt`, `package-lock.json`, `vercel.json`, `preflight-deploy.sh` — **3**.

---

## Category E — Repository Hygiene

Boundary conditions; below these, no rubric score is meaningful.

### E1. Index-clean (excluded artifacts) `[heuristic, but necessary]`
*Generated files, caches, and vendored libs pollute retrieval. Agents waste tokens reading committed `dist/`.*

**Measure:**
```bash
# Heuristic: anything > 1MB committed that isn't source.
git ls-files | xargs -I{} sh -c 'wc -c < "{}"' 2>/dev/null | sort -n | tail
cat .gitignore | grep -E '^(node_modules|dist|build|\.venv|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|coverage|\.vercel|\.next)'
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| `node_modules/`, `dist/`, build artifacts committed. | Some cache directories committed (`.pytest_cache`, `.mypy_cache`); large generated files in tree. | Clean tree; `.gitignore` covers the standard set. | E1 level-2 plus an `.aiignore` / retrieval-tool exclusion list keeps the indexer focused on source. |

**socratink-app baseline:** `node_modules/`, `.vercel/`, `.mypy_cache/`, `.ruff_cache/`, and `.agents/` are ignored and not tracked; `.aiignore` now mirrors retrieval-tool exclusions for local runtime, cache, coverage, and scratch surfaces. Currently **3**.

---

### E2. Code-review-graph or equivalent static index `[heuristic]`
*If the repo ships a precomputed graph (call sites, communities, impact radius), agents can do bounded impact analysis without re-parsing the world. This is workflow infrastructure, not a research-validated property — keep heuristic.*

**Measure:**
```bash
ls .code-review-graph/graph.db .code-review-graph/wiki/ 2>/dev/null
```

| 0 | 1 | 2 | 3 |
| --- | --- | --- | --- |
| No static index. | Index exists but is months stale. | Current index; reviewers know how to query it. | Index refreshed automatically per push; integrated into the agent's tool surface. |

**socratink-app baseline:** `.code-review-graph/graph.db` (32 MB, last refreshed 2026-05-12). Currently **2**.

---

## Scoring & Interpretation

**Max total: 36** (12 criteria × 3). Compute per-category and overall.

| Total | Tier | Meaning |
| :--- | :--- | :--- |
| 30–36 | **AI-Native** | Agents can do bounded, verified work autonomously on most diffs. Retrieval is accurate, verification is automated, instruction files are honest. |
| 22–29 | **AI-Augmented** | Agents are effective copilots; humans pull the right file occasionally; first-or-second-try working code is common. |
| 14–21 | **Human-Dependent** | Agents need hand-holding: copy-paste the right files, warn about architectural quirks, expect frequent wrong-chunk retrieval. |
| 0–13 | **AI-Resistant** | Agent-led work is slower than human-written. Hallucinated dependencies and broken hidden contracts are the norm. |

**Critical caveat — published evidence does NOT support a claim of "near-zero human intervention" at the top tier for any current codebase.** Even at 36/36, agents will hallucinate. Tier names describe relative quality, not autonomy.

---

## Measurement protocol

1. **One scorer, one branch.** Score against a named commit SHA.
2. **Run the protocol commands literally.** Paste outputs into a scoring log.
3. **For heuristic-only criteria, document the judgment call** so the next reviewer can replicate.
4. **Re-score quarterly or after any architectural change** (new framework, large refactor, major dependency upgrade).
5. **Track score delta over time, not absolute score.** A repo moving from 18 → 26 is a stronger signal than 26 in isolation.

---

## What this rubric intentionally does *not* score

- **Vertical-slice vs layered architecture.** No empirical comparison exists; encoding a preference here would penalize legitimate layered designs (Django, FastAPI conventions).
- **Raw file length as a scalar.** Patch-scope stats from SWE-bench are about *patches*, not files. We score AST-chunkability (A1) instead, which captures the underlying concern.
- **Codebase-level OpenAPI / GraphQL presence.** MCP and schema benchmarks measure runtime tool selection, not codebase-quality effects. Keep this in deployment-time tooling, not in this rubric.
- **Cyclomatic complexity / fan-in / fan-out.** MLSec ICSE 2026: "no significant correlations with LLM bug fix accuracy" at repo scale.

---

## Provenance

- Empirical claims sourced from cAST (arXiv 2506.15655), SWE-bench (arXiv 2310.06770), SWE-Bench+ (OpenReview R40rS2afQ3), PatchDiff (arXiv 2503.15223), Type-constrained decoding (arXiv 2504.09246), MLSec ICSE 2026, Arize Prompt Learning on .clinerules, SWE-agent NeurIPS 2024, Tree-sitter limitations (blog.jez.io/tree-sitter-limitations).
- Codebase indicators sourced from a survey of socratink-app at commit `cc92040` (2026-05-12), with CI, retrieval-exclusion, and test/source baselines refreshed at commit `ee257c4` (2026-05-18).
- Folklore items removed from the previous draft are listed in *"What this rubric intentionally does not score"* with cited reasons.
