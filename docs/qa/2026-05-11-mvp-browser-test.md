# Socratink MVP Browser QA Test — for Gemini 3 Pro (or any browser-capable agent)

## Your role

You are a senior QA engineer with browser automation tools (Playwright, Puppeteer, or equivalent). You are running a comprehensive pre-merge browser test on the Socratink MVP. Your output is a structured report that the founder will use to decide whether to ship to first learners.

Stay rigorous. Test every step. Capture EVIDENCE, not impressions. When you say "this works," include the DOM snippet or screenshot path that proves it. When you say "this is broken," include the exact error / unexpected output.

## Product context (one paragraph)

Socratink is a metacognitive learning tool. The learner picks a concept, writes a sketch of what they think they know, then the system generates a 7-screen scaffold with one starting "core thesis" entry. Before any study material is shown, the learner does a COLD ATTEMPT — answers one focused Socratic question by writing what they can reconstruct from memory. The system surfaces a small Targeted Study artifact and routes them to a nearby entry. **No streaks. No badges. No mastery claims from reading.**

## Test environment

- **URL:** `http://app.socratink.ai` (production) OR `http://localhost:8000` (worktree dev server) OR the URL the founder provides
- **Auth:** Use guest mode (auto-guest is enabled; if landed on `/login`, click "Continue as guest")
- **Browser:** Headless or headed Chromium. Keep DevTools Network tab open for Phase 5.
- **Viewports to test:** Desktop (1440×900), tablet (768×1024), mobile (390×844)
- **Themes to test:** Light (default) AND dark (toggle in Settings)

## Doctrine — non-negotiable invariants

Flag any violation as **BLOCKER**. These rules bind every surface:

| Rule | Forbidden examples |
|--|--|
| No praise copy | "Great job", "Excellent answer", "You did it", "Nailed it" |
| No scoring | "Score: 4/5", "85% accuracy", "Quiz", "Test score" |
| No mastery claims | "You've mastered X", "You understand Y", "Advanced level" |
| No streaks / badges / XP | "3-day streak", "Level 4", "Achievement unlocked" |
| No "AI is typing" indicators | "..." dots, "AI is responding", typing animations |
| No em dashes in user-visible copy | `—` (use periods, colons, semicolons, parentheses, or `--`) |
| No completion claims from reading | "You finished this section by reading" |

## Phase 1 — Landing + concept creation

### 1.1 Land on Desk

1. Navigate to base URL.
2. If redirected to `/login`, click "Continue as guest".
3. Verify Desk view loads with sidebar nav (`New concept`, `Desk`, `Library`, `Settings`, `Send Feedback`).
4. Verify the isometric board renders.
5. Verify no console errors (one allowed: `/_vercel/speed-insights/script.js` 404 — cosmetic).

### 1.2 Create a concept (ignition door)

6. Click `New concept` in the sidebar.
7. Verify the ignition page loads with headline "What do you want to explain?"
8. Verify the input has NO placeholder text (the rotating-placeholder animation was removed).
9. Verify the cursor sits at the LEFT edge of the textarea with ~14px breathing room (not flush against the focus ring).
10. Type "Photosynthesis". Verify the cursor + first character sit on the rule line of the lined-paper background (baseline alignment).
11. Verify the witness-anchor diamond (top of page) is OUTLINE-ONLY (muted ink stroke, no fill).
12. Click "Continue".

### 1.3 Launch pad (sketch capture)

13. Verify navigation to launch pad with headline "What do you already think is inside this concept?"
14. Verify the witness-anchor diamond is now SOLID VIOLET with a subtle halo (the actualization beat).
15. Verify the textarea placeholder reads "A sentence or two is plenty — be specific over comprehensive." (or similar).
16. Type a real sketch (200+ chars about photosynthesis).
17. Click "Save sketch".
18. Verify Gemini round-trip completes within 10 seconds.

## Phase 2 — Concept page (B-2 layout)

### 2.1 Header

19. Verify concept title appears at top with crystal mark + "concept" eyebrow.
20. Verify pills appear: a quiet "thin sketch" pill (if backend flagged low_density) and a violet "N of M entries primed" pill.
21. Verify the "thin sketch" copy is exactly that string — NOT "lightweight draft" (older copy).
22. Verify there is NO "Try from memory" button in the header (header should only show the title + tags).
23. Verify there is NO Route/Graph toggle in the header.

### 2.2 Map strip

24. Verify a 110px-tall map strip card appears below the header.
25. Verify it has a subtle violet ambient glow centered behind it.
26. Verify the SVG constellation shows N nodes (matching backbone count).
27. Verify the active node is slightly larger (radius 9 vs 6/7) and shows its label below.
28. Verify primed nodes have violet fill (light) or cyan fill (dark) with a halo.
29. Verify locked nodes are muted with dashed borders.
30. Verify the eyebrow "DRAFT ROUTE" appears top-left of the strip with monospace 10px tracking — NOT inheriting body text size.
31. Verify the active-name label "{entry name} · N of M" sits next to the eyebrow.

### 2.3 Strip interaction

32. Click the second strip node. Verify the work column swaps with a 240ms fade-out / 320ms fade-in transition.
33. If the second node is locked AND a predecessor is also locked, verify the CTA reads "Locked" and is disabled.
34. Click the first strip node. Verify the active entry returns and the CTA becomes enabled.
35. Hover a non-active strip node. Verify a small tooltip appears with the entry's title (solid background, subtle shadow — NOT a blurry glassmorphism panel).
36. Tab into the strip (focus the first node). Verify a violet focus halo appears around the focused circle.
37. Press `→`. Verify the active node advances by one and focus moves with it.
38. Press `←`. Verify the active node moves back.
39. Press `Enter` on the active node. Verify that entry stays selected and its active-entry block is shown.

### 2.4 Threshold quote

40. Verify the threshold quote appears as italic text with a 2px violet left border.
41. Verify it shows the learner's actual sketch text verbatim (NOT placeholder text, NOT a generic AI summary).
42. Verify a small "edit" link appears at the end of the quote.
43. Click "edit". Verify the quote is replaced by a textarea with the current text + "Cancel" (ghost) and "Save sketch" (primary violet) buttons.
44. Press `Esc`. Verify the editor closes and the quote is restored unchanged.
45. Click "edit" again. Edit the text. Press `Cmd+Return` (or `Ctrl+Return`). Verify the quote updates with the new text.
46. Refresh the page. Verify the new sketch text is still there (persisted to localStorage).

### 2.5 Active entry block

47. Verify the eyebrow above the H2 reads one of the current derived-state phrases, such as "first reconstruction entry 1 of N", "study required entry N of M", "repair the gap entry N of M", "ready to reconstruct again entry N of M", "spaced reconstruction ready entry N of M", or "locked entry N of M".
48. Verify the H2 (concept entry title) is large (~36px on desktop, ~26px on mobile).
49. Verify a one-paragraph purpose sits below the H2.
50. Verify the CTA button text:
    - Ready first entry → "Write what you remember" (entry 0 is NEVER blocked)
    - Locked entry N>0 with locked predecessor → "Locked" (disabled, with `disabled` attribute)
    - Primed entry before study reveal → "Reveal study note"
    - Repair-ready entry → "Try from memory again" or "Write it again" after a repair record exists
51. Verify the CTA hover treatment does not shift surrounding layout.

### 2.6 Nearby entries list

52. Verify a faint list at the bottom (0.62 opacity) with the eyebrow "nearby entries  all locked until first reconstruction".
53. Verify each row: monospace `01`–`0N` numbers + entry title + uppercase status pill on the right.

## Phase 3 — Inline reconstruction

### 3.1 Entering the reconstruction panel

54. From the concept page, click "Write what you remember" on entry 0.
55. Verify an inline `.concept-page-b2__attempt` panel appears in the active entry block; the concept page stays visible.
56. Verify the textarea is focused, has `aria-label="Write what you can reconstruct"`, and uses the placeholder "Put the part you can explain in your own words."
57. Verify the body does NOT enter `chamber-open` or `is-drilling` for this inline reconstruction path.

### 3.2 Saving an attempt

58. Click "Save what I wrote" while the textarea is empty. Verify the inline error appears and focus returns to the textarea.
59. Type a substantive 2-3 sentence reconstruction and click "Save what I wrote".
60. Verify exactly one `/api/drill` POST is sent for the save.
61. Verify the active entry re-renders from training state: weak attempts expose "Reveal study note" or a repair panel after study; strong attempts can show review/spaced reconstruction readiness.
62. Verify the Library card body later shows the learner's saved reconstruction, not `graphData.metadata.core_thesis`.

## Phase 4 — Doctrine + copy audit

### 4.1 Copy sweep

82. Across all surfaces visited (Desk, ignition, launch pad, concept page, inline reconstruction), grep the page text for:
    - "great job", "excellent", "amazing", "awesome", "nice work" — should be ZERO
    - "score", "quiz", "test", "assessment" — should be ZERO (in user-facing copy; backend code may use these words)
    - "mastered", "complete", "finished", "level up" — should be ZERO
    - "streak", "badge", "achievement", "XP" — should be ZERO
    - `—` (em dash, U+2014) in user-visible prose — should be ZERO
83. Verify that all eyebrows are SAME-CASE, SAME-FONT (10px monospace, uppercase, 0.18em tracking, lavender accent in light, lavender-cream in dark).

### 4.2 No "AI is typing" theatre

84. During any inline reconstruction save round-trip, verify there is NO "..." typing indicator, NO "AI is responding" text, NO loading spinner that fakes intimacy.

## Phase 5 — Theme + responsive

### 5.1 Theme toggle

85. Open Settings. Toggle to dark mode.
86. Re-walk Phase 2 + 3 in dark mode. Note any rendering regressions:
    - Cream backgrounds should become graphite (`#18181b`)
    - Ink text should become cream
    - Violet accent should shift to lavender
    - Strip primed nodes should become cyan (not violet)
87. Verify the theme persists across navigation (no flash of unstyled content).
88. Switch theme with the inline reconstruction panel open. Verify the panel re-renders correctly without losing typed state.

### 5.2 Responsive

89. Resize browser to 720px wide (tablet). Verify:
    - Strip overlay drops to bottom-left
    - Entry title scales to ~26px
    - CTA still readable
90. Resize to 390px wide (mobile). Verify:
    - Strip is shorter (~84px)
    - Active-name label truncates with ellipsis if long
    - CTA goes full-width
    - Inline reconstruction composer remains usable
    - Touch targets on strip nodes are at least 28×28 (the SVG `<rect>` overlay)

## Phase 6 — Edge cases & stress

### 6.1 Browser back

91. With the inline reconstruction panel open, press the browser BACK button. Document whether the app exits, stays on the concept page, or loses unsaved text.

### 6.2 Refresh inside reconstruction

92. With the inline reconstruction panel open, hard-refresh (`Cmd+Shift+R`). Note where you land and whether saved training evidence remains available.

### 6.3 Rapid concept hop

93. Open Concept A. Wait for it to render. Open Concept B. Verify the strip + work column show Concept B's data, NOT Concept A's (no ghost nodes from a stale render).

### 6.4 Idle session

94. (Optional, time-permitting) Leave the inline reconstruction panel idle for 15+ minutes. Try to save an attempt. Note any auth-expiry or session-loss behavior.

### 6.5 Long input

95. In the inline reconstruction textarea, paste 3000+ characters of text. Press "Save what I wrote". Note whether:
    - There's a character limit warning
    - The backend accepts the payload
    - The AI response handles the long input

## Output format — required

Produce a markdown report with this structure:

```markdown
# Socratink MVP QA Report — {date}

**Tester:** {your model name}
**Build under test:** {git SHA or branch tip}
**Test environment:** {URL + viewport + theme}
**Test duration:** {start time → end time}

## Phase results table

| Phase | Tests run | Pass | Fail | Notes |
|--|--|--|--|--|
| 1 Landing + concept creation | 18 | ?? | ?? | |
| 2 Concept page B-2 layout | 35 | ?? | ?? | |
| 3 Inline reconstruction | 9 | ?? | ?? | |
| 4 Doctrine + copy audit | 3 | ?? | ?? | |
| 5 Theme + responsive | 6 | ?? | ?? | |
| 6 Edge cases & stress | 5 | ?? | ?? | |

## Bugs found

### BLOCKER bugs
{List with: bug ID, surface, repro, expected, actual, evidence (DOM snippet/screenshot)}

### HIGH severity
{Same format}

### MEDIUM severity
{Same format}

### LOW / NOTE
{Same format}

## Doctrine violations

For each violation: surface, exact quote, why it violates the doctrine.

## Strengths to preserve

3-5 things that worked particularly well — call them out so the team doesn't accidentally break them in a future patch.

## Verdict

One paragraph. One of:

- **SHIP** — clean to merge.
- **SHIP-WITH-PATCH** — clean to merge if the BLOCKER + HIGH bugs above are addressed first.
- **DO-NOT-MERGE-UNTIL** — fundamental issue requires re-design or significant fix.

Justify the verdict in the paragraph.
```

## How to interpret pass/fail

- **Pass (✓):** Step completed exactly as described, no unexpected console errors or visual artifacts.
- **Fail (✗):** Step did not complete as described, OR completed with side effects not in the spec, OR threw a console error you can't trace to a known harmless source (e.g., the speed-insights 404).

When a step fails, capture:
- The exact step number
- What you expected
- What you observed (with DOM/screenshot evidence)
- Severity (your judgment): BLOCKER / HIGH / MEDIUM / LOW

## When to escalate vs continue

- **Continue** if a step fails but the next steps are still testable.
- **Escalate** if a step fails and blocks all subsequent steps (e.g., guest login is broken so nothing else can be tested). In this case, write the report up to the failure and surface it as a BLOCKER.

## Final note

Be honest. The founder is shipping to first learners on this build. A ✓ that hides a problem is worse than a ✗ that surfaces a real one. If something looks subjectively off but you can't find a concrete bug, note it under "Strengths to preserve" with a "but verify with the founder" caveat. Don't pad the report.

Report complete when the verdict is written. Estimated test time: 25–45 minutes for a thorough run.
