# app_prompts/

Production Gemini prompt assets. Versioned plain-text/markdown files
that the LLM pipeline loads at runtime from this directory. Bundled with
the Vercel serverless function deployment.

## Files

| File | Stage | What it does |
| :--- | :--- | :--- |
| `extract-system-v1.txt` | Stage 1 — Extract | Turns raw source material into a structured `ProvisionalMap`. The schema this prompt produces matches `models.ProvisionalMap`. |
| `generate-smallest-route-system-v1.txt` | Stage 2 — Draft | Generates a minimal traversal path through the map for the first drill session, including `learner_scaffold` on source-less smallest-route subnodes and optional `learner_goal` relevance framing. |
| `drill-system-v1.md` | Stage 3 — Drill | The Socratic drill agent. Forces recall, scaffolds repair, tags Shallow/Deep/Misconception. The drill route runtime-appends a "Target Node (ANSWER KEY)" block, a "Learner Scaffold" block when present, the learner goal as relevance context, and the pruned map context. |
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
  dynamically appends the "Target Node (ANSWER KEY)" block and, when
  present, a "Learner Scaffold" block to the system prompt before each
  turn. If you rename anchors inside the prompt that the backend's
  appender depends on, drill silently breaks.
- **Source-less smallest routes require `learner_scaffold`.** The runtime
  rejects smallest-route subnodes that omit it. Scaffold fields shape the
  task and evaluator scope; they are not learner evidence and must not
  reveal the mechanism.
- **Learner goals are relevance context, not evidence.** Smallest-route
  generation may use `<learner_goal>` to shape route emphasis and scaffold
  copy. Drill may use `metadata.learner_goal` to frame why a node matters,
  but it must not grade against the broad goal or mutate graph truth.
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
