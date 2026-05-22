# socratink — Gestalt Hybrid Launch QA Agent Prompt

**Purpose.** A self-contained directive for a QA/browser agent to verify the
source-less sketch-to-scaffold loop from the real new concept entrance:
Ignition → Launch Pad → tailored first concept view → draft → reveal → repair →
expanded route.

**Hand-off.** Paste the **Directive** block below into a fresh Codex, Antigravity,
or browser-QA agent thread. The agent should be able to run shell commands and
control Chromium/Playwright. This is a read-only QA pass unless a bug is found
and the owner explicitly asks the agent to fix it.

---

## Directive

> **Role:** You are a QA browser agent auditing one Socratink feature:
> the source-less Gestalt Hybrid launch loop. Your job is to run the flow,
> capture bugs/logs, and report findings. **Do not modify code.**
>
> **Repository:**
>
> ```bash
> cd /Users/jondev/dev/socratink/prod/socratink-app
> ```
>
> **Start the app if needed:**
>
> ```bash
> curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/health
> ```
>
> If that does not return `200`, start the local dev server:
>
> ```bash
> SOCRATINK_E2E_LOCAL_GUEST=1 bash scripts/dev.sh
> ```
>
> Keep the server running while you test.
>
> **First run the deterministic QA test:**
>
> ```bash
> SOCRATINK_E2E_LOCAL_GUEST=1 .venv/bin/pytest tests/e2e/test_gestalt_hybrid_launch_qa.py -v
> ```
>
> This test uses the real Ignition and Launch Pad UI and mocks only
> `/api/extract` and `/api/drill`. If it fails, report the full pytest failure
> and inspect the Playwright trace under `test-results/` if one was generated.
>
> **Then run a manual browser QA pass at `http://127.0.0.1:8000/`.**
>
> Use this scenario:
>
> - Concept name: `Thermostat feedback loop`
> - Launch sketch:
>
> ```text
> I manage facilities for a small clinic. I think thermostats turn heat on when the room feels cold, but I am fuzzy on what they compare.
> ```
>
> If you need deterministic AI responses, mock only `/api/extract` and
> `/api/drill` with the same scenario shape used in
> `tests/e2e/test_gestalt_hybrid_launch_qa.py`. Do not seed localStorage with a
> pregenerated concept. The point of this QA pass is to use the real new concept
> entrance.
>
> **Required flow checks:**
>
> 1. Enter as guest and open **New concept** / Ignition.
> 2. Type the concept name and continue to Launch Pad.
> 3. Confirm Launch Pad shows the concept name and blocks thin sketches.
> 4. Enter the launch sketch and save it.
> 5. On the first concept view, verify:
>    - The first prompt is tailored to the sketch.
>    - A visible line like `Shaped by your sketch: ...` appears.
>    - The prompt asks for the learner's guess before study content appears.
>    - The mechanism answer is not visible before the draft.
>    - Generated descriptions do not leak before the draft.
>    - The route is inert/quiet before the learner has produced evidence.
> 6. Write a learner draft and save it.
> 7. Verify the saved-draft gate:
>    - The learner draft is visible.
>    - Study remains hidden until the explicit compare/reveal action.
>    - No gap/missing-piece copy appears before study reveal.
> 8. Reveal notes and compare.
> 9. Verify the comparison state:
>    - Study note appears.
>    - One missing link appears.
>    - The learner is not scored or diagnosed.
>    - The `Keep working` action appears.
> 10. Save a repair in the learner's own words.
> 11. Click `Keep working`.
> 12. Verify the route expands, but remains truthful:
>     - Current contract: future route entries are visible but inert until the
>       learner reconstructs/repairs enough evidence to move.
>     - Do not report inert future entries as a bug unless product ownership has
>       changed this contract.
>
> **Logs and failure capture:**
>
> Capture and report:
>
> - same-origin `console.error`
> - browser `pageerror`
> - same-origin failed requests
> - same-origin `4xx` or `5xx` responses
> - screenshots for any visible UI bug
> - trace path for any Playwright failure
>
> Cross-origin browser-extension noise is out of scope. Same-origin asset,
> API, or console failures are in scope.
>
> **Bug report format:**
>
> ```md
> ### [SEV-{1-4}] {Short title}
>
> **Where:** {Ignition | Launch Pad | first concept view | saved draft | comparison | repair | expanded route}
> **Severity:**
> - SEV-1 = broken flow, data loss, console/page error, same-origin 4xx/5xx
> - SEV-2 = product-truth violation, answer leak, route contract break, inaccessible control
> - SEV-3 = degraded UX, confusing copy, visual overlap, weak tailoring
> - SEV-4 = polish
>
> **What I saw:** {concrete observation}
> **What I expected:** {contract from this prompt}
> **Repro steps:** {numbered, lossless}
> **Evidence:** {screenshot path, trace path, console/request snippet}
> **Likely cause:** {optional, only if supported by evidence}
> ```
>
> End with:
>
> ```md
> ## Summary
> - Test command result:
> - Manual flow result:
> - Console/page errors:
> - Failed requests:
> - Open product questions:
> ```
