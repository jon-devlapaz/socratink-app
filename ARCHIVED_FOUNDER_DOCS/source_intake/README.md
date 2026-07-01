# source_intake/

Unified content intake. The single seam that turns a URL or raw-text
submission into an `ImportedSource` value ready for Gemini extraction.

## Public surface

Import from `source_intake` directly.

| Export | What it is |
| :--- | :--- |
| `ImportedSource` | Frozen dataclass: `url`, `title`, `text`, `is_remote_source`. The value type the rest of the pipeline consumes. |
| `from_url(url)` | Fetch + parse a single page. Strips whitespace, validates outbound target, decodes, parses. Returns `ImportedSource(is_remote_source=True)`. |
| `from_text(text, *, min_text_length=1)` | Normalize a raw-text submission. No fetch. Returns `ImportedSource(is_remote_source=False)`. |
| `SourceIntakeError` (+ 6 subclasses) | Normalized error hierarchy: `InvalidUrl`, `BlockedSource`, `FetchFailed`, `UnsupportedContent`, `TooLarge`, `ParseEmpty`. |

## Files

| File | Role |
| :--- | :--- |
| `__init__.py` | Public API surface + `from_url`/`from_text` facade. |
| `fetch.py` | Outbound HTTP. Owns target validation (SSRF guard), redirect handling, content-type sniffing. |
| `parse.py` | HTML and plaintext extraction. Returns title + normalized text. |
| `errors.py` | The 7-class exception hierarchy. |

## Footguns

- **`is_remote_source` is internal-only and load-bearing.** It tags content as
  remote-attacker-controllable for downstream prompt-injection awareness in
  `ai_service.py` extraction prompt assembly (per OWASP LLM01). The
  `ImportedSource.to_dict()` method **intentionally omits** it; regression
  test `test_to_dict_omits_is_remote_source` enforces this. Do not expose
  the flag in any HTTP response shape.
- **`from_text` defaults to `min_text_length=1`**, not the URL-path floor of
  200. This preserves `/api/extract`'s current behavior of accepting any
  non-empty text. Callers that want the URL-path floor must pass it
  explicitly.
- **URL strip happens before fetch.** Without `url.strip()`, URLs pasted with
  surrounding whitespace fail scheme parsing in `_validate_outbound_target`.
  Don't refactor it out of `from_url`.
- **Content-type branching is in `from_url`, not `parse`.** `text/plain`
  uses `extract_plain`; everything else (default `text/html`) uses
  `extract_html`. If you add a new MIME type, branch here.
- **`ParseEmpty` is a real outcome, not always a bug.** Some real pages
  contain only navigation chrome; the pipeline must handle it as a
  user-facing error, not a 500.

## Related

- OWASP LLM01: <https://owasp.org/www-project-top-10-for-large-language-model-applications/>
- Tests: `tests/source_intake/` (7 files).
- Consumer: `ai_service.py` extraction path; `/api/extract` and `/api/extract-url` routes.
