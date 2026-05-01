# Extraction Phase Catalog

This document catalogues all codebase resources related to the extraction phase, where the app processes the user's text to generate an evidence-weighted concept map.

## 🧠 Backend & AI Pipeline

These files handle the core data processing, API routing, and AI interactions.

| File | Purpose |
| :--- | :--- |
| [ai_service.py](file:///Users/jondev/dev/socratink/prod/socratink-app/ai_service.py) | **Core Engine:** Contains the `extract_knowledge` logic. Orchestrates calls to the Gemini model, manages retries, normalizes errors, and structures the resulting knowledge map. |
| [main.py](file:///Users/jondev/dev/socratink/prod/socratink-app/main.py) | **API Router:** Defines and wires the `/api/extract` and `/api/extract-url` endpoints, which act as the entry points for extraction requests. |
| [extract-system-v1.txt](file:///Users/jondev/dev/socratink/prod/socratink-app/app_prompts/extract-system-v1.txt) | **AI Prompt:** The system prompt injected into the LLM defining the strict schema and behavioral rules for concept extraction. |

## 💻 Frontend & Visualization

These files manage how the extraction is triggered by the user and how the resulting concept map is visualized in the browser.

| File | Purpose |
| :--- | :--- |
| [app.js](file:///Users/jondev/dev/socratink/prod/socratink-app/public/js/app.js) | **App Controller:** Manages the main UI state, captures user form input, and coordinates the start and end of the extraction phase. |
| [ai_service.js](file:///Users/jondev/dev/socratink/prod/socratink-app/public/js/ai_service.js) | **API Client:** The frontend wrapper responsible for making the asynchronous fetch requests to the backend API. |
| [graph-view.js](file:///Users/jondev/dev/socratink/prod/socratink-app/public/js/graph-view.js) | **Visualization logic:** Responsible for taking the JSON concept map data and rendering the interactive node/edge graph in the browser. |
| [index.html](file:///Users/jondev/dev/socratink/prod/socratink-app/public/index.html) | **Markup:** Contains the DOM structure for the extraction input forms, loading indicators, and the canvas/container for the concept map. |
| [layout.css](file:///Users/jondev/dev/socratink/prod/socratink-app/public/css/layout.css) | **Styles:** CSS classes that handle the layout positioning of the map and extraction UI elements. |

## 📝 Product Specs & Documentation

These documents define the intended product behavior, UX rules, and system architecture for the extraction phase.

| File | Purpose |
| :--- | :--- |
| [evidence-weighted-map.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/product/evidence-weighted-map.md) | **Product Spec:** Defines how the concept map nodes and edges are structured and how they correspond to evidence from the source text. |
| [progressive-disclosure.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/product/progressive-disclosure.md) | **UX Spec:** Details rules on how information from the extraction phase should be revealed to the user without overwhelming them. |
| [hermes-agent-concept-source.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/reference/hermes-agent-concept-source.md) | **Reference:** Describes the AI agent behavior specifically focused on sourcing and verifying extracted concepts. |
| [doc-map.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/project/doc-map.md) | **Index:** The master map of the project's documentation, which registers all of the above specs. |
| [drill-build-measure-learn.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/codex/drill-build-measure-learn.md) | **Context:** Details how the extracted concept map feeds into the downstream "Drill" testing phase. |
| [engineering.md](file:///Users/jondev/dev/socratink/prod/socratink-app/docs/drill/engineering.md) | **Context:** Additional engineering details linking extraction outputs to system components. |
