# Socratink.ai PRD: LLM KB + MemPalace Integration

## Product Overview

Socratink.ai is a metacognitive SaaS transforming docs into interactive knowledge graphs for active recall quizzes, emphasizing "Generation Before Recognition" to expose and close understanding gaps. This PRD specifies integrating Karpathy's LLM Knowledge Base (KB) as a compilation layer with MemPalace as persistent memory/retrieval, creating an agentic backbone for product KB management, user learning loops, and scalable recall.

Scope: MVP adds KB+Palace to core upload->graph->quiz flow; agents handle ingest/compile/query autonomously. Excludes: Multi-tenant sharding (Phase 2).

Success Metrics:

- 90% agent-autonomy in KB hygiene (pre/post lint recall@5 >95%).
- User recall lift: +25% graph rebuild accuracy via KG priors.
- Token efficiency: <10k ctx for map gen (wiki+MemPalace vs. raw).

## Objectives & Key Results

Obj1: Durable product memory--codify logs/docs into queryable truth for dev agents (e.g., "the-socratinker").

KR1: Compile 100+ artifacts into wiki w/ backlinks; 99% traceability.

Obj2: Enhance user graphs w/ persistent recall.

KR2: Mine sessions to Palace; +30% quiz personalization via temporal KG.

Obj3: Agentic scalability--offload hygiene to MCP hooks.

KR3: 5-min ingest->quiz cycle; <1% hallucination on priors.

## User Personas & Journeys

| Persona | Needs | Journey w/ Integration |
| --- | --- | --- |
| Nurse/PA (You) | Clinical protocol mastery; log->workflow synthesis. | Upload traces -> Auto-mine to Palace wing -> Wiki compiles mechanisms -> Quiz rebuilds gaps. |
| Dev/Founder | Product-memory hygiene; spec evolution. | the-socratinker ingest logs/ -> Lint -> Query "UX implications". |
| Learner Pro | Persistent vaults across sessions. | Freemium: Per-wing graphs; Pro: Cross-wing KG recall. |

Happy Path (User): Upload doc -> Palace indexes -> Wiki summarizes -> Graph gen (cited) -> Rebuild quiz -> Gaps -> Personalized spacing.

Happy Path (Agent): mcp ingest raw/artifact.md -> Compile wiki -> Mine triples -> Health-check -> Respond cited.

## Functional Requirements

### Core Components

Folder Structure (Git-ignored vaults):

```text
kb/
├── raw/          # Immutable sources (logs, docs)
├── wiki/         # LLM Markdown (entities, concepts, backlinks)
│   └── schema.yaml # KB rules ("every page states product implication")
└── mempalace/    # Wings: socratink-dev, clinical-recall
    ├── chroma/   # Semantic search DB
    └── kg.sqlite # Temporal triples (e.g., Node -> Gap -> 2026-04-13)
```

Ingest Pipeline (Agentic, via Claude MCP):

- Raw drop -> the-socratinker compile (10+ wiki touches).
- mempalace mine --wing clinical (verbatim + summaries).

Query Engine:

- Palace semantic/KG first -> Wiki synthesis -> Graph output (Marp/JSON).
- Tools: 19 MCP (search_entities, timeline, invalidate).

Lint/Health:

- Daily: Check inconsistencies, missing links, gap ideas.

### Tech Stack Additions

- MemPalace: pip install mempalace -> mcp_server endpoint.
- Wiki: Karpathy Gist schema + "the-socratinker" prompts.
- Agents: Claude Code w/ MCP; fallback local Ollama.
- UI: Vault selector; Graphviz for palace preview.

## Non-Functional Requirements

- Perf: Ingest <2min/artifact; Query <5s (local Chroma).
- Privacy: 100% local/offline; No API keys.
- Scalability: 10k nodes/wing; SQLite partitioning.
- Reliability: Triple-backup (git raw/wiki, Palace export); Rollback via schema.

## Dependencies & Risks

| Dep | Status | Risk |
| --- | --- | --- |
| MemPalace v0.x | Stable | Palace schema drift -> Mitigate: Pin version. |
| Claude MCP | Beta | Offline fallback -> Ollama sim. |
| Graph Gen | Existing | KG overload -> Prune >30d invalids. |

Risks: Over-reliance on agent output (Mit: Human veto in schema); Graph bloat (Mit: Auto-prune low-recall nodes).

## Implementation Phases

Week 1 (MVP): Init kb/mempalace; Wire ingest script; Test "the-socratinker" on 10 logs.

Week 2: UI vault integration; Agent query hooks; E2E clinical demo.

Week 3: Lint cron; Metrics dashboard; Beta user vaults.

Launch: Docker compose; Docs: readme.md w/ happy paths.

## Deliberation Prompts for Codebase Agent

Build: "Emit folder scaffold + ingest CLI using MemPalace MCP and socratinker schema."

Maintain: "Lint kb/wiki: Flag uncited implications; Propose merges."

Query: "Synthesize 'recall happy path risks' -> File as new wiki page w/ citations."

Health-Check: "Score KB density (pages/sources); Alert if <0.8."

Approve for agent deliberation: Prioritize ingest -> query loop; Iterate via PRs on this PRD.
