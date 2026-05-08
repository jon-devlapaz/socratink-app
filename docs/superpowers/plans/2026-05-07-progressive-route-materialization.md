# Progressive Route Materialization (C-prime) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current two-textarea Ignition view with a tiny door + a separate launch-pad surface, and constrain source-less map generation to a smallest ProvisionalMap (≤4 drillable nodes).

**Architecture:** Door captures concept name only and writes a pending shell to `sessionStorage`; source-less submits navigate to a launch pad that captures the threshold and POSTs to `/api/extract` (stateless: returns ProvisionalMap, frontend persists, then clears sessionStorage). Source-attached submits keep today's `/api/extract` two-step (URL via `/api/extract-url` first). Backend dispatch (`_resolve_extract_path`) already enforces `thin_sketch_no_source` rejection; this plan adds the ≤4-node cap on source-less generation, extracts the source panel into a reusable module, rewrites the frontend surfaces, and updates home/desk vocabulary.

**Tech Stack:** Python 3.x + FastAPI (backend); vanilla JS + HTML + CSS (frontend); pytest (backend tests); existing LLM client (`build_llm_client`) and Pydantic `ProvisionalMap` model.

**Spec:** `docs/superpowers/specs/2026-05-07-progressive-route-materialization-design.md`
**Brief:** `docs/design/handoffs/2026-05-07-progressive-route-materialization-agent-brief.md`

---

## File Structure

**Backend (modifications):**
- `app_prompts/generate-smallest-route-system-v1.txt` — **new**, system prompt for smallest-route generation (≤4 drillable nodes).
- `ai_service.py` — **add** `generate_smallest_provisional_map(concept, threshold, lc_context)` and `_validate_smallest_route(map: ProvisionalMap)` near the existing `generate_provisional_map_from_sketch` (line 693). The existing function is **kept** for back-compat callers; the new function is the one the dispatch uses.
- `main.py` — **modify** the `from_sketch` branch in `extract()` (around line 480+) to call `generate_smallest_provisional_map` instead of `generate_provisional_map_from_sketch`. `_resolve_extract_path` itself is unchanged (it already enforces `thin_sketch_no_source`).
- `tests/test_generate_smallest_route.py` — **new** unit tests for the cap + prompt wiring.
- `tests/test_extract_route_smallest.py` — **new** integration tests for the dispatch returning a smallest route.

**Frontend (modifications):**
- `public/js/source-panel.js` — **new**, exports `mountSourcePanel(targetEl, { onAttach, onCancel, onReplace })` extracted from `concept-create.js::beginEditSource`.
- `public/js/concept-create.js` — **refactor** `beginEditSource` (line 601+) to call `mountSourcePanel`; preserve every existing behavior.
- `public/js/launch-pad.js` — **new**, exports `mountLaunchPad()` (or attaches `App.runLaunchPadAction`); reads `socratink:pendingShell` from sessionStorage, validates ts <24h, handles submit + persist-then-clear.
- `public/js/app.js` — **modify** the door submit handler (`runHeroAction`); add navigation to launch pad on no-source; integrate `mountSourcePanel` for the door's `+ add source material` affordance.
- `public/index.html` — **modify** the `ignition-view` section (lines 279–328) to strip the sketch field, eyebrow, voice line, and descriptive paragraph; **add** a new `<section class="primary-view launch-pad-view">`; **modify** the home/desk hero (lines 198–225) for vocabulary swap.
- `public/css/components.css` — **modify** to remove sketch-field styles, add launch-pad styles, add the post-launch "skeleton" framing line.
- Wherever the home/desk renders concept tiles — **verify** vocabulary text is sourced from the updated DOM/JS (no hard-coded "draft path" strings remain).

**Bindings docs:**
- `DESIGN.md` — **modify** §3 Screen 1 to point to the new launch pad surface.
- `UBIQUITOUS_LANGUAGE.md` — **modify** to add `launch pad`, `launch attempt`, `pending shell`, `smallest actionable route`.

---

## Task 1: Smallest-route system prompt

**Files:**
- Create: `app_prompts/generate-smallest-route-system-v1.txt`

This task creates the prompt file. The Python wiring comes in Task 2.

- [ ] **Step 1: Read the existing sketch-based prompt as the structural baseline**

Run: `cat app_prompts/generate-from-sketch-system-v1.txt | head -60`

The new prompt copies the schema/voice rules from this file and adds the ≤4-node cap.

- [ ] **Step 2: Write the new prompt file**

Create `app_prompts/generate-smallest-route-system-v1.txt` with content:

```
You generate a smallest actionable route for a learner who has provided
a concept name and a rough starting sketch (their threshold). Your output
is a ProvisionalMap.

Hard constraints:

1. The output contains AT MOST 4 drillable nodes total: ONE suggested
   first target (which carries the core thesis as its display name AND
   is the node the learner's first cold attempt will fire against),
   PLUS at most 3 backbone hints (additional drillable nodes the
   learner may attempt later). There is no separate "thesis" node.
2. NO cluster lattice. NO synthesis surfaces. NO container/parent
   structure beyond what ProvisionalMap requires for a flat list of
   drillable nodes.
3. The suggested first target's display name IS the core thesis: a
   single sentence that names the central mechanism the learner will
   reconstruct first.
4. Each backbone hint is one drillable mechanism the learner could
   attempt after the first target. Hints are suggestions, not bound
   parts of the route.
5. Use the learner's threshold as the seed: the suggested first target
   should sit at the centre of what the threshold reveals the learner
   already touches; backbone hints should fill the most salient gaps.
6. If <lc_context> is present, use it to ground hypothesis structure,
   but favour the learner's threshold when the two diverge.

Voice rules (DESIGN.md §10):
- Calm, precise, Socratic. Plain, complete sentences.
- Verbs over adjectives.
- No emoji. No exclamation marks.
- No "AI tutor" framing in any text the learner sees.

[Include the same JSON output schema block as
generate-from-sketch-system-v1.txt — the response must be a valid
ProvisionalMap.]
```

When writing this, copy the JSON schema block (response_schema description) verbatim from `app_prompts/generate-from-sketch-system-v1.txt` so the model produces a Pydantic-compatible output. Read both files side-by-side and reconcile.

- [ ] **Step 3: Commit**

```bash
git add app_prompts/generate-smallest-route-system-v1.txt
git commit -m "feat(prompts): add smallest-route system prompt for C-prime concept entry"
```

---

## Task 2: `_validate_smallest_route` + tests

**Files:**
- Modify: `ai_service.py` (add helper near line 693)
- Create: `tests/test_generate_smallest_route.py`

This is a pure function — easy TDD.

- [ ] **Step 1: Write the failing test**

Create `tests/test_generate_smallest_route.py`:

```python
"""Tests for the ≤4-node cap on source-less generation per C-prime spec §5.1."""
from __future__ import annotations

import pytest

from ai_service import _validate_smallest_route, SmallestRouteCapExceeded
from models import ProvisionalMap


def _node(name: str) -> dict:
    """Minimal drillable node dict; expand if ProvisionalMap requires more."""
    return {"name": name, "purpose": "test"}


def _provisional_map_with_node_count(n: int) -> ProvisionalMap:
    """Build a ProvisionalMap with `n` drillable nodes for the cap test.

    Adjust the construction here once the actual ProvisionalMap shape
    is consulted (see `from models import ProvisionalMap`).
    """
    return ProvisionalMap.model_validate({
        "core_thesis": "test thesis",
        "rooms": [_node(f"node-{i}") for i in range(n)],
    })


def test_smallest_route_validator_accepts_one_node():
    """Suggested first target alone is allowed (n=1)."""
    pm = _provisional_map_with_node_count(1)
    _validate_smallest_route(pm)  # no raise


def test_smallest_route_validator_accepts_four_nodes():
    """1 first target + 3 backbone hints = 4. Allowed."""
    pm = _provisional_map_with_node_count(4)
    _validate_smallest_route(pm)  # no raise


def test_smallest_route_validator_rejects_five_nodes():
    """One over the cap. Must raise."""
    pm = _provisional_map_with_node_count(5)
    with pytest.raises(SmallestRouteCapExceeded):
        _validate_smallest_route(pm)


def test_smallest_route_validator_rejects_zero_nodes():
    """No drillable nodes is a malformed route (no first target)."""
    pm = _provisional_map_with_node_count(0)
    with pytest.raises(SmallestRouteCapExceeded):
        _validate_smallest_route(pm)
```

Note: the helper `_provisional_map_with_node_count` likely needs adjustment based on the real `ProvisionalMap` schema. Open `models/__init__.py` (or wherever `ProvisionalMap` is defined) and read the field names. Replace `"rooms"` with the actual field name for the drillable-node list. Replace `_node()` with whatever fields the node Pydantic model requires.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_smallest_route.py -v`
Expected: FAIL with `ImportError: cannot import name '_validate_smallest_route'` and/or `SmallestRouteCapExceeded`.

- [ ] **Step 3: Implement the validator + exception**

Add to `ai_service.py`, immediately above the existing `generate_provisional_map_from_sketch` (before line 693):

```python
SMALLEST_ROUTE_MAX_DRILLABLE_NODES = 4
"""C-prime spec §5.1: ≤4 drillable nodes total (1 first target + ≤3 hints)."""


class SmallestRouteCapExceeded(ValueError):
    """Raised when source-less generation returns a ProvisionalMap exceeding
    the smallest-route cap. Server returns 500 in this case (it's a
    generation-side failure, not a client-input failure)."""


def _validate_smallest_route(pm: ProvisionalMap) -> None:
    """Enforce C-prime spec §5.1 ≤4-node cap.

    Counts drillable nodes on the ProvisionalMap. Raises
    SmallestRouteCapExceeded if the count is 0 or >4.
    """
    # Adjust attribute access to the actual ProvisionalMap field name.
    drillable = list(getattr(pm, "rooms", []) or [])
    n = len(drillable)
    if n == 0:
        raise SmallestRouteCapExceeded(
            "smallest route must have at least one drillable node "
            "(the suggested first target / core thesis)"
        )
    if n > SMALLEST_ROUTE_MAX_DRILLABLE_NODES:
        raise SmallestRouteCapExceeded(
            f"smallest route exceeded cap: {n} drillable nodes "
            f"(max {SMALLEST_ROUTE_MAX_DRILLABLE_NODES})"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_generate_smallest_route.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_service.py tests/test_generate_smallest_route.py
git commit -m "feat(ai): add smallest-route validator with ≤4 drillable-nodes cap"
```

---

## Task 3: `generate_smallest_provisional_map` function + tests

**Files:**
- Modify: `ai_service.py` (add function near line 693, after the validator from Task 2)
- Modify: `tests/test_generate_smallest_route.py` (add a wiring test)

- [ ] **Step 1: Add the wiring test**

Append to `tests/test_generate_smallest_route.py`:

```python
from unittest.mock import MagicMock, patch
from ai_service import generate_smallest_provisional_map


def test_generate_smallest_provisional_map_uses_new_prompt(monkeypatch):
    """Verifies the new function loads the smallest-route prompt, not the
    existing sketch prompt, and routes the generated map through
    _validate_smallest_route."""
    fake_pm = _provisional_map_with_node_count(2)
    fake_result = MagicMock(parsed=fake_pm)

    captured = {}

    class FakeClient:
        def generate_structured(self, request):
            captured["system_prompt"] = request.system_prompt
            captured["task_name"] = request.task_name
            return fake_result

    out = generate_smallest_provisional_map(
        concept="Photosynthesis",
        threshold="plants take in light and somehow make sugar",
        llm=FakeClient(),
    )

    assert out is fake_pm
    # New prompt is loaded, not the from-sketch one
    assert "smallest actionable route" in captured["system_prompt"].lower()
    # Task name is distinct so telemetry can distinguish stages
    assert captured["task_name"] == "smallest_route_from_threshold"


def test_generate_smallest_provisional_map_rejects_oversized(monkeypatch):
    """If the model returns a 5-node map, the wrapper raises."""
    oversized = _provisional_map_with_node_count(5)
    fake_result = MagicMock(parsed=oversized)

    class FakeClient:
        def generate_structured(self, request):
            return fake_result

    with pytest.raises(SmallestRouteCapExceeded):
        generate_smallest_provisional_map(
            concept="X",
            threshold="abc def ghi",
            llm=FakeClient(),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_generate_smallest_route.py -v -k generate_smallest_provisional_map`
Expected: FAIL with `ImportError: cannot import name 'generate_smallest_provisional_map'`.

- [ ] **Step 3: Implement the function**

Add to `ai_service.py`, near the existing `generate_provisional_map_from_sketch` (after the validator from Task 2). Match the existing function's signature shape exactly so the dispatcher swap in Task 4 is mechanical:

```python
GENERATE_SMALLEST_ROUTE_PROMPT_PATH = APP_PROMPTS_DIR / "generate-smallest-route-system-v1.txt"
GENERATE_SMALLEST_ROUTE_PROMPT_VERSION = "v1"
GENERATE_SMALLEST_ROUTE_TEMPERATURE = GENERATE_FROM_SKETCH_TEMPERATURE  # reuse


def generate_smallest_provisional_map(
    concept: str,
    threshold: str,
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    lc_context: list["LCStandard"] | None = None,
    telemetry_context: dict | None = None,
    on_call_complete: Callable[["StructuredLLMResult"], None] | None = None,
) -> ProvisionalMap:
    """Generate a smallest actionable route from {concept, threshold}.

    C-prime spec §5.1: returns a ProvisionalMap with ≤4 drillable nodes
    total (one suggested first target which carries the core thesis,
    plus up to 3 backbone hints). Raises SmallestRouteCapExceeded if the
    model returns more.

    Optional ``lc_context`` is grounding-only, never authoritative.
    """
    from learning_commons import LCStandard  # local import to avoid cycle

    client: LLMClient = llm if llm is not None else build_llm_client(api_key=api_key)

    user_prompt_parts: list[str] = [
        f"<concept>{concept}</concept>",
        f"<threshold>{threshold}</threshold>",
    ]
    if lc_context:
        lc_block_lines = ["<lc_context>"]
        for std in lc_context:
            code = f" [{std.statement_code}]" if std.statement_code else ""
            lc_block_lines.append(f"- {std.jurisdiction}{code}: {std.description}")
        lc_block_lines.append("</lc_context>")
        user_prompt_parts.append("\n".join(lc_block_lines))

    user_prompt = "\n\n".join(user_prompt_parts)

    request = StructuredLLMRequest(
        system_prompt=GENERATE_SMALLEST_ROUTE_PROMPT_PATH.read_text(),
        user_prompt=user_prompt,
        response_schema=ProvisionalMap,
        temperature=GENERATE_SMALLEST_ROUTE_TEMPERATURE,
        task_name="smallest_route_from_threshold",
        prompt_version=GENERATE_SMALLEST_ROUTE_PROMPT_VERSION,
    )
    result = client.generate_structured(request)
    if on_call_complete is not None:
        on_call_complete(result)

    pm: ProvisionalMap = result.parsed  # type: ignore[assignment]
    _validate_smallest_route(pm)
    return pm
```

- [ ] **Step 4: Run all tests**

Run: `pytest tests/test_generate_smallest_route.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_service.py tests/test_generate_smallest_route.py
git commit -m "feat(ai): add generate_smallest_provisional_map for C-prime concept entry"
```

---

## Task 4: Wire dispatch — `from_sketch` calls smallest-route generator

**Files:**
- Modify: `main.py` (the `from_sketch` branch inside `extract()`, around line 480+)
- Create: `tests/test_extract_route_smallest.py`

The existing dispatch already routes source-less concepts to the `from_sketch` path, calls `generate_provisional_map_from_sketch`, and runs LC enrichment. This task swaps the generation call to `generate_smallest_provisional_map`. `_resolve_extract_path` itself is **not modified** — it already enforces `thin_sketch_no_source` (the bypass guard).

- [ ] **Step 1: Read the current `from_sketch` branch**

Run: `sed -n '478,640p' main.py`

Find the line that calls `generate_provisional_map_from_sketch(...)`. That call site is what we replace.

- [ ] **Step 2: Write the failing dispatch integration test**

Create `tests/test_extract_route_smallest.py`:

```python
"""C-prime spec §5.2 acceptance: source-less /api/extract returns a
smallest ProvisionalMap (≤4 nodes), and name-only/source-null bypasses
are still rejected."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_extract_thin_sketch_no_source_still_rejected():
    """The existing thin_sketch_no_source guard is preserved (defense in depth)."""
    r = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "",
        "source": None,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "thin_sketch_no_source"


def test_extract_idk_sketch_no_source_rejected():
    """`idk` is not substantive."""
    r = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "idk",
        "source": None,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "thin_sketch_no_source"


def test_extract_substantive_threshold_returns_smallest_route():
    """Source-less + substantive threshold → smallest ProvisionalMap (≤4)."""
    from ai_service import _validate_smallest_route, SmallestRouteCapExceeded
    from tests.test_generate_smallest_route import _provisional_map_with_node_count

    fake_pm = _provisional_map_with_node_count(3)

    with patch("main.generate_smallest_provisional_map", return_value=fake_pm) as mocked:
        r = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "plants take in light and somehow make sugar through leaves",
            "source": None,
        })

    assert r.status_code == 200
    mocked.assert_called_once()
    # Verify call kwargs match expected signature
    _args, kwargs = mocked.call_args
    assert kwargs.get("concept") == "Photosynthesis" or _args[0] == "Photosynthesis"
```

- [ ] **Step 3: Run test to verify the third test fails (the first two should pass already)**

Run: `pytest tests/test_extract_route_smallest.py -v`
Expected: tests 1 and 2 PASS (existing dispatch already enforces). Test 3 FAILS because `main.py` still calls `generate_provisional_map_from_sketch`, not `generate_smallest_provisional_map`.

- [ ] **Step 4: Update `main.py`'s `from_sketch` branch**

In `main.py` around line 480+, find the line:

```python
        if decision["path"] == "from_sketch":
            ...
            map_obj = generate_provisional_map_from_sketch(
                concept=decision["name"],
                sketch=decision["sketch"],
                lc_context=lc_context,
                ...
            )
```

(The actual variable names and surrounding code may differ; locate via `grep -n "generate_provisional_map_from_sketch" main.py`.)

Replace with:

```python
        if decision["path"] == "from_sketch":
            ...
            map_obj = generate_smallest_provisional_map(
                concept=decision["name"],
                threshold=decision["sketch"],  # `sketch` key in decision is the threshold per C-prime
                lc_context=lc_context,
                ...
            )
```

Also update the import at the top of `main.py`:

```python
# Was:
from ai_service import generate_provisional_map_from_sketch, extract_knowledge_map
# Becomes:
from ai_service import generate_smallest_provisional_map, extract_knowledge_map
```

If `generate_provisional_map_from_sketch` is referenced elsewhere in `main.py` (run `grep -n generate_provisional_map_from_sketch main.py`), update each call site or leave the import for back-compat — but the dispatch in `extract()` MUST call the new function.

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/test_extract_route_smallest.py -v`
Expected: all 3 PASS.

Run: `pytest tests/test_extract_route_source_optional.py tests/test_extract_route.py -v`
Expected: existing tests still PASS (the swap should be transparent to them — they already mock or expect the call shape).

If existing tests fail because they patched `generate_provisional_map_from_sketch` directly, update the patch target to `generate_smallest_provisional_map` in each test.

- [ ] **Step 6: Verify the bypass-rejection acceptance via curl**

Spec acceptance #4: `POST /api/extract` with `{name: "X", source: null, starting_sketch: ""}` returns 422 with `error: "thin_sketch_no_source"`.

Start a local server: `uvicorn main:app --port 8000 --reload`

Then in another terminal:

```bash
curl -i -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"name":"Photosynthesis","starting_sketch":"","source":null}'
```

Expected: HTTP/1.1 422; body contains `"error":"thin_sketch_no_source"`.

(Note: spec §5.2 and the agent brief use `thin_sketch_no_source`, which matches the name wired through telemetry. Use the existing name.)

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_extract_route_smallest.py
git commit -m "feat(extract): route source-less /api/extract through smallest-route generator"
```

---

## Task 5: Extract source panel into reusable module

**Files:**
- Create: `public/js/source-panel.js`
- Modify: `public/js/concept-create.js` (refactor `beginEditSource` at line 601+)

This is a mechanical extraction. The concept-create modal must continue working byte-equivalently after the refactor.

- [ ] **Step 1: Read the current `beginEditSource` implementation**

Run: `sed -n '601,790p' public/js/concept-create.js`

Identify the boundaries: `beginEditSource()` opens at line 601 and closes when its closure ends (~line 790 based on existing greps showing `addBtn` event wiring). Read the entire function block.

- [ ] **Step 2: Create the extracted module**

Create `public/js/source-panel.js`:

```javascript
/**
 * Reusable source-attach panel.
 *
 * Mounts the Text/URL/File tabs (paste/clipboard/file/url handlers)
 * inside any container element. Used by:
 *   - the concept-create modal (existing source chip)
 *   - the loop-entry door (new affordance)
 *
 * The DOM markup, tab-switching, validation, paste/upload/url handlers,
 * and Cancel/Attach buttons are identical to the inline implementation
 * that previously lived inside concept-create.js::beginEditSource.
 *
 * mountSourcePanel(targetEl, opts) -> { teardown: () => void }
 *
 *   targetEl: HTMLElement to mount the panel into. Existing innerHTML is
 *             replaced (matching the modal's previous behavior).
 *
 *   opts.onAttach({type, text?, url?, filename?}): called when the
 *     learner clicks the Attach button with valid input.
 *   opts.onCancel(): called when the learner clicks Cancel.
 *
 *   teardown(): removes event listeners. Optional cleanup; the modal
 *     today does not call this (it relies on the chip being
 *     re-rendered).
 */
export function mountSourcePanel(targetEl, opts = {}) {
  const onAttach = opts.onAttach || (() => {});
  const onCancel = opts.onCancel || (() => {});

  // [PASTE HERE — verbatim — the markup and handler logic from
  // concept-create.js::beginEditSource. Replace `valueEl.innerHTML = ...`
  // with `targetEl.innerHTML = ...`. Replace any closure-captured
  // references to `sourceChip` / `valueEl` / etc. with `targetEl`.
  // The handler that previously called inline persistence is replaced
  // with `onAttach({type, text, url, filename})`. The cancel handler
  // calls `onCancel()`.]
  // ...

  return {
    teardown() {
      // Remove any listeners attached above. For the v1 cut, modal-side
      // teardown is a no-op (the chip is replaced wholesale). The door
      // surface uses teardown to collapse the panel cleanly.
    },
  };
}
```

The actual content of the module is the existing `beginEditSource` body, with three substitutions:
1. `sourceChip.querySelector('[data-role="source-value"]')` → `targetEl`
2. The persistence call (e.g., `setSourceMetadata({...})` or whatever the existing modal does on Attach) → `onAttach({type, ...payload})`
3. The cancel/restore call → `onCancel()`

- [ ] **Step 3: Refactor `concept-create.js::beginEditSource` to call the module**

In `public/js/concept-create.js`, replace the `beginEditSource` body (line 601+) with:

```javascript
import { mountSourcePanel } from "./source-panel.js";

function beginEditSource() {
  const sourceChip = container.querySelector('[data-chip="source"]');
  if (!sourceChip) return;
  const valueEl = sourceChip.querySelector('[data-role="source-value"]');

  mountSourcePanel(valueEl, {
    onAttach({ type, text, url, filename }) {
      // Mirror the previous inline persistence path. Whatever the old
      // implementation did on Attach (setSourceMetadata, updating the
      // chip header to "replace" mode, etc.) goes here verbatim.
      // [PORT THE EXISTING ATTACH BEHAVIOR HERE.]
    },
    onCancel() {
      // Restore the chip to its prior state. [PORT THE EXISTING CANCEL
      // BEHAVIOR HERE.]
    },
  });
}
```

If `concept-create.js` is not currently an ES module, add a `<script type="module">` reference in `index.html` for both files OR leave both as classic scripts and expose `mountSourcePanel` via `window.SourcePanel` instead of `export`. Inspect the existing `<script>` tags in `index.html` to match the project's module convention.

- [ ] **Step 4: Manual smoke — modal source flow still works (acceptance criterion #5)**

Start the dev server:

```bash
bash scripts/dev-host.sh
# or whatever the project's dev launcher is — see scripts/ for the canonical entrypoint
```

Open the app in a browser. Click the "+" or "New concept" button to open the existing concept-create modal. Walk all three source paths:

1. **Text:** click `+ add source material` chip → Text tab → paste a few sentences → Attach. Verify the chip reads e.g. `Source: 240 chars pasted` and `Build` enables.
2. **URL:** repeat with a public URL. Verify URL validation feedback appears, the Attach button enables when the URL is well-formed, and Attach triggers the existing `/api/extract-url` two-step.
3. **File:** drop a small `.txt` or `.md` file. Verify the chip reads `Source: filename · N chars` and Attach completes.

If any of the three breaks, the extraction is wrong. Re-read the original `beginEditSource` and reconcile.

- [ ] **Step 5: Commit**

```bash
git add public/js/source-panel.js public/js/concept-create.js
git commit -m "refactor(source-panel): extract reusable mountSourcePanel from concept-create.js"
```

---

## Task 6: Strip Ignition view to door + arrow-only CTA + sessionStorage shell

**Files:**
- Modify: `public/index.html` (lines 279–328 — the `ignition-view` section)
- Modify: `public/css/components.css` (remove sketch-field styles)
- Modify: `public/js/app.js` (`runHeroAction` or equivalent submit handler)

- [ ] **Step 1: Locate the existing handler**

Run: `grep -n "runHeroAction\|hero-single-input" public/js/app.js | head`

Open the function body. Identify where it reads the concept input and the sketch input, what payload it constructs, and where it dispatches the source-attached vs source-less paths today.

- [ ] **Step 2: Rewrite the `<section id="ignition-view">` DOM in `index.html`**

Replace lines 279–328 of `public/index.html` with:

```html
<!-- Ignition View: door for new concept entry (C-prime) -->
<section id="ignition-view" class="primary-view ignition-view" aria-labelledby="ignition-title">
  <div class="intro-particles" aria-hidden="true">
    <canvas id="intro-particle-canvas"></canvas>
  </div>
  <div class="ignition-view__inner">
    <h1 class="ignition-title" id="ignition-title">What do you want to understand?</h1>

    <!-- Library-cap gate. Hidden by default; shown by renderIgnitionGate() at board capacity. -->
    <div class="ignition-cap-gate" id="ignition-cap-gate" hidden>
      <p class="ignition-cap-gate__message">The board holds nine concepts. Retire one to start another.</p>
      <button class="ignition-cap-gate__cta" type="button" onclick="App.showLibrary()">Open Library</button>
    </div>

    <!-- Door composer. -->
    <form class="hero-single-input" id="hero-single-input" onsubmit="return App.runHeroAction(event)" autocomplete="off">
      <label class="hero-threshold-field" for="hero-single-input-field">
        <span class="hero-threshold-field__label sr-only">Concept</span>
        <textarea class="hero-single-input__field hero-single-input__field--concept"
                  id="hero-single-input-field"
                  rows="2"
                  maxlength="200"
                  placeholder="e.g. photosynthesis, the Krebs cycle, recursion in Python…"
                  aria-label="What do you want to understand?"></textarea>
      </label>

      <button type="button" class="hero-source-attach" id="hero-source-attach"
              aria-expanded="false" aria-controls="hero-source-panel">
        + add source material
      </button>
      <div class="hero-source-panel" id="hero-source-panel" hidden></div>

      <div class="hero-single-input__row">
        <button type="submit" class="hero-single-input__submit" id="hero-door-submit" disabled
                aria-label="Continue">
          <span class="sr-only">Continue</span>
          <svg class="hero-single-input__submit-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h13"></path>
            <path d="m13 6 6 6-6 6"></path>
          </svg>
        </button>
      </div>
    </form>
  </div>
</section>
```

What changed:
- Removed `ignition-eyebrow`.
- Removed the `hero-threshold-field--sketch` field.
- Removed `hero-threshold-validation`.
- Door submit button has `aria-label="Continue"` and a visually-hidden `<span class="sr-only">Continue</span>` (acceptance #14). The icon is `aria-hidden`.
- Added `<button class="hero-source-attach">` and an empty `<div class="hero-source-panel">` for source attach mounting.

- [ ] **Step 3: Remove the deprecated CSS rules**

Open `public/css/components.css`. Remove or stub out:

- `.hero-threshold-field--sketch` and any descendant rules
- `.hero-threshold-validation`
- `.ignition-eyebrow`
- `.hero-voice-line`
- `.hero-guidance` (only if it isn't used by other surfaces; grep first: `grep -rn "hero-guidance" public/`)

Add styles for the new elements:

```css
/* Source-attach affordance on the door */
.hero-source-attach {
  background: transparent;
  border: 1px dashed var(--color-border-muted, #c8c2b9);
  color: var(--color-fg-muted, #6b6358);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  margin-top: 12px;
}
.hero-source-attach[aria-expanded="true"] { background: var(--color-bg-soft, #f5f1eb); }
.hero-source-panel { margin-top: 12px; }
.hero-source-panel[hidden] { display: none; }

/* sr-only utility (if not already defined elsewhere) */
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0);
  white-space: nowrap; border: 0;
}
```

Run `grep -n "sr-only" public/css/*.css` first — if the utility already exists, skip the `.sr-only` block.

- [ ] **Step 4: Rewrite `runHeroAction` in `public/js/app.js`**

Find `runHeroAction` (or whatever the door submit handler is named — see Step 1). Replace its body with:

```javascript
async function runHeroAction(event) {
  event.preventDefault();
  const conceptInput = document.getElementById("hero-single-input-field");
  const name = (conceptInput?.value || "").trim();
  if (!name) return false;

  const sourcePayload = App._pendingDoorSource || null;

  if (sourcePayload) {
    // Source-attached: existing /api/extract path (or two-step for URL)
    return App.submitConceptCreateFromDoor({ name, source: sourcePayload });
  }

  // Source-less: write pending shell to sessionStorage, navigate to launch pad
  try {
    sessionStorage.setItem(
      "socratink:pendingShell",
      JSON.stringify({ name, ts: Date.now() }),
    );
  } catch (err) {
    // sessionStorage failed (storage disabled, quota, etc). Surface, don't proceed.
    console.error("socratink: sessionStorage unavailable", err);
    alert("Your browser has storage disabled. Please enable session storage to continue.");
    return false;
  }
  App.showLaunchPad();
  return false;
}

// Source-attach affordance toggle (door)
function bindDoorSourceAttach() {
  const btn = document.getElementById("hero-source-attach");
  const panel = document.getElementById("hero-source-panel");
  if (!btn || !panel) return;

  btn.addEventListener("click", () => {
    const isOpen = btn.getAttribute("aria-expanded") === "true";
    if (isOpen) {
      panel.hidden = true;
      panel.innerHTML = "";
      btn.setAttribute("aria-expanded", "false");
      btn.textContent = "+ add source material";
      App._pendingDoorSource = null;
      updateDoorSubmitState();
    } else {
      panel.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      // Lazy-load the source panel module so the modal path keeps working
      // even if this fails.
      import("./source-panel.js").then(({ mountSourcePanel }) => {
        mountSourcePanel(panel, {
          onAttach(payload) {
            App._pendingDoorSource = payload;
            btn.textContent = `Source: ${describeSource(payload)} (replace)`;
            updateDoorSubmitState();
          },
          onCancel() {
            panel.hidden = true;
            panel.innerHTML = "";
            btn.setAttribute("aria-expanded", "false");
            btn.textContent = "+ add source material";
            App._pendingDoorSource = null;
            updateDoorSubmitState();
          },
        });
      });
    }
  });
}

function describeSource(payload) {
  if (!payload) return "";
  if (payload.type === "text") return `${(payload.text || "").length} chars pasted`;
  if (payload.type === "url") return payload.url || "URL";
  if (payload.type === "file") return `${payload.filename || "file"} · ${(payload.text || "").length} chars`;
  return payload.type;
}

function updateDoorSubmitState() {
  const conceptInput = document.getElementById("hero-single-input-field");
  const submitBtn = document.getElementById("hero-door-submit");
  if (!conceptInput || !submitBtn) return;
  submitBtn.disabled = !(conceptInput.value || "").trim();
}

// Wire up
document.addEventListener("DOMContentLoaded", () => {
  bindDoorSourceAttach();
  const conceptInput = document.getElementById("hero-single-input-field");
  if (conceptInput) {
    conceptInput.addEventListener("input", updateDoorSubmitState);
  }
});

// Expose on App namespace
App.runHeroAction = runHeroAction;
```

Adjust the import style (`import(...)` dynamic vs `import {} from`) to match existing app.js conventions. If app.js is a non-module classic script, replace `import("./source-panel.js").then(...)` with the equivalent pattern (e.g., a global `window.SourcePanel.mount(...)`).

`App.submitConceptCreateFromDoor` is the existing source-attached path used today — locate the analogous existing call and reuse it. If today's `runHeroAction` already implements the source-attached branch, leave that branch and only modify the source-less branch.

- [ ] **Step 5: Manual browser smoke — door**

Start dev server. Open the app, navigate to the door (New Entry).

1. Type "Photosynthesis" in the concept field. Submit button enables.
2. Press Tab to move focus to the submit button. Read the accessible name with VoiceOver (Cmd+F5) or Chrome DevTools "Accessibility" pane — it should say "Continue" (or "Continue to launch pad" — whichever you wired). NOT empty.
3. Click submit. Verify in DevTools → Application → Session Storage that `socratink:pendingShell` is set with `{name: "Photosynthesis", ts: <recent>}`.
4. Click `+ add source material`. The panel expands. Paste text, click Attach. The button text reads `Source: <N> chars pasted (replace)`. Now submit — should NOT navigate to launch pad; should follow the source-attached path.

If any step fails, fix before continuing. Console errors are not acceptable.

- [ ] **Step 6: Commit**

```bash
git add public/index.html public/css/components.css public/js/app.js
git commit -m "feat(door): strip Ignition view to door-only with sessionStorage pending shell"
```

---

## Task 7: Launch-pad surface

**Files:**
- Modify: `public/index.html` (add `<section class="launch-pad-view">`)
- Modify: `public/css/components.css` (launch-pad styles)
- Create: `public/js/launch-pad.js`
- Modify: `public/js/app.js` (`App.showLaunchPad`, navigation wiring)

- [ ] **Step 1: Add the new view section to `index.html`**

Insert immediately after the `<section id="ignition-view">` closing tag:

```html
<!-- Launch Pad: threshold capture for source-less concepts (C-prime) -->
<section id="launch-pad-view" class="primary-view launch-pad-view" aria-labelledby="launch-pad-title" hidden>
  <div class="launch-pad-view__inner">
    <p class="launch-pad-concept-name" id="launch-pad-concept-name"></p>
    <h1 class="launch-pad-title" id="launch-pad-title">What do you already think is inside this concept?</h1>
    <p class="launch-pad-helper">Name the parts, guesses, examples, or confusions you have.</p>
    <form class="launch-pad-form" id="launch-pad-form" onsubmit="return App.runLaunchPadAction(event)" autocomplete="off">
      <label class="launch-pad-field" for="launch-pad-input">
        <span class="launch-pad-field__label sr-only">Your starting model</span>
        <textarea class="launch-pad-input"
                  id="launch-pad-input"
                  rows="5"
                  maxlength="1200"
                  aria-describedby="launch-pad-validation"
                  aria-label="Your starting model"></textarea>
      </label>
      <p class="launch-pad-validation" id="launch-pad-validation" aria-live="polite"></p>
      <div class="launch-pad-form__row">
        <button type="submit" class="launch-pad-submit" id="launch-pad-submit" disabled>
          <span>Build my map</span>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h13"></path><path d="m13 6 6 6-6 6"></path>
          </svg>
        </button>
      </div>
      <p class="launch-pad-footer">Study content stays locked until the cold attempt.</p>
    </form>
  </div>
</section>
```

- [ ] **Step 2: Add launch-pad CSS**

Append to `public/css/components.css`:

```css
.launch-pad-view {
  /* Match ignition-view register: vertically centered, calm */
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
}
.launch-pad-view:not([hidden]) { display: flex; }
.launch-pad-view__inner { max-width: 640px; width: 100%; }
.launch-pad-concept-name {
  font-size: 14px;
  color: var(--color-fg-muted, #6b6358);
  margin: 0 0 24px;
  text-align: center;
}
.launch-pad-title {
  font-size: 28px;
  margin: 0 0 12px;
  text-align: center;
  font-weight: 500;
}
.launch-pad-helper {
  font-size: 14px;
  color: var(--color-fg-muted, #6b6358);
  margin: 0 0 24px;
  text-align: center;
}
.launch-pad-input {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 1px solid var(--color-border, #d8d3ca);
  border-radius: 6px;
  resize: vertical;
  font-family: inherit;
  font-size: 16px;
}
.launch-pad-validation {
  font-size: 13px;
  color: var(--color-fg-muted, #6b6358);
  margin: 8px 0 0;
  min-height: 18px;
}
.launch-pad-form__row { display: flex; justify-content: flex-end; margin-top: 16px; }
.launch-pad-submit {
  background: var(--color-accent-violet, #6b4ee0);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.launch-pad-submit[disabled] { opacity: 0.4; cursor: not-allowed; }
.launch-pad-submit svg {
  width: 16px; height: 16px;
  fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}
.launch-pad-footer {
  font-size: 12px;
  color: var(--color-fg-muted, #6b6358);
  margin: 24px 0 0;
  text-align: center;
}
```

Adjust palette tokens to whatever variables the project actually uses — run `grep -n "color-accent-violet\|--color-accent" public/css/*.css` to find the canonical name.

- [ ] **Step 3: Create the launch-pad module**

Create `public/js/launch-pad.js`:

```javascript
/**
 * Launch pad for source-less concept creation (C-prime spec §3.2).
 *
 * Reads the pending shell from sessionStorage, captures the learner's
 * launch attempt (threshold), POSTs to /api/extract, persists the
 * returned ProvisionalMap through the existing client-side concept
 * store, and only then clears the pending shell.
 */

const PENDING_SHELL_KEY = "socratink:pendingShell";
const PENDING_SHELL_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24h

const SUBSTANTIVE_MIN_WORDS = 3;
const IDK_PATTERN = /^(\?+|…+|idk|i\s*don'?t\s*know|no\s*idea)$/i;

function isSubstantiveThreshold(text) {
  const t = (text || "").trim();
  if (!t) return false;
  if (IDK_PATTERN.test(t)) return false;
  return t.split(/\s+/).filter(Boolean).length >= SUBSTANTIVE_MIN_WORDS;
}

function readPendingShell() {
  try {
    const raw = sessionStorage.getItem(PENDING_SHELL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.name !== "string" || typeof parsed.ts !== "number") return null;
    if (Date.now() - parsed.ts > PENDING_SHELL_MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
}

function clearPendingShell() {
  try { sessionStorage.removeItem(PENDING_SHELL_KEY); } catch {}
}

export function showLaunchPad(App) {
  // Hide the ignition view, show the launch pad
  document.getElementById("ignition-view")?.setAttribute("hidden", "");
  const view = document.getElementById("launch-pad-view");
  if (!view) return;
  view.removeAttribute("hidden");

  const shell = readPendingShell();
  if (!shell) {
    // No pending shell or expired — bounce back to door
    App.telemetry?.("concept_create.launch_pad.evaporated", { age_ms: 0 });
    view.setAttribute("hidden", "");
    document.getElementById("ignition-view")?.removeAttribute("hidden");
    return;
  }

  // Hydrate concept name
  const nameEl = document.getElementById("launch-pad-concept-name");
  if (nameEl) nameEl.textContent = shell.name;

  App.telemetry?.("concept_create.launch_pad.entered", {
    from_localstorage_age_ms: Date.now() - shell.ts,
  });

  // Wire input → submit-state, validation footer
  const input = document.getElementById("launch-pad-input");
  const submit = document.getElementById("launch-pad-submit");
  const validation = document.getElementById("launch-pad-validation");
  if (!input || !submit || !validation) return;

  function update() {
    const ok = isSubstantiveThreshold(input.value);
    submit.disabled = !ok;
    validation.textContent = !ok && (input.value || "").trim()
      ? "A few words about how you think it works will give socratink something to draft from."
      : "";
  }
  input.addEventListener("input", update);
  update();
  input.focus();
}

export async function runLaunchPadAction(event, App) {
  event.preventDefault();
  const shell = readPendingShell();
  if (!shell) return false;
  const input = document.getElementById("launch-pad-input");
  const validation = document.getElementById("launch-pad-validation");
  const threshold = (input?.value || "").trim();
  if (!isSubstantiveThreshold(threshold)) return false;

  App.telemetry?.("concept_create.launch_pad.submit", {
    threshold_len: threshold.length,
    build_blocked: false,
  });

  let map;
  try {
    map = await App.submitConceptCreate({
      name: shell.name,
      startingSketch: threshold,
      source: null,
    });
  } catch (err) {
    // 422 from the server-side bypass guard surfaces here. Render the
    // strategy-framed footer and let the learner retry.
    if (err && err.status === 422 && err.body?.error === "thin_sketch_no_source") {
      validation.textContent = err.body.message
        || "A few words about how you think it works will give socratink something to draft from.";
      App.telemetry?.("concept_create.launch_pad.submit", {
        threshold_len: threshold.length,
        build_blocked: true,
      });
      return false;
    }
    // Any other failure: keep the pending shell so the learner can retry.
    console.error("launch_pad submit failed", err);
    validation.textContent = "Something went wrong. Try again.";
    return false;
  }

  // Persist client-side. The concept store path mirrors what the
  // source-attached `/api/extract` flow does today on success.
  try {
    await App.persistCreatedConcept(map);
  } catch (err) {
    console.error("launch_pad persistence failed", err);
    validation.textContent = "Could not save the concept locally. Try again.";
    return false;
  }

  // Only after persistence succeeds, clear the shell and navigate.
  clearPendingShell();
  App.showGraphView(map, { fromLaunchPad: true });
  return false;
}
```

`App.submitConceptCreate`, `App.persistCreatedConcept`, `App.showGraphView`, and `App.telemetry` are existing or to-be-existing namespace functions. Find the today equivalents (probably `submitConceptCreate` already in `ai_service.js`; `persistCreatedConcept` is whatever the existing modal does on successful response; `showGraphView` is the existing navigation).

- [ ] **Step 4: Wire `App.showLaunchPad` and `App.runLaunchPadAction` in `app.js`**

Add to `public/js/app.js`:

```javascript
import { showLaunchPad, runLaunchPadAction } from "./launch-pad.js";

App.showLaunchPad = () => showLaunchPad(App);
App.runLaunchPadAction = (event) => runLaunchPadAction(event, App);
```

(Or the classic-script equivalent — match the project's module style.)

- [ ] **Step 5: Manual browser smoke — full source-less happy path (acceptance #1)**

Start dev server. Walk:

1. At the door: type "Photosynthesis", click submit.
2. Land on launch pad: concept name reads "Photosynthesis"; input is focused.
3. Type "idk". Submit stays disabled. Validation reads the strategy-framed line.
4. Replace with "plants take in light and somehow make sugar through leaves". Submit enables.
5. Click `Build my map`. Network tab shows `POST /api/extract` with `{name, starting_sketch, source: null}` returning 200 + a ProvisionalMap. Application → Session Storage shows `socratink:pendingShell` is **gone after** the POST returns.
6. Land on the graph view. Verify the smallest route renders: the suggested first target node is visible and ≤3 backbone hints (or fewer).
7. Reload the page. Land back on the home/desk. The new concept should appear in the library tile listing (today's behavior, unchanged).

If sessionStorage is cleared **before** the POST returns and persistence then fails, the learner loses the shell — that's the bug Task 7 step 3's `clearPendingShell()` ordering prevents. Verify the order by setting a breakpoint at `clearPendingShell()` and confirming the network request resolved successfully first.

- [ ] **Step 6: Acceptance #6 verification — sessionStorage hydration**

Open DevTools → Application → Session Storage. Submit door with no source → key appears. Reload the launch pad URL directly without going through the door (e.g., delete the key in DevTools then refresh the launch pad section): the launch pad must bounce to the door.

- [ ] **Step 7: Commit**

```bash
git add public/index.html public/css/components.css public/js/launch-pad.js public/js/app.js
git commit -m "feat(launch-pad): add C-prime threshold capture surface for source-less concepts"
```

---

## Task 8: Home/desk vocabulary update + skeleton-line on fresh route view

**Files:**
- Modify: `public/index.html` (lines 198–225 — the home/desk hero section)
- Modify: `public/js/app.js` or wherever home/desk text is rendered (search for "draft path")
- Modify: `public/css/components.css` (skeleton-line style)
- Modify: wherever the graph view renders post-launch (locate via `grep -n "showGraphView\|fromLaunchPad" public/js/`)

- [ ] **Step 1: Find every hard-coded "draft path" string**

Run: `grep -rn "draft path\|draft paths\|Draft path\|Draft Path\|Begin at New Entry" public/ docs/`

Each match in `public/` is a candidate to update. Matches in `docs/` are not in scope (those are spec/handoff files, not the app).

- [ ] **Step 2: Update `public/index.html` lines 198–225**

In the hero block (around line 208), replace:

```html
<div class="hero-state-chip" id="hero-state-chip" data-state="empty">no map yet</div>
```

with:

```html
<div class="hero-state-chip" id="hero-state-chip" data-state="empty">no concepts yet</div>
```

Replace:

```html
<h1 class="hero-title" id="title">Your draft paths.</h1>
<p class="desc hero-guidance" id="desc" aria-live="polite">Pick a tile to open an entry, or start a new draft path at New Entry.</p>
<p class="hero-voice-line">The map stays honest because evidence comes from your reconstruction.</p>
```

with:

```html
<h1 class="hero-title" id="title">Your concepts.</h1>
<p class="desc hero-guidance" id="desc" aria-live="polite">Pick a tile to enter, or start a new concept.</p>
```

(Voice line removed entirely.)

Replace:

```html
<button class="hero-primary-action" type="button" onclick="App.showIgnition()">
  <span class="hero-primary-action__label">Begin at New Entry</span>
```

with:

```html
<button class="hero-primary-action" type="button" onclick="App.showIgnition()">
  <span class="hero-primary-action__label">New concept</span>
```

- [ ] **Step 3: Update any JS that overwrites these texts at runtime**

Search for `renderHero\|hero-title\|draft path` in `public/js/`. If `renderHero()` (or similar) sets `title.textContent = "Your draft paths."` for non-empty states, update that string too. The empty-state text from index.html is the default; non-empty states may be set in JS.

- [ ] **Step 4: Add the skeleton-line on fresh route view**

Find where the graph view renders after a successful concept create. Search:

```bash
grep -n "showGraphView\|graph-view\|map-view" public/js/app.js public/js/dom.js
```

In the chosen location, add a small inline element that appears only when `fromLaunchPad: true` was passed:

```javascript
function renderSkeletonLineIfFresh(opts) {
  const banner = document.getElementById("graph-skeleton-line");
  if (!banner) return;
  if (opts && opts.fromLaunchPad) {
    banner.textContent = "This is the skeleton. It will grow as you reconstruct.";
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
}
```

And in `index.html`, near the graph/map view container, add:

```html
<p class="graph-skeleton-line" id="graph-skeleton-line" hidden></p>
```

CSS in `components.css`:

```css
.graph-skeleton-line {
  font-size: 13px;
  color: var(--color-fg-muted, #6b6358);
  text-align: center;
  margin: 12px 0;
  font-style: italic;
}
.graph-skeleton-line[hidden] { display: none; }
```

- [ ] **Step 5: Acceptance #9 verification — no "draft path" remains**

Run: `grep -rn "draft path\|draft paths" public/`
Expected: empty (or only matches in JS comments / non-user-facing identifiers, which is OK).

If any user-facing string remains, fix it.

- [ ] **Step 6: Manual browser smoke — vocabulary + skeleton line**

Reload the home/desk view: title reads "Your concepts.", state chip reads "no concepts yet" (when empty), CTA reads "New concept".

Walk the source-less happy path again. On landing in the graph view, the line "This is the skeleton. It will grow as you reconstruct." should appear above (or near) the graph. Reload the same concept later: the skeleton line should be gone (only shows on `fromLaunchPad`).

- [ ] **Step 7: Commit**

```bash
git add public/index.html public/css/components.css public/js/app.js public/js/dom.js
git commit -m "feat(home): replace draft-path vocabulary with concepts; add fresh-route skeleton line"
```

(Adjust the `git add` list to whichever files actually changed in this task.)

---

## Task 9: Bindings docs

**Files:**
- Modify: `DESIGN.md` (Screen 1 reference)
- Modify: `UBIQUITOUS_LANGUAGE.md`

- [ ] **Step 1: Update DESIGN.md §3 Screen 1**

Run: `grep -n "Screen 1\|threshold\|Concept Threshold" DESIGN.md | head`

Find the Screen 1 section. Replace the description of the threshold-as-a-form with a note pointing to the new launch-pad surface:

```markdown
### Screen 1 — Door + Launch Pad (C-prime, 2026-05-07)

The door captures only the concept name (and optional source attach).
Source-less concepts pass through a **launch pad** that captures the
learner's threshold (rough whole-concept model) before any AI generation
runs. See `docs/superpowers/specs/2026-05-07-progressive-route-materialization-design.md`.

The launch pad replaces the previous in-form "Starting sketch" textarea.
The threshold is no longer a field on the door; it is a dedicated
post-commit surface. This change preserves the learner-seeded route
contract: no graph or thesis is generated from the concept name alone.
```

- [ ] **Step 2: Update UBIQUITOUS_LANGUAGE.md**

Run: `grep -n "starting sketch\|threshold" UBIQUITOUS_LANGUAGE.md | head`

Add new terms, alphabetically placed:

- `launch attempt` — the learner's threshold submission on the launch pad. Captures the rough whole-concept model. Mutates no node state. Seeds the smallest-route generation.
- `launch pad` — the post-door surface where the learner enters the launch attempt for a source-less concept. New in C-prime (2026-05-07).
- `pending shell` — an in-flight concept name committed at the door but not yet built. Lives only in `sessionStorage`. Evaporates on tab close.
- `smallest actionable route` — a ProvisionalMap with ≤4 drillable nodes (1 suggested first target carrying the core thesis + ≤3 backbone hints). The output of source-less generation in C-prime.

Mark `starting sketch` as deprecated (or note that it has been replaced by `launch attempt` / `threshold`).

- [ ] **Step 3: Commit**

```bash
git add DESIGN.md UBIQUITOUS_LANGUAGE.md
git commit -m "docs(bindings): update DESIGN.md Screen 1 + UBIQUITOUS_LANGUAGE for C-prime"
```

---

## Task 10: Final acceptance — smoke, a11y, screenshots

This task is verification, not new code. Skip code blocks; check each acceptance criterion.

- [ ] **Step 1: Run qa-smoke against a deploy preview (acceptance #11)**

Run: `bash scripts/qa-smoke.sh`
Expected: PASS.

If qa-smoke is configured to run against a deploy preview rather than locally, push the dev branch and trigger the appropriate CI/preview workflow.

- [ ] **Step 2: Browser smoke — three happy paths (acceptance #12)**

With the dev server running:

1. Source-less: door → launch pad → graph (covered in Task 7 Step 5).
2. Source-attached text: door → `+ add source material` → Text tab → paste → Attach → submit → graph (no launch pad). Verify the existing extract path runs.
3. Source-attached URL: door → `+ add source material` → URL tab → enter a public URL → Attach. Verify `/api/extract-url` is called first, then `/api/extract` with the materialized text. Land on graph (no launch pad).

In each path, verify:
- No console errors.
- No regression on adjacent screens (graph view renders, library opens, settings opens).

- [ ] **Step 3: Bypass rejection via curl (acceptance #4)**

Already covered in Task 4 Step 6. Re-run if needed:

```bash
curl -i -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"name":"X","starting_sketch":"","source":null}'
```

Expected: 422 with `error: thin_sketch_no_source`.

- [ ] **Step 4: A11y check — door submit button (acceptance #14)**

In Chrome DevTools:

1. Open the door. Open DevTools → Elements. Click the submit button.
2. Switch to the Accessibility pane (next to Computed). Verify:
   - "Name" is non-empty (e.g., "Continue").
   - "Role" is "button".
3. Run Lighthouse → Accessibility audit on the door surface. Expected: no failures on WCAG 4.1.2 ("Name, Role, Value").

If the button shows an empty accessible name, fix the `aria-label` and visually-hidden span in Task 6 Step 2 and re-run.

- [ ] **Step 5: Visual smoke — screenshots (acceptance #13)**

Capture screenshots in dark mode AND light mode of:

- Door at rest.
- Door with source panel expanded.
- Launch pad with empty input.
- Launch pad with substantive threshold typed (submit enabled).
- Launch pad with thin/idk threshold (submit disabled, validation visible).
- Graph view post-launch with the "skeleton" framing line visible.

Attach all screenshots to the PR description.

- [ ] **Step 6: Final cleanup**

Run: `git status` — should be clean.
Run: `git log --oneline origin/main..HEAD` — review the commit list. Confirm the sequence reads cleanly.

- [ ] **Step 7: Open a PR (or merge to dev per project workflow)**

The user's stated workflow: commit straight to dev, PR only for dev → main. Per the user's memory, no feature branch is needed. If the work is already on `dev`, the commits should be visible on the remote after a `git push`.

Run:

```bash
git push origin dev
```

If the project has a no-mistakes CI gate (`feedback_no_mistakes_integration.md` indicates one is active), pushing to the no-mistakes remote may trigger an automated review:

```bash
git push no-mistakes dev
```

Per the user's instruction at the start of this work, this push is not authorized without explicit user confirmation.

---

## Self-Review

**Spec coverage:**
- §3.1 door — Task 6 ✓
- §3.2 launch pad — Task 7 ✓
- §3.3 cold attempt unchanged — N/A (no work)
- §4.1 no creation_phase column — N/A (we deliberately don't add it)
- §4.2 sessionStorage shell — Tasks 6 & 7 ✓
- §4.3 home/desk no shell tiles — N/A (today's behavior unchanged)
- §4.4 vocabulary — Task 8 ✓
- §5.1 generation function + cap — Tasks 1, 2, 3 ✓
- §5.2 dispatch + bypass — Task 4 ✓
- §5.3 extract-url unchanged — N/A
- §5.4 no new endpoints — N/A
- §5.5 telemetry — partial (telemetry events fire from launch-pad.js Steps 3–5; existing build_blocked events in main.py cover the rejection telemetry. Spec's `bypass_rejected` event is covered by existing `build_blocked` per Task 4 Step 6 note; if a separate event is required by spec, add a Task 9-bis to wire it. For v1, existing events are sufficient.)
- §6.1 frontend files — Tasks 5–8 ✓
- §6.2 source panel extraction — Task 5 ✓
- §6.3 voice-line removal — Task 6 ✓
- §7 acceptance criteria 1–14 — Task 10 ✓
- §8 out-of-scope — no tasks needed (deliberate omissions)
- §9 implementation sequencing — followed
- §10 risks — no tasks (risk-table is informational)

**Placeholder scan:** several places intentionally leave engineer judgment ("locate the analogous existing call", "match the project's module style", etc.) because they depend on existing code shapes the engineer must read. These are bounded by an explicit "verify with grep" step. No "TODO" or "implement later" markers.

**Type consistency:** `mountSourcePanel(targetEl, opts)` signature consistent across Tasks 5 and 6. `submitConceptCreate({name, startingSketch, source})` matches existing `ai_service.js` signature. `App.showLaunchPad`, `App.runLaunchPadAction`, `App.persistCreatedConcept`, `App.showGraphView` are namespace functions used consistently across Tasks 6, 7, 8.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-07-progressive-route-materialization.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — tasks executed in this session with checkpoints for review.

Which approach?
