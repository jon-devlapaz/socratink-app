# Extraction Phase Catalog

This document catalogues all codebase resources related to the extraction phase, where the app processes the user's text to generate an evidence-weighted concept map.

## 🧠 Backend & AI Pipeline

These files handle the core data processing, API routing, and AI interactions.

| File | Purpose |
| :--- | :--- |
| [ai_service.py](../../ai_service.py) | **Core Engine:** Contains the `extract_knowledge` logic. Orchestrates calls to the Gemini model, manages retries, normalizes errors, and structures the resulting knowledge map. |
| [main.py](../../main.py) | **API Router:** Defines and wires the `/api/extract` and `/api/extract-url` endpoints, which act as the entry points for extraction requests. |
| [extract-system-v1.txt](../../app_prompts/extract-system-v1.txt) | **AI Prompt:** The system prompt injected into the LLM defining the strict schema and behavioral rules for concept extraction. |
| [generate-smallest-route-system-v1.txt](../../app_prompts/generate-smallest-route-system-v1.txt) | **AI Prompt (C-prime):** System prompt for the source-less branch of `/api/extract`. Drives `generate_smallest_provisional_map` to emit a provisional map of ≤4 drillable nodes (cap-exceeded yields a 500 `smallest_route_cap_exceeded`). |

## 💻 Frontend & Visualization

These files manage how the extraction is triggered by the user and how the resulting concept map is visualized in the browser.

| File | Purpose |
| :--- | :--- |
| [app.js](../../public/js/app.js) | **App Controller:** Manages the main UI state, captures user form input, and coordinates the start and end of the extraction phase. |
| [ai_service.js](../../public/js/ai_service.js) | **API Client:** The frontend wrapper responsible for making the asynchronous fetch requests to the backend API. |
| [source-panel.js](../../public/js/source-panel.js) | **Door (C-prime):** Mounts the concept-name + optional source entry (the "Door"). Routes source-attached submissions to the source-aware extract path. |
| [launch-pad.js](../../public/js/launch-pad.js) | **Launch Pad (C-prime):** Mounts the threshold for source-less concepts. Drives the smallest-route extract branch and surfaces cap-exceeded server messages. |
| [app.js](../../public/js/app.js) + [concept-page.css](../../public/css/concept-page.css) | **Concept view:** Strip-as-nav navigator plus the B-2 concept page that replaced the Cytoscape graph view. Renders the extraction map as a list/strip of nodes and a per-node detail surface. |
| [drill-chamber.js](../../public/js/drill-chamber.js) + [drill-chamber.css](../../public/css/drill-chamber.css) | **Drill chamber view:** Full-screen drill surface (`#drill-chamber-view`) that hosts cold-attempt, study, and re-drill flows after a strip node is selected. |
| [index.html](../../public/index.html) | **Markup:** Contains the DOM structure for the extraction input forms, loading indicators, and the canvas/container for the concept map. |
| [layout.css](../../public/css/layout.css) | **Styles:** CSS classes that handle the layout positioning of the map and extraction UI elements. |

## 📝 Product Specs & Documentation

These documents define the intended product behavior, UX rules, and system architecture for the extraction phase.

| File | Purpose |
| :--- | :--- |
| [evidence-weighted-map.md](../../docs/product/evidence-weighted-map.md) | **Product Spec:** Defines how the concept map nodes and edges are structured and how they correspond to evidence from the source text. |
| [progressive-disclosure.md](../../docs/product/progressive-disclosure.md) | **UX Spec:** Details rules on how information from the extraction phase should be revealed to the user without overwhelming them. |
| [doc-map.md](../../docs/project/doc-map.md) | **Index:** The master map of the project's documentation, which registers all of the above specs. |
| [drill-build-measure-learn.md](../../../agents/WORKFLOWS/drill-build-measure-learn.md) | **Context:** Details how the extracted concept map feeds into the downstream "Drill" testing phase. |
| [engineering.md](../../docs/drill/engineering.md) | **Context:** Additional engineering details linking extraction outputs to system components. |
