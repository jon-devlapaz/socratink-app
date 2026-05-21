# Constellation UX Goal Log

## 2026-05-21

- Baseline captured in `.qa-runs/constellation/` for the current production constellation, mobile view, and lab prototype reference.
- Renderer slice: kept `deriveConceptEntryViewState` as the state source, added crystal SVG nodes, lit route edges, keyboard focus, and a selected-room card.
- Redaction correction: selected-room copy now uses learner-scaffold cues only, with generic no-spoiler fallback. It does not reuse derived `purpose` because that can contain source-preview text.
- Styling slice: ported the Obsidian-like canvas feel from the lab reference into the production constellation surface, including dark stage, subtle grid, warm selected card, and mobile bottom drawer.
- Verification so far: `node --check public/js/concept-constellation-view.js`, `node --check public/js/app.js`, and `pytest tests/test_frontend_app_helper_modules.py -q`.
- Browser slice: `pytest tests/e2e/test_smoke.py::test_concept_view_opens_to_route_margin_canvas -q` covers route default, constellation toggle, click/keyboard node selection, no study-content leak, and return-to-route behavior.
- Final gate: `./scripts/check-coverage.sh` passed with 100% diff coverage.
- Visual artifacts: `.qa-runs/constellation/after-production-desktop-final.png` and `.qa-runs/constellation/after-production-mobile-final-polished.png`.

## 2026-05-21 Wow-Gate Polish

- Agy gate: `.playwright-mcp/persona-constellation-wow-gate-20260521-164301.txt` pushed hardest on fake-progress risk, mobile crowding, and SaaS-like visual noise.
- Product decision: do not expand Constellation into a study browser. Keep it secondary and route-first; polish the graph truth and phone legibility instead.
- Truthful Graph slice: Constellation edges now light only when both adjacent rooms have reconstruction attempts. Selection can update the card, but it no longer creates glowing progress.
- Visual slice: removed the overt grid/breathing-line treatment, softened star/noise levels, added deterministic organic node offsets, and made mobile detail live inside the Constellation card rather than fixed over the graph.
- Verification artifacts: `.qa-runs/constellation/after-wow-gate-desktop.png` and `.qa-runs/constellation/after-wow-gate-mobile.png`.
