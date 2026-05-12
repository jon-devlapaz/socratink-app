# app_prompts/

Production Gemini prompt assets. Versioned plain-text/markdown files
that the LLM pipeline loads at runtime from this directory. Bundled with
the Vercel serverless function deployment.

## Files

| File | Stage | What it does |
| :--- | :--- | :--- |
| `extract-system-v1.txt` | Stage 1 — Extract | Turns raw source material into a structured `ProvisionalMap`. The schema this prompt produces matches `models.ProvisionalMap`. |
| `generate-smallest-route-system-v1.txt` | Stage 2 — Draft | Generates a minimal traversal path through the map for the first drill session. |
| `drill-system-v1.md` | Stage 3 — Drill | The Socratic drill agent. Forces recall, scaffolds repair, tags Shallow/Deep/Misconception. The drill route runtime-appends a "Target Node (ANSWER KEY)" block and the pruned map context. |
| `repair-reps-system-v1.md` | Stage 4 — Repair Reps | Post-drill spaced-repetition repair routine for nodes flagged Deep/Misconception. |

## Loading

`ai_service.py` resolves the directory once at module load:

```python
PROMPT_DIR = Path(__file__).parent / "app_prompts"
```

Then reads files as needed. There is no caching layer; file reads are
cheap and Vercel's filesystem is read-only at runtime.

## Footguns

- **Versioning is in the filename, not git history.** A prompt change that
  alters extraction output should ship as `extract-system-v2.txt` plus a
  code change that loads it. Overwriting v1 silently is a product-truth
  hazard — downstream maps may have been generated with the old version.
- **The extract prompt's output schema is contractual.** The shape the LLM
  produces must match `models.ProvisionalMap`. If you change the prompt's
  output structure, change the Pydantic model and the model's tests in
  the same commit. The Pydantic validation step in `ai_service.py` will
  reject anything that drifts.
- **The drill prompt is appended at runtime.** The drill backend
  dynamically appends the "Target Node (ANSWER KEY)" block to the system
  prompt before each turn. If you rename anchors inside the prompt that
  the backend's appender depends on, drill silently breaks.
- **EPISTEMIC RULE in `extract-system-v1.txt` is load-bearing.** "Prefer
  omission over invention" is what keeps the graph truthful. Softening
  this language to "Be thorough" produces hallucinated backbone items in
  practice. Don't.
- **Prompts are part of the deploy.** Vercel ships them via
  `vercel.json`'s `includeFiles`. If a new prompt asset isn't ship-listed
  the function will 500 in prod with a missing-file error.

## Related

- Consumer: `ai_service.py` (all four stages).
- Schema: `models/provisional_map.py`.
- Drill backend appender: search `ai_service.py` for `Target Node`.
- Deploy include-list: `vercel.json`.
