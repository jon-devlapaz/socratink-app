# tools/pipette/cli.py
"""argparse surface for /pipette. Subcommands fall into three groups:

LIFECYCLE — driven by user via slash command:
  start <topic>            — acquire lock, create folder
  resume <topic>           — flip paused → running (markdown handles findings via research-findings first)
  abort <topic>            — rename folder to -aborted, release lock (topic verified)
  recover <topic>          — force release of stale `state: running` lock without renaming the folder; user takes responsibility
  doctor                   — preflight checks (§6)
  lock-status              — print current lockfile YAML

ORCHESTRATOR-INTERNAL — slash command markdown shells in:
  pause --step --reason    — heartbeat-style transition to paused
  finish --folder          — Step 7 cleanup; remove lockfile
  trace-append --folder ...— append a single event to trace.jsonl
  archive-for-loop-back ...— move artifacts to _attempts/ on Step 3 FAIL
  research-brief --folder ...— write a NEEDS_RESEARCH brief; auto-aborts on cap exceeded (§5.5)
  research-findings ...    — append `## Findings` to a brief on resume
  gemini --prompt-file ... — Step 3 picker (auto-pauses on process failure)

PARSING + VALIDATION HELPERS — slash command markdown shells in:
  verifier-filter          — read ReviewerOutput JSON from stdin, drop <0.8 confidence findings
  parse-jump <input>       — strict regex validation of `--jump-to N` chat input
  build-verifier-prompt ...— concatenate verifier.md + 4 reviewer outputs into one prompt

The SubagentStop hook is invoked via `python -m tools.pipette.subagent_stop` (separate __main__),
not via this CLI; that path is wired in `.claude/settings.json`.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import yaml

def _cmd_doctor(args: argparse.Namespace) -> int:
    from tools.pipette.doctor import run_doctor
    return run_doctor()

def _cmd_start(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import start
    return start(topic=args.topic, root=Path(args.root))

def _cmd_resume(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import resume_run
    return resume_run(topic=args.topic, root=Path(args.root))

def _cmd_abort(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import abort_run
    return abort_run(topic=args.topic, root=Path(args.root))

def _cmd_recover(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import recover_run
    return recover_run(topic=args.topic, root=Path(args.root))

def _cmd_lock_status(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import lock_status
    return lock_status()

def _cmd_gemini(args: argparse.Namespace) -> int:
    from tools.pipette.gemini_picker import invoke_and_print
    return invoke_and_print(prompt_file=Path(args.prompt_file), folder=Path(args.folder))

def _cmd_research_brief(args: argparse.Namespace) -> int:
    from tools.pipette.research_gate import write_brief, ResearchCapExceeded
    from tools.pipette.orchestrator import abort_run
    if args.brief_file:
        data = yaml.safe_load(Path(args.brief_file).read_text())
        if not isinstance(data, dict) or "question" not in data or "why_needed" not in data:
            print("pipette: --brief-file must contain `question` and `why_needed` keys", file=sys.stderr)
            return 2
        question, why = data["question"], data["why_needed"]
    else:
        question, why = args.question_and_why
    try:
        write_brief(folder=Path(args.folder), step=args.step, question=question, why=why)
    except ResearchCapExceeded as e:
        print(f"pipette: research cap exceeded: {e}", file=sys.stderr)
        print("pipette: aborting pipeline per spec §5.5", file=sys.stderr)
        try:
            lock = Path(args.folder).parent / "_meta" / ".lock"
            cur = yaml.safe_load(lock.read_text()) if lock.exists() else {}
            if topic := cur.get("topic"):
                abort_run(topic=topic, root=Path(args.folder).parent)
        except Exception as ae:  # noqa: BLE001
            print(f"pipette: abort during cap-exceeded also failed: {ae}", file=sys.stderr)
        return 1
    return 0

def _cmd_research_findings(args: argparse.Namespace) -> int:
    from tools.pipette.research_gate import write_findings
    text = Path(args.findings_file).read_text()
    write_findings(folder=Path(args.folder), step=args.step, question=args.question, findings_text=text)
    return 0

def _cmd_pause(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import pause_run
    return pause_run(step=args.step, reason=args.reason, root=Path(args.root))

def _cmd_finish(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import finish_run
    return finish_run(folder=Path(args.folder), root=Path(args.root))

def _cmd_trace_append(args: argparse.Namespace) -> int:
    from tools.pipette.trace import append_event, Event, parse_extra_kv
    try:
        extra = parse_extra_kv(args.data)
    except ValueError as e:
        print(f"pipette: {e}", file=sys.stderr)
        return 2
    append_event(
        Path(args.folder) / "trace.jsonl",
        Event(step=args.step, event=args.event, decision=args.decision,
              jump_back_to=args.jump_back_to, extra=extra),
    )
    return 0

def _cmd_archive_for_loop_back(args: argparse.Namespace) -> int:
    from tools.pipette.orchestrator import archive_for_loop_back
    archive_for_loop_back(folder=Path(args.folder), jump_back_to=args.jump_back_to)
    return 0

def _cmd_verifier_filter(args: argparse.Namespace) -> int:
    import re as _re
    from tools.pipette.sanity.schema import ReviewerOutput
    from tools.pipette.sanity.verifier import filter_by_confidence
    raw = sys.stdin.read()
    raw = _re.sub(r"^\s*```(?:json)?\s*\n?", "", raw)
    raw = _re.sub(r"\n?```\s*$", "", raw)
    ro = ReviewerOutput.model_validate_json(raw)
    filtered = ReviewerOutput(reviewer=ro.reviewer, findings=filter_by_confidence(ro.findings), notes=ro.notes)
    print(filtered.model_dump_json())
    return 0

def _cmd_parse_jump(args: argparse.Namespace) -> int:
    import re as _re
    m = _re.match(r"^\s*--jump-to\s+(1|2)\s*$", args.input)
    if not m:
        print(f"pipette: invalid jump target {args.input!r}; expected `--jump-to 1` or `--jump-to 2`", file=sys.stderr)
        return 2
    print(m.group(1))
    return 0

def _cmd_build_verifier_prompt(args: argparse.Namespace) -> int:
    import re as _re
    from tools.pipette.sanity.schema import ReviewerOutput
    from tools.pipette.sanity.verifier import build_verifier_prompt
    outputs = []
    for path_str in args.reviewer_files:
        raw = Path(path_str).read_text()
        raw = _re.sub(r"^\s*```(?:json)?\s*\n?", "", raw)
        raw = _re.sub(r"\n?```\s*$", "", raw)
        outputs.append(ReviewerOutput.model_validate_json(raw))
    sys.stdout.write(build_verifier_prompt(outputs))
    return 0

def _cmd_build_coverage_map(args: argparse.Namespace) -> int:
    from tools.pipette.coverage import build_coverage_map
    return build_coverage_map(Path(args.dump_file), args.affected_files, Path(args.output))

def _cmd_step3_heuristic_check(args: argparse.Namespace) -> int:
    import json as _json
    from tools.pipette.heuristics import step3_heuristic_decision
    decision = step3_heuristic_decision(folder=Path(args.folder), write_trace=True)
    print(_json.dumps({"auto_pass": decision.auto_pass, "reason": decision.reason}))
    return 0

def _cmd_lite_pipeline_steps(args: argparse.Namespace) -> int:
    import json as _json
    from tools.pipette.orchestrator import lite_pipeline_steps
    print(_json.dumps(lite_pipeline_steps()))
    return 0

def _cmd_should_run_step3(args: argparse.Namespace) -> int:
    from tools.pipette.heuristics import should_run_step3
    result = should_run_step3(folder=Path(args.folder), lite_mode=args.lite)
    print("true" if result else "false")
    return 0

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pipette", description="Heavy-planning pipeline orchestrator")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="start a new pipeline run")
    s.add_argument("topic", help="natural-language topic (kebab-cased internally)")
    s.add_argument("--root", default="docs/pipeline", help="pipeline tree root")
    s.set_defaults(func=_cmd_start)

    r = sub.add_parser("resume", help="resume a paused pipeline run")
    r.add_argument("topic")
    r.add_argument("--root", default="docs/pipeline")
    r.set_defaults(func=_cmd_resume)

    a = sub.add_parser("abort", help="abort an active or paused run")
    a.add_argument("topic")
    a.add_argument("--root", default="docs/pipeline")
    a.set_defaults(func=_cmd_abort)

    rc = sub.add_parser("recover", help="force release of a stale `state: running` lock without renaming folder; user takes responsibility")
    rc.add_argument("topic")
    rc.add_argument("--root", default="docs/pipeline")
    rc.set_defaults(func=_cmd_recover)

    doc = sub.add_parser("doctor", help="run preflight (§6) — deps, fs detection, pipeline graph validation",
                         description="run preflight checks (§6): deps, fs detection, pipeline graph validation")
    doc.set_defaults(func=_cmd_doctor)

    ls = sub.add_parser("lock-status", help="print current lockfile YAML")
    ls.set_defaults(func=_cmd_lock_status)

    g = sub.add_parser("gemini", help="invoke gemini and print parsed verdict")
    g.add_argument("--prompt-file", required=True)
    g.add_argument("--folder", required=True, help="per-feature folder; trace.jsonl lives here")
    g.set_defaults(func=_cmd_gemini)

    rb = sub.add_parser("research-brief", help="write a research brief; increments caps")
    rb.add_argument("--folder", required=True)
    rb.add_argument("--step", type=float, required=True)
    rb_src = rb.add_mutually_exclusive_group(required=True)
    rb_src.add_argument("--brief-file", help="JSON or YAML file with {question, why_needed}")
    rb_src.add_argument("--question-and-why", nargs=2, metavar=("QUESTION", "WHY"),
                        help="alt: pass both as positional pair (escape strings carefully)")
    rb.set_defaults(func=_cmd_research_brief)

    rf = sub.add_parser("research-findings", help="paste back research findings under ## Findings")
    rf.add_argument("--folder", required=True)
    rf.add_argument("--step", type=float, required=True)
    rf.add_argument("--question", required=True)
    rf.add_argument("--findings-file", required=True)
    rf.set_defaults(func=_cmd_research_findings)

    pa = sub.add_parser("pause", help="transition lockfile to paused (heartbeat-style)")
    pa.add_argument("--step", type=float, required=True)
    pa.add_argument("--reason", required=True, choices=["NEEDS_RESEARCH", "gemini_cli_failure", "hook_crash", "user_initiated"])
    pa.add_argument("--root", default="docs/pipeline")
    pa.set_defaults(func=_cmd_pause)

    fi = sub.add_parser("finish", help="remove lockfile after Step 7 completion")
    fi.add_argument("--folder", required=True)
    fi.add_argument("--root", default="docs/pipeline")
    fi.set_defaults(func=_cmd_finish)

    ta = sub.add_parser("trace-append", help="append a single event to trace.jsonl")
    ta.add_argument("--folder", required=True)
    ta.add_argument("--step", type=float, required=True)
    ta.add_argument("--event", required=True)
    ta.add_argument("--decision", default=None)
    ta.add_argument("--jump-back-to", type=float, default=None)
    ta.add_argument("--data", default=None, help="extra structured fields as 'k=v,k2=v2' (F4)")
    ta.set_defaults(func=_cmd_trace_append)

    al = sub.add_parser("archive-for-loop-back", help="archive Step N+ artifacts to _attempts/")
    al.add_argument("--folder", required=True)
    al.add_argument("--jump-back-to", type=float, required=True, choices=[1, 2])
    al.set_defaults(func=_cmd_archive_for_loop_back)

    vf = sub.add_parser("verifier-filter", help="reads a ReviewerOutput JSON from stdin, applies 0.8 confidence filter, prints filtered JSON")
    vf.set_defaults(func=_cmd_verifier_filter)

    pj = sub.add_parser("parse-jump", help="strict regex validator for `--jump-to N` chat input")
    pj.add_argument("input", help="raw chat input string to validate")
    pj.set_defaults(func=_cmd_parse_jump)

    bv = sub.add_parser("build-verifier-prompt",
                        help="concatenates verifier.md + 4 reviewer ReviewerOutput JSON files into a single prompt; prints to stdout")
    bv.add_argument("--reviewer-files", nargs="+", required=True,
                    help="paths to per-reviewer JSON files (e.g. FOLDER/_reviewer-contracts.json ... FOLDER/_reviewer-coverage.json)")
    bv.set_defaults(func=_cmd_build_verifier_prompt)

    cm = sub.add_parser("build-coverage-map",
                        help="generate coverage_map.json from a graph-query dump (v1 approximation)")
    cm.add_argument("--dump-file", required=True,
                    help="JSON file containing the graph-query dump from Step 0 (test→source edges)")
    cm.add_argument("--affected-files", nargs="+", required=True,
                    help="list of affected source files to compute coverage for")
    cm.add_argument("--output", required=True, help="write coverage_map.json here")
    cm.set_defaults(func=_cmd_build_coverage_map)

    sh = sub.add_parser("step3-heuristic-check",
                        help="F15: run Step 3 heuristic gate; prints JSON decision to stdout (exit 0 always)")
    sh.add_argument("--folder", required=True,
                    help="per-feature pipeline folder (contains coverage_map.json and 01-grill.md)")
    sh.set_defaults(func=_cmd_step3_heuristic_check)

    lps = sub.add_parser("lite-pipeline-steps",
                         help="F14: print the step list that pipette-lite runs as JSON")
    lps.set_defaults(func=_cmd_lite_pipeline_steps)

    srs = sub.add_parser("should-run-step3",
                         help="F14/F15: combined gate; prints 'true' or 'false' to stdout (exit 0 always)")
    srs.add_argument("--folder", required=True,
                     help="per-feature pipeline folder")
    srs.add_argument("--lite", action="store_true", default=False,
                     help="if set, lite mode is active (Step 3 is unconditionally skipped)")
    srs.set_defaults(func=_cmd_should_run_step3)

    return p

def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # Avoid crashing with sys.exit when just wanting to print help
        return e.code
    
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 0
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
