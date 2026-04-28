# tools/pipette/validate_pipeline_graph.py
"""Hand-rolled structural validator for the pipette pipeline graph.

Replaces the spec's mistakenly-referenced "Agentproof" check (PyPI agentproof
is a test-assertion library, not a workflow-graph validator).

Checks:
  1. Every non-exit node has at least one outgoing edge.
  2. Every node is reachable from `start` (no orphans).
  3. Every gate node (type ∈ {user_gate, automated_gate}) has outgoing
     edges for each label declared in its `decision` field.
  4. The only cycles allowed are the explicit jump-back / revise loops
     declared in `ALLOWED_LOOP_BACK_EDGES`. As of B-revision (2026-04-28):
     gate_sanity → step_1_grill (FAIL/jump_back_to=1)
     gate_sanity → step_2_diagram (FAIL/jump_back_to=2)
     gate_sanity → step_3_sanity (NEEDS_RESEARCH self-loop after pause+resume)
     gate_grill / gate_diagram / gate_plan → their step (revise)
     gate_subagent_stop → step_5_execute (deny → next subagent)
"""
from __future__ import annotations
import json
from pathlib import Path

GATE_TYPES = {"user_gate", "automated_gate"}
EXIT_TYPES = {"exit"}
ALLOWED_LOOP_BACK_EDGES = {
    ("gate_sanity", "step_1_grill"),
    ("gate_sanity", "step_2_diagram"),
    ("gate_sanity", "step_3_sanity"),  # NEEDS_RESEARCH after pause+resume
    ("gate_grill", "step_1_grill"),     # revise
    ("gate_diagram", "step_2_diagram"),
    ("gate_plan", "step_4_plan"),
    ("gate_subagent_stop", "step_5_execute"),
    # B-revision (2026-04-28): Step 1.5 collapsed into Step 1; grill-with-docs
    # handles glossary inline. gate_glossary edges no longer exist.
}


def validate(graph_path: Path) -> list[str]:
    """Returns a list of human-readable error strings; empty list = valid."""
    g = json.loads(graph_path.read_text())
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    edges = g.get("edges", [])
    errs: list[str] = []

    # Check 1: every non-exit node has ≥1 outgoing edge
    outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for e in edges:
        outgoing.setdefault(e["from"], []).append(e)
    for nid, node in nodes.items():
        if node.get("type") in EXIT_TYPES:
            continue
        if not outgoing.get(nid):
            errs.append(f"node {nid!r} ({node.get('type')}) has no outgoing edges")

    # Check 2: every node reachable from `start`
    if "start" not in nodes:
        errs.append("no node with id 'start'")
    else:
        reachable: set[str] = set()
        stack = ["start"]
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            for e in outgoing.get(cur, []):
                stack.append(e["to"])
        unreachable = set(nodes) - reachable
        for u in sorted(unreachable):
            errs.append(f"node {u!r} unreachable from `start`")

    # Check 3: every gate has outgoing edges for each declared label
    for nid, node in nodes.items():
        if node.get("type") not in GATE_TYPES:
            continue
        decision = node.get("decision")
        if not decision:
            continue
        labels = {label.strip() for label in decision.split("|")}
        # Edge labels must match exactly; descriptive text belongs in a `notes`
        # field on the edge, not in `label`. The previous split-on-`/` heuristic
        # silently let mislabeled edges pass (round 27).
        edge_labels = {e.get("label", "").strip() for e in outgoing.get(nid, [])}
        missing = labels - edge_labels
        if missing:
            errs.append(f"gate {nid!r} missing outgoing edges for labels: {sorted(missing)}")

    # Check 4: cycle detection. Filter out the whitelisted loop-back edges first,
    # then run DFS. Any cycle that remains is an illegal cycle.
    # (A previous draft compared cycle edges against the whitelist directly — that
    # was wrong because cycles include forward edges by definition; the comparison
    # always reported the forward edges as "bad". See ChatGPT review round 26.)
    filtered_outgoing: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for nid, edges_out in outgoing.items():
        for e in edges_out:
            if (e["from"], e["to"]) not in ALLOWED_LOOP_BACK_EDGES:
                filtered_outgoing[nid].append(e)
    for cycle in _find_cycles(nodes, filtered_outgoing):
        errs.append(f"unexpected cycle through nodes: {' -> '.join(cycle)}")

    return errs


def _find_cycles(nodes: dict, outgoing: dict[str, list[dict]]) -> list[list[str]]:
    """Recursive DFS to find simple cycles in the post-filter graph.

    Tri-color DFS: GRAY = on current recursion path, BLACK = fully explored.
    A back-edge to a GRAY node is a cycle.

    A previous iterative draft marked nodes BLACK immediately after pushing
    children — before those children were popped — so cycles through nodes
    reachable from multiple paths went undetected (e.g., a→b→a where `a` is
    also reachable directly from start). Codex Phase-S review caught this;
    the recursive form preserves GRAY for the duration of child exploration.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in nodes}
    found: list[list[str]] = []

    def dfs(cur: str, path: list[str]) -> None:
        color[cur] = GRAY
        for e in outgoing.get(cur, []):
            nxt = e["to"]
            if nxt not in color:
                continue  # edge points at unknown node; reachability check covers it
            if color[nxt] == GRAY:
                idx = path.index(nxt)
                found.append(path[idx:] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, path + [nxt])
        color[cur] = BLACK

    if "start" in nodes:
        dfs("start", ["start"])
    # Cover disconnected components — reachability check flags them as
    # unreachable, but they may still contain cycles worth reporting.
    for nid in nodes:
        if color[nid] == WHITE:
            dfs(nid, [nid])
    return found


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "tools/pipette/pipeline_graph.json")
    errs = validate(path)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        sys.exit(1)
    print(f"OK: {path} is structurally valid")
