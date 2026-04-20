# Hermes Agent - Socratink Concept Source

Source: Hermes Agent documentation by Nous Research, retrieved 2026-04-18.
Primary docs site: https://hermes-agent.nousresearch.com/docs/
GitHub source tree: https://github.com/NousResearch/hermes-agent/tree/main/website/docs
Source tree SHA: `8a0c774e9efd771c317e6f158a080ea19267182b`

This file is intentionally compressed below Socratink extraction limits. It is a learnable concept source derived from the public Hermes Agent documentation, not a verbatim mirror of every page. Use `docs/reference/hermes-agent-docs-manifest.md` as the full bibliography and page map.

## Core Thesis
Hermes Agent is an autonomous, self-improving agent that can run outside the user laptop, communicate through CLI and messaging platforms, use tools and MCP integrations, remember across sessions, create and improve reusable skills, delegate work to subagents, run scheduled automations, and operate across local, container, remote, and serverless environments.

## System Boundary
Hermes is not just a chat UI or IDE copilot. The product combines an agent loop, terminal/runtime backends, provider routing, tool execution, memory, skills, messaging gateways, security approvals, context assembly, and optional research workflows into one long-running agent system.

## Learning Loop
The distinctive mechanism is closed-loop improvement: Hermes observes work, stores durable memory, retrieves prior sessions through search and summarization, nudges itself to preserve knowledge, creates skills after repeated tasks, and improves skills while they are used. The learner should understand how memory, skills, context, tools, and runtime execution reinforce one another.

## Operating Model
A user can talk to Hermes in the terminal or through messaging platforms. Hermes selects a model/provider, assembles context from config, SOUL/personality, project files, memory, skills, tools, and session state, then executes work in an environment backend. Tool calls may run locally, in containers, over SSH, or in serverless/persistent remote environments.

## Safety Model
Hermes exposes powerful tools, so safe operation depends on command approval, authorization, scoped toolsets, MCP filtering, secrets handling, sandbox/container isolation, user confirmation for risky actions, and clear separation between configuration, credentials, runtime environments, and externally reachable gateway surfaces.

## Extensibility Model
Hermes expands through providers, tools, toolsets, MCP servers, platform adapters, memory provider plugins, context engine plugins, skills, hooks, skins, profiles, and dashboard plugins. Each extension point has its own boundary: providers route model calls, tools perform actions, skills encode procedures, memory stores durable facts, and messaging adapters expose conversations.

## Learning Path

1. Start with the product frame: what Hermes is, where it runs, and why an agent that persists beyond one laptop changes the user workflow.
2. Learn the core interaction paths: CLI/TUI, slash commands, sessions, checkpoints, rollback, profiles, and configuration.
3. Study the closed learning loop: memory providers, memory search, Honcho user modeling, skills, skill creation, and self-improvement.
4. Study the action layer: built-in tools, toolsets, code execution, browser/vision/image/voice capabilities, and tool gateway behavior.
5. Study integration surfaces: model providers, MCP servers, messaging gateway platforms, cron automations, hooks, dashboard plugins, and external APIs.
6. Study runtime and deployment choices: local, Docker, SSH, Daytona, Singularity, Modal, Termux, Nix, and serverless persistence tradeoffs.
7. Study safety and operations: security rules, credential pools, approvals, environment variables, troubleshooting, provider fallback, and update/migration paths.
8. Study developer internals last: agent loop, architecture, prompt assembly, context compression/caching, provider runtime, tools runtime, gateway internals, session storage, cron internals, and trajectory format.

## Map-Relevant Mechanisms

- **Agent loop:** Turns user messages, assembled context, model outputs, tool calls, approvals, and observations into iterative work until the task is complete or blocked.
- **Context assembly:** Combines configuration, SOUL/personality, context files, memory, skills, active session state, and tool definitions so the model receives the right operating frame.
- **Memory system:** Persists selected facts and summaries across sessions, then retrieves them through search and summarization so future turns can build on past work.
- **Skills system:** Stores procedural know-how as reusable instructions; Hermes can create and improve skills from repeated work patterns.
- **Tool and toolset runtime:** Exposes controlled actions such as shell, browser, search, files, messaging, image generation, and MCP-backed capabilities. Toolsets scope which actions are available.
- **Provider routing:** Lets Hermes use Nous Portal, OpenRouter, OpenAI-compatible endpoints, local models, or other providers while preserving a common agent interface.
- **Messaging gateway:** Connects the same agent to Telegram, Discord, Slack, WhatsApp, Signal, email, SMS, Matrix, Mattermost, WeCom, Feishu, DingTalk, BlueBubbles, Home Assistant, and related platforms.
- **Environment backends:** Let work run locally, in Docker, over SSH, through Daytona, Singularity, Modal, or other persistent/serverless execution contexts.
- **Cron and automations:** Schedules natural-language tasks that wake Hermes up and deliver results through the configured platform.
- **Security boundary:** Uses approvals, command authorization, credential management, container isolation, MCP/tool filtering, and explicit configuration to reduce risk from powerful agent actions.
- **Developer extension points:** Providers, tools, adapters, plugins, hooks, memory providers, context plugins, skins, and skills let developers add behavior without collapsing all logic into the core loop.

## Documentation Coverage

### Developer Guide
- **ACP Internals:** How the ACP adapter works: lifecycle, sessions, event bridge, approvals, and tool rendering Source: https://hermes-agent.nousresearch.com/docs/developer-guide/acp-internals/
- **Adding a Platform Adapter:** This guide covers adding a new messaging platform to the Hermes gateway. A platform adapter connects Hermes to an external messaging service (Telegram, Discord, WeCom, etc.) so users can interact with the agent through that service. Source: https://hermes-agent.nousresearch.com/docs/developer-guide/adding-platform-adapters/
- **Adding Providers:** How to add a new inference provider to Hermes Agent — auth, runtime resolution, CLI flows, adapters, tests, and docs Source: https://hermes-agent.nousresearch.com/docs/developer-guide/adding-providers/
- **Adding Tools:** How to add a new tool to Hermes Agent — schemas, handlers, registration, and toolsets Source: https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools/
- **Agent Loop Internals:** Detailed walkthrough of AIAgent execution, API modes, tools, callbacks, and fallback behavior Source: https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop/
- **Architecture:** Hermes Agent internals — major subsystems, execution paths, data flow, and where to read next Source: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/
- **Context Compression and Caching:** Hermes Agent uses a dual compression system and Anthropic prompt caching to manage context window usage efficiently across long conversations. Source: https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching/
- **Context Engine Plugins:** How to build a context engine plugin that replaces the built-in ContextCompressor Source: https://hermes-agent.nousresearch.com/docs/developer-guide/context-engine-plugin/
- **Contributing:** How to contribute to Hermes Agent — dev setup, code style, PR process Source: https://hermes-agent.nousresearch.com/docs/developer-guide/contributing/
- **Creating Skills:** How to create skills for Hermes Agent — SKILL.md format, guidelines, and publishing Source: https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills/
- **Cron Internals:** How Hermes stores, schedules, edits, pauses, skill-loads, and delivers cron jobs Source: https://hermes-agent.nousresearch.com/docs/developer-guide/cron-internals/
- **Environments, Benchmarks & Data Generation:** Building RL training environments, running evaluation benchmarks, and generating SFT data with the Hermes-Agent Atropos integration Source: https://hermes-agent.nousresearch.com/docs/developer-guide/environments/
- **Extending the CLI:** Build wrapper CLIs that extend the Hermes TUI with custom widgets, keybindings, and layout changes Source: https://hermes-agent.nousresearch.com/docs/developer-guide/extending-the-cli/
- **Gateway Internals:** How the messaging gateway boots, authorizes users, routes sessions, and delivers messages Source: https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-internals/
- **Memory Provider Plugins:** How to build a memory provider plugin for Hermes Agent Source: https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin/
- **Prompt Assembly:** How Hermes builds the system prompt, preserves cache stability, and injects ephemeral layers Source: https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly/
- **Provider Runtime Resolution:** How Hermes resolves providers, credentials, API modes, and auxiliary models at runtime Source: https://hermes-agent.nousresearch.com/docs/developer-guide/provider-runtime/
- **Session Storage:** Hermes Agent uses a SQLite database ( ~/.hermes/state.db ) to persist session metadata, full message history, and model configuration across CLI and gateway sessions. This replaces the earlier per-session JSONL file approach. Source: https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage/
- **Tools Runtime:** Runtime behavior of the tool registry, toolsets, dispatch, and terminal environments Source: https://hermes-agent.nousresearch.com/docs/developer-guide/tools-runtime/
- **Trajectory Format:** Hermes Agent saves conversation trajectories in ShareGPT-compatible JSONL format for use as training data, debugging artifacts, and reinforcement learning datasets. Source: https://hermes-agent.nousresearch.com/docs/developer-guide/trajectory-format/

### Getting Started
- **Installation:** Install Hermes Agent on Linux, macOS, WSL2, or Android via Termux Source: https://hermes-agent.nousresearch.com/docs/getting-started/installation/
- **Learning Path:** Choose your learning path through the Hermes Agent documentation based on your experience level and goals. Source: https://hermes-agent.nousresearch.com/docs/getting-started/learning-path/
- **Nix & NixOS Setup:** Install and deploy Hermes Agent with Nix — from quick `nix run` to fully declarative NixOS module with container mode Source: https://hermes-agent.nousresearch.com/docs/getting-started/nix-setup/
- **Quickstart:** Your first conversation with Hermes Agent — from install to chatting in 2 minutes Source: https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/
- **Android / Termux:** Run Hermes Agent directly on an Android phone with Termux Source: https://hermes-agent.nousresearch.com/docs/getting-started/termux/
- **Updating & Uninstalling:** How to update Hermes Agent to the latest version or uninstall it Source: https://hermes-agent.nousresearch.com/docs/getting-started/updating/

### Guides And Tutorials
- **Automate Anything with Cron:** Real-world automation patterns using Hermes cron — monitoring, reports, pipelines, and multi-skill workflows Source: https://hermes-agent.nousresearch.com/docs/guides/automate-with-cron/
- **Automation Templates:** Ready-to-use automation recipes — scheduled tasks, GitHub event triggers, API webhooks, and multi-skill workflows Source: https://hermes-agent.nousresearch.com/docs/guides/automation-templates/
- **AWS Bedrock:** Use Hermes Agent with Amazon Bedrock — native Converse API, IAM authentication, Guardrails, and cross-region inference Source: https://hermes-agent.nousresearch.com/docs/guides/aws-bedrock/
- **Build a Hermes Plugin:** Step-by-step guide to building a complete Hermes plugin with tools, hooks, data files, and skills Source: https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin/
- **Cron Troubleshooting:** Diagnose and fix common Hermes cron issues — jobs not firing, delivery failures, skill loading errors, and performance problems Source: https://hermes-agent.nousresearch.com/docs/guides/cron-troubleshooting/
- **Tutorial: Daily Briefing Bot:** Build an automated daily briefing bot that researches topics, summarizes findings, and delivers them to Telegram or Discord every morning Source: https://hermes-agent.nousresearch.com/docs/guides/daily-briefing-bot/
- **Delegation & Parallel Work:** When and how to use subagent delegation — patterns for parallel research, code review, and multi-file work Source: https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns/
- **Run Local LLMs on Mac:** Set up a local OpenAI-compatible LLM server on macOS with llama.cpp or MLX, including model selection, memory optimization, and real benchmarks on Apple Silicon Source: https://hermes-agent.nousresearch.com/docs/guides/local-llm-on-mac/
- **Migrate from OpenClaw:** Complete guide to migrating your OpenClaw / Clawdbot setup to Hermes Agent — what gets migrated, how config maps, and what to check after. Source: https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw/
- **Using Hermes as a Python Library:** Embed AIAgent in your own Python scripts, web apps, or automation pipelines — no CLI required Source: https://hermes-agent.nousresearch.com/docs/guides/python-library/
- **Tutorial: Team Telegram Assistant:** Step-by-step guide to setting up a Telegram bot that your whole team can use for code help, research, system admin, and more Source: https://hermes-agent.nousresearch.com/docs/guides/team-telegram-assistant/
- **Tips & Best Practices:** Practical advice to get the most out of Hermes Agent — prompt tips, CLI shortcuts, context files, memory, cost optimization, and security Source: https://hermes-agent.nousresearch.com/docs/guides/tips/
- **Use MCP with Hermes:** A practical guide to connecting MCP servers to Hermes Agent, filtering their tools, and using them safely in real workflows Source: https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes/
- **Use SOUL.md with Hermes:** How to use SOUL.md to shape Hermes Agent's default voice, what belongs there, and how it differs from AGENTS.md and /personality Source: https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes/
- **Use Voice Mode with Hermes:** A practical guide to setting up and using Hermes voice mode across CLI, Telegram, Discord, and Discord voice channels Source: https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes/
- **Working with Skills:** Find, install, use, and create skills — on-demand knowledge that teaches Hermes new workflows Source: https://hermes-agent.nousresearch.com/docs/guides/work-with-skills/

### Overview
- **Hermes Agent Documentation:** The self-improving AI agent built by Nous Research. A built-in learning loop that creates skills from experience, improves them during use, and remembers across sessions. Source: https://hermes-agent.nousresearch.com/docs/

### Integrations
- **Integrations:** Hermes Agent connects to external systems for AI inference, tool servers, IDE workflows, programmatic access, and more. These integrations extend what Hermes can do and where it can run. Source: https://hermes-agent.nousresearch.com/docs/integrations/
- **AI Providers:** This page covers setting up inference providers for Hermes Agent — from cloud APIs like OpenRouter and Anthropic, to self-hosted endpoints like Ollama and vLLM, to advanced routing and fallback configurations. You need at least one provider configured to... Source: https://hermes-agent.nousresearch.com/docs/integrations/providers/

### Reference
- **CLI Commands Reference:** Authoritative reference for Hermes terminal commands and command families Source: https://hermes-agent.nousresearch.com/docs/reference/cli-commands/
- **Environment Variables:** Complete reference of all environment variables used by Hermes Agent Source: https://hermes-agent.nousresearch.com/docs/reference/environment-variables/
- **FAQ & Troubleshooting:** Frequently asked questions and solutions to common issues with Hermes Agent Source: https://hermes-agent.nousresearch.com/docs/reference/faq/
- **MCP Config Reference:** Reference for Hermes Agent MCP configuration keys, filtering semantics, and utility-tool policy Source: https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/
- **Optional Skills Catalog:** Official optional skills shipped with hermes-agent — install via hermes skills install official/<category>/<skill> Source: https://hermes-agent.nousresearch.com/docs/reference/optional-skills-catalog/
- **Profile Commands Reference:** This page covers all commands related to Hermes profiles. For general CLI commands, see CLI Commands Reference. Source: https://hermes-agent.nousresearch.com/docs/reference/profile-commands/
- **Bundled Skills Catalog:** Catalog of bundled skills that ship with Hermes Agent Source: https://hermes-agent.nousresearch.com/docs/reference/skills-catalog/
- **Slash Commands Reference:** Complete reference for interactive CLI and messaging slash commands Source: https://hermes-agent.nousresearch.com/docs/reference/slash-commands/
- **Built-in Tools Reference:** Authoritative reference for Hermes built-in tools, grouped by toolset Source: https://hermes-agent.nousresearch.com/docs/reference/tools-reference/
- **Toolsets Reference:** Reference for Hermes core, composite, platform, and dynamic toolsets Source: https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference/

### User Guide
- **Checkpoints and /rollback:** Filesystem safety nets for destructive operations using shadow git repos and automatic snapshots Source: https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback/
- **CLI Interface:** Master the Hermes Agent terminal interface — commands, keybindings, personalities, and more Source: https://hermes-agent.nousresearch.com/docs/user-guide/cli/
- **Configuration:** Configure Hermes Agent — config.yaml, providers, models, API keys, and more Source: https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
- **Docker:** Running Hermes Agent in Docker and using Docker as a terminal backend Source: https://hermes-agent.nousresearch.com/docs/user-guide/docker/
- **ACP Editor Integration:** Use Hermes Agent inside ACP-compatible editors such as VS Code, Zed, and JetBrains Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/acp/
- **API Server:** Expose hermes-agent as an OpenAI-compatible API for any frontend Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server/
- **Batch Processing:** Generate agent trajectories at scale — parallel processing, checkpointing, and toolset distributions Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/batch-processing/
- **Browser Automation:** Control browsers with multiple providers, local Chrome via CDP, or cloud browsers for web interaction, form filling, scraping, and more. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/browser/
- **Code Execution:** Programmatic Python execution with RPC tool access — collapse multi-step workflows into a single turn Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution/
- **Context Files:** Project context files — .hermes.md, AGENTS.md, CLAUDE.md, global SOUL.md, and .cursorrules — automatically injected into every conversation Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files/
- **Context References:** Inline @-syntax for attaching files, folders, git diffs, and URLs directly into your messages Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-references/
- **Credential Pools:** Pool multiple API keys or OAuth tokens per provider for automatic rotation and rate limit recovery. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/credential-pools/
- **Scheduled Tasks (Cron):** Schedule automated tasks with natural language, manage them with one cron tool, and attach one or more skills Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/
- **Dashboard Plugins:** Build custom tabs and extensions for the Hermes web dashboard Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/dashboard-plugins/
- **Subagent Delegation:** Spawn isolated child agents for parallel workstreams with delegate_task Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/
- **Fallback Providers:** Configure automatic failover to backup LLM providers when your primary model is unavailable. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers/
- **Honcho Memory:** AI-native persistent memory via Honcho — dialectic reasoning, multi-agent user modeling, and deep personalization Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho/
- **Event Hooks:** Run custom code at key lifecycle points — log activity, send alerts, post to webhooks Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/
- **Image Generation:** Generate images via FAL.ai — 8 models including FLUX 2, GPT-Image, Nano Banana Pro, Ideogram, Recraft V4 Pro, and more, selectable via `hermes tools`. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/image-generation/
- **MCP (Model Context Protocol):** Connect Hermes Agent to external tool servers via MCP — and control exactly which MCP tools Hermes loads Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/
- **Memory Providers:** External memory provider plugins — Honcho, OpenViking, Mem0, Hindsight, Holographic, RetainDB, ByteRover, Supermemory Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/
- **Persistent Memory:** How Hermes Agent remembers across sessions — MEMORY.md, USER.md, and session search Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/
- **Features Overview:** Hermes Agent includes a rich set of capabilities that extend far beyond basic chat. From persistent memory and file-aware context to browser automation and voice conversations, these features work together to make Hermes a powerful autonomous assistant. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/overview/
- **Personality & SOUL.md:** Customize Hermes Agent's personality with a global SOUL.md, built-in personalities, and custom persona definitions Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/personality/
- **Plugins:** Extend Hermes with custom tools, hooks, and integrations via the plugin system Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins/
- **Provider Routing:** Configure OpenRouter provider preferences to optimize for cost, speed, or quality. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing/
- **RL Training:** Reinforcement learning on agent behaviors with Tinker-Atropos — environment discovery, training, and evaluation Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/rl-training/
- **Skills System:** On-demand knowledge documents — progressive disclosure, agent-managed skills, and the Skills Hub Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/
- **Skins & Themes:** Customize the Hermes CLI with built-in and user-defined skins Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/skins/
- **Nous Tool Gateway:** Route web search, image generation, text-to-speech, and browser automation through your Nous subscription — no extra API keys needed Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway/
- **Tools & Toolsets:** Overview of Hermes Agent's tools — what's available, how toolsets work, and terminal backends Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/
- **Voice & TTS:** Text-to-speech and voice message transcription across all platforms Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/tts/
- **Vision & Image Paste:** Paste images from your clipboard into the Hermes CLI for multimodal vision analysis. Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/vision/
- **Voice Mode:** Real-time voice conversations with Hermes Agent — CLI, Telegram, Discord (DMs, text channels, and voice channels) Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode/
- **Web Dashboard:** Browser-based dashboard for managing configuration, API keys, sessions, logs, analytics, cron jobs, and skills Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard/
- **Git Worktrees:** Run multiple Hermes agents safely on the same repository using git worktrees and isolated checkouts Source: https://hermes-agent.nousresearch.com/docs/user-guide/git-worktrees/
- **BlueBubbles (iMessage):** Connect Hermes to Apple iMessage via BlueBubbles — a free, open-source macOS server that bridges iMessage to any device. Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles/
- **DingTalk:** Set up Hermes Agent as a DingTalk chatbot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/dingtalk/
- **Discord:** Set up Hermes Agent as a Discord bot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord/
- **Email:** Set up Hermes Agent as an email assistant via IMAP/SMTP Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/email/
- **Feishu / Lark:** Set up Hermes Agent as a Feishu or Lark bot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu/
- **Home Assistant:** Control your smart home with Hermes Agent via Home Assistant integration. Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/homeassistant/
- **Messaging Gateway:** Chat with Hermes from Telegram, Discord, Slack, WhatsApp, Signal, SMS, Email, Home Assistant, Mattermost, Matrix, DingTalk, Webhooks, or any OpenAI-compatible frontend via the API server — architecture and setup overview Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
- **Matrix:** Set up Hermes Agent as a Matrix bot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/matrix/
- **Mattermost:** Set up Hermes Agent as a Mattermost bot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/mattermost/
- **Open WebUI:** Connect Open WebUI to Hermes Agent via the OpenAI-compatible API server Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/open-webui/
- **QQ Bot:** Connect Hermes to QQ via the Official QQ Bot API (v2) — supporting private (C2C), group @-mentions, guild, and direct messages with voice transcription. Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/qqbot/
- **Signal:** Set up Hermes Agent as a Signal messenger bot via signal-cli daemon Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/signal/
- **Slack:** Set up Hermes Agent as a Slack bot using Socket Mode Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack/
- **SMS (Twilio):** Set up Hermes Agent as an SMS chatbot via Twilio Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/sms/
- **Telegram:** Set up Hermes Agent as a Telegram bot Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram/
- **Webhooks:** Receive events from GitHub, GitLab, and other services to trigger Hermes agent runs Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/
- **WeCom Callback (Self-Built App):** Connect Hermes to WeCom (Enterprise WeChat) as a self-built enterprise application using the callback/webhook model. Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/wecom-callback/
- **WeCom (Enterprise WeChat):** Connect Hermes Agent to WeCom via the AI Bot WebSocket gateway Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/wecom/
- **Weixin (WeChat):** Connect Hermes Agent to personal WeChat accounts via the iLink Bot API Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/weixin/
- **WhatsApp:** Set up Hermes Agent as a WhatsApp bot via the built-in Baileys bridge Source: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/whatsapp/
- **Profiles: Running Multiple Agents:** Run multiple independent Hermes agents on the same machine — each with its own config, API keys, memory, sessions, skills, and gateway. Source: https://hermes-agent.nousresearch.com/docs/user-guide/profiles/
- **Security:** Security model, dangerous command approval, user authorization, container isolation, and production deployment best practices Source: https://hermes-agent.nousresearch.com/docs/user-guide/security/
- **Sessions:** Session persistence, resume, search, management, and per-platform session tracking Source: https://hermes-agent.nousresearch.com/docs/user-guide/sessions/
- **G0DM0D3 — Godmode Jailbreaking:** Automated LLM jailbreaking using G0DM0D3 techniques — system prompt templates, input obfuscation, and multi-model racing Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/godmode/
- **Google Workspace — Gmail, Calendar, Drive, Sheets & Docs:** Send email, manage calendar events, search Drive, read/write Sheets, and access Docs — all through OAuth2-authenticated Google APIs Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/google-workspace/
- **TUI:** Launch the modern terminal UI for Hermes — mouse-friendly, rich overlays, and non-blocking input. Source: https://hermes-agent.nousresearch.com/docs/user-guide/tui/
