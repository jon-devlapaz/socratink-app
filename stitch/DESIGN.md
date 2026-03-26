# Design System Document: The Architect of Thought

## 1. Overview & Creative North Star

### Creative North Star: "The Architect of Thought"
This design system is not a static interface; it is a living blueprint of the user’s cognitive landscape. We move beyond the "SaaS dashboard" trope to create a **Knowledge Architecture**. The visual language balances the cold, structural rigidity of cognitive science (isometric grids, wireframe textures) with the organic, high-dopamine rewards of progress (glassmorphism, crystal transitions, and "Pulse" accents).

### Breaking the Template
To achieve a high-end editorial feel, we eschew traditional rigid grids. We embrace **intentional asymmetry**—where data visualization might bleed off-canvas or headers overlap structural containers. We treat the screen as a three-dimensional workspace where "Zen" mode provides the breathing room of a gallery, and "Ops" mode provides the high-density precision of a flight deck.

---

## 2. Colors & Visual Soul

The palette is rooted in deep, intellectual tones of Indigo and Purple, punctuated by vibrant "Pulse" indicators that signify neural activity and mastery.

### The Palette Roles
*   **Primary (`#4343d5`):** The structural ink. Used for active navigation states and primary actions.
*   **Secondary (`#9026c3`):** The "active learning" pulse. Represents Electric Lavender in its interactive state.
*   **Tertiary (`#006731`):** The "mastered" state. Transitioning to Neon Emerald (`tertiary_fixed_dim: #00e475`) to provide that visual dopamine hit when a concept is conquered.
*   **Surface Hierarchy:** We utilize `surface-container-lowest` to `highest` to build depth without lines.

### The "No-Line" Rule
**1px solid borders are strictly prohibited for sectioning.** Boundaries must be defined solely through:
1.  **Tonal Shifts:** A `surface-container-low` card sitting on a `surface` background.
2.  **Negative Space:** Utilizing our Spacing Scale (specifically `12` and `16` units) to create "invisible" partitions.
3.  **Isometric Grids:** Subtle, non-solid grid patterns that imply structure without enclosing it.

### Signature Textures
Main CTAs and hero elements should utilize a **Crystal Gradient**: a transition from `primary` to `primary_container`. For background elements, use isometric wireframe textures that "solidify" into glass containers as the user scrolls or interacts.

---

## 3. Typography: Precision & Authority

Our type system is a dialogue between high-precision utility and editorial elegance.

*   **Display & Headlines (Manrope):** Chosen for its geometric foundation. Use `display-lg` and `headline-md` for high-impact metacognitive summaries. The wide apertures feel "forward-thinking" and open.
*   **Body & Titles (Inter):** The workhorse of high-precision UI. `body-md` is the standard for analytical text, providing maximum legibility in data-dense "Ops" mode.
*   **Labels (Space Grotesk):** This is our "Analytical" layer. Used for metadata and metrics. Its quirkiness signals that this is a technical, metacognitive tool.

---

## 4. Elevation & Depth

We achieve hierarchy through **Tonal Layering** rather than traditional drop shadows.

### The Layering Principle
Stacking `surface-container` tiers creates a natural, physical lift. 
*   **Base:** `surface` (`#f8f9ff`)
*   **Section:** `surface-container-low`
*   **Content Card:** `surface-container-lowest` (The "Brightest" layer feels closest to the user).

### Ambient Shadows
Where floating elements (like Modals or Tooltips) require separation, use **Ambient Shadows**:
*   **Color:** Tinted with `on_surface` at 5% opacity.
*   **Blur:** Extra-diffused (32px - 64px) to mimic natural light passing through frosted glass.

### Glassmorphism & "Ghost Borders"
For floating "Zen" mode controls, use a backdrop-blur (12px-20px) on `surface` at 70% opacity. If a container needs further definition, use a **Ghost Border**: the `outline-variant` token at **15% opacity**. Never 100%.

---

## 5. Components

### Buttons: The Kinetic Trigger
*   **Primary:** Solid `primary` with a subtle gradient to `primary_container`. No border. `rounded-md` (0.75rem).
*   **Secondary:** Glassmorphic background with `primary` text.
*   **States:** On hover, buttons should "pulse" with a subtle outer glow using their respective accent color (`secondary_fixed` for lavender).

### Cards & Metrics
Cards must never have dividers. Use `surface-container-high` for the header area and `surface-container-lowest` for the body to create a natural "shelf." 
*   **Zen Variant:** Minimal data, high white space (`spacing-10`).
*   **Ops Variant:** High-density, utilizing `label-sm` for micro-metrics and `spacing-2`.

### Knowledge Chips
*   **Active:** `secondary_container` background with `on_secondary_container` text.
*   **Mastered:** `tertiary_fixed` background. These should have a slight "inner glow" to feel like polished emerald crystals.

### Inputs
Text inputs use `surface_container_highest` with a 2px bottom-only highlight (Ghost Border) that expands to a full `primary` underline on focus. This maintains the "architectural drawing" aesthetic.

---

## 6. Do’s and Don’ts

### Do:
*   **Use Asymmetry:** Place a floating action button or a metric off-center to break the "boxed-in" feel.
*   **Leverage Glass:** Overlay analytical metrics over isometric grid backgrounds using backdrop-blur.
*   **Embrace the "Ops" Density:** In data views, don't be afraid of small, high-precision type (`label-sm`) if it is aligned to a strict spacing rhythm.

### Don’t:
*   **No Grey Shadows:** Never use `#000000` or neutral grey for shadows; always tint them with the surface color.
*   **No "Boxy" Layouts:** Avoid 4-sided high-contrast borders. If a container feels too heavy, revert to a tonal shift.
*   **Don't Overuse Accents:** The Neon Emerald (`tertiary`) is a reward. Using it for non-essential elements dilutes the "dopamine hit" of mastery.