# Drill Through-Line Alignment

## Scope

- Align `app_prompts/drill-system-v1.md` and `app_prompts/README.md` with the current uncommitted `PRODUCT.md` through-line.
- Preserve Generation Before Recognition, source/goal/sketch/scaffold as context not evidence, Bloom as internal node-intent grammar, and the structured drill output contract.
- Do not touch unrelated dirty files `tests/test_provisional_map.py` or `tests/test_sketch_validation.py`.

## Checkpoint Log

### Checkpoint 1 - Baseline

- `git status --short`
  - `PRODUCT.md` was already modified.
  - `tests/test_provisional_map.py` and `tests/test_sketch_validation.py` were already modified and remain out of scope.
- `pytest tests/test_app_prompts.py -q`
  - Result: `3 passed in 0.72s`.
- `rg -n "Theta|Stage 3|evaluator taxonomy|evaluator-taxonomy|Bloom taxonomy|Bloom's taxonomy|taxonomy" PRODUCT.md DESIGN.md docs/product/spec.md docs/product/evidence-weighted-map.md app_prompts/drill-system-v1.md app_prompts/README.md tests/test_app_prompts.py ai_service.py`
  - Result: found retired `Stage 3` / `Theta` framing in `app_prompts/README.md` and `app_prompts/drill-system-v1.md`; found one unrelated `taxonomy` use in `docs/product/spec.md`.
- Code Review Graph minimal context for `app_prompts/drill-system-v1.md`, `app_prompts/README.md`, and `tests/test_app_prompts.py`
  - Result: risk `low`; graph flow output is not meaningful for prompt/doc files.

### Checkpoint 2 - Failing Contract Assertions

- Added prompt-contract assertions in `tests/test_app_prompts.py` for:
  - structured output fields and runtime anchors,
  - PRODUCT.md reconstruction through-line,
  - app prompt documentation through-line,
  - retired `Theta` / `Stage 3` / evaluator-taxonomy framing absence.
- `pytest tests/test_app_prompts.py -q`
  - Result: failed as expected.
  - Failure reasons: missing PRODUCT.md reconstruction through-line in the drill prompt and prompt README; retired `Theta`, `Stage 3`, `LearnOps pipeline`, `neurocognitive`, and evaluator-taxonomy drift still present in bounded prompt surfaces.

### Checkpoint 3 - Prompt And Docs Update

- Updated `app_prompts/drill-system-v1.md`.
  - Replaced inherited platform/pipeline framing with the Socratink reconstruction-through-line.
  - Preserved "Target Node (ANSWER KEY)", "Learner Scaffold", `bloom_level`, and every structured output field.
  - Replaced retired classification examples with neutral dependency-lockfile examples while preserving `solid`, `deep`, `shallow`, and `misconception`.
- Updated `app_prompts/README.md`.
  - Replaced the stage table with runtime roles.
  - Added the prompt product contract: Generation Before Recognition; source material, learner goals, learner sketches, and learner scaffolds as context, not evidence; Bloom/node-intent grammar internal.

### Checkpoint 4 - Validation

- `pytest tests/test_app_prompts.py -q`
  - Result: `7 passed, 12 subtests passed in 0.59s`.
- `rg -n "Theta|Stage 3|evaluator taxonomy|evaluator-taxonomy|LearnOps pipeline|neurocognitive|taxonomy and input type constraints" app_prompts/drill-system-v1.md app_prompts/README.md`
  - Result: no matches; command exited `1`.
- `rg -n "Theta|Stage 3|evaluator taxonomy|evaluator-taxonomy|LearnOps pipeline|neurocognitive|taxonomy and input type constraints|Bloom taxonomy|Bloom's taxonomy" PRODUCT.md DESIGN.md docs/product/spec.md docs/product/evidence-weighted-map.md app_prompts/drill-system-v1.md app_prompts/README.md ai_service.py`
  - Result: no matches; command exited `1`.
- `rg -n "Target Node \\(ANSWER KEY\\)|Learner Scaffold|agent_response|answer_mode|score_eligible|help_request_reason|classification|routing|gap_description|response_tier|response_band|tier_reason" app_prompts/drill-system-v1.md`
  - Result: all runtime anchors and structured output fields present.
- `git diff --name-only`
  - Result: changed tracked files are `PRODUCT.md` (pre-existing), `app_prompts/README.md`, `app_prompts/drill-system-v1.md`, `tests/test_app_prompts.py`, and the pre-existing dirty `tests/test_provisional_map.py` / `tests/test_sketch_validation.py`.
  - Out-of-scope dirty tests remain dirty but were not used as edit targets.
