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

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pipette", description="Heavy-planning pipeline orchestrator")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("start", help="start a new pipeline run")
    s.add_argument("topic", help="natural-language topic (kebab-cased internally)")
    s.add_argument("--root", default="docs/pipeline", help="pipeline tree root")

    r = sub.add_parser("resume", help="resume a paused pipeline run")
    r.add_argument("topic")
    r.add_argument("--root", default="docs/pipeline")

    a = sub.add_parser("abort", help="abort an active or paused run")
    a.add_argument("topic")
    a.add_argument("--root", default="docs/pipeline")

    rc = sub.add_parser("recover", help="force release of a stale `state: running` lock without renaming folder; user takes responsibility")
    rc.add_argument("topic")
    rc.add_argument("--root", default="docs/pipeline")

    sub.add_parser("doctor", help="run preflight (§6) — deps, fs detection, pipeline graph validation",
                   description="run preflight checks (§6): deps, fs detection, pipeline graph validation")

    sub.add_parser("lock-status", help="print current lockfile YAML")

    g = sub.add_parser("gemini", help="invoke gemini and print parsed verdict")
    g.add_argument("--prompt-file", required=True)
    g.add_argument("--folder", required=True, help="per-feature folder; trace.jsonl lives here")

    rb = sub.add_parser("research-brief", help="write a research brief; increments caps")
    rb.add_argument("--folder", required=True)
    rb.add_argument("--step", type=float, required=True)
    rb_src = rb.add_mutually_exclusive_group(required=True)
    rb_src.add_argument("--brief-file", help="JSON or YAML file with {question, why_needed}")
    rb_src.add_argument("--question-and-why", nargs=2, metavar=("QUESTION", "WHY"),
                        help="alt: pass both as positional pair (escape strings carefully)")

    rf = sub.add_parser("research-findings", help="paste back research findings under ## Findings")
    rf.add_argument("--folder", required=True)
    rf.add_argument("--step", type=float, required=True)
    rf.add_argument("--question", required=True)
    rf.add_argument("--findings-file", required=True)

    pa = sub.add_parser("pause", help="transition lockfile to paused (heartbeat-style)")
    pa.add_argument("--step", type=float, required=True)
    pa.add_argument("--reason", required=True, choices=["NEEDS_RESEARCH", "gemini_cli_failure", "hook_crash", "user_initiated"])
    pa.add_argument("--root", default="docs/pipeline")

    fi = sub.add_parser("finish", help="remove lockfile after Step 7 completion")
    fi.add_argument("--folder", required=True)
    fi.add_argument("--root", default="docs/pipeline")

    ta = sub.add_parser("trace-append", help="append a single event to trace.jsonl")
    ta.add_argument("--folder", required=True)
    ta.add_argument("--step", type=float, required=True)
    ta.add_argument("--event", required=True)
    ta.add_argument("--decision", default=None)
    ta.add_argument("--jump-back-to", type=float, default=None)

    al = sub.add_parser("archive-for-loop-back", help="archive Step N+ artifacts to _attempts/")
    al.add_argument("--folder", required=True)
    al.add_argument("--jump-back-to", type=float, required=True, choices=[1, 2])

    sub.add_parser("verifier-filter", help="reads a ReviewerOutput JSON from stdin, applies 0.8 confidence filter, prints filtered JSON")

    pj = sub.add_parser("parse-jump", help="strict regex validator for `--jump-to N` chat input")
    pj.add_argument("input", help="raw chat input string to validate")

    bv = sub.add_parser("build-verifier-prompt",
                        help="concatenates verifier.md + 4 reviewer ReviewerOutput JSON files into a single prompt; prints to stdout")
    bv.add_argument("--reviewer-files", nargs="+", required=True,
                    help="paths to per-reviewer JSON files (e.g. FOLDER/_reviewer-contracts.json ... FOLDER/_reviewer-coverage.json)")

    cm = sub.add_parser("build-coverage-map",
                        help="generate coverage_map.json from a graph-query dump (v1 approximation)")
    cm.add_argument("--dump-file", required=True,
                    help="JSON file containing the graph-query dump from Step 0 (test→source edges)")
    cm.add_argument("--affected-files", nargs="+", required=True,
                    help="list of affected source files to compute coverage for")
    cm.add_argument("--output", required=True, help="write coverage_map.json here")

    return p


def main(argv: list[str] | None = None) -> int:
    import yaml  # used in research-brief branch
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 0
    if args.cmd == "doctor":
        from tools.pipette.doctor import run_doctor
        return run_doctor()
    if args.cmd == "start":
        from tools.pipette.orchestrator import start
        return start(topic=args.topic, root=Path(args.root))
    if args.cmd == "resume":
        from tools.pipette.orchestrator import resume_run
        return resume_run(topic=args.topic, root=Path(args.root))
    if args.cmd == "abort":
        from tools.pipette.orchestrator import abort_run
        return abort_run(topic=args.topic, root=Path(args.root))
    if args.cmd == "recover":
        from tools.pipette.orchestrator import recover_run
        return recover_run(topic=args.topic, root=Path(args.root))
    if args.cmd == "lock-status":
        from tools.pipette.orchestrator import lock_status
        return lock_status()
    if args.cmd == "gemini":
        from tools.pipette.gemini_picker import invoke_and_print
        return invoke_and_print(prompt_file=Path(args.prompt_file), folder=Path(args.folder))
    if args.cmd == "research-brief":
        from tools.pipette.research_gate import write_brief, ResearchCapExceeded
        from tools.pipette.orchestrator import abort_run
        if args.brief_file:
            # PyYAML's safe_load handles JSON natively (JSON is a YAML subset).
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
            # Spec §5.5: cap exceeded → pipeline aborts hard.
            print(f"pipette: research cap exceeded: {e}", file=sys.stderr)
            print("pipette: aborting pipeline per spec §5.5", file=sys.stderr)
            # Read topic from the lockfile so abort can find the right run.
            try:
                lock = Path(args.folder).parent / "_meta" / ".lock"
                cur = yaml.safe_load(lock.read_text()) if lock.exists() else {}
                if topic := cur.get("topic"):
                    abort_run(topic=topic, root=Path(args.folder).parent)
            except Exception as ae:  # noqa: BLE001
                print(f"pipette: abort during cap-exceeded also failed: {ae}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "research-findings":
        from tools.pipette.research_gate import write_findings
        text = Path(args.findings_file).read_text()
        write_findings(folder=Path(args.folder), step=args.step, question=args.question, findings_text=text)
        return 0
    if args.cmd == "pause":
        from tools.pipette.orchestrator import pause_run
        return pause_run(step=args.step, reason=args.reason, root=Path(args.root))
    if args.cmd == "finish":
        from tools.pipette.orchestrator import finish_run
        return finish_run(folder=Path(args.folder), root=Path(args.root))
    if args.cmd == "trace-append":
        from tools.pipette.trace import append_event, Event
        append_event(
            Path(args.folder) / "trace.jsonl",
            Event(step=args.step, event=args.event, decision=args.decision, jump_back_to=args.jump_back_to),
        )
        return 0
    if args.cmd == "archive-for-loop-back":
        from tools.pipette.orchestrator import archive_for_loop_back
        archive_for_loop_back(folder=Path(args.folder), jump_back_to=args.jump_back_to)
        return 0
    if args.cmd == "verifier-filter":
        import re as _re
        from tools.pipette.sanity.schema import ReviewerOutput
        from tools.pipette.sanity.verifier import filter_by_confidence
        raw = sys.stdin.read()
        # Strip markdown code fences — LLMs commonly wrap JSON in ```json...```
        raw = _re.sub(r"^\s*```(?:json)?\s*\n?", "", raw)
        raw = _re.sub(r"\n?```\s*$", "", raw)
        ro = ReviewerOutput.model_validate_json(raw)
        filtered = ReviewerOutput(reviewer=ro.reviewer, findings=filter_by_confidence(ro.findings), notes=ro.notes)
        print(filtered.model_dump_json())
        return 0
    if args.cmd == "parse-jump":
        import re as _re
        # B-revision (2026-04-28): jump_back_to=1.5 dropped; only 1 or 2 valid.
        m = _re.match(r"^\s*--jump-to\s+(1|2)\s*$", args.input)
        if not m:
            print(f"pipette: invalid jump target {args.input!r}; expected `--jump-to 1` or `--jump-to 2`", file=sys.stderr)
            return 2
        print(m.group(1))  # stdout: just the number for caller to consume
        return 0
    if args.cmd == "build-verifier-prompt":
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
    if args.cmd == "build-coverage-map":
        import json as _json
        dump = _json.loads(Path(args.dump_file).read_text())
        # The dump is whatever the orchestrator pipes from MCP query_graph. We
        # accept either a list of edges [{"from": {"source_file": "tests/foo.py"}, "to": {"source_file": "src/foo.py"}}, ...]
        # OR a flat list of nodes with a `tested_files` field. Support both.
        edges = dump.get("edges") if isinstance(dump, dict) else dump
        tested_files: set[str] = set()
        if isinstance(edges, list):
            for e in edges:
                src = (e.get("from") or {}).get("source_file") if isinstance(e, dict) else None
                dst = (e.get("to") or {}).get("source_file") if isinstance(e, dict) else None
                if src and dst and src.startswith("tests/"):
                    tested_files.add(dst)
        files_map = {f: (0.85 if f in tested_files else 0.30) for f in args.affected_files}
        out = {"_method": "graph_approx_v1", "files": files_map}
        Path(args.output).write_text(_json.dumps(out, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
