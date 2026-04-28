---
name: pipette-weekly
description: Weekly aggregator over docs/pipeline/*/07-eval.md. Reads all completed runs in the last 7 days, identifies the weakest step, writes docs/pipeline/_meta/weekly-YYYY-MM-DD.md.
user-invocable: false
---

# pipette-weekly

Run by scheduled cron `socratink-app-pipette-weekly`. Aggregates eval signals across runs.

## Procedure

1. Glob `docs/pipeline/*/07-eval.md` filtered to `mtime > now-7d`. List the runs.
2. For each: parse the YAML front block (auto-collected signals + 1-line self-report).
3. Aggregate:
   - Mean self-rated score per step
   - Min self-rated score per step (weakest step)
   - Total NEEDS_RESEARCH raises this week
   - Total Gemini FAIL → jump-back distribution
   - Best-of-N triggered count
4. Write `docs/pipeline/_meta/weekly-<today>.md` with a one-paragraph summary + the table.
5. Commit the file.
