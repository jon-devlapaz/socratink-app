# tools/pipette/heuristics.py
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path

from tools.pipette.trace import append_event, Event

# F15 thresholds — hardcoded constants per spec scope cuts.
# Tuning requires editing this file (deliberate; no scoring module).
F15_COVERAGE_FLOOR = 0.80
F15_RISK_CEILING = 0.30
F15_LINES_CEILING = 50


@dataclass
class Step3HeuristicDecision:
    """Result of the F15 heuristic gate at Step 3 entry.

    `reason` is one of:
      "heuristic_auto_pass" — all thresholds met, skip Step 3 ceremony
      "coverage_missing"    — coverage_map.json absent (Step 2 didn't produce it)
      "coverage_malformed"  — coverage_map.json parse error or unexpected shape
      "coverage_below_80"   — min coverage across affected files < F15_COVERAGE_FLOOR
      "risk_above_30"       — max_risk_score >= F15_RISK_CEILING
      "lines_above_50"      — total_changed_lines >= F15_LINES_CEILING
      "grill_meta_missing"  — 01-grill.md present but lacks the pipette-meta comment
    """
    auto_pass: bool
    reason: str


def _read_grill_meta(folder: Path) -> tuple[int | None, float | None]:
    """Parse the `<!-- pipette-meta total_changed_lines=N max_risk_score=F -->`
    annotation that the grill writes into 01-grill.md. The grill prompt
    instructs it to emit this block; if missing, both values are None and
    F15 falls through (no auto-pass without a grounded count).

    NOTE: until Chunk E lands the grill-prompt change that emits this
    comment, every real grill output will lack the meta and F15 will
    always fall through with reason='grill_meta_missing'. This is the
    correct conservative behavior — auto-passing on missing meta would
    be more permissive than spec'd.
    """
    p = folder / "01-grill.md"
    if not p.exists():
        return None, None
    text = p.read_text()
    m = re.search(r"pipette-meta\s+total_changed_lines=(\d+)\s+max_risk_score=([\d.]+)", text)
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2))


def _read_coverage_min(folder: Path) -> tuple[float | None, str | None]:
    """Returns (min_coverage_across_affected, error_reason).

    error_reason is one of:
      "coverage_missing"   — coverage_map.json does not exist
      "coverage_malformed" — JSON parse error or unexpected shape (e.g., no
                             `files` dict, empty `files` dict)

    Caller (step3_heuristic_decision) maps these distinct reasons through
    to the final decision so the audit trail (`autopass_rejected reason=...`)
    distinguishes "Step 2 didn't produce coverage_map.json" from "the file
    is corrupt." Both are non-OK for F15, but they imply different fixes.
    """
    p = folder / "coverage_map.json"
    if not p.exists():
        return None, "coverage_missing"
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None, "coverage_malformed"
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        return None, "coverage_malformed"
    return min(float(v) for v in files.values()), None


def step3_heuristic_decision(*, folder: Path, write_trace: bool = False) -> Step3HeuristicDecision:
    """F15: gate at Step 3 entry. Auto-pass IFF all thresholds met.

    On fall-through, optionally emits an `autopass_rejected` trace event
    naming the failed threshold — needed for future threshold tuning.
    """
    cov_min, cov_err = _read_coverage_min(folder)
    if cov_err is not None:
        decision = Step3HeuristicDecision(auto_pass=False, reason=cov_err)
    elif cov_min is None:  # defensive: cov_err None + cov_min None should be impossible
        decision = Step3HeuristicDecision(auto_pass=False, reason="coverage_malformed")
    elif cov_min < F15_COVERAGE_FLOOR:
        decision = Step3HeuristicDecision(auto_pass=False, reason="coverage_below_80")
    else:
        lines, risk = _read_grill_meta(folder)
        if lines is None or risk is None:
            decision = Step3HeuristicDecision(auto_pass=False, reason="grill_meta_missing")
        elif risk >= F15_RISK_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="risk_above_30")
        elif lines >= F15_LINES_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="lines_above_50")
        else:
            decision = Step3HeuristicDecision(auto_pass=True, reason="heuristic_auto_pass")

    if write_trace and not decision.auto_pass:
        try:
            append_event(folder / "trace.jsonl",
                         Event(step=3, event="autopass_rejected",
                               extra={"reason": decision.reason}))
        except OSError:
            pass
    return decision


def should_run_step3(*, folder: Path, lite_mode: bool) -> bool:
    """Combined gate. Lite mode is an absolute manual override (P-spec
    enhancement #5): even if F15 demands a full review, lite skips Step 3.
    Default path: respect F15 — auto-pass means skip, fall-through means run."""
    if lite_mode:
        return False
    return not step3_heuristic_decision(folder=folder, write_trace=False).auto_pass
