"""gemini --approval-mode plan invocation with YAML-retry and process-failure semantics.

Spec: §3 Step 3. Three regimes:
  - YAML-retry (3 max): bad YAML or schema violation → re-prompt with prior bad output.
  - Process failure (gemini exit ≠ 0): pause pipeline immediately. Never retry.
  - Success: parse and return Verdict.

LLM output is fence-stripped before YAML decoding because LLMs reliably
wrap outputs in ```yaml...``` despite explicit instructions to the contrary.
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import yaml
from pydantic import ValidationError

from tools.pipette.sanity.schema import Verdict

from tools.pipette.llm import invoke_gemini, GeminiProcessFailure, GeminiYamlInvalidAfterRetries


def invoke_and_print(*, prompt_file: Path, folder: Path) -> int:
    """CLI entry from the slash command; reads prompt from file, prints YAML on stdout.
    Exit codes:
      0 — verdict printed; orchestrator advances or loops back per verdict
      1 — gemini process failure; lockfile transitioned to paused before exit
      2 — YAML invalid 4x; hard error to user (no pause — this is a bug, not a transient)
    """
    from tools.pipette.trace import append_event, Event
    from tools.pipette.lockfile import pause
    prompt = prompt_file.read_text()
    # folder is `docs/pipeline/<run-folder>/`; lockfile is `docs/pipeline/_meta/.lock`.
    # `folder.parent` resolves to `docs/pipeline/`; appending `_meta/.lock` gives the right path.
    lock_path = folder.parent / "_meta" / ".lock"
    try:
        v = invoke_gemini(prompt, Verdict, approval_mode=True)
    except GeminiProcessFailure as e:
        append_event(folder / "trace.jsonl", Event(step=3, event="gemini_process_failure", extra={"err": str(e)}))
        try:
            pause(lock_path, paused_at_step=3, pause_reason="gemini_cli_failure")
        except (FileNotFoundError, OSError) as pe:
            print(f"pipette: gemini process failure ({e}) AND lockfile pause failed ({pe})", file=sys.stderr)
            return 1
        print(f"pipette: gemini process failure: {e}\npipeline paused; resume with /pipette resume <topic> after resolving gemini auth/rate-limit", file=sys.stderr)
        return 1
    except GeminiYamlInvalidAfterRetries as e:
        append_event(folder / "trace.jsonl", Event(step=3, event="gemini_yaml_invalid_4x", extra={"err": str(e)}))
        print(f"pipette: gemini YAML invalid after retries: {e}", file=sys.stderr)
        return 2
    append_event(folder / "trace.jsonl", Event(step=3, event="gemini_verdict",
                                               decision=v.verdict, jump_back_to=v.jump_back_to))
    print(yaml.safe_dump(v.model_dump()))
    return 0
