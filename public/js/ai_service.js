/**
 * Conversational concept-create submit. Posts the `/api/extract` payload
 * `{name, learner_goal?, starting_sketch, source}` and returns the
 * parsed `provisional_map` (no source) or `knowledge_map` (source attached).
 *
 * On any non-OK JSON response, throws an Error with `.status` and `.body`
 * (the parsed `{error, message}` payload) so the caller can render
 * `err.body.message` inline. This covers both the 422 bypass-rejected case
 * and the 500 `smallest_route_cap_exceeded` case emitted by the source-less
 * branch when the smallest-route generator violates the cap, cluster-shape,
 * or learner-scaffold contract. Non-JSON error bodies fall back to a generic
 * `Server error <status>: <text>` message with `.status` set.
 *
 * @param {{ name: string, learnerGoal?: string, startingSketch: string,
 *           routeOwner?: 'extract'|'seda',
 *           source: null | { type: 'text'|'url'|'file', text?: string, url?: string, filename?: string } }} args
 * @returns {Promise<{ provisional_map?: object, knowledge_map?: object }>}
 */
export async function submitConceptCreate({ name, learnerGoal, startingSketch, source, routeOwner }) {
  const body = {
    name,
    learner_goal: learnerGoal || undefined,
    starting_sketch: startingSketch,
    source,
    route_owner: routeOwner || undefined,
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

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(async () => ({
      message: await response.text().catch(() => ''),
    }));
    const error = new Error(
      payload?.message || payload?.error || `Server error ${response.status}`,
    );
    error.status = response.status;
    error.code = payload?.code || payload?.error || null;
    error.body = payload || {};
    throw error;
  }
  return response.json();
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function createSedaSession({ sourceLessDoorBootstrap = false } = {}) {
  return postJson("/api/session", sourceLessDoorBootstrap === true
    ? { sourceLessDoorBootstrap: true }
    : {});
}

export async function getSedaSession(sessionId) {
  const response = await fetch(`/api/session/${encodeURIComponent(sessionId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const payload = await response.json().catch(async () => ({
      message: await response.text().catch(() => ''),
    }));
    const error = new Error(
      payload?.message || payload?.error || `Server error ${response.status}`,
    );
    error.status = response.status;
    error.code = payload?.code || payload?.error || null;
    error.body = payload || {};
    throw error;
  }
  return response.json();
}

function assertSessionVersion(value) {
  if (!Number.isInteger(value) || value < 0) {
    throw new Error('A nonnegative SEDA expectedVersion is required.');
  }
  return value;
}

export function createSedaTurnSubmission(text, expectedVersion, requestId = null) {
  const generated = globalThis.crypto?.randomUUID?.();
  const stableRequestId = String(requestId || generated || '').trim();
  if (!UUID_RE.test(stableRequestId)) throw new Error('A SEDA turn requestId UUID is required.');
  return {
    text: String(text ?? ''),
    requestId: stableRequestId,
    expectedVersion: assertSessionVersion(expectedVersion),
  };
}

export function sendSedaTurn(sessionId, submission) {
  const turn = submission;
  if (!turn || typeof turn !== 'object') {
    throw new Error('A SEDA turn submission is required.');
  }
  const requestId = String(turn.requestId || '').trim();
  if (!UUID_RE.test(requestId)) throw new Error('A SEDA turn requestId UUID is required.');
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/turn`, {
    text: String(turn.text ?? ''),
    requestId,
    expectedVersion: assertSessionVersion(turn.expectedVersion),
  });
}
