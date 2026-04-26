# Archive

Frozen artifacts that are no longer part of the active codebase. Kept here so they're easy to find, easy to triage, and easy to delete when you're confident they're not load-bearing.

## Layout

```
archive/
  tooling/   — configs for tools/IDEs not currently in active use
  planning/  — old planning/spec documents superseded by current work
```

Each category has its own README listing what's inside and when it was archived.

## Triage rules

When deciding whether to keep or delete an archived item, ask:

1. **Is the origin still relevant?** (e.g. is the tool still in use, is the plan still being executed)
2. **Has the content been promoted into active docs** (`docs/`, `.socratink-brain/`)? If yes, the archive copy is redundant.
3. **Would I miss this if it disappeared in 6 months?** If no, delete.

When you delete, do it in a single commit per category so the history stays clean and reversible.

## Adding new items

```
git mv <path> archive/<category>/<name>
```

Then add a one-line note to that category's README: what it was, when archived, and the trigger to delete it (e.g. "delete after Q3 if Kiro is still unused").
