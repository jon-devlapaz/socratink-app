import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const SESSION_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const SESSION_STORE_LIMITS = Object.freeze({
  events: 128,
  eventBytes: 512 * 1024,
  transcriptEntries: 80,
  transcriptBytes: 128 * 1024,
  metadataBytes: 256 * 1024,
  replayResponseBytes: 768 * 1024,
  receiptEntries: 16,
  receiptBytes: 2_000_000,
});

export class SessionStoreError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "SessionStoreError";
    this.code = code;
  }
}

export function defaultSessionStoreRoot(env = process.env) {
  return (
    env.SOCRATINK_LOOP_SESSION_STORE_DIR ||
    path.join(os.tmpdir(), "socratink-loop-sessions")
  );
}

export function durableSessionStoreRequired(env = process.env) {
  return Boolean(
    env.VERCEL
    || env.VERCEL_ENV
    || String(env.NODE_ENV || "").toLowerCase() === "production"
    || String(env.SOCRATINK_LOOP_SESSION_STORE || "").toLowerCase() === "supabase"
  );
}

export function assertSessionId(sessionId) {
  if (!SESSION_ID_PATTERN.test(String(sessionId || ""))) {
    throw new SessionStoreError("InvalidSessionId", "invalid session id");
  }
}

export function assertRequestId(requestId) {
  if (requestId == null || requestId === "") return null;
  if (!SESSION_ID_PATTERN.test(String(requestId))) {
    throw new SessionStoreError("InvalidRequestId", "requestId must be a UUID");
  }
  return String(requestId).toLowerCase();
}

export function replayForRequest(stored, requestId, requestHash) {
  const normalizedRequestId = assertRequestId(requestId);
  if (!normalizedRequestId) return null;
  const receipts = normalizeReceipts(stored.receipts || []);
  const receipt = [...receipts]
    .reverse()
    .find((candidate) => candidate.request_id === normalizedRequestId);
  if (!receipt) return null;
  if (!requestHash || receipt.request_hash !== requestHash) {
    throw new SessionStoreError(
      "IdempotencyConflict",
      "requestId was already used with a different turn payload",
    );
  }
  return receipt.response;
}

export function buildSessionCommit({
  stored,
  addedEvents,
  metadata = {},
  expectedVersion,
  requestId = null,
  requestHash = null,
  response = null,
  updatedAt,
}) {
  if (!Array.isArray(addedEvents)) {
    throw new SessionStoreError("InvalidEvents", "events must be an array");
  }
  const normalizedRequestId = assertRequestId(requestId);
  const replayedResponse = replayForRequest(stored, normalizedRequestId, requestHash);
  if (replayedResponse) return { replayedResponse };
  if (
    expectedVersion != null
    && Number(expectedVersion) !== Number(stored.version)
  ) {
    throw new SessionStoreError("SessionConflict", "session version changed");
  }

  if (
    normalizedRequestId
    && (typeof requestHash !== "string" || !requestHash || response == null)
  ) {
    throw new SessionStoreError(
      "InvalidRequestId",
      "requestId requires a payload hash and replay response",
    );
  }

  const events = [...stored.events, ...addedEvents];
  assertJsonArrayBounds(events, {
    maxEntries: SESSION_STORE_LIMITS.events,
    maxBytes: SESSION_STORE_LIMITS.eventBytes,
    code: "SessionEventsLimitExceeded",
  });
  if (response != null) {
    assertJsonBytes(
      response,
      SESSION_STORE_LIMITS.replayResponseBytes,
      "SessionResponseLimitExceeded",
    );
  }
  const receipts = normalizedRequestId
    ? appendBoundedReceipt(stored.receipts || [], {
        request_id: normalizedRequestId,
        request_hash: requestHash,
        response,
      })
    : normalizeReceipts(stored.receipts || []);

  const transcriptTail = boundTranscript([
    ...(stored.metadata.transcript_tail || []),
    ...(Array.isArray(metadata.transcript) ? metadata.transcript : []),
  ]);
  const nextVersion = Number(stored.version) + 1;
  const nextMetadata = {
    ...stored.metadata,
    session_id: stored.sessionId,
    created_at: stored.metadata.created_at || updatedAt,
    updated_at: updatedAt,
    event_count: events.length,
    version: nextVersion,
    status: metadata.status || stored.metadata.status || "active",
    phase: metadata.phase ?? stored.metadata.phase ?? null,
    awaiting: metadata.awaiting ?? stored.metadata.awaiting ?? null,
    transcript_tail: transcriptTail,
    complete: Boolean(metadata.complete ?? stored.metadata.complete),
    case_complete: Boolean(metadata.caseComplete ?? stored.metadata.case_complete),
    llm: metadata.llm_active ?? stored.metadata.llm ?? null,
    bridge_diagnostics_dir:
      metadata.bridgeDiagnosticsDir
      ?? stored.metadata.bridge_diagnostics_dir
      ?? null,
  };
  assertJsonBytes(
    nextMetadata,
    SESSION_STORE_LIMITS.metadataBytes,
    "SessionMetadataLimitExceeded",
  );

  return {
    events,
    metadata: nextMetadata,
    version: nextVersion,
    receipts,
  };
}

export function normalizeReceipts(value) {
  if (!Array.isArray(value)) {
    throw new SessionStoreError(
      "StoreUnavailable",
      "session receipt history is invalid",
    );
  }
  const receipts = value.map((receipt) => {
    if (
      !receipt
      || typeof receipt !== "object"
      || typeof receipt.request_hash !== "string"
      || !receipt.request_hash
      || receipt.response == null
    ) {
      throw new SessionStoreError(
        "StoreUnavailable",
        "session receipt history is invalid",
      );
    }
    let requestId;
    try {
      requestId = assertRequestId(receipt.request_id);
    } catch {
      throw new SessionStoreError(
        "StoreUnavailable",
        "session receipt history is invalid",
      );
    }
    assertJsonBytes(
      receipt.response,
      SESSION_STORE_LIMITS.replayResponseBytes,
      "StoreUnavailable",
    );
    return {
      request_id: requestId,
      request_hash: receipt.request_hash,
      response: receipt.response,
    };
  });
  assertJsonArrayBounds(receipts, {
    maxEntries: SESSION_STORE_LIMITS.receiptEntries,
    maxBytes: SESSION_STORE_LIMITS.receiptBytes,
    code: "StoreUnavailable",
  });
  return receipts;
}

function appendBoundedReceipt(existing, receipt) {
  const receipts = [...normalizeReceipts(existing), receipt]
    .slice(-SESSION_STORE_LIMITS.receiptEntries);
  while (
    receipts.length > 1
    && jsonBytes(receipts) > SESSION_STORE_LIMITS.receiptBytes
  ) {
    receipts.shift();
  }
  assertJsonArrayBounds(receipts, {
    maxEntries: SESSION_STORE_LIMITS.receiptEntries,
    maxBytes: SESSION_STORE_LIMITS.receiptBytes,
    code: "SessionReceiptsLimitExceeded",
  });
  return receipts;
}

export function createFileSessionStore({
  rootDir = defaultSessionStoreRoot(),
  now = () => new Date().toISOString(),
} = {}) {
  const root = path.resolve(rootDir);
  const locks = new Map();

  function sessionDir(sessionId) {
    assertSessionId(sessionId);
    const resolved = path.resolve(root, sessionId);
    if (!resolved.startsWith(`${root}${path.sep}`)) {
      throw new SessionStoreError("InvalidSessionId", "invalid session path");
    }
    return resolved;
  }

  async function create(sessionId, metadata = {}) {
    return withSessionLock(sessionId, async () => {
      const dir = sessionDir(sessionId);
      await fs.mkdir(root, { recursive: true });
      try {
        await fs.mkdir(dir, { recursive: false });
      } catch (error) {
        if (error?.code === "EEXIST") {
          throw new SessionStoreError("SessionConflict", "session already exists");
        }
        throw error;
      }
      const createdAt = now();
      await writeJson(path.join(dir, "metadata.json"), {
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
        bridge_diagnostics_dir: metadata.bridgeDiagnosticsDir || null,
        source_less_door_bootstrap: metadata.sourceLessDoorBootstrap === true,
        source_revision: sourceRevisionMetadata(metadata.sourceRevision),
        turn_receipts: [],
      });
      await fs.writeFile(path.join(dir, "events.jsonl"), "", { flag: "wx" });
      return load(sessionId);
    });
  }

  async function load(sessionId) {
    const dir = sessionDir(sessionId);
    try {
      const [metadata, journal] = await Promise.all([
        readJson(path.join(dir, "metadata.json")),
        fs.readFile(path.join(dir, "events.jsonl"), "utf8"),
      ]);
      const events = journal
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => JSON.parse(line));
      const { turn_receipts: turnReceipts = [], ...sessionMetadata } = metadata;
      return {
        sessionId,
        metadata: sessionMetadata,
        events,
        version: Number(sessionMetadata.version || 0),
        receipts: normalizeReceipts(turnReceipts),
      };
    } catch (error) {
      if (error?.code === "ENOENT") {
        throw new SessionStoreError("SessionNotFound", "session not found");
      }
      throw error;
    }
  }

  async function listRecent({ limit = 12 } = {}) {
    let entries;
    try {
      entries = await fs.readdir(root, { withFileTypes: true });
    } catch (error) {
      if (error?.code === "ENOENT") return [];
      throw error;
    }

    const sessions = [];
    for (const entry of entries) {
      if (!entry.isDirectory() || !SESSION_ID_PATTERN.test(entry.name)) continue;
      try {
        sessions.push(await load(entry.name));
      } catch (error) {
        if (!(error instanceof SessionStoreError)) throw error;
      }
    }

    return sessions
      .sort((a, b) =>
        String(b.metadata.updated_at || "").localeCompare(
          String(a.metadata.updated_at || ""),
        ),
      )
      .slice(0, Math.max(0, limit));
  }

  async function clearReports() {
    let entries;
    try {
      entries = await fs.readdir(root, { withFileTypes: true });
    } catch (error) {
      if (error?.code === "ENOENT") return { deleted_count: 0 };
      throw error;
    }

    let deletedCount = 0;
    for (const entry of entries) {
      if (!entry.isDirectory() || !SESSION_ID_PATTERN.test(entry.name)) continue;
      await fs.rm(sessionDir(entry.name), { recursive: true, force: true });
      deletedCount += 1;
    }
    return { deleted_count: deletedCount };
  }

  async function appendEvents(sessionId, events, metadata = {}, commit = {}) {
    return withSessionLock(sessionId, async () => {
      const dir = sessionDir(sessionId);
      const existing = await load(sessionId);
      const mutation = buildSessionCommit({
        stored: existing,
        addedEvents: events,
        metadata,
        ...commit,
        updatedAt: now(),
      });
      if (mutation.replayedResponse) {
        return { ...existing, replayedResponse: mutation.replayedResponse };
      }
      if (events.length) {
        const lines = `${events.map((event) => JSON.stringify(event)).join("\n")}\n`;
        await fs.appendFile(path.join(dir, "events.jsonl"), lines, "utf8");
      }
      await writeJson(path.join(dir, "metadata.json"), {
        ...mutation.metadata,
        turn_receipts: mutation.receipts,
      });
      return load(sessionId);
    });
  }

  async function updateMetadata(sessionId, partial, { expectedVersion } = {}) {
    return withSessionLock(sessionId, async () => {
      const dir = sessionDir(sessionId);
      const existing = await load(sessionId);
      if (
        expectedVersion != null
        && Number(expectedVersion) !== Number(existing.version)
      ) {
        throw new SessionStoreError("SessionConflict", "session version changed");
      }
      await writeJson(path.join(dir, "metadata.json"), {
        ...existing.metadata,
        ...partial,
        session_id: sessionId,
        version: existing.version + 1,
        updated_at: now(),
        turn_receipts: existing.receipts,
      });
      return load(sessionId);
    });
  }

  async function withSessionLock(sessionId, operation) {
    assertSessionId(sessionId);
    const previous = locks.get(sessionId) || Promise.resolve();
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const current = previous.then(() => gate);
    locks.set(sessionId, current);
    await previous;
    try {
      return await operation();
    } finally {
      release();
      if (locks.get(sessionId) === current) locks.delete(sessionId);
    }
  }

  return {
    rootDir: root,
    create,
    load,
    listRecent,
    clearReports,
    appendEvents,
    updateMetadata,
    assertSessionId,
  };
}

function sourceRevisionMetadata(value) {
  if (!value) return null;
  return {
    source_id: value.sourceId,
    revision_id: value.revisionId,
    normalization_version: value.normalizationVersion,
    extraction_version: value.extractionVersion,
    parser_version: value.parserVersion,
    source_kind: value.sourceKind,
  };
}

function assertJsonArrayBounds(value, { maxEntries, maxBytes, code }) {
  if (value.length > maxEntries) {
    throw new SessionStoreError(code, "session event limit exceeded");
  }
  assertJsonBytes(value, maxBytes, code);
}

function assertJsonBytes(value, maxBytes, code) {
  if (jsonBytes(value) > maxBytes) {
    throw new SessionStoreError(code, "session payload limit exceeded");
  }
}

function jsonBytes(value) {
  return Buffer.byteLength(JSON.stringify(value), "utf8");
}

function boundTranscript(entries) {
  const bounded = entries
    .map((entry) => {
      if (!entry || typeof entry !== "object") return entry;
      if (typeof entry.text !== "string" || entry.text.length <= 8_000) return entry;
      return { ...entry, text: entry.text.slice(0, 8_000) };
    })
    .slice(-SESSION_STORE_LIMITS.transcriptEntries);
  while (
    bounded.length
    && Buffer.byteLength(JSON.stringify(bounded), "utf8")
      > SESSION_STORE_LIMITS.transcriptBytes
  ) {
    bounded.shift();
  }
  return bounded;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function writeJson(filePath, value) {
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}
