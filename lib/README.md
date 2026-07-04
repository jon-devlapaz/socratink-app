# App-local SEDA runtime

`lib/` contains the Node runtime that powers app-local SEDA sessions. It is
vendored into this repo so the learner product flow does not depend on a
sibling checkout.

## Runtime directories

- `seda/`: loop state machine, handlers, session rehydration, and evidence
  projection
- `loop-server/`: local HTTP server used by `/api/session` and `/loop`
- `bridge/`: Node client for the Python bridge in `bridge.py`
- `canon/`: graph-truth training store and derivation modules
- `config/`: repo-local path resolution and runtime preflight checks
- `feedback/`: loop feedback command handling
- `observability/`: dashboard/session metrics projection
- `ui/`: transcript and map formatting helpers shared by loop surfaces

## Lab-only directories

- `lab/`: founder and persona lab tooling. Do not treat this as learner product
  surface unless a task explicitly targets lab tooling.
