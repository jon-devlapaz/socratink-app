import ipaddress
import json
import logging
import os
import re
import socket
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from html import unescape

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.responses import Response

from ai_service import (
    GeminiRateLimitError,
    GeminiServiceError,
    MissingAPIKeyError,
    drill_chat,
    extract_knowledge_map,
)
from scripts.summarize_ai_runs import build_summary_payload
from scripts.summarize_ai_runs import build_learner_summary_payload

load_dotenv()

app = FastAPI()
logger = logging.getLogger(__name__)

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
    knowledge_map: dict | str
    messages: list[DrillMessage] = Field(..., max_length=100)
    session_phase: str = Field(..., max_length=20)
    probe_count: int = Field(0, ge=0, le=100)
    nodes_drilled: int = Field(0, ge=0, le=100)
    attempt_turn_count: int = Field(0, ge=0, le=100)
    help_turn_count: int = Field(0, ge=0, le=100)
    session_start_iso: str | None = Field(None, max_length=100)
    api_key: str | None = Field(None, max_length=200)


def _resolve_node_mechanism(knowledge_map: dict, node_id: str, fallback: str = "") -> str:
    if not isinstance(knowledge_map, dict):
        return fallback

    metadata = knowledge_map.get("metadata") or {}
    if node_id == "core-thesis":
        return str(
            metadata.get("core_thesis")
            or metadata.get("thesis")
            or fallback
        )

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
    }


@app.get("/api/analytics/ai-runs")
def analytics_ai_runs():
    try:
        return build_summary_payload()
    except Exception as err:
        logger.exception("Failed to build AI runs analytics payload")
        raise HTTPException(status_code=500, detail="Could not build AI runs analytics.") from err


@app.get("/api/analytics/learner-runs")
def analytics_learner_runs(concept_ids: str | None = None):
    parsed_concept_ids: list[str] | None = None
    if concept_ids:
        parsed_concept_ids = [
            concept_id.strip()[:100]
            for concept_id in concept_ids.split(",")
            if concept_id.strip()
        ][:50]
    try:
        return build_learner_summary_payload(parsed_concept_ids)
    except Exception as err:
        logger.exception("Failed to build learner analytics payload")
        raise HTTPException(status_code=500, detail="Could not build learner analytics.") from err


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
        raise HTTPException(status_code=500, detail="Unexpected server error during extraction.") from err


def _extract_text_from_html(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript|svg|iframe).*?>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6|tr)>", "\n", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def _extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if "youtu.be" in host:
        return path_parts[0] if path_parts else None

    if "youtube.com" in host or "youtube-nocookie.com" in host:
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            return query["v"][0]

        if len(path_parts) >= 2 and path_parts[0] in {"live", "shorts", "embed", "v"}:
            return path_parts[1]

        if len(path_parts) >= 2 and path_parts[0] == "watch":
            return path_parts[1]

    return None


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


@app.post("/api/extract-url")
def extract_url(req: UrlExtractRequest):
    url = req.url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Enter a valid http(s) URL.")
    if _is_private_url(url):
        raise HTTPException(status_code=400, detail="Cannot fetch internal addresses.")

    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; socratink/1.0; +https://localhost)"
            },
        )
        with urlopen(request, timeout=12) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise HTTPException(
                    status_code=415,
                    detail="That URL did not return an HTML or plain text page.",
                )

            raw_bytes = response.read(2_000_000 + 1)
            if len(raw_bytes) > 2_000_000:
                raise HTTPException(status_code=413, detail="Page is too large to import.")

            charset = response.headers.get_content_charset() or "utf-8"
            raw_text = raw_bytes.decode(charset, errors="replace")
    except HTTPException:
        raise
    except HTTPError as err:
        raise HTTPException(status_code=502, detail=f"Source page returned HTTP {err.code}.")
    except URLError:
        raise HTTPException(status_code=502, detail="Could not fetch that URL.")
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract-url for %s", url)
        raise HTTPException(status_code=500, detail="Unexpected error while fetching that URL.") from err

    if "text/plain" in content_type:
        text = raw_text.strip()
        title = parsed.netloc
    else:
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_text)
        title = unescape(title_match.group(1)).strip() if title_match else parsed.netloc
        text = _extract_text_from_html(raw_text)

    if len(text) < 200:
        raise HTTPException(status_code=422, detail="Could not extract enough readable text from that page.")

    return {"url": url, "title": title[:200], "text": text[:500_000]}


@app.post("/api/extract-youtube")
def extract_youtube(req: UrlExtractRequest):
    url = req.url.strip()
    video_id = _extract_youtube_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Enter a valid YouTube video URL.")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            IpBlocked,
            NoTranscriptFound,
            RequestBlocked,
            TranscriptsDisabled,
            VideoUnavailable,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="YouTube transcript support is not installed on the server.")

    try:
        transcript_list = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(segment.text for segment in transcript_list).strip()
    except (RequestBlocked, IpBlocked) as err:
        logger.exception("YouTube transcript fetch blocked for video_id=%s", video_id)
        raise HTTPException(
            status_code=503,
            detail="YouTube blocked transcript retrieval from the hosted server. Paste the transcript text manually instead.",
        ) from err
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as err:
        logger.exception("YouTube transcript unavailable for video_id=%s", video_id)
        raise HTTPException(
            status_code=422,
            detail="This video does not have a retrievable public transcript. Paste the transcript text manually instead.",
        ) from err
    except Exception as err:
        logger.exception("YouTube transcript fetch failed for video_id=%s", video_id)
        raise HTTPException(status_code=502, detail="Could not fetch YouTube transcript.") from err

    if len(text) < 100:
        raise HTTPException(status_code=422, detail="Transcript was too short or unavailable.")

    return {
        "url": url,
        "title": f"YouTube Transcript {video_id}",
        "text": text[:500_000],
        "video_id": video_id,
    }


@app.post("/api/drill")
def drill(req: DrillRequest):
    if not req.node_id.strip():
        raise HTTPException(status_code=400, detail="No node_id provided.")
    if req.session_phase == "turn" and not req.messages:
        raise HTTPException(status_code=400, detail="No drill messages provided.")
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
            messages=[msg.model_dump() for msg in req.messages],
            session_phase=req.session_phase,
            probe_count=req.probe_count,
            nodes_drilled=req.nodes_drilled,
            attempt_turn_count=req.attempt_turn_count,
            help_turn_count=req.help_turn_count,
            session_start_iso=req.session_start_iso,
            api_key=req.api_key,
        )
        return {"concept_id": req.concept_id, **result}
    except MissingAPIKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except GeminiRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except GeminiServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid knowledge_map JSON.")
    except ValueError as err:
        logger.exception("Drill normalization failed for concept_id=%s node_id=%s", req.concept_id, req.node_id)
        raise HTTPException(status_code=502, detail="Drill evaluation failed. Please retry.") from err
    except Exception as err:
        logger.exception("Unexpected failure in /api/drill for concept_id=%s node_id=%s", req.concept_id, req.node_id)
        raise HTTPException(status_code=500, detail="Unexpected server error during drill.") from err


# Serve the frontend locally. On Vercel, static files are served by the CDN.
_public_dir = Path(__file__).parent / "public"
if _public_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_public_dir), html=True), name="static")
