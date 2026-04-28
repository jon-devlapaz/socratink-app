# Project Constitution

Architectural constraints that govern every feature. Hand-curated. Updated rarely. Read by every `/pipette` run before Step 0.

## C1. The graph is a floor, not a ceiling

`code-review-graph` CALLS counts under-report. Any plan or claim of the form "only call site of X" requires a hand-grep of the symbol in addition to the graph query. (memory: `feedback_graph_count_floor_not_ceiling.md`)

## C2. Hosted validation is the only validation that ships

Local success ≠ prod success. Any change touching `main.py`, `api/index.py`, or `public/index.html` requires `bash scripts/qa-smoke.sh https://app.socratink.ai` after merge before declaring "shipped." (`CLAUDE.md` "QA: Browser Smoke")

## C3. MVP scope discipline

Conservative on deployment blockers (data loss, security holes, core flow breakage). Liberal on polish. Acceptable tradeoffs noted in PR description, not buried in the diff. (`CLAUDE.md` "MVP Scope Discipline")
