// ai_service.js
// Calls the local Python backend for AI extraction.

export async function generateKnowledgeMap(rawText, onProgress) {
  if (onProgress) onProgress("Drafting map...");
  const apiKey = localStorage.getItem("gemini_key") || undefined;
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: rawText, api_key: apiKey }),
  });
  if (!response.ok) {
    const err = await response.text().catch(() => "");
    throw new Error(`Server error ${response.status}: ${err}`);
  }
  const data = await response.json();
  return data.knowledge_map;
}

/**
 * Conversational concept-create submit. Posts the spec §5.3 payload shape
 * and returns the parsed `provisional_map` (no source) or `knowledge_map`
 * (source attached).
 *
 * On any non-OK JSON response, throws an Error with `.status` and `.body`
 * (the parsed `{error, message}` payload) so the caller can render
 * `err.body.message` inline. This covers both the 422 bypass-rejected case
 * and the 500 `smallest_route_cap_exceeded` case emitted by the source-less
 * branch when the smallest-route generator returns more than the drillable
 * node cap. Non-JSON error bodies fall back to a generic
 * `Server error <status>: <text>` message with `.status` set.
 *
 * @param {{ name: string, startingSketch: string,
 *           source: null | { type: 'text'|'url'|'file', text?: string, url?: string, filename?: string },
 *           apiKey?: string }} args
 * @returns {Promise<{ provisional_map?: object, knowledge_map?: object }>}
 */
export async function submitConceptCreate({ name, startingSketch, source, apiKey }) {
  const body = {
    name,
    starting_sketch: startingSketch,
    source,
    api_key: apiKey,
  };
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (response.status === 422) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || payload || {};
    const err = new Error(detail.message || "Submission rejected.");
    err.status = 422;
    err.body = detail;
    throw err;
  }
  if (!response.ok) {
    // Try to parse a JSON `{detail: {error, message}}` body so callers can
    // surface actionable server messages (e.g. smallest_route_cap_exceeded)
    // rather than generic retry copy. Falls back to text on parse failure.
    const ct = response.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const payload = await response.json().catch(() => ({}));
      // FastAPI's HTTPException(detail="…") yields a string; HTTPException(detail={...})
      // yields a dict. Normalize so callers always get (msg: string, body: object).
      const rawDetail = payload.detail !== undefined ? payload.detail : payload;
      const isStringDetail = typeof rawDetail === "string";
      const msg = isStringDetail
        ? rawDetail
        : (rawDetail && rawDetail.message) || `Server error ${response.status}`;
      const body = isStringDetail ? {} : (rawDetail || {});
      const err = new Error(msg);
      err.status = response.status;
      err.body = body;
      throw err;
    }
    const txt = await response.text().catch(() => "");
    const err = new Error(`Server error ${response.status}: ${txt}`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}
