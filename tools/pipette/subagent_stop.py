# tools/pipette/subagent_stop.py — stub; full impl lands in Task C7
"""SubagentStop hook handler. Reads JSON from stdin, writes permissionDecision JSON to stdout.

Wired in .claude/settings.json. Crash semantics (per spec §3 Step 5):
  any non-zero exit OR malformed stdout → orchestrator treats as deny.
"""
import json
import sys

def main() -> int:
    _ = sys.stdin.read()  # discarded in stub
    json.dump({"permissionDecision": "allow", "reason": "stub — full impl in C7"}, sys.stdout)
    return 0

if __name__ == "__main__":
    sys.exit(main())
