# Internal Tasting Harness

Purpose: define a one-click internal workflow for rapidly calibrating extraction, drill routing, and answer-quality behavior without contaminating the learner-facing product.

This is a dev and product-calibration tool.
It is not a learner feature.

## Steelman

The strongest version of this request is not "make testing easier."
It is:

- make taste evaluation repeatable
- reduce setup friction between extraction and drill
- let the team compare concept shape, drill quality, and response handling on the same fixture over time
- shorten the loop between prompt changes and felt UX judgment

If this loop stays manual, the team will under-sample important seams because setup cost is too high.
That creates false confidence.

## Non-Negotiable Guardrails

- The graph must remain truthful.
- Generation Before Recognition must remain intact for learner-facing UX.
- Fixture runs must be clearly separated from real learner runs in telemetry.
- Canned answers must not be confused with real user behavior.
- The harness must be visibly internal/dev-only.

## MVP Scope

Build this first:

1. A hidden dev-only "Run Fixture" control.
2. A repo-owned fixture file containing:
   - source text blob
   - fixture title
   - preferred start node id
   - optional scripted answer bank
3. One-click flow:
   - inject source text
   - call extraction
   - create concept
   - open graph view
   - auto-start drill on the configured node
4. A side panel showing copy/paste answer variants for that fixture.
5. Fixture telemetry tags so these runs can be filtered out from real usage.

This is enough to make the loop feel like "boop, test, taste, compare."

## Current Terminal Entry Point

The current MVP harness can be run from the repo root in the terminal:

```bash
python3 scripts/run_tasting_fixture.py action-potential-core
```

Useful variants:

```bash
python3 scripts/run_tasting_fixture.py --list
python3 scripts/run_tasting_fixture.py action-potential-core --sequence explicit_unknown,shallow_attempt,solid
python3 scripts/run_tasting_fixture.py action-potential-core --node core-thesis
```

This runner is sandboxed and ephemeral.
It uses the real extraction and drill pipeline, but it does not persist learner-facing graph state.

## Recommended Fixture Shape

Store fixtures in a repo-owned JSON file, for example under `public/data/taste-fixtures/`.

Suggested shape:

```json
{
  "id": "action-potential-core",
  "title": "Action Potential Core Thesis",
  "source_text": "Full predefined source blob here",
  "preferred_start_node_id": "core-thesis",
  "notes": "Use for help-vs-attempt calibration",
  "scripted_answers": [
    {
      "label": "Explicit Unknown",
      "input": "I don't know.",
      "expected_answer_mode": "help_request",
      "expected_routing": "SCAFFOLD"
    },
    {
      "label": "Shallow Attempt",
      "input": "An action potential is the signal neurons use to communicate.",
      "expected_answer_mode": "attempt",
      "expected_classification": "shallow"
    }
  ]
}
```

## Suggested Interaction Model

The best MVP interaction is not full autoplay.

Use:

- `Run Fixture`
- `Start Drill`
- answer chips or copy buttons for each scripted answer

Why:

- you still feel the tutor output turn by turn
- you still judge wording quality
- you avoid the harness becoming an opaque batch runner too early

## What Should Stay For Later

Defer these until the basic harness is useful:

- fully automated answer autoplay
- matrix runs across every node in one concept
- pass/fail assertions against expected labels
- golden-fixture regression dashboard
- screenshot or video capture

These are valuable, but the first win is reducing setup friction.

## Truthful Graph Requirements

Fixture runs should default to one of these modes:

- `sandbox mode`
  - graph state is ephemeral
  - ideal for repeated answer-sequence trials
- `persisted fixture mode`
  - graph state is saved
  - useful when testing unlock behavior across multiple nodes

Default recommendation: `sandbox mode`.

Why:

- avoids stale fixture concepts piling up
- avoids accidental confusion with real learning artifacts
- makes repeated taste trials cheaper

## Telemetry Requirements

Every fixture run should carry tags such as:

- `run_mode = fixture`
- `fixture_id`
- `fixture_title`
- `scripted_answer_label`
- `sandbox = true|false`

This keeps internal calibration data available without polluting production-style analytics.

## Product Boundary

This harness should live behind a dev flag, internal route, or explicit test mode.

Do not:

- expose canned answers in the normal learner UI
- expose answer banks during standard drill sessions
- let fixture affordances become hidden cheat-sheet behavior

## Best First Slice

If implemented tomorrow, the best first slice is:

1. one action-potential fixture
2. one hidden "Run Fixture" button
3. auto-extract
4. auto-open graph
5. auto-start drill on `core-thesis`
6. side panel with the 9 scripted answer variants from the answer grid

That is enough to dramatically shorten prompt-calibration cycles without overbuilding the harness.
