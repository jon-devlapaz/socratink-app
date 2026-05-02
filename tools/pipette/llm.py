# tools/pipette/llm.py
from __future__ import annotations
import os
import re
import subprocess
from typing import TypeVar, Type
import yaml
from pydantic import BaseModel, ValidationError

GEMINI_BIN = os.environ.get("PIPETTE_GEMINI_BIN", "/opt/homebrew/bin/gemini")
MAX_YAML_RETRIES = 3
LLM_TIMEOUT_S = 120

class GeminiYamlInvalidAfterRetries(Exception):
    pass

class GeminiProcessFailure(Exception):
    pass

_FENCE_OPEN = re.compile(r"^\s*```(?:yaml|json)?\s*\n?", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"\n?```\s*$")

def strip_code_fences(raw: str) -> str:
    """LLMs reliably wrap their YAML/JSON output in markdown code fences
    despite explicit instructions to the contrary. Strip them before parsing."""
    return _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", raw))

T = TypeVar("T", bound=BaseModel)

def try_parse(stdout: str, model: Type[T]) -> T | None:
    try:
        data = yaml.safe_load(strip_code_fences(stdout))
        if not isinstance(data, dict):
            return None
        return model.model_validate(data)
    except (yaml.YAMLError, ValidationError, ValueError):
        return None

def invoke_gemini(prompt: str, model: Type[T], approval_mode: bool = False) -> T:
    """Returns a parsed Pydantic model on success. Raises GeminiProcessFailure on CLI exit ≠ 0.
    Raises GeminiYamlInvalidAfterRetries if 4 attempts all produce invalid YAML/schema.
    """
    cur_prompt = prompt
    args = [GEMINI_BIN]
    if approval_mode:
        args.extend(["--approval-mode", "plan"])
        
    for attempt in range(MAX_YAML_RETRIES + 1):  # 1 initial + 3 retries
        try:
            proc = subprocess.run(
                args, input=cur_prompt, capture_output=True, text=True, timeout=LLM_TIMEOUT_S,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise GeminiProcessFailure(f"gemini subprocess failure: {type(e).__name__}: {e}") from e
        
        if proc.returncode != 0:
            raise GeminiProcessFailure(
                f"gemini exited with code {proc.returncode}: {proc.stderr.strip()}"
            )
            
        verdict = try_parse(proc.stdout, model)
        if verdict is not None:
            return verdict
            
        # Invalid YAML/schema → re-prompt with prior bad output appended.
        cur_prompt = (
            prompt + "\n\n---\n\nthis output was not valid YAML for the required schema; "
            "emit only the YAML and nothing else.\n\nprior bad output:\n" + proc.stdout
        )
        
    raise GeminiYamlInvalidAfterRetries(
        f"{MAX_YAML_RETRIES + 1} attempts failed to produce valid YAML; last stdout:\n{proc.stdout}"
    )
