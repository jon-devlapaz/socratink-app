# Imported Source Intake — design

**Date:** 2026-04-30
**Scope:** Extract a deep `source_intake` module from `main.py:285-449`. Unify URL fetch and raw-text submission behind one value type. Close known SSRF/redirect gap inline. Replace regex HTML stripping with a real parser.
**Source candidate:** Candidate #4 from the 2026-04-30 architecture review session (lowest-coupling deepening opportunity; chosen first per the testing-order analysis).
**Codex research:** All seven domains in this spec align with the 2026-04-30 Codex peer review (best practice + antipatterns for Python web fetching, SSRF, charset, HTML→text, denylist, module shape).

---

## Goal

Replace the 67-line `extract_url` route + three private helpers in `main.py` with:

- A self-contained `source_intake/` module that owns network I/O, parsing, and domain errors.
- A unified entry point (`from_url`, `from_text`) producing a single value type (`ImportedSource`).
- Redirect-aware SSRF defense with pinned-IP connect (closes DNS rebinding TOCTOU).
- A pure-function parser tested without network mocking.
- A small route-layer mapping table that maps domain exceptions to HTTP responses with oracle-defense collapsing of SSRF/DNS errors.

Wire contract is preserved on both `/api/extract-url` and `/api/extract`.

---

## Domain-language addition

Add to `UBIQUITOUS_LANGUAGE.md` under a new "Content Intake" section before any code lands (commit 1).

| Term | Definition | Aliases to avoid |
|---|---|---|
| **Imported source** | A normalized text source ready for Gemini extraction. Either fetched from a URL or supplied as raw text by the learner. Carries the canonical (post-redirect) URL when present and a flag indicating remote-attacker-controllability. | "Article", "fetched page", "scraped content" |

Relationships:

- An **Imported source** is the input to the **Draft map** extraction pipeline.
- An **Imported source** that is `is_remote_source=True` is treated as untrusted in extraction prompt assembly (per OWASP LLM01).

---

## Principles

These shape every decision below.

1. **The interface is the test surface.** Pure-function parser is the largest test layer. Network is contained behind one seam.
2. **Oracle defense is co-located.** Route-layer mapping table is the only place that translates domain errors into user-visible messages; SSRF and DNS failures collapse to one user response.
3. **Redirect re-validation is non-negotiable.** Every redirect target re-runs the full validation chain. SSRF protection lives at the same seam regardless of redirect depth.
4. **Pinned-IP connect closes DNS rebinding.** Validated IPs are connected to directly; original hostname preserved for Host header, SNI, and cert verification.
5. **Wire contract preserved.** Both routes' request/response shapes do not change in this refactor.
6. **Native deps are out.** BS4 with stdlib `html.parser`, `charset-normalizer` (pure-Python wheel), `urllib3` (no native build). No `lxml`, no `selectolax`.
7. **Old code is removed only after the new code is proven wired.** Helpers stay orphaned for one commit so a clean revert point exists.

---

## Architecture

```
            ┌─────────────────────────────┐
            │      main.py route          │
            │   /api/extract-url          │
            │   /api/extract              │
            │                             │
            │   try:                      │
            │     src = from_url(req.url) │  ← or from_text(req.text)
            │   except SourceIntakeError: │
            │     raise _map_intake_error │  ← single mapping table
            │                             │
            │   return src.to_dict()      │  (extract-url)
            │   return knowledge_map      │  (extract — wire-shape unchanged)
            └──────────────┬──────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │   source_intake/__init__.py │
            │     from_url, from_text     │
            │     ImportedSource (export) │
            │     errors (re-export)      │
            │   Orchestrates fetch → parse│
            └──────┬───────────────┬──────┘
                   │               │
                   ▼               ▼
        ┌────────────────┐  ┌──────────────────┐
        │   fetch.py     │  │    parse.py      │
        │ (network I/O)  │  │ (pure functions) │
        │                │  │                  │
        │ fetch(url)     │  │ decode(...)      │
        │   → FetchedSrc │  │ extract_html(...)│
        │                │  │ extract_plain(...)│
        │ Validates →    │  │   → ParsedPage   │
        │ pins IP →      │  │                  │
        │ streams        │  │ Raises:          │
        │                │  │   ParseEmpty     │
        │ Re-validates   │  └──────────────────┘
        │ on redirect    │
        │                │
        │ Raises:        │
        │   InvalidUrl,  │
        │   BlockedSrc,  │
        │   FetchFailed, │
        │   UnsupportedContent,│
        │   TooLarge     │
        └────────────────┘
```

**Module tree:**

```
source_intake/
  __init__.py    # public facade: ImportedSource, from_url, from_text, errors
  fetch.py       # all network I/O: SSRF (initial + redirect), caps, content-type
  parse.py       # pure: decode, DOM, title fallback, text extraction
  errors.py      # InvalidUrl, BlockedSource, FetchFailed, UnsupportedContent, TooLarge, ParseEmpty
```

**Boundary rules:**

- `fetch.py` returns `FetchedSource(raw_bytes, headers, final_url, content_type)`. No HTML parsing. No `HTTPException`. No charset interpretation.
- `parse.py` is pure: imports nothing from `urllib`, `socket`, `ipaddress`, or any I/O module.
- `__init__.py` is the only orchestrator. Routes import from `__init__.py`; nothing else.
- `errors.py` has zero dependencies. Imported everywhere.
- `final_url` (post-redirect) is what `ImportedSource.url` carries — the canonical URL, not the user's submitted URL.
- `from_text` cannot raise network-domain errors. Only `ParseEmpty` is reachable.

---

## Public interface

### Value types

```python
# source_intake/__init__.py
@dataclass(frozen=True)
class ImportedSource:
    """An imported text source, ready for Gemini extraction.

    Either fetched from a URL (`from_url`) or supplied as raw text (`from_text`).
    Carries the canonical (post-redirect) URL when present.

    `is_remote_source` flags content as remote-attacker-controllable for
    downstream prompt-injection awareness in ai_service.py extraction prompt
    assembly. (See OWASP LLM01.)
    """
    url: str | None             # final_url after redirects, or None for from_text
    title: str                  # max 200 chars, never empty (host fallback)
    text: str                   # max 500_000 chars
    is_remote_source: bool      # True from_url, False from_text

    def to_dict(self) -> dict:
        """JSON shape for the /api/extract-url response.
        
        Intentionally omits is_remote_source — that flag is internal-only.
        Regression test enforces this omission.
        """
        return {"url": self.url, "title": self.title, "text": self.text}


# source_intake/fetch.py
@dataclass(frozen=True)
class FetchedSource:
    """Raw fetch result. Headers preserved verbatim; lowercase keys; no charset interpretation."""
    raw_bytes: bytes
    headers: Mapping[str, str]   # lowercase keys; values verbatim
    final_url: str               # post-redirect canonical URL
    content_type: str            # lowercase, no charset suffix


# source_intake/parse.py
@dataclass(frozen=True)
class ParsedPage:
    """Pure-function output of html or plain-text parsing.
    Title is always populated (host fallback applied here, not in the facade).
    """
    title: str    # max 200 chars, never empty
    text: str     # max 500_000 chars; raises ParseEmpty if < min_text_length
```

### Public functions

```python
# source_intake/__init__.py

def from_url(url: str) -> ImportedSource:
    """Fetch and parse a single web page.
    
    Raises (any of): InvalidUrl, BlockedSource, FetchFailed,
                     UnsupportedContent, TooLarge, ParseEmpty.
    """
    fetched = fetch.fetch(url)
    decoded = parse.decode(fetched.raw_bytes, fetched.headers)
    if fetched.content_type == "text/plain":
        parsed = parse.extract_plain(decoded, source_url=fetched.final_url)
    else:
        parsed = parse.extract_html(decoded, source_url=fetched.final_url)
    return ImportedSource(
        url=fetched.final_url,
        title=parsed.title,
        text=parsed.text,
        is_remote_source=True,
    )


def from_text(text: str, *, min_text_length: int = 1) -> ImportedSource:
    """Normalize a raw-text submission. No fetch.
    
    Default min_text_length=1 preserves /api/extract's current behavior of
    accepting any non-empty text. Callers that want the URL-path floor pass
    min_text_length=200 explicitly.
    
    Raises: ParseEmpty.
    """
    parsed = parse.extract_plain(text, source_url=None, min_text_length=min_text_length)
    return ImportedSource(
        url=None,
        title=parsed.title,
        text=parsed.text,
        is_remote_source=False,
    )
```

### Domain exceptions

```python
# source_intake/errors.py
class SourceIntakeError(Exception):
    """Base for all domain exceptions raised by source_intake."""

class InvalidUrl(SourceIntakeError): ...           # malformed URL, missing hostname, invalid port (scheme errors → BlockedSource(blocked_scheme))

class BlockedSource(SourceIntakeError):            # SSRF/port/scheme/denylist (also after redirect)
    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        self.reason = reason
        # one of: "private_address" | "blocked_port" | "blocked_video" | "blocked_scheme"

class FetchFailed(SourceIntakeError):              # DNS / connect / timeout / upstream HTTP
    def __init__(self, message: str, *, cause: str):
        super().__init__(message)
        self.cause = cause
        # one of: "dns" | "connect" | "timeout" | "http_4xx" | "http_5xx"

class UnsupportedContent(SourceIntakeError): ...   # content-type not text/html or text/plain; or content-encoding != identity
class TooLarge(SourceIntakeError): ...             # streamed bytes exceeded MAX_BYTES
class ParseEmpty(SourceIntakeError): ...           # extracted text below min_text_length after parsing
```

`reason` and `cause` carry full fidelity for server-side logging. Route mapping reads `BlockedSource.reason` to drive UX messaging for `blocked_scheme`/`blocked_port`/`blocked_video` (each gets its own user message). The oracle-defense rule is narrower than "never reads": `BlockedSource(private_address)` and any `FetchFailed.cause` collapse to one identical 502 user response, so an attacker cannot distinguish "this is a private IP" from "DNS failed" / "connection refused" / etc.

---

## Error handling & route mapping

### Mapping function (lives in `main.py` near the route)

```python
def _map_intake_error(exc: SourceIntakeError) -> HTTPException:
    """Maps domain exception → HTTP response.

    Oracle defense: BlockedSource(private_address) and FetchFailed both
    surface as 502 with the same generic user-facing message, so an
    attacker cannot use response differences to map internal network state.
    """
    if isinstance(exc, InvalidUrl):
        return HTTPException(400, "Enter a valid http(s) URL.")
    if isinstance(exc, BlockedSource):
        if exc.reason == "private_address":
            return HTTPException(502, "We couldn't reach that URL.")
        if exc.reason == "blocked_port":
            return HTTPException(400, "Only standard web ports (80/443) are supported.")
        if exc.reason == "blocked_scheme":
            return HTTPException(400, "Only http and https URLs are supported.")
        if exc.reason == "blocked_video":
            return HTTPException(400, "Video links aren't supported. Paste the text directly instead.")
        return HTTPException(502, "We couldn't reach that URL.")  # unknown reason → fail closed
    if isinstance(exc, FetchFailed):
        return HTTPException(502, "We couldn't reach that URL.")
    if isinstance(exc, UnsupportedContent):
        return HTTPException(415, "We can only import HTML or plain-text pages.")
    if isinstance(exc, TooLarge):
        return HTTPException(413, "Page is too large to import.")
    if isinstance(exc, ParseEmpty):
        return HTTPException(422, "Couldn't extract enough readable text from that page.")
    logger.exception("Unmapped SourceIntakeError")
    return HTTPException(500, "Unexpected error while importing.")
```

### Mapping table

| Domain error | `reason` / `cause` | Status | User-visible message |
|---|---|---|---|
| `InvalidUrl` | — | 400 | "Enter a valid http(s) URL." |
| `BlockedSource` | `private_address` | **502 generic** | "We couldn't reach that URL." |
| `BlockedSource` | `blocked_port` | 400 | "Only standard web ports (80/443) are supported." |
| `BlockedSource` | `blocked_scheme` | 400 | "Only http and https URLs are supported." |
| `BlockedSource` | `blocked_video` | 400 | "Video links aren't supported. Paste the text directly instead." |
| `FetchFailed` | `dns` / `connect` / `timeout` / `http_4xx` / `http_5xx` | **502 generic** | "We couldn't reach that URL." |
| `UnsupportedContent` | — | 415 | "We can only import HTML or plain-text pages." |
| `TooLarge` | — | 413 | "Page is too large to import." |
| `ParseEmpty` | — | 422 | "Couldn't extract enough readable text from that page." |

### Routes after refactor

```python
# /api/extract-url
@app.post("/api/extract-url")
def extract_url(req: UrlExtractRequest):
    try:
        src = source_intake.from_url(req.url)
    except SourceIntakeError as exc:
        logger.info("intake_failed", extra={
            "exc_type": type(exc).__name__,
            "reason": getattr(exc, "reason", None),
            "cause": getattr(exc, "cause", None),
            "url_summary": _summarize_url_for_log(req.url),  # see helper below
        })
        raise _map_intake_error(exc)
    except Exception:
        logger.exception("intake_unexpected", extra={"url_summary": _summarize_url_for_log(req.url)})
        raise HTTPException(500, "Unexpected error while importing.")
    return src.to_dict()


def _summarize_url_for_log(url: str) -> dict:
    """Sanitized fields for logging. URLs can carry basic-auth credentials,
    signed query tokens, fragments, or private course links — we never log
    the raw URL.
    """
    try:
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "port": parsed.port,
            "path_len": len(parsed.path or ""),
            "has_query": bool(parsed.query),
            "has_userinfo": bool(parsed.username or parsed.password),
        }
    except Exception:
        # Don't let the logger choke on malformed URLs.
        return {"unparseable": True, "len": len(url) if url else 0}


# /api/extract — wire contract unchanged; from_text added for normalization.
# IMPORTANT: preserves the existing route's Gemini-error shell verbatim
# (MissingAPIKeyError → 401, GeminiRateLimitError → 429, GeminiServiceError → 503,
# ValueError → 400, generic → 500). The ONLY change is normalizing input via
# from_text() before calling extract_knowledge_map.
@app.post("/api/extract")
def extract(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        src = source_intake.from_text(req.text)   # default min_text_length=1
    except ParseEmpty as err:
        raise HTTPException(status_code=400, detail=str(err))
    try:
        knowledge_map = extract_knowledge_map(src.text, api_key=req.api_key)
        return {"knowledge_map": knowledge_map}
    except MissingAPIKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except GeminiRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except GeminiServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract")
        raise HTTPException(
            status_code=500, detail="Unexpected server error during extraction."
        ) from err
```

---

## Fetch internals

### Constants

```python
ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
SUPPORTED_CONTENT_TYPES = frozenset({"text/html", "text/plain"})
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 12
USER_AGENT = "Mozilla/5.0 (compatible; socratink/1.0; +https://app.socratink.ai)"
VIDEO_HOST_SUFFIXES = ("youtube.com", "youtu.be", "youtube-nocookie.com")
```

### `fetch.fetch(url)` — redirect lifecycle

```
def fetch(url) -> FetchedSource:
    current_url = url
    redirects = 0
    while True:
        validated_ips = _validate_outbound_target(current_url)   # raises; returns ordered list of validated IPs

        try:
            response = _open_pinned(current_url, validated_ips)   # tries IPs in order until one connects
        except urllib3 connection / timeout errors:
            raise FetchFailed(cause=...)

        if 300 <= response.status < 400:
            location = response.headers.get("location")
            response.release_conn()   # close before re-validating new target
            if not location:
                raise FetchFailed("3xx without Location", cause="connect")
            redirects += 1
            if redirects > MAX_REDIRECTS:
                raise FetchFailed("too many redirects", cause="connect")
            current_url = urljoin(current_url, location)
            continue   # ← re-validates next target at top of loop

        # urllib3 returns 4xx/5xx as responses, not exceptions.
        # Catch them BEFORE content-type policing so a 404 HTML error page
        # cannot pass through as importable content.
        if 400 <= response.status < 500:
            response.release_conn()
            raise FetchFailed(f"upstream HTTP {response.status}", cause="http_4xx")
        if 500 <= response.status < 600:
            response.release_conn()
            raise FetchFailed(f"upstream HTTP {response.status}", cause="http_5xx")

        if response.headers.get("content-encoding", "identity").lower() != "identity":
            response.release_conn()
            raise UnsupportedContent("server returned encoded content")

        content_type_header = response.headers.get("content-type", "")
        if not content_type_header:
            response.release_conn()
            raise UnsupportedContent("missing content-type")
        content_type = content_type_header.split(";")[0].strip().lower()
        if content_type not in SUPPORTED_CONTENT_TYPES:
            response.release_conn()
            raise UnsupportedContent(f"content-type {content_type!r}")

        try:
            raw = _read_with_cap(response, MAX_BYTES)   # raises TooLarge
        except Exception:
            response.release_conn()
            raise
        finally:
            # Successful path also closes; release_conn is idempotent.
            response.release_conn()

        headers = {k.lower(): v for k, v in response.headers.items()}
        return FetchedSource(raw, headers, current_url, content_type)
```

### `_validate_outbound_target(url)` — pre-fetch checks

Single function, two call sites (initial URL + every redirect target). Returns the ordered list of validated global IPs.

```
1. parsed = urlparse(url)                     # raises InvalidUrl on URL parse failure
2. if scheme not in {http, https}:            BlockedSource(blocked_scheme)
3. if not parsed.hostname:                    InvalidUrl("missing hostname")
4. try parsed.port:                           except ValueError → InvalidUrl("invalid port")
5. resolve hostname → list of ip addresses    (socket.getaddrinfo)
   if gaierror:                               FetchFailed(cause="dns")
6. for each resolved IP:
     if private/loopback/link-local/reserved/multicast/unspecified:
                                              BlockedSource(private_address)
7. effective_port = parsed.port or scheme-default
   if effective_port not in {80, 443}:        BlockedSource(blocked_port)
8. if hostname matches video denylist:        BlockedSource(blocked_video)
9. return ordered list of validated IPs
```

Order rationale: scheme check first (so `file://` never reaches DNS); hostname presence next; DNS resolve next (so private-IP rejection is the visible signal for any privately-hosted target); then port, then denylist. Port check after DNS so `http://10.0.0.1:25` and `http://10.0.0.1:80` both surface as `private_address` (oracle defense).

### Pinned-IP connection

```python
class _PinnedHTTPSConnection(urllib3.connection.HTTPSConnection):
    """Connects to a pre-validated IP while preserving Host/SNI/cert
    verification against the original hostname. Closes DNS rebinding TOCTOU."""
    def __init__(self, *args, dest_ip: str, **kwargs):
        self._dest_ip = dest_ip
        super().__init__(*args, **kwargs)
    def _new_conn(self):
        # Connect to self._dest_ip; self.host (Host header, SNI, cert verification)
        # remains the original hostname.
        ...

# (parallel _PinnedHTTPConnection for http://)

def _open_pinned(url: str, validated_ips: list[str]) -> urllib3.HTTPResponse:
    """Try each validated IP in order; first connect wins.

    Sends a relative request target (path + query), not the absolute URL.
    Direct origin connections expect origin-form `/path?query`; sending the
    absolute form would cause some servers to misroute or 400.
    """
    parsed = urlparse(url)
    request_target = parsed.path or "/"
    if parsed.query:
        request_target = f"{request_target}?{parsed.query}"

    last_exc = None
    for ip in validated_ips:
        try:
            pool = _build_pinned_pool(parsed, ip)   # pool carries hostname for Host/SNI/cert
            return pool.urlopen(
                "GET",
                request_target,
                headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
                redirect=False,
                preload_content=False,
                decode_content=False,
                timeout=urllib3.Timeout(total=TIMEOUT_SECONDS),
            )
        except (NewConnectionError, ConnectTimeoutError) as exc:
            last_exc = exc
            continue
    raise FetchFailed("all validated IPs unreachable", cause="connect") from last_exc
```

**Three implementation invariants:**

- **Relative request target.** `pool.urlopen` receives `/path?query`, not the absolute URL. Direct origin connections expect origin-form. Host/SNI/cert verification stays tied to the hostname via the pinned pool's configuration.
- **`preload_content=False` is critical.** Without it, urllib3 buffers the full response before `_read_with_cap` enforces `MAX_BYTES`. Streaming actually streams.
- **`decode_content=False`** ensures we never auto-decompress (paired with `Accept-Encoding: identity`).
- **Every early exit closes the response.** With `preload_content=False`, redirects, 4xx/5xx, unsupported content, oversized bodies, and exceptions all need `response.release_conn()` (or `.close()`). Otherwise commit 5 leaks sockets during redirect loops and size-cap failures. The fetch lifecycle pseudocode above shows the close points; implementation must include them at every early-exit branch.

### Streaming byte cap

```python
def _read_with_cap(response: urllib3.HTTPResponse, max_bytes: int) -> bytes:
    """Stream-read up to max_bytes; raise TooLarge if exceeded.
    
    Reads in chunks; aborts as soon as cumulative size exceeds cap.
    Does not trust Content-Length.
    """
    chunks = []
    total = 0
    try:
        for chunk in response.stream(amt=16384, decode_content=False):
            total += len(chunk)
            if total > max_bytes:
                raise TooLarge(f"exceeded {max_bytes} bytes")
            chunks.append(chunk)
        return b"".join(chunks)
    except TooLarge:
        # Drain not attempted; let the caller release the connection.
        raise
```

---

## Parse internals

### `decode(raw_bytes, headers) -> str`

```
1. BOM detection (UTF-8 → UTF-32 → UTF-16; check longest first)
2. Content-Type charset header (parsed for `charset=...`)
3. Early <meta charset> peek (first 1024 bytes ASCII-decoded; HTML only)
4. charset-normalizer fallback
5. Final fallback: utf-8 with errors="replace"
```

Never raises. Each step skipped if the step before yielded a successful decode.

### `extract_html(html, source_url) -> ParsedPage`

```python
def extract_html(html: str, source_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")   # stdlib parser; no native dep

    title = _extract_title(soup, source_url)

    # Preserve <pre> content before stripping (whitespace matters for code blocks)
    pre_blocks = _extract_pre_blocks(soup)

    # Drop non-content tags
    for tag in soup.select("script, style, noscript, svg, iframe, template, head"):
        tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)
    text = _restore_pre_blocks(text, pre_blocks)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)   # strip control chars; preserve \t \n \r
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if len(text) < 200:
        raise ParseEmpty(f"extracted {len(text)} chars after parsing")

    return ParsedPage(title=title[:200], text=text[:500_000])
```

**Title fallback chain** (in `_extract_title`):

1. `<title>` text (`.get_text(strip=True)` to handle entity refs and nested tags)
2. `<meta property="og:title" content="…">`
3. `<meta name="twitter:title" content="…">`
4. First `<h1>`
5. `urlparse(source_url).hostname`
6. `"Imported text"` (final default)

Each step skipped if empty/whitespace-only. Truncated to 200 chars.

**`<pre>` preservation rationale:** indentation in code blocks matters for technical docs (which Socratink frequently imports). Inline `<code>` is NOT special-cased; only block `<pre>` — special-casing inline `<code>` produces weird spacing in normal prose.

### `extract_plain(text, source_url=None, *, min_text_length=200) -> ParsedPage`

```python
def extract_plain(text: str, source_url: str | None = None, *, min_text_length: int = 200) -> ParsedPage:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if len(cleaned) < min_text_length:
        raise ParseEmpty(f"raw text {len(cleaned)} chars (min {min_text_length})")

    # Title: first non-empty line if short, else host or default
    first_line = next((l.strip() for l in cleaned.split("\n") if l.strip()), "")
    if first_line and len(first_line) <= 200:
        title = first_line
    elif source_url and (host := urlparse(source_url).hostname):
        title = host
    else:
        title = "Imported text"

    return ParsedPage(title=title[:200], text=cleaned[:500_000])
```

`min_text_length` is a parameter rather than a parser invariant because the two intake paths have different policies: `from_url` enforces 200 (preserves URL-path behavior), `from_text` defaults to 1 (preserves `/api/extract` behavior). Layered defaults: `extract_plain` defaults to 200 (the URL-path policy); `from_text` overrides to 1 (the raw-text-path policy). Callers that want a different floor pass `min_text_length` explicitly.

### Length thresholds

- `MIN_TEXT_LENGTH = 200` for URL paths (preserved from current code)
- `MIN_TEXT_LENGTH = 1` for `from_text` (preserves `/api/extract` wire contract)
- `MAX_TEXT_LENGTH = 500_000` — truncated, never raises
- `MAX_TITLE_LENGTH = 200` — truncated, never raises

### Security note for `parse.py` docstring

> BS4 with stdlib `html.parser` does not parse XML and is not vulnerable to billion-laughs / XXE. We deliberately do not depend on `lxml` for this reason.

---

## Testing strategy

### Test layout

```
tests/source_intake/
  test_parse_decode.py            # charset chain ordering
  test_parse_extract_html.py      # title chain, text extraction, <pre>, ParseEmpty, control chars
  test_parse_extract_plain.py     # title heuristic, min_text_length parameter, control chars
  test_fetch_validate.py          # _validate_outbound_target() raises correctly
  test_fetch_redirect.py          # redirect re-validation; 302 to private IP blocked
  test_fetch_pinned_ip.py         # pinned-IP connect actually pins (rebinding defense)
  test_fetch_size_cap.py          # streaming abort fires before MAX_BYTES
  test_fetch_content_type.py      # encoded content rejected, missing CT rejected
  test_facade.py                  # from_url + from_text orchestration; is_remote_source flag
  fixtures/                       # real HTML/byte fixtures

tests/test_intake_route_mapping.py   # _map_intake_error parametrized over the table
tests/test_extract_url_route.py      # FastAPI TestClient end-to-end (mocked from_url for smoke)
```

### Test layers

1. **Pure parse tests** — input/output, no mocks. Highest count (~50). Charset chain ordering, title fallback, `<pre>` preservation, control char stripping, `min_text_length` parameter, `ParseEmpty` thresholds.
2. **Fetch validation tests** — `fake_dns` fixture (monkey-patches `socket.getaddrinfo`). Parametrized over schemes, ports, video hosts, and a battery of private IPv4/IPv6 addresses (10.0.0.1, 127.0.0.1, 169.254.169.254, ::1, fc00::1, fe80::1, etc.).
3. **Pinned-IP rebinding test** — `fake_dns` with sequential responses (first lookup returns global IP, second would return private). Pinned-connector shim records intended dest_ip. Asserts (a) connection went to the validated IP, (b) DNS was resolved exactly once.
4. **Redirect re-validation** — local stdlib `ThreadingHTTPServer` returns `302 Location: http://10.0.0.1/`. `fake_dns` resolves the start URL's fake-public hostname to a routable test IP (e.g., `203.0.113.5` from RFC 5737 test space — passes the private-IP rejection check). The pinned-connector test shim records that IP as the intended dest while physically connecting to localhost where the test server is bound. Validation rejects the redirect target with `BlockedSource(private_address)`.
5. **Size cap test** — slow/large local server (10MB at 100KB/s); cap is 2MB. Test must complete in <30s — proves streaming abort fired.
6. **Facade tests** — `is_remote_source` propagation (True from URL, False from text); `to_dict()` regression test asserting `is_remote_source` is absent from output.
7. **Route mapping table** — parametrized over `(exc, status, fragment)` tuples. Includes explicit oracle-defense equality test: `BlockedSource(private_address)` and `FetchFailed(dns)` produce identical responses.
8. **Route smoke** — FastAPI TestClient with `from_url` patched. Catches wiring errors only; not a substitute for hosted smoke.

### Test infrastructure

- **Local HTTP server:** stdlib `http.server.ThreadingHTTPServer`. No new test deps.
- **Pinned-IP shim:** small test-only subclass of `_PinnedHTTPSConnection` that records the *intended* `dest_ip` while physically connecting to localhost (where the test server is bound). Lives in `tests/source_intake/conftest.py` — not in production `fetch.py`.
- **`fake_dns` returns public test IPs.** Use RFC 5737 test ranges (`203.0.113.0/24`, `198.51.100.0/24`, `192.0.2.0/24`) so `_validate_outbound_target` correctly accepts them as global. The shim then physically routes the connection to localhost. `_validate_outbound_target` would (correctly) block any test that tried to point a fake hostname at `127.0.0.1` directly — that's why the shim layer exists.
- **No production `--allow-test-dns` flag.** Production fetch stays config-free.

### Test budget

~80 tests total. Pure-parse layer runs in well under one second.

### Existing tests to retire after refactor

Inventoried in writing-plans. Any test directly exercising `_extract_text_from_html` or `_is_private_url` becomes redundant once the helpers are removed in commit 9.

---

## Migration sequencing

Nine commits, each a clean checkpoint. Each can be reverted independently of subsequent commits.

| # | Commit | Verification gate | Rollback risk |
|---|---|---|---|
| 1 | **Glossary update.** Add "Imported source" to `UBIQUITOUS_LANGUAGE.md`. No code changes. | `bash scripts/doctor.sh` | none |
| 2 | **Add deps.** `requirements.txt` exact pins: `beautifulsoup4==<verified>`, `charset-normalizer==<verified>`, `urllib3==2.6.3`. Verify exact versions at preflight time. | `bash scripts/preflight-deploy.sh` | low — pure additive |
| 3 | **Scaffolding.** `source_intake/` directory with `__init__.py`, `errors.py`, `parse.py`, `fetch.py` as stubs. Public types declared. No logic. | `pytest` (existing suite green; new stubs don't break collection) | none — code unreached |
| 4 | **Pure parse module + tests.** Full `parse.py`. ~50 tests, no I/O. | `pytest tests/source_intake/test_parse_*.py -v` | none |
| 5 | **Fetch module + tests.** Full `fetch.py` including `_validate_outbound_target`, `_PinnedHTTPSConnection`, redirect loop, `_read_with_cap`. **Pinned-IP rebinding test must pass before this commit lands.** | `pytest tests/source_intake/test_fetch_*.py -v` + manual review of `_validate_outbound_target` ordering | none — module unreached by routes |
| 6 | **Facade.** `from_url` + `from_text` in `__init__.py`. Layer-6 tests including `is_remote_source` propagation and `to_dict()` omission regression. | `pytest tests/source_intake/test_facade.py -v` | none |
| 7 | **Route swap (extract-url).** `/api/extract-url` body replaced with `try/except → _map_intake_error`. Add `_map_intake_error` and parametrized mapping table tests. **No deletion of old helpers yet.** | Full `pytest`; smoke `bash scripts/qa-smoke.sh local`; manual `curl` checks on success/video/oversized/malformed paths; deploy + `bash scripts/verify-deploy.sh HEAD`; hosted smoke; observation window | **medium** — first commit users actually exercise |
| 8 | **Route swap (extract).** `/api/extract` body normalizes through `from_text(req.text)` before passing to Gemini (default `min_text_length=1` preserves wire contract). | Full `pytest`; smoke local; deploy + hosted smoke; observation window | low |
| 9 | **Delete old code.** Remove `_extract_text_from_html`, `_is_blocked_video_url`, `_is_private_url` from `main.py`. Remove inline route logic. | Full `pytest`; smoke local; preflight; hosted smoke | none — test suite proves replacement is wired |

### Verification cadence

Per AGENTS.md, `main.py` is on the high-risk list. Three production deploys total (commits 7, 8, 9). Each deploy gets:

- `bash scripts/verify-deploy.sh HEAD`
- Full hosted smoke
- One observation window before the next commit lands

---

## Out of scope

Locked. These items are explicitly NOT included in this refactor.

- **`is_remote_source` flag is set but not yet read.** Wiring the flag into `ai_service.py` extraction prompt assembly is a separate change. The flag is in place so that change is a one-liner.
- **No `/api/extract` response shape change.** Stays `{ knowledge_map: ... }`.
- **No new logging infrastructure.** `logger.info("intake_failed", extra={...})` reuses the existing logger.
- **No new tests for `ai_service.py` extraction path.** Outside scope — that's candidates #2/#3 territory.
- **No PDF, SPA, or paywall handling.** Codex's research argued these are net-negative for our pipeline. Status quo.
- **No allowlist mechanism for "narrow exceptions."** If a real user hits a legitimate non-standard-port redirect, we add a hostname-specific allowlist in a follow-up — not a global port relaxation.

---

## Residual risks

- **SSRF tightening could reject legitimate redirect chains.** A 302 to a non-standard port (`:8080`) returns a 502 it didn't before. Acceptable; flagged for monitoring after commit 7 deploy.
- **`charset-normalizer` cold-start on Vercel.** Pure-Python wheel per Codex, but worth measuring response time on the first cold container. If startup adds >100ms, revisit lazy import.
- **BS4 `html.parser` accuracy on adversarial HTML.** Pages with malformed nesting decode differently from `lxml`. Accepted trade-off for avoiding a native dep. Fixture-driven regression tests catch real-page issues.
- **DNS rebinding closure depends on the pinned-IP test passing.** If that test fails or is skipped, we ship an SSRF-broken refactor. Commit 5 gate is non-negotiable.

---

## Cross-references

- Codex research output (2026-04-30) — informs all seven domain decisions
- Architecture review session (2026-04-30) — Candidate #4
- AGENTS.md — high-risk file list, smoke discipline, deployment verification
- UBIQUITOUS_LANGUAGE.md — domain glossary (gets the "Imported source" addition in commit 1)
- OWASP SSRF cheat sheet — basis for redirect re-validation, scheme/port allowlists
- OWASP LLM01 — basis for `is_remote_source` flag
