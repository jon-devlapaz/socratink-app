# Agent Config Compatibility Layer

This directory exists to make agent config resolution unambiguous for Codex.

Canonical agent definitions live under `.codex/agents/`.

The repo-level Codex config currently registers agents with paths like
`agents/rob.toml`. Depending on how `config_file` is resolved by the runtime,
that may be interpreted relative to the repo root or relative to
`.codex/config.toml`.

To keep the project robust across resolver behavior, this directory contains
symlinks that point to the canonical files in `.codex/agents/`.

This assumes a symlink-capable checkout. On filesystems where Git checks
symlinks out as plain files, this compatibility layer will not behave
correctly and should be replaced with generated regular files instead.

Do not edit files here directly. Edit the corresponding file in
`.codex/agents/`.
