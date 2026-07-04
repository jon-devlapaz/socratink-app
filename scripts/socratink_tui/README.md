# Socratink TUI Legacy Lab

This directory is the legacy founder terminal lab. It is still covered by
`tests/test_socratink_tui.py`, but it is not the learner product runtime.

Use the root app-local SEDA runtime for product work:

- `lib/seda/`
- `lib/loop-server/`
- `bridge.py`
- `bridge_lib/`
- `learning_cases/`
- `pedagogical_agents/`
- `vendor/python/`

Use this directory only when a task explicitly targets the terminal dogfood
CLI, dashboard, or old harness wrappers:

- `scripts/socratink-tui`
- `scripts/socratink-dashboard`
- `scripts/socratink-harness`
