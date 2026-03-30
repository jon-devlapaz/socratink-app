# LearnOps UX Architecture: The Progressive Knowledge Graph "Happy Path"

## Purpose
This document serves as the architectural reference for AI agents (Codex, Claude, etc.) building features for the LearnOps platform. It defines the core Generative UI loop, the "Fog of War" progressive disclosure mechanics, and the expected state boundaries between the LLM and the Cytoscape graph.

When touching any related files (such as `graph-view.js`, `app.js`, `ai_service.py`, or `index.html`), ensure your logic strictly adheres to the workflow defined below.

---

## The Core Philosophy
1. **First Principles Learning (Progressive Disclosure):** The user should *never* see the entire 50-node map upon initial extraction. That causes cognitive overload. The UI defaults to a "Fog of War" state—nodes are locked silhouettes until actively drilled and mastered by the user.
2. **The Generation Effect:** During a drill session on a specific node, the descriptive text for *that* node must be visually obscured to prevent the user from simply reading the answer. They must generate the answer from memory.
3. **Generative UI:** The Socratic AI acts as the state manager. When it determines mastery, it outputs a hidden JSON payload to explicitly unlock UI elements.

---

## 1. State Diagram: The Happy Path Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Learner
    participant UI as Graph UI (Cytoscape)
    participant Backend as FastApi/Router
    participant AI as Socratic Agent (Skill: learnops-drill)

    %% INGEST PHASE
    Note over Learner, AI: Phase 1: Ingest & The Seed
    Learner->>Backend: Uploads PDF / Source Material
    Backend->>Backend: Executes Extraction Pipeline
    Backend-->>UI: Returns Extracted Map JSON
    UI->>Learner: Renders "Fog of War" Graph. Only the `backbone` node is solid/glowing. `Clusters` are rendered as locked silhouettes. Subnodes are invisible.
    
    %% DRILL INITIATION
    Note over Learner, AI: Phase 2: Drill Initiation (Split Screen)
    Learner->>UI: Clicks "Core Thesis" (Backbone) to initiate Drill
    UI->>UI: Enters "Drill Mode". Chat panel slides in. The Active Node pulses; its description label blurs.
    UI->>Backend: Triggers `learnops-drill` skill with Node Context
    Backend->>AI: Agent loads Socratic ruleset + Target Node
    AI->>Learner: "Explain this Core Thesis to me without looking at your notes."
    
    %% GENERATIVE STRUGGLE
    Note over Learner, AI: Phase 3: Socratic Dialogue
    Learner->>AI: Learner attempts to explain the text from memory.
    AI->>Learner: Agent applies Feynman challenge moves. Iterates until cycle closure ("Lock it in").
    
    %% THE BLOOM (GENERATIVE UI REWARD)
    Note over Learner, AI: Phase 4: State Evolution & The Bloom
    AI->>Backend: Cycle complete. Agent emits response + Hidden System Payload.
    Note right of AI: Payload Payload Schema:<br/>{"action": "UNLOCK_NODE", "target_node_id": "cluster-1", "status": "solidified"}
    Backend-->>UI: Forwards payload to Frontend
    UI->>UI: Intercepts JSON payload. Evaluates target.
    UI->>Learner: ANIMATION: Active node locks solid. Text unblurs. Next cluster node(s) switch from silhouette -> Solid/Unlocked.
    
    %% FORWARD MOMENTUM
    AI->>Learner: "Now that we have the foundation, let's look at this new cluster. How does [Cluster 1] connect?"
    UI->>UI: Camera pans to spotlight the newly unlocked Cluster 1.
```

## 2. Agent Implementation Rules

When implementing features related to this flow, agents must adhere to the following technical contracts:

### A. The Hidden Payload Contract
The backend router and frontend `app.js` must be configured to silently strip and process specific JSON structures appended by the LLM before rendering the markdown to the DOM.
*   **Format:** The LLM should output `<tool_call>` or pure JSON block demarcated as `[SYSTEM_ACTION]` at the end of its conversational text.
*   **Example Output from LLM:**
    ```text
    Spot on! That perfectly describes the mechanism. Let's lock it in.

    [SYSTEM_ACTION: {"action": "UPDATE_NODE_STATE", "id": "cluster-1", "newState": "unlocked"}]
    ```

### B. Cytoscape Node State CSS Reference
The `graph-view.js` stylesheet must distinctly map Node States to visual properties:
*   `.is-locked`: Transparent fill, dashed gray border, blurry text, no mouse-interaction. (Fog of War).
*   `.is-active-drill`: Pulsing animation, solid border, text explicitly applying `filter: blur(8px)` so it can't be read during the drill.
*   `.is-solidified`: Full `--primary` or `--success` theme color, solid text, full interaction.

### C. Layout Physics During "The Bloom"
Nodes must dynamically re-adjust their physical position if new child nodes suddenly appear on the canvas. Instead of static preset algorithms, continuous physics/concentric force layouts (`cola`, `cose`) should run briefly when a new node unhides to provide the organic, satisfying "blooming" animation.
