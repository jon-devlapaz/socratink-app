# pipette TODO

Polish + future-work items. Not blockers. Order is rough priority.

## ASCII-graph pretty-printer for the pipeline

Add `python -m tools.pipette graph` (or `pipette graph`) — read
`tools/pipette/pipeline_graph.json` and render a terminal-friendly tree of
the 8-step pipeline (Step −1 through Step 7), showing decision labels on
gate edges and marking exit terminals. Recursive descent from `start`.

**Inspiration:** csurfer/pypette's `Pipe.graph()` method
(<https://github.com/csurfer/pypette>). Their renderer is a small ASCII-tree
walker — nothing fancy, just box-drawing characters with `├─` / `└─` /
`│ ` indentation per level.

**Why bother:** the structured graph is already validated end-to-end by
`validate_pipeline_graph.py`. Pretty-printing turns that machine-readable
artifact into something humans can scan in a single screenful. Useful
when teaching the pipeline to a new collaborator, or when the graph
changes and we want a quick visual diff.

**Scope:** new file `tools/pipette/render_graph.py` + subcommand wired in
`cli.py`. Don't touch `validate_pipeline_graph.py`. Pure stdlib (no rich,
no networkx). One unit test that asserts a known shape for a small graph
fixture.

**Out of scope:** Mermaid/Graphviz output, runtime visualization of an
in-flight run, animation. Static structure only.
