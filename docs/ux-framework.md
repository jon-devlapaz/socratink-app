# **Product UX Framework: Tink (LearnOps)**

## **1\. Product Vision & Core Philosophy**

**The Problem:** The "Illusion of Competence." Traditional learning platforms enable passive reading. Users confuse *fluency* (understanding text in the moment) with *mastery* (the ability to recall and apply knowledge).

**The Solution:** Tink masks high-friction cognitive science (The Generation Effect / Active Recall) behind high-dopamine game mechanics ("Solo Leveling" / RPG Skill Trees).

**The Core Value:** A "Bring-Your-Own-Content" (BYOC) gamified learning engine that forces users to think harder, but makes that hard work feel incredibly rewarding.

## **2\. The Visual & Thematic Aesthetic**

The platform borrows heavily from RPG gaming interfaces rather than traditional B2B SaaS or sterile EdTech.

* **The Metaphor:** The user is a player conquering a "Skill Tree" (The Tinkboard / Knowledge Graph).  
* **The Aesthetic (Target):** "Solo Leveling." High contrast, sleek, and responsive.  
* **Color & Lighting:** While the current MVP uses a clean, light-mode pastel palette, the ultimate vision leans toward **Dark Mode**. Dark backgrounds allow for neon accents (electric blue, emerald, purple) to create visceral "glowing" and "blooming" effects when nodes are unlocked.  
* **Nomenclature:** Tinkboard, Facets, Crystals, Backbone, Clusters, Drill, Consolidate. (Proprietary vocabulary makes the system feel sophisticated and specialized).

## **3\. The 5-Phase UX Loop (The Happy Path)**

This is the core engine of the platform, defining how a user moves from uploading a document to mastering a concept.

### **Phase 1: The Seed (Ingest & Map)**

* **Action:** User uploads a raw document (PDF/Text).  
* **System:** The Backend pre-extracts the entire knowledge structure into a JSON graph schema (Backbone, Clusters, Links) to save latency and AI costs later.  
* **UI:** Renders the "Fog of War." Only the central "Backbone" node glows. Future concepts are locked, mysterious silhouettes.

### **Phase 2: Focus Mode (The Drill)**

* **Action:** User selects an available node and clicks \+ START DRILL.  
* **System:** Triggers the Socratic AI with the specific Node ID context.  
* **UI:** The screen splits. **Context-Aware Blur** is applied to the study material (obscuring the text to prevent passive reading). A chat interface slides in.

### **Phase 3: The Struggle (Generation Effect)**

* **Action:** The AI asks the user to explain or apply the concept from memory.  
* **System:** The AI evaluates the user's typed response against a hidden rubric.  
* **UI:** A back-and-forth Socratic chat. The AI does not give answers, only hints and follow-up questions until the user demonstrates first-principles understanding.

### **Phase 4: The Bloom (The Reward)**

* **Action:** The user successfully explains the concept.  
* **System:** The AI outputs a low-latency hidden JSON payload (e.g., {"action": "UNLOCK", "target": "node\_123"}).  
* **UI:** The Generative Animation. The text unblurs instantly. The node locks into a solid color ("Level Up\!"). A shockwave travels down the graph edges.

### **Phase 5: Momentum (Autonomy)**

* **Action:** The user surveys the board.  
* **System:** The graph updates state.  
* **UI:** The newly unlocked node illuminates adjacent, prerequisite paths. The user autonomously selects their next "quest," maintaining high momentum.

## **4\. UI Architecture & Screen Strategy**

### **Screen A: The Tinkboard (Macro Dashboard)**

* **Purpose:** The 10,000-foot view of overall progress.  
* **Current State:** Beautiful 3D isometric grid with floating "Facets."  
* **UX Rules:**  
  * **CTA Hierarchy:** Ensure the primary action (e.g., "3. Drill") is undeniably prominent. Secondary actions (Map, Consolidate) should be ghosted or visually demoted until required.  
  * **Infinite Scale:** Use fading grid lines to imply the board is massive, leaning into the "expansive skill tree" psychology.

### **Screen B: The Graph View (Spatial Exploration)**

* **Purpose:** Visualizing the mental model (how concepts connect).  
* **Current State:** 2D force-directed graph with a contextual side panel.  
* **UX Rules:**  
  * **Graph Legibility:** Prevent node text from overlapping. Consider hiding text on tightly clustered nodes until hover, or relying heavily on the right-hand panel for reading.  
  * **Curiosity Gap:** Locked nodes should hide their titles (or use teasers) to encourage users to drill current nodes to reveal the hidden paths.

### **Screen C: The Study View (Micro Preparation)**

* **Purpose:** Reading the deconstructed material before being tested.  
* **Current State:** Clean, linear breakdown of Backbone Principles, Clusters, and Connections.  
* **UX Rules:**  
  * **The Working Memory Trap:** Prevent users from immediately parroting what they just read. When \+ START DRILL is clicked, the AI must ask them to *apply* the concept, not just recite it, to enforce true active recall.  
  * **Triumphant CTA:** The \+ START DRILL button must be the most visually magnetic element on the screen.

## **5\. Critical UX Safeguards**

To ensure the product succeeds, the engineering and design teams must guard against these specific failure modes:

1. **AI Pedantry (Frustration Risk):** If the Socratic AI acts like a strict grader looking for exact keywords, users will churn. The system prompt must instruct the AI to act like an encouraging, forgiving mentor who guides the user to the answer.  
2. **Graph Clutter (Cognitive Overload):** If a user uploads a 100-page manual, a 500-node graph will overwhelm the browser and the user. The UI must aggressively chunk maps into nested "Zones" or "Chapters."  
3. **Dopamine Exhaustion:** The visual reward of "The Bloom" must scale. Early unlocks should be quick to build confidence, while deeper, complex nodes should require more struggle but offer a more spectacular UI reward when conquered.