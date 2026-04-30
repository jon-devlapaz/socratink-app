# MCP fallback for `code-review-graph`

If `mcp__code-review-graph__*` tools are not exposed in the running session
(the doctor's F1 in-session probe will WARN about this), use one of these
fallbacks instead of waiting on tool turns to rediscover them:

## SQLite fallback

The graph database lives at `.code-review-graph/graph.db` (relative to repo
root). Open with:

```bash
sqlite3 .code-review-graph/graph.db
```

Useful schemas:
- `nodes(id, kind, qualified_name, source_file, line_start, line_end)`
- `edges(id, kind, src_id, dst_id)` where `kind` includes `calls`, `imports`, `tests`

Example query (test→source coverage):

```sql
SELECT n_src.source_file AS test_file, n_dst.source_file AS source_file
FROM edges e
JOIN nodes n_src ON e.src_id = n_src.id
JOIN nodes n_dst ON e.dst_id = n_dst.id
WHERE e.kind = 'tests';
```

## Grep fallback

For a quick "where is this symbol used?" the Grep tool with a fully
qualified name (`MyClass.my_method` or `module.function`) is fast and cheap.
Trade-off: misses dynamic dispatch and indirect call sites — Grep is a
floor, not a ceiling. (See user memory: "Graph counts are a floor, not a
ceiling.")
