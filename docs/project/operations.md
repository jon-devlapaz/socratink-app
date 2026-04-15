# socratink — Operations & Stabilization

This document defines the release discipline for the current Socratink MVP.

## 1. Current Merge Standard

Do not expand scope until the narrow thermostat loop is healthy on hosted and local.

The minimum acceptable loop is:
1. cold attempt
2. study
3. interleave on another room
4. spaced re-drill
5. truthful graph update

## 2. Release Checks

Before merging to `main`, verify:
1. **Loop integrity**: the thermostat path in [mvp-happy-path.md](mvp-happy-path.md) works without obvious breaks
2. **Truthful state**: only valid transitions occur
3. **Graph stability**: no UI crash, stale panel, or wrong-node patch
4. **Hosted caution**: local success is not treated as final if the change could diverge on Vercel
5. **Error handling**: external/API failures do not leak internals to the learner
6. **Evidence captured**: the run is documented in the Socratink Brain KB or explicitly noted as missing coverage

## 3. Current Evidence Policy

Use the branch itself as the evidence sink for this MVP merge:
- live findings
- open issues
- shipping syntheses
- instrumentation gaps

At minimum, keep the supporting evidence in:
- `logs/drill-runs.jsonl`
- any transcript logs that exist
- exported Vercel runtime logs from Socratink Brain-marked drill events when validating hosted behavior
- screenshots for visible contradictions
- a short merge note describing what was actually verified

If evidence is missing, say so explicitly instead of writing confident prose around it.

For hosted drill-conversation capture, `/api/drill` emits structured `socratink_event` runtime log events in addition to local JSONL. Summary capture is on by default. Full learner/assistant transcript capture requires setting `SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS=true` in Vercel, then exporting logs with `scripts/eval-pull` before running Socratink Brain `evaluate-logs`.

Use the Build-Measure-Learn drill workflow in [docs/codex/drill-build-measure-learn.md](../codex/drill-build-measure-learn.md) when turning a drill run into evaluated logs and a proposed fix.

## 4. Near-Term Engineering Priorities
- keep drill state, panel state, and graph state aligned
- keep CTA logic and actual allowed actions aligned
- improve transcript/replay coverage without blocking the narrow release gate
- harden hosted fallbacks for external ingestion paths
- reduce `app.js` state entanglement after the loop is stable enough to ship

## 5. Active Decisions

| Date | Decision | Why it matters | Consequence |
|---|---|---|---|
| 2026-04-08 | Ship the narrow truthful loop first | The MVP needs a believable working loop before broader science or polish layers | Thermostat is the release gate; gaps are logged in the KB |
| 2026-04-05 | Three-phase node loop is the MVP architecture | It preserves generation, correction, and delayed verification | UI and persistence work must respect `locked -> primed -> drilled -> solidified` |
