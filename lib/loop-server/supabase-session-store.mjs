import {
  assertSessionId,
  buildSessionCommit,
  normalizeReceipts,
  replayForRequest,
  SessionStoreError,
} from "./session-store.mjs";

const DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30;
const MAX_RECENT_SESSIONS = 50;

export function createSupabaseSessionStore({
  supabaseUrl = process.env.SUPABASE_URL,
  publishableKey = process.env.SUPABASE_PUBLISHABLE_KEY,
  accessToken,
  fetchImpl = globalThis.fetch,
  now = () => new Date().toISOString(),
  sessionTtlSeconds = Number(
    process.env.SOCRATINK_LOOP_SESSION_TTL_SECONDS || DEFAULT_SESSION_TTL_SECONDS,
  ),
} = {}) {
  const baseUrl = String(supabaseUrl || "").trim().replace(/\/+$/, "");
  const apiKey = String(publishableKey || "").trim();
  const userToken = String(accessToken || "").trim();
  if (!baseUrl || !apiKey) {
    throw new SessionStoreError(
      "StoreConfigurationError",
      "durable loop storage requires Supabase URL and publishable key",
    );
  }
  if (!userToken) {
    throw new SessionStoreError(
      "StoreAuthenticationRequired",
      "durable loop storage requires an authenticated user token",
    );
  }
  if (isServiceRoleKey(apiKey)) {
    throw new SessionStoreError(
      "StoreConfigurationError",
      "loop storage must use a Supabase publishable key",
    );
  }
  if (typeof fetchImpl !== "function") {
    throw new SessionStoreError(
      "StoreConfigurationError",
      "durable loop storage requires fetch",
    );
  }
  const ttlSeconds = boundedTtl(sessionTtlSeconds);
  const tableUrl = `${baseUrl}/rest/v1/loop_sessions`;

  async function request(path = "", options = {}) {
    let response;
    try {
      response = await fetchImpl(`${tableUrl}${path}`, {
        ...options,
        signal: options.signal || AbortSignal.timeout(10_000),
        headers: {
          apikey: apiKey,
          authorization: `Bearer ${userToken}`,
          "content-type": "application/json",
          ...(options.headers || {}),
        },
      });
    } catch (error) {
      throw new SessionStoreError(
        "StoreUnavailable",
        "durable loop storage is unavailable",
      );
    }

    let text;
    try {
      text = await response.text();
    } catch {
      throw new SessionStoreError(
        "StoreUnavailable",
        "durable loop storage response failed",
      );
    }
    const body = text ? safeJson(text) : null;
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new SessionStoreError(
          "StoreAuthenticationRequired",
          "durable loop storage rejected the user session",
        );
      }
      if (response.status === 409) {
        throw new SessionStoreError("SessionConflict", "session version changed");
      }
      throw new SessionStoreError(
        "StoreUnavailable",
        "durable loop storage request failed",
      );
    }
    return body;
  }

  async function create(sessionId, metadata = {}) {
    assertSessionId(sessionId);
    const createdAt = now();
    const rows = await request("", {
      method: "POST",
      headers: { prefer: "return=representation" },
      body: JSON.stringify({
        session_id: sessionId,
        metadata: initialMetadata(sessionId, metadata, createdAt),
        events: [],
        version: 0,
        turn_receipts: [],
        expires_at: expiresAt(createdAt, ttlSeconds),
      }),
    });
    return normalizeSingleRow(rows, sessionId);
  }

  async function load(sessionId) {
    assertSessionId(sessionId);
    const query = new URLSearchParams({
      select:
        "session_id,metadata,events,version,turn_receipts,expires_at",
      session_id: `eq.${sessionId}`,
      limit: "1",
    });
    const rows = await request(`?${query}`);
    const stored = normalizeSingleRow(rows, sessionId, { missingOk: true });
    if (!stored || Date.parse(stored.expiresAt) <= Date.parse(now())) {
      throw new SessionStoreError("SessionNotFound", "session not found");
    }
    return stored;
  }

  async function listRecent({ limit = 12 } = {}) {
    const boundedLimit = Math.max(0, Math.min(MAX_RECENT_SESSIONS, Number(limit) || 0));
    if (!boundedLimit) return [];
    const query = new URLSearchParams({
      select:
        "session_id,metadata,events,version,turn_receipts,expires_at",
      expires_at: `gt.${now()}`,
      order: "updated_at.desc",
      limit: String(boundedLimit),
    });
    const rows = await request(`?${query}`);
    return Array.isArray(rows) ? rows.map(normalizeRow) : [];
  }

  async function clearReports() {
    const rows = await request("?session_id=not.is.null", {
      method: "DELETE",
      headers: { prefer: "return=representation" },
    });
    return { deleted_count: Array.isArray(rows) ? rows.length : 0 };
  }

  async function appendEvents(sessionId, events, metadata = {}, commit = {}) {
    if (commit.expectedVersion == null) {
      throw new SessionStoreError(
        "InvalidExpectedVersion",
        "durable session writes require an expected version",
      );
    }
    const stored = await load(sessionId);
    const mutation = buildSessionCommit({
      stored,
      addedEvents: events,
      metadata,
      ...commit,
      updatedAt: now(),
    });
    if (mutation.replayedResponse) {
      return { ...stored, replayedResponse: mutation.replayedResponse };
    }

    const rows = await casPatch(sessionId, commit.expectedVersion, {
      metadata: mutation.metadata,
      events: mutation.events,
      version: mutation.version,
      turn_receipts: mutation.receipts,
      updated_at: mutation.metadata.updated_at,
      expires_at: expiresAt(mutation.metadata.updated_at, ttlSeconds),
    });
    if (Array.isArray(rows) && rows.length) return normalizeRow(rows[0]);

    const winner = await load(sessionId);
    const replayedResponse = replayForRequest(
      winner,
      commit.requestId,
      commit.requestHash,
    );
    if (replayedResponse) return { ...winner, replayedResponse };
    throw new SessionStoreError("SessionConflict", "session version changed");
  }

  async function updateMetadata(sessionId, partial, { expectedVersion } = {}) {
    if (expectedVersion == null) {
      throw new SessionStoreError(
        "InvalidExpectedVersion",
        "durable session writes require an expected version",
      );
    }
    const stored = await load(sessionId);
    if (Number(stored.version) !== Number(expectedVersion)) {
      throw new SessionStoreError("SessionConflict", "session version changed");
    }
    const updatedAt = now();
    const version = stored.version + 1;
    const rows = await casPatch(sessionId, expectedVersion, {
      metadata: {
        ...stored.metadata,
        ...partial,
        session_id: sessionId,
        version,
        updated_at: updatedAt,
      },
      version,
      updated_at: updatedAt,
      expires_at: expiresAt(updatedAt, ttlSeconds),
    });
    if (!Array.isArray(rows) || !rows.length) {
      throw new SessionStoreError("SessionConflict", "session version changed");
    }
    return normalizeRow(rows[0]);
  }

  async function casPatch(sessionId, expectedVersion, values) {
    const query = new URLSearchParams({
      session_id: `eq.${sessionId}`,
      version: `eq.${expectedVersion}`,
    });
    return request(`?${query}`, {
      method: "PATCH",
      headers: { prefer: "return=representation" },
      body: JSON.stringify(values),
    });
  }

  return {
    rootDir: null,
    create,
    load,
    listRecent,
    clearReports,
    appendEvents,
    updateMetadata,
    assertSessionId,
  };
}

function initialMetadata(sessionId, metadata, createdAt) {
  return {
    session_id: sessionId,
    created_at: createdAt,
    updated_at: createdAt,
    event_count: 0,
    version: 0,
    status: metadata.status || "active",
    phase: metadata.phase || "idle",
    awaiting: metadata.awaiting || null,
    transcript_tail: [],
    complete: Boolean(metadata.complete),
    case_complete: Boolean(metadata.caseComplete),
    llm: metadata.llm || null,
    bridge_diagnostics_dir: null,
    source_less_door_bootstrap: metadata.sourceLessDoorBootstrap === true,
  };
}

function normalizeSingleRow(rows, sessionId, { missingOk = false } = {}) {
  if (!Array.isArray(rows) || !rows.length) {
    if (missingOk) return null;
    throw new SessionStoreError("SessionNotFound", "session not found");
  }
  return normalizeRow(rows[0], sessionId);
}

function normalizeRow(row, expectedSessionId = null) {
  const sessionId = String(row?.session_id || "");
  assertSessionId(sessionId);
  if (expectedSessionId && sessionId !== expectedSessionId) {
    throw new SessionStoreError("StoreUnavailable", "durable loop storage returned bad data");
  }
  if (!row.metadata || !Array.isArray(row.events)) {
    throw new SessionStoreError("StoreUnavailable", "durable loop storage returned bad data");
  }
  const version = Number(row.version || 0);
  return {
    sessionId,
    metadata: { ...row.metadata, version },
    events: row.events,
    version,
    receipts: normalizeReceipts(row.turn_receipts || []),
    expiresAt: row.expires_at || "",
  };
}

function boundedTtl(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return DEFAULT_SESSION_TTL_SECONDS;
  return Math.max(60 * 60, Math.min(60 * 60 * 24 * 365, Math.floor(seconds)));
}

function expiresAt(timestamp, ttlSeconds) {
  return new Date(Date.parse(timestamp) + ttlSeconds * 1000).toISOString();
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    throw new SessionStoreError(
      "StoreUnavailable",
      "durable loop storage returned an invalid response",
    );
  }
}

function isServiceRoleKey(key) {
  if (key.startsWith("sb_secret_")) return true;
  const parts = key.split(".");
  if (parts.length !== 3) return false;
  try {
    const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
    return payload?.role === "service_role";
  } catch {
    return false;
  }
}
