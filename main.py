import hashlib
import json
import logging
import os
import time as _time
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, RedirectResponse, Response

from auth import (
    auth_router,
    build_auth_service_from_env,
    load_current_session_state,
)
from auth.supabase_client import build_supabase_client
from ai_service import (
    GeminiRateLimitError,
    GeminiServiceError,
    MissingAPIKeyError,
    drill_chat,
    extract_knowledge_map,
    generate_provisional_map_from_sketch,
    generate_repair_reps,
    get_drill_session_time_limit_seconds,
)
from learning_commons import (
    LC_STATUS_HTTP_ERROR,
    LC_STATUS_KEY_MISSING,
    LC_STATUS_PARSE_ERROR,
    LC_STATUS_TIMEOUT,
    LC_STATUS_TRANSPORT_ERROR,
    LCClient,
    should_enrich_with_lc,
)
from llm.errors import (
    LLMClientError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
import source_intake
from source_intake import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)
from runtime_env import load_app_env

load_app_env()

app = FastAPI()
app.state.auth_service = build_auth_service_from_env()
logger = logging.getLogger(__name__)


# Per-1k-token rates by model name. Update when model pricing changes.
# Source: https://ai.google.dev/pricing as of 2026-05-03.
_MODEL_PRICING_PER_1K: dict[str, tuple[float, float]] = {
    # (input_per_1k_usd, output_per_1k_usd)
    "gemini-2.5-flash": (0.000125, 0.000375),
    "gemini-2.5-flash-lite": (0.0000625, 0.0001875),
    "gemini-2.5-pro": (0.00125, 0.005),
}


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Best-effort cost estimate. Returns None for unknown models."""
    rates = _MODEL_PRICING_PER_1K.get(model)
    if rates is None:
        logger.warning("ai_call.unknown_model_for_cost_estimate", extra={"model": model})
        return None
    in_rate, out_rate = rates
    return round(
        (input_tokens / 1000.0) * in_rate
        + (output_tokens / 1000.0) * out_rate,
        6,
    )


def _emit_ai_call(*, stage: str, model: str, latency_ms: float,
                  input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Emit concept_create.ai_call telemetry per spec §5.4.

    Cost estimation uses a model-aware pricing table. Unknown models log a
    warning and emit cost_usd_est=None — honest signal beats a wrong-looking number.
    """
    cost_usd_est = _estimate_cost_usd(model, input_tokens, output_tokens)
    logger.info(
        "concept_create.ai_call",
        extra={
            "stage": stage,
            "model": model,
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "latency_ms": latency_ms,
            "cost_usd_est": cost_usd_est,
        },
    )


PROTECTED_HTML_PATHS = frozenset({"/", "/index.html", "/admin/todo"})
PROTECTED_API_PATHS = frozenset(
    {
        "/api/drill",
        "/api/extract",
        "/api/extract-url",
        "/api/repair-reps",
        "/api/admin/todo",
        "/api/admin/todo/mtime",
        "/api/admin/todo/toggle",
        "/api/admin/todo/move",
        "/api/admin/todo/edit",
        "/api/admin/todo/issue",
        "/api/admin/feedback",
    }
)

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def block_sensitive_files(request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        return await call_next(request)
    parts = [p for p in path.split("/") if p]
    if any(part.startswith(".") for part in parts):
        return Response(status_code=404)
    if path.endswith(".py"):
        return Response(status_code=404)
    return await call_next(request)


def _request_return_to(request: Request) -> str:
    path = request.url.path or "/"
    if request.url.query:
        return f"{path}?{request.url.query}"
    return path


def _is_protected_html_request(request: Request) -> bool:
    if request.method not in {"GET", "HEAD"}:
        return False
    path = request.url.path
    if path in PROTECTED_HTML_PATHS:
        return True
    return path.endswith(".html") and path != "/login.html"


def _is_protected_api_request(request: Request) -> bool:
    path = request.url.path
    if not path.startswith("/api/"):
        return False
    if path in {"/api/health", "/api/me"}:
        return False
    if path.startswith("/api/auth/"):
        return False
    return path in PROTECTED_API_PATHS


def _resolve_session_state(request: Request):
    """Returns AuthSessionState (or None if no service / disabled)."""
    service = getattr(request.app.state, "auth_service", None)
    if service is None:
        return None
    sealed_session = request.cookies.get(service.cookie_name)
    try:
        return service.load_session(sealed_session)
    except Exception:
        logger.exception("Auth session gate failed for path=%s", request.url.path)
        return None


def _has_app_entry_session(request, state) -> bool:
    if state is None:
        return False
    return bool(
        getattr(state, "authenticated", False) or getattr(state, "guest_mode", False)
    )


_TRUTHY_AUTOGUEST = {"1", "true", "yes", "on"}


def _dev_autoguest_enabled() -> bool:
    """Local-only escape hatch that auto-mints a guest session on first protected
    GET, so agents and ad-hoc local browsing don't have to click through /login.

    Hard-gated against any production-shaped runtime env. Only fires when the
    explicit opt-in env var is set AND no Vercel/CI markers are present.
    """
    if not os.getenv("SOCRATINK_DEV_AUTOGUEST", "").strip().lower() in _TRUTHY_AUTOGUEST:
        return False
    if os.getenv("VERCEL", "").strip().lower() in _TRUTHY_AUTOGUEST:
        return False
    if os.getenv("VERCEL_ENV"):
        return False
    if os.getenv("CI", "").strip().lower() in _TRUTHY_AUTOGUEST:
        return False
    return True


def _apply_writeback(request: Request, response, state) -> None:
    """Apply refreshed sealed cookie to response if Supabase rotated tokens."""
    if state is None:
        return
    service = request.app.state.auth_service
    sealed = getattr(state, "sealed_session", None)
    if sealed:
        response.set_cookie(
            service.cookie_name,
            sealed,
            secure=service.resolve_cookie_secure(str(request.base_url).rstrip("/")),
            httponly=True,
            samesite=service.cookie_samesite,
            max_age=service.cookie_max_age,
            path="/",
        )
    elif getattr(state, "should_clear_cookie", False):
        response.delete_cookie(service.cookie_name, path="/")


@app.middleware("http")
async def require_login_or_guest_entry(request: Request, call_next):
    path = request.url.path
    if path == "/login.html":
        query = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(url=f"/login{query}", status_code=302)

    state = _resolve_session_state(request)
    is_protected = _is_protected_html_request(request) or _is_protected_api_request(
        request
    )

    if is_protected and not _has_app_entry_session(request, state):
        if path.startswith("/api/"):
            return JSONResponse(
                {
                    "detail": "Choose Google sign-in or continue as guest before using the app."
                },
                status_code=401,
            )
        if _dev_autoguest_enabled():
            # Local dev: skip the /login wall by trampolining straight through
            # the existing guest sign-in route, which sets the session cookie
            # and redirects to the originally requested path.
            return RedirectResponse(
                url=f"/auth/guest?return_to={quote(_request_return_to(request), safe='')}",
                status_code=302,
            )
        return RedirectResponse(
            url=f"/login?return_to={quote(_request_return_to(request), safe='')}",
            status_code=302,
        )

    response = await call_next(request)
    _apply_writeback(request, response, state)
    return response


class SourceAttachment(BaseModel):
    """Optional source material attached to a concept submission."""
    type: Literal["text", "url", "file"]
    text: str | None = Field(None, max_length=500_000)
    url: str | None = Field(None, max_length=2_000)
    filename: str | None = Field(None, max_length=255)


class ExtractRequest(BaseModel):
    """Concept-creation submission.

    Two payload shapes are accepted:

    NEW (Plan A — conversational concept creation):
      {name, starting_sketch, source, api_key?}

    LEGACY (back-compat for the existing form-based client during rollout):
      {text, api_key?}

    Server-side validation in /api/extract enforces the spec §3.2
    substantiveness rule: source-less submits require a substantive sketch.
    """
    # New shape
    name: str | None = Field(None, max_length=200)
    starting_sketch: str | None = Field(None, max_length=10_000)
    source: SourceAttachment | None = None
    # Legacy back-compat
    text: str | None = Field(None, max_length=500_000)
    # Common
    api_key: str | None = Field(None, max_length=200)


def _resolve_extract_path(req: "ExtractRequest") -> dict:
    """Decide which generation path the request takes, with server-side validation.

    Returns one of:
      {"path": "extract", "text": str}
      {"path": "from_sketch", "name": str, "sketch": str}
      {"path": "error", "status": 422, "error": str, "message": str}

    Spec §3.2 truth table is enforced here as defense in depth.
    """
    from models.sketch_validation import is_substantive_sketch

    # Legacy {text} payload — back-compat path. Bypasses the new shape entirely.
    if req.text is not None and req.name is None and req.source is None:
        if not req.text.strip():
            return {"path": "error", "status": 422,
                    "error": "missing_text", "message": "Source text required."}
        return {"path": "extract", "text": req.text}

    # New shape: name is mandatory
    name = (req.name or "").strip()
    if not name:
        return {"path": "error", "status": 422,
                "error": "missing_concept", "message": "Concept name required."}

    sketch = (req.starting_sketch or "").strip()
    has_source_text = (
        req.source is not None
        and req.source.type in ("text", "file")
        and (req.source.text or "").strip()
    )
    has_source_url = (
        req.source is not None
        and req.source.type == "url"
        and (req.source.url or "").strip()
    )
    sketch_ok = is_substantive_sketch(sketch)

    if has_source_text:
        assert req.source is not None
        return {"path": "extract", "text": (req.source.text or "").strip()}

    if has_source_url:
        # URL fetching belongs in /api/extract-url; the dispatcher does
        # not handle URL fetch inline. The frontend should call the right
        # endpoint, but if it sends a URL here we surface the situation
        # rather than silently failing.
        return {"path": "error", "status": 422,
                "error": "url_source_unsupported_here",
                "message": "URL sources go through /api/extract-url."}

    if not sketch_ok:
        # Spec §3.2 row 1: thin sketch + no source → block.
        return {"path": "error", "status": 422,
                "error": "thin_sketch_no_source",
                "message": "Add more to your sketch, or attach source material — either path opens the build."}

    return {"path": "from_sketch", "name": name, "sketch": sketch}


class UrlExtractRequest(BaseModel):
    url: str = Field(..., max_length=2_000)


class DrillMessage(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=50_000)


class DrillRequest(BaseModel):
    concept_id: str = Field(..., max_length=100)
    node_id: str = Field(..., max_length=200)
    node_label: str = Field(..., max_length=500)
    node_mechanism: str = Field("", max_length=10_000)
    drill_session_id: str | None = Field(None, max_length=120)
    client_turn_index: int = Field(0, ge=0, le=200)
    knowledge_map: dict | str
    messages: list[DrillMessage] = Field(..., max_length=100)
    session_phase: str = Field(..., max_length=20)
    drill_mode: str = Field("re_drill", max_length=20)
    re_drill_count: int = Field(0, ge=0, le=999)
    probe_count: int = Field(0, ge=0, le=100)
    nodes_drilled: int = Field(0, ge=0, le=100)
    attempt_turn_count: int = Field(0, ge=0, le=100)
    help_turn_count: int = Field(0, ge=0, le=100)
    session_start_iso: str | None = Field(None, max_length=100)
    bypass_session_limits: bool = False
    api_key: str | None = Field(None, max_length=200)


class RepairRepsRequest(BaseModel):
    concept_id: str = Field(..., max_length=100)
    node_id: str = Field(..., max_length=200)
    node_label: str = Field(..., max_length=500)
    knowledge_map: dict | str
    gap_type: str | None = Field(None, max_length=100)
    gap_description: str | None = Field(None, max_length=1_000)
    count: int = Field(3, ge=3, le=3)
    api_key: str | None = Field(None, max_length=200)


def _resolve_node_mechanism(
    knowledge_map: dict, node_id: str, fallback: str = ""
) -> str:
    if not isinstance(knowledge_map, dict):
        return fallback

    metadata = knowledge_map.get("metadata") or {}
    if node_id == "core-thesis":
        return str(metadata.get("core_thesis") or metadata.get("thesis") or fallback)

    for backbone in knowledge_map.get("backbone") or []:
        if isinstance(backbone, dict) and backbone.get("id") == node_id:
            return str(backbone.get("principle") or backbone.get("label") or fallback)

    for cluster in knowledge_map.get("clusters") or []:
        if not isinstance(cluster, dict):
            continue
        if cluster.get("id") == node_id:
            return str(cluster.get("description") or cluster.get("label") or fallback)
        for subnode in cluster.get("subnodes") or []:
            if isinstance(subnode, dict) and subnode.get("id") == node_id:
                return str(subnode.get("mechanism") or subnode.get("label") or fallback)

    return fallback


def _map_intake_error(exc: SourceIntakeError) -> HTTPException:
    """Maps source_intake domain exception → HTTP response.

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


def _summarize_url_for_log(url: str) -> dict:
    """Sanitized fields for logging. URLs can carry basic-auth credentials,
    signed query tokens, fragments, or private course links — never log raw URL.
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
        return {"unparseable": True, "len": len(url) if url else 0}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "server_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "drill_session_time_limit_seconds": get_drill_session_time_limit_seconds(),
    }


@app.post("/api/extract")
def extract(req: ExtractRequest):
    decision = _resolve_extract_path(req)

    if decision["path"] == "error":
        logger.info(
            "concept_create.build_blocked",
            extra={"reason": decision["error"], "origin": "server"},
        )
        raise HTTPException(status_code=decision["status"], detail={
            "error": decision["error"],
            "message": decision["message"],
        })

    try:
        if decision["path"] == "from_sketch":
            lc_result = None
            lc_query_failed = False
            lc_client = None
            lc_query_started = _time.monotonic()
            try:
                lc_client = LCClient()
                lc_result = lc_client.search_concept(decision["name"])
            except Exception:
                lc_query_failed = True
                logger.exception("lc_query_unexpected")
            lc_latency_ms = int((_time.monotonic() - lc_query_started) * 1000)

            # Always emit lc.queried (spec §5.4 — fires regardless of outcome)
            _concept_hash = hashlib.sha1(decision["name"].lower().encode()).hexdigest()[:12]
            logger.info(
                "concept_create.lc.queried",
                extra={
                    "concept_hash": _concept_hash,
                    "top_score": (lc_result.top_score if lc_result else 0.0),
                    "standards_count": (len(lc_result.standards) if lc_result else 0),
                    "latency_ms": lc_latency_ms,
                },
            )

            lc_context = should_enrich_with_lc(lc_result)
            if lc_context is None:
                # Reason classification for telemetry. Consult lc_client.last_status
                # to distinguish timeout from other null returns (I-1 fix).
                lc_last_status = lc_client.last_status if lc_client is not None else None
                if lc_query_failed:
                    reason = "error"
                elif lc_last_status == LC_STATUS_KEY_MISSING:
                    reason = "key_missing"
                elif lc_last_status == LC_STATUS_TIMEOUT:
                    reason = "timeout"
                elif lc_last_status in (LC_STATUS_TRANSPORT_ERROR, LC_STATUS_HTTP_ERROR, LC_STATUS_PARSE_ERROR):
                    reason = "error"
                elif lc_result is None or not lc_result.standards:
                    reason = "no_results"
                elif lc_result.top_score < 0.70:
                    reason = "low_score"
                else:
                    reason = "non_k12"
                logger.info("concept_create.lc.enrichment_skipped",
                            extra={"reason": reason})
            else:
                logger.info("concept_create.lc.enrichment_applied",
                            extra={"standards_count": len(lc_context)})

            def _on_sketch_call(result):
                _emit_ai_call(
                    stage="generation_lc_enriched" if lc_context else "generation_pure",
                    model=result.model,
                    latency_ms=result.latency_ms,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                )

            provisional_map = generate_provisional_map_from_sketch(
                concept=decision["name"],
                sketch=decision["sketch"],
                lc_context=lc_context,
                api_key=req.api_key,
                on_call_complete=_on_sketch_call,
            )
            return {"provisional_map": provisional_map.model_dump()}
        else:  # decision["path"] == "extract"
            # Preserve existing source-intake behavior byte-for-byte.
            # source_intake.from_text normalizes the raw text before the AI call.
            try:
                src = source_intake.from_text(decision["text"])
            except ParseEmpty:
                raise HTTPException(
                    status_code=422,
                    detail="Couldn't find enough readable text in what you pasted.",
                )

            def _on_extract_call(result):
                _emit_ai_call(
                    stage="generation_extract",
                    model=result.model,
                    latency_ms=result.latency_ms,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                )

            provisional_map = extract_knowledge_map(
                src.text,
                api_key=req.api_key,
                on_call_complete=_on_extract_call,
            )
            # Wire-shape preserved: frontend consumes a dict at "knowledge_map".
            return {"knowledge_map": provisional_map.model_dump()}

    # All LLM-error branches: stable user-facing copy ONLY. Provider details
    # (model name, error code, original message) flow into operator logs but
    # never into the response body. This is consistent across the whole LLM
    # error hierarchy — the user is never told which provider we use.
    except HTTPException:
        raise
    except LLMMissingKeyError as err:
        logger.warning("extract: LLMMissingKeyError: %s", err)
        raise HTTPException(
            status_code=401,
            detail="No API key configured. Add one in Settings to continue.",
        )
    except LLMRateLimitError as err:
        logger.warning("extract: LLMRateLimitError: %s", err)
        raise HTTPException(
            status_code=429,
            detail="The AI service is rate-limiting requests. Try again in a minute.",
        )
    except LLMValidationError as err:
        # raw_text preserved internally on the exception object for fixture
        # refresh / debugging; never serialized to the response.
        logger.warning("extract: LLMValidationError: %s", err)
        raise HTTPException(
            status_code=502,
            detail="Extraction returned malformed structure. Please retry.",
        )
    except LLMServiceError as err:
        logger.warning("extract: LLMServiceError: %s", err)
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable. Please try again shortly.",
        )
    except LLMClientError as err:
        # Operator-misconfiguration (expired key, unknown model, etc.).
        # Same UX as a transient outage from the learner's perspective.
        logger.warning("extract: LLMClientError: %s", err)
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable. Please try again shortly.",
        )
    except ValueError as err:
        # Pydantic structural-validation errors raised by ProvisionalMap
        # (closure rules, identifier grammar). The message here is OUR
        # internal validator output, not provider-debug, so it is safe
        # AND informative to surface.
        logger.warning("extract: structural validation failed: %s", err)
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract")
        raise HTTPException(
            status_code=500, detail="Unexpected server error during extraction."
        ) from err


class FeedbackRequest(BaseModel):
    message: str = Field(..., min_length=10, max_length=1000)


def _is_feedback_storage_unavailable(err: Exception) -> bool:
    err_msg = str(err)
    normalized = err_msg.lower()
    return (
        "PGRST205" in err_msg
        or ("feedback" in normalized and "not found" in normalized)
        or "permission denied for table users" in normalized
        or "permission denied for table feedback" in normalized
        or "'code': '42501'" in err_msg
        or '"code":"42501"' in err_msg
        or '"code": "42501"' in err_msg
    )


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    """Securely capture user feedback and store in Supabase."""
    session = load_current_session_state(request)
    user_id = session.user.id if (session.authenticated and session.user) else None

    supabase_url = os.environ.get("SUPABASE_URL", "")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")

    try:
        client = build_supabase_client(supabase_url, publishable_key)
        client.table("feedback").insert(
            {"message": req.message, "user_id": user_id, "status": "pending"},
            returning="minimal",
        ).execute()
    except Exception as err:
        if _is_feedback_storage_unavailable(err):
            logger.warning("Feedback storage unavailable: %s", err)
            raise HTTPException(
                status_code=503,
                detail="Feedback storage is currently unavailable. Please try again later.",
            )

        logger.exception("Unexpected failure in /api/feedback")
        raise HTTPException(
            status_code=500, detail="Unexpected error while saving feedback."
        ) from err

    return {"status": "ok"}


@app.post("/api/extract-url")
def extract_url(req: UrlExtractRequest):
    try:
        src = source_intake.from_url(req.url)
    except SourceIntakeError as exc:
        logger.info("intake_failed", extra={
            "exc_type": type(exc).__name__,
            "reason": getattr(exc, "reason", None),
            "cause": getattr(exc, "cause", None),
            "url_summary": _summarize_url_for_log(req.url),
        })
        raise _map_intake_error(exc) from exc
    except Exception as exc:
        logger.exception("intake_unexpected", extra={"url_summary": _summarize_url_for_log(req.url)})
        raise HTTPException(500, "Unexpected error while importing.") from exc
    return src.to_dict()


@app.post("/api/drill")
def drill(req: DrillRequest):
    if not req.node_id.strip():
        raise HTTPException(status_code=400, detail="No node_id provided.")
    if req.session_phase == "turn" and not req.messages:
        raise HTTPException(status_code=400, detail="No drill messages provided.")
    messages_in = [msg.model_dump() for msg in req.messages]
    try:
        knowledge_map = req.knowledge_map
        if isinstance(knowledge_map, str):
            knowledge_map = json.loads(knowledge_map)

        node_mechanism = _resolve_node_mechanism(
            knowledge_map,
            req.node_id,
            fallback="",
        )
        result = drill_chat(
            knowledge_map=knowledge_map,
            concept_id=req.concept_id,
            node_id=req.node_id,
            node_label=req.node_label,
            node_mechanism=node_mechanism,
            messages=messages_in,
            session_phase=req.session_phase,
            drill_mode=req.drill_mode,
            re_drill_count=req.re_drill_count,
            probe_count=req.probe_count,
            nodes_drilled=req.nodes_drilled,
            attempt_turn_count=req.attempt_turn_count,
            help_turn_count=req.help_turn_count,
            session_start_iso=req.session_start_iso,
            bypass_session_limits=req.bypass_session_limits,
            api_key=req.api_key,
            telemetry_context={
                "drill_session_id": req.drill_session_id,
                "client_turn_index": req.client_turn_index,
            },
        )
        response_payload = {"concept_id": req.concept_id, **result}
        return response_payload
    except MissingAPIKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except GeminiRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except GeminiServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid knowledge_map JSON.")
    except ValueError as err:
        logger.exception(
            "Drill normalization failed for concept_id=%s node_id=%s",
            req.concept_id,
            req.node_id,
        )
        raise HTTPException(
            status_code=502, detail="Drill evaluation failed. Please retry."
        ) from err
    except Exception as err:
        logger.exception(
            "Unexpected failure in /api/drill for concept_id=%s node_id=%s",
            req.concept_id,
            req.node_id,
        )
        raise HTTPException(
            status_code=500, detail="Unexpected server error during drill."
        ) from err


@app.post("/api/repair-reps")
def repair_reps(req: RepairRepsRequest):
    if not req.node_id.strip():
        raise HTTPException(status_code=400, detail="No node_id provided.")

    try:
        knowledge_map = req.knowledge_map
        if isinstance(knowledge_map, str):
            knowledge_map = json.loads(knowledge_map)

        node_mechanism = _resolve_node_mechanism(
            knowledge_map,
            req.node_id,
            fallback="",
        )
        result = generate_repair_reps(
            knowledge_map=knowledge_map,
            concept_id=req.concept_id,
            node_id=req.node_id,
            node_label=req.node_label,
            node_mechanism=node_mechanism,
            gap_type=req.gap_type,
            gap_description=req.gap_description,
            count=req.count,
            api_key=req.api_key,
        )
        return {"concept_id": req.concept_id, **result}
    except MissingAPIKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except GeminiRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except GeminiServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=400, detail="Invalid knowledge_map JSON."
        ) from err
    except ValueError as err:
        reason = str(err)
        if (
            reason.startswith("Unknown node_id:")
            or reason.startswith("Repair Reps MVP requires")
            or reason.startswith("knowledge_map")
        ):
            raise HTTPException(status_code=400, detail=reason) from err
        logger.exception(
            "Repair reps generation failed for concept_id=%s node_id=%s",
            req.concept_id,
            req.node_id,
        )
        raise HTTPException(
            status_code=502, detail="Repair Reps generation failed. Please retry."
        ) from err
    except Exception as err:
        logger.exception(
            "Unexpected failure in /api/repair-reps for concept_id=%s node_id=%s",
            req.concept_id,
            req.node_id,
        )
        raise HTTPException(
            status_code=500, detail="Unexpected server error during Repair Reps."
        ) from err


app.include_router(auth_router)

# Admin Surface (dev-only). Must be included BEFORE the StaticFiles mount,
# or the catch-all "/" mount with html=True would shadow /admin/todo.
from admin import register_admin_router  # noqa: E402
register_admin_router(app)

# Serve the frontend locally. On Vercel, static files are served by the CDN.
_public_dir = Path(__file__).parent / "public"
if _public_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_public_dir), html=True), name="static")
