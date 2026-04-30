import ipaddress
import json
import logging
import os
import re
import socket
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest, urlopen

from html import unescape

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
    generate_repair_reps,
    get_drill_session_time_limit_seconds,
)
from runtime_env import load_app_env

load_app_env()

app = FastAPI()
app.state.auth_service = build_auth_service_from_env()
logger = logging.getLogger(__name__)
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
        return RedirectResponse(
            url=f"/login?return_to={quote(_request_return_to(request), safe='')}",
            status_code=302,
        )

    response = await call_next(request)
    _apply_writeback(request, response, state)
    return response


class ExtractRequest(BaseModel):
    text: str = Field(..., max_length=500_000)
    api_key: str | None = Field(None, max_length=200)


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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "server_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "drill_session_time_limit_seconds": get_drill_session_time_limit_seconds(),
    }


@app.post("/api/extract")
def extract(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        knowledge_map = extract_knowledge_map(req.text, api_key=req.api_key)
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


def _extract_text_from_html(raw_html: str) -> str:
    cleaned = re.sub(
        r"(?is)<(script|style|noscript|svg|iframe).*?>.*?</\1>", " ", raw_html
    )
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(
        r"(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6|tr)>", "\n", cleaned
    )
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def _is_blocked_video_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )


def _is_private_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True

    try:
        direct_ip = ipaddress.ip_address(hostname)
        resolved_addresses = [direct_ip]
    except ValueError:
        try:
            addr_info = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror:
            return True
        resolved_addresses = []
        for _, _, _, _, sockaddr in addr_info:
            try:
                resolved_addresses.append(ipaddress.ip_address(sockaddr[0]))
            except ValueError:
                return True

    if not resolved_addresses:
        return True

    return any(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
        for addr in resolved_addresses
    )


class FeedbackRequest(BaseModel):
    message: str = Field(..., min_length=10, max_length=1000)


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    """Securely capture user feedback and store in Supabase."""
    session = load_current_session_state(request)
    user_id = session.user.id if (session.authenticated and session.user) else None

    supabase_url = os.environ.get("SUPABASE_URL")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

    try:
        client = build_supabase_client(supabase_url, publishable_key)
        client.table("feedback").insert(
            {"message": req.message, "user_id": user_id, "status": "pending"}
        ).execute()
    except Exception as err:
        err_msg = str(err)
        if "PGRST205" in err_msg or "feedback" in err_msg and "not found" in err_msg.lower():
            logger.warning("Feedback table not found in Supabase. Submission failed gracefully.")
            raise HTTPException(
                status_code=503, 
                detail="Feedback system is currently being set up. Please try again later."
            )

        logger.exception("Unexpected failure in /api/feedback")
        raise HTTPException(
            status_code=500, detail="Unexpected error while saving feedback."
        ) from err

    return {"status": "ok"}


@app.post("/api/extract-url")
def extract_url(req: UrlExtractRequest):
    url = req.url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Enter a valid http(s) URL.")
    if _is_blocked_video_url(url):
        raise HTTPException(
            status_code=400,
            detail="Video links are not supported in this deployment. Paste the text directly instead.",
        )
    if _is_private_url(url):
        raise HTTPException(status_code=400, detail="Cannot fetch internal addresses.")

    try:
        request = UrlRequest(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; socratink/1.0; +https://localhost)"
            },
        )
        # SECURITY: redirects are followed by default; private targets reachable via 30x. See audit-pass-1.
        with urlopen(request, timeout=12) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise HTTPException(
                    status_code=415,
                    detail="That URL did not return an HTML or plain text page.",
                )

            raw_bytes = response.read(2_000_000 + 1)
            if len(raw_bytes) > 2_000_000:
                raise HTTPException(
                    status_code=413, detail="Page is too large to import."
                )

            charset = response.headers.get_content_charset() or "utf-8"
            raw_text = raw_bytes.decode(charset, errors="replace")
    except HTTPException:
        raise
    except HTTPError as err:
        raise HTTPException(
            status_code=502, detail=f"Source page returned HTTP {err.code}."
        )
    except URLError:
        raise HTTPException(status_code=502, detail="Could not fetch that URL.")
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract-url for %s", url)
        raise HTTPException(
            status_code=500, detail="Unexpected error while fetching that URL."
        ) from err

    if "text/plain" in content_type:
        text = raw_text.strip()
        title = parsed.netloc
    else:
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_text)
        title = unescape(title_match.group(1)).strip() if title_match else parsed.netloc
        text = _extract_text_from_html(raw_text)

    if len(text) < 200:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough readable text from that page.",
        )

    return {"url": url, "title": title[:200], "text": text[:500_000]}


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
