1. Repo Overview
What it is
socratink-app is a FastAPI + vanilla JS app deployed via Vercel serverless, with Gemini doing both knowledge-map extraction and Socratic drill evaluation. The app stores concept state in browser localStorage, renders a graph with Cytoscape, and runs a three-phase loop: cold attempt → study → spaced re-drill.
Tech stack
	•	Backend: FastAPI, Pydantic, google-genai, youtube-transcript-api
	•	Frontend: vanilla JS, Cytoscape, localStorage/sessionStorage
	•	Hosting: Vercel serverless via api/index.py + vercel.json
	•	AI layer: prompt assets in learnops/skills/*
	•	Analytics: JSONL logs + summary endpoints/scripts
Repo shape
Core files I inspected:
	•	README.md
	•	main.py
	•	ai_service.py
	•	public/js/app.js
	•	public/js/graph-view.js
	•	public/js/store.js
	•	public/js/ai_service.js
	•	scripts/summarize_ai_runs.py
	•	docs/project/state.md
	•	docs/drill/engineering.md
	•	learnops/skills/learnops-extract/extract-system-v1.txt
	•	learnops/skills/learnops-drill/SKILL.md
	•	requirements.txt
	•	vercel.json
Recent commit signal
Recent activity is hot, with multiple commits in late March and early April 2026. The repo is actively changing. The strongest pattern is not “stable product scaling,” it is “MVP doctrine + loop refinement + UI adjustment + docs-heavy stabilization.”
Recent examples:
	•	73800c4 — “updating crystal loading” (2026-04-07)
	•	c3970fe — rename/reposition to Socratink + three-phase loop plan
	•	208f5b1 — Vercel config update
	•	6a92ec0 — wire Socratic drill backend, harden security, move frontend to public/
That tells me the repo is alive, but still in active surgery.
Deploy status
There is a Vercel deployment target configured. That does not prove production health. The repo itself repeatedly warns not to confuse local success with hosted success.
Size / maturity
	•	Repo size from GitHub metadata: ~7.3 MB
	•	Front-end state machine is concentrated in a very large public/js/app.js
	•	This is not a toy scaffold. It has real product logic.
	•	It is also not mature enough to call “stable.”
One-sentence MVP thesis
It partially nails “rebuild knowledge from memory via Socratic AI,” but only as a fragile single-user prototype; the core loop exists, the graph is real enough to demo, and the lack of true persistence/user identity is a major blocker to serious retention.

2. Code Explanation
End-to-end execution flow

Diagram is not supported.

Core module 1: main.py
This is the API shell and the only real backend entrypoint.
What it does well:
	•	Strong request schemas with max_length guards
	•	Health endpoint
	•	Extraction endpoints for raw text, URL, and YouTube transcript
	•	Drill endpoint with logging and explicit error mapping
	•	Static file serving lockdown to avoid exposing .py and dotfiles
	•	Basic SSRF defense for URL fetches
What matters:
	•	/api/extract calls extract_knowledge_map
	•	/api/drill calls drill_chat
	•	_resolve_node_mechanism finds the authoritative mechanism text for the target node
	•	Drill transcripts and structured telemetry are logged
Brutal truth:
	•	This file is competent glue.
	•	It is not where the moat lives.
	•	It is also not where your hardest product risk lives.
Core module 2: ai_service.py
This is the actual product brain.
Extraction path
extract_knowledge_map(...)
	•	loads Gemini client
	•	sends raw text + extraction system prompt
	•	expects JSON only
	•	cleans fences
	•	validates JSON schema shape
	•	logs success/failure telemetry
Drill path
drill_chat(...)
	•	validates session phase and target node
	•	prunes the knowledge map around the target node
	•	appends hidden answer key into the system prompt
	•	asks Gemini for a strict structured response
	•	normalizes result into product rules
	•	increments session counters
	•	enforces node/time limits
	•	emits routing like NEXT, PROBE, SCAFFOLD, SESSION_COMPLETE
This is the repo’s strongest file.
Strengths
	•	Good normalization layer after LLM output
	•	Good use of structured responses instead of free-form parsing
	•	Pruned context is smart: it limits token cost and blast radius
	•	Separation between extraction and drill logic is clean
Weaknesses
	•	Product truth still depends heavily on LLM obedience
	•	“Graph mutation” is mostly derived from LLM classification plus frontend patching
	•	The system claims epistemic discipline, but it is still prompt-first, not model-verified
	•	No persistent learner model beyond the serialized graph object
Core module 3: public/js/app.js
This is the real MVP engine on the client.
What it handles:
	•	concept creation
	•	ingestion UI
	•	extraction overlay
	•	local concept storage
	•	graph view toggling
	•	drill session state
	•	session limits
	•	spacing/interleaving logic
	•	node progression
	•	tutorial mode
	•	analytics navigation
	•	theming
This is both impressive and dangerous.
Why impressive
	•	The product loop is actually wired
	•	Cold attempt, study, re-drill, spacing, node gating: all exist
	•	The graph is not decorative; it reacts to drill outcomes
	•	There is real UX thought here
Why dangerous
	•	It is a god-file
	•	Business logic, UI orchestration, storage rules, analytics hooks, and drill protocol all live together
	•	A solo founder can move fast with this until the file becomes a landmine
	•	That moment is coming
Core module 4: public/js/graph-view.js
This transforms the extracted JSON map into the graph UI.
What it does:
	•	converts knowledge map into graph nodes and edges
	•	derives cluster/backbone/subnode states
	•	enforces “reachable now” vs locked visuals
	•	manages inspect/study/drill/post-drill detail panels
	•	handles graph animation and interaction modes
This file is one of the best parts of the repo.
Strengths
	•	Real graph semantics, not fake bubbles
	•	State derivation is thoughtful
	•	Good separation between representation and display
	•	Supports the “graph tells the truth” doctrine better than I expected
Limitation
The graph is still a projection of a JSON blob. It is not a true learning graph engine with durable user-level history.
Core module 5: public/js/store.js
This is the state truth on the client.
What it does:
	•	stores concepts in localStorage
	•	normalizes legacy drill states
	•	keeps transient full text out of localStorage
	•	exposes active concept helpers
This is a practical MVP move.
This is also the smoking gun: the “system of record” for learner progress is basically the browser.
What’s elegant/scalable
	•	Backend structured response normalization
	•	Pruned drill context
	•	Explicit node-state progression
	•	Derived graph state rather than arbitrary UI status
	•	Logging/analytics plumbing for extraction and drill turns
	•	SSRF awareness on URL ingestion
	•	Vercel-compatible thin Python entrypoint
That is not fluff. There is real architectural taste here.

3. Gaps & Missing MVP Essentials
Critical
These break the business, not just the code.
1) No real persistence / no user memory
This is the main blocker.
Yes, there is localStorage. No, that is not product-grade persistence for a multi-session Socratic learning product.
What this means in practice:
	•	no user identity
	•	no durable cross-device continuity
	•	no true long-term progress ledger
	•	no server-side recovery
	•	easy wipe on browser clear/reset
	•	weak retention loop
	•	no real subscription enforcement
	•	no defensible data asset
For Socratink, this is not “missing polish.” It attacks the core value proposition.
2) No authentication / account system
No auth means:
	•	no saved learner history tied to a person
	•	no billing readiness
	•	no cohort analytics
	•	no teacher/team/shared graph future
	•	no real retention mechanics
3) Product truth still depends on LLM judgment
The repo says “the graph tells the truth.” That is aspirational.
Reality:
	•	extraction truth = LLM output + schema validation
	•	drill truth = LLM classification + normalization
	•	no independent verification layer
	•	no replay harness proving consistent outcomes on canonical cases
This is tolerable for MVP taste tests.It is not robust enough for “truth” branding.
4) No reliable automated test harness for the core loop
I found docs, telemetry, and manual release-gate doctrine. I did not find a real automated test suite for the core loop.
That means:
	•	regressions can slip through on drill state transitions
	•	hosted/local divergence is underdefended
	•	your “truthful graph” promise can silently rot
High
These hurt UX, trust, or survivability.
5) Frontend god-object architecture
public/js/app.js is carrying too much.Risk:
	•	brittle state bugs
	•	feature additions become slower
	•	hard-to-reproduce regressions
	•	solo-founder velocity eventually collapses
6) Session logic is split across frontend and backend
Some limits and progression logic are backend-enforced, some client-enforced, some patched client-side after backend classification.
That creates:
	•	drift risk
	•	duplicated rules
	•	edge-case mismatch
	•	“graph says one thing, backend expects another” danger
7) Ingestion path fragility
The app supports:
	•	raw text
	•	file upload
	•	URL extraction
	•	YouTube transcript extraction
This is ambitious for MVP. Also fragile.Hosted YouTube issues are already acknowledged in docs.
8) API key handling in localStorage
The product allows storing a Gemini API key in browser localStorage.That is a reasonable founder hack.It is not a serious production pattern.
9) No monetization path in code
No subscriptions, no usage caps tied to accounts, no billing hooks. That means no revenue loop yet.
Medium
These are not fatal today, but they accumulate.
10) Prompt-heavy product logic
A lot of behavior is in prompt docs, not enforceable code.Great for fast iteration.Bad for reproducibility.
11) No mature replay framework
There is telemetry summarization. Good.There is not a convincing replay rig for canonical learner transcripts. Bad.
12) Manual release discipline is doing work that automation should do
The docs are compensating for missing engineering infrastructure.

Prioritized by impact
Priority
Issue
Why it matters
Critical
No true persistence
Kills continuity, retention, and product compounding
Critical
No auth/accounts
No durable learner identity, no monetization path
Critical
LLM-as-truth without robust replay tests
Core promise can drift silently
Critical
Missing automated core-loop tests
Regression risk on the very thing you’re selling
High
Giant app.js
State bugs and slowed iteration
High
Split client/server progression logic
Drift and edge-case failures
High
Ingestion fragility
Real users hit import failures fast
High
Browser-stored API key
Unsafe production pattern
Medium
Prompt-heavy behavior
Harder to stabilize
Medium
Analytics without enough replay coverage
You can observe failure but not reliably prevent it

4. Persistent Memory Blueprint (New Gap)
Acknowledge
No real persistence exists yet in the only way that matters for this product.
Current state is browser localStorage, plus some session storage and logs. That is not multi-session continuity in a serious sense. Users can lose their graphs, progress, drill history, spacing state, and learning trajectory.
For Socratink, this undermines:
	•	retention
	•	mastery tracking
	•	spaced return
	•	trust
	•	billing
	•	habit formation
Product Vision
A user should be able to return and hear:
“Last time you missed the causal link between X and Y. Ready to rebuild it from memory?”
That requires:
	•	durable user identity
	•	persisted concept graph
	•	node-level history
	•	time-based revisit scheduling
	•	session journal
	•	retrieval analytics over time
Options
Option
Description
Pros
Cons
Effort (Solo Founder)
Socratink Fit
Session Redis
Store user_id -> serialized graph/session in Redis.
Fast, simple, great for active sessions, low latency.
Weak long-term durability alone, limited analytics/querying, not enough for mastery history.
Low
Only good as a stopgap for session continuity.
Postgres + pgvector
Relational storage for users, concepts, nodes, drill turns, plus embeddings for semantic recall/history search.
Durable, queryable, cheap, flexible, supports billing/auth/analytics, enough for history-aware drills.
Schema work, migrations, some complexity, embedding pipeline adds latency.
Medium
Best MVP choice by far.
Full Graph DB (Neo4j)
Native graph persistence for nodes/edges/mastery state.
Elegant graph queries, native traversal, future-rich visual products.
Operational overhead, extra cost, overkill early, splits product data model.
High
Future fit, wrong first move.
Recommendation
Start with Postgres.
Not because it is sexy.Because it solves the actual business problem.
Minimal schema
	•	users
	•	concepts
	•	concept_sources
	•	knowledge_maps
	•	knowledge_nodes
	•	drill_sessions
	•	drill_turns
	•	node_mastery_events
	•	revisit_queue
What to persist
Per concept:
	•	source title
	•	raw extracted map JSON
	•	normalized node records
	•	active graph state
	•	last opened timestamp
Per node:
	•	node_id
	•	label
	•	type
	•	drill_status
	•	drill_phase
	•	gap_type
	•	gap_description
	•	cold_attempt_at
	•	study_completed_at
	•	re_drill_eligible_after
	•	re_drill_count
	•	re_drill_band
	•	last_drilled
Per turn:
	•	learner text
	•	assistant text
	•	classification
	•	routing
	•	response tier/band
	•	latency
	•	model version
	•	prompt version
Migration strategy
	1	Add auth
	2	Save new concepts to Postgres
	3	Save drill turns server-side
	4	Persist graph state server-side
	5	Add “resume last session” API
	6	Add revisit queue endpoint
	7	Backfill localStorage import once on first login
Why Postgres wins
Because it unifies:
	•	persistence
	•	auth
	•	analytics
	•	freemium enforcement
	•	revisit scheduling
	•	product memory
Freemium fit
	•	Free: 10 saved sessions / 3 active concepts / limited history
	•	Pro: unlimited concepts, unlimited history, revisit queue, analytics, shareable graphs
That is a real business skeleton.

5. Useful Feature Ideas
Ranked by effort/reward, not fantasy.
Rank
Feature
Reward
Effort
Why it matters
1
True multi-session memory
Very high
Medium
Converts demo into retention product
2
Revisit queue / “resume weak links”
Very high
Medium
Makes spacing visible and habit-forming
3
A/B mode: Socratic drill vs direct explanation
High
Medium
Gives you PMF signal instead of vibes
4
Shareable graph snapshots
High
Low-Med
Social proof, user pride, virality, teacher use cases
5
Voice drill mode
High
Med-High
Strong fit for recall practice and ADHD-friendly usage
My ruthless priors for Socratink
1) Multi-session memory
Not optional. This is the product.
2) Revisit queue
A daily queue of “what is weak and why” is likely more valuable than prettier graph animations.
3) Shareable mastery maps
If users can share:
	•	“what I’ve mapped”
	•	“what I solidified”
	•	“what I still miss”
you get social proof and identity.
4) A/B testable drill paths
You need evidence that Socratic reconstruction beats direct tutoring for retention and return rate.
5) Voice mode
Strong fit. Spoken recall is closer to tutoring and may unlock stickier usage.

6. Potential Problems
Bugs / security
Prompt injection
Risk: 7/10Raw source text goes straight into extraction. The model can be manipulated by adversarial content. Schema validation helps, but this is still vulnerable at the semantic layer.
Answer-key leakage in drill
Risk: 6/10The hidden answer key is appended to the drill prompt. The product relies on prompt discipline not to leak it. That is fragile.
Browser-stored Gemini key
Risk: 6/10Convenient, not production-safe.
SSRF / ingestion abuse
Risk: 4/10There is some real defense here: private-IP blocking, content-type checks, size limits, timeout. Better than most MVPs.
XSS
Risk: 3/10Escaping is handled reasonably in graph/detail/chat rendering.
Scalability
LLM cost growth
Risk: 8/10Every extraction is an LLM call. Every drill turn is an LLM call. Long sessions will burn tokens fast. The pruned context helps, and Flash is the right cheap model, but cost can still become ugly.
DB bottleneck post-persistence
Risk: 3/10 initiallyPostgres will be fine for a long time if the schema is sane.
Serverless latency / cold starts
Risk: 5/10Vercel + Python + external model API + logging = potential user-facing lag.
Architecture smells
Smell
Risk (1-10)
Notes
God file in app.js
8
Biggest technical smell in the repo
Split state authority between client/server
7
Easy drift vector
Prompt-driven core behavior
7
Fast now, fragile later
Graph truth projected from JSON blob
6
Good enough for MVP, limited as moat
Manual ops/docs replacing tests
6
Signals missing engineering muscle
Deploy risks
Secrets management
Risk: 5/10Server key via env is fine; browser key storage is not.
Error handling divergence local vs hosted
Risk: 7/10The repo itself warns about this repeatedly. That is a red flag and a sign of self-awareness.
No strong release harness
Risk: 8/10When your product promise is “truthful graph state,” you need replayable truth tests.

7. Overall Health Score (0-100)
Breakdown
Category
Score
Rationale
Core Loop
74
There is a real extraction → graph → drill → patch loop. This is not fake. The three-phase learning architecture is actually wired.
Code Quality
63
Backend is fairly disciplined. Frontend has a large god-file and state entanglement.
Persistence Gap
18
This is the biggest deduction. Browser storage is not durable product memory.
Gaps / MVP Essentials
41
No auth, no billing, no robust automated loop tests, no durable learner identity.
Problems / Risk
52
Prompt dependence, hosted/local divergence, cost growth, and fragile state logic are real risks.
Weighted MVP Signal
Using your weights:
	•	Core Loop (40%): 74 → 29.6
	•	Code Quality (20%): 63 → 12.6
	•	Persistence Readiness (15%): 18 → 2.7
	•	Gaps (15%): 41 → 6.15
	•	Problems (10%): 52 → 5.2
Overall Health Score
56 / 100
That is not dead.That is not launch-ready.That is “promising prototype with one brutal blocker and several solvable risks.”

Final Verdict
Ship narrowly, not broadly. Do not pivot. Do not call it done. Do not pretend this is a durable learning platform yet.
This repo has something real:
	•	a coherent doctrine
	•	an implemented learning loop
	•	a graph that actually does product work
	•	enough architecture to justify continuing
But the business is still standing on browser-local sand.
One actionable next step
Wire Postgres-backed persistence first.
Not prettier graphs.Not more starter maps.Not more doctrine docs.
Persistence first, because that is the line between:
	•	a memorable demo, and
	•	a compounding learning product.
