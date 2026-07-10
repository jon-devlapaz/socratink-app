import http from "node:http";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  advanceSession,
  materializeSessionRecord,
  sessionResponse,
} from "./session.mjs";
import {
  assertRequestId,
  createFileSessionStore,
  defaultSessionStoreRoot,
  durableSessionStoreRequired,
  replayForRequest,
  SessionStoreError,
} from "./session-store.mjs";
import { createSupabaseSessionStore } from "./supabase-session-store.mjs";
import { isFeedbackConfigured } from "../feedback/send.mjs";
import { LOOP_APP_VERSION } from "./version.mjs";
import {
  createSessionState,
  loadAgentLookup,
  paths,
} from "./runtime.mjs";
import { CannotRehydrateSession } from "../seda/session-rehydration.mjs";
import {
  activeLlm,
  buildLlmOptions,
  isModelOverrideAllowed,
  validateLlmSelection,
} from "./llm-options.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = paths.workspaceRoot;
const LOOP_PUBLIC = process.env.SOCRATINK_LOOP_PUBLIC_DIR
  ? path.resolve(process.env.SOCRATINK_LOOP_PUBLIC_DIR)
  : path.join(WORKSPACE_ROOT, "lib/loop-public");
const USER_ACCESS_TOKEN_HEADER = "x-socratink-user-access-token";
const MAX_REQUEST_BODY_BYTES = 64 * 1024;

const { lookup: agentLookup, contracts: agentContracts } = await loadAgentLookup();

function json(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(body));
}

function unauthorized(res) {
  json(res, 401, { error: "unauthorized" });
}

function checkAuth(req, res) {
  const apiKey = String(process.env.SOCRATINK_LOOP_API_KEY || "").trim();
  if (!apiKey) {
    if (durableSessionStoreRequired(process.env)) {
      json(res, 503, { error: "loop_api_key_required" });
      return false;
    }
    return true;
  }
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (token !== apiKey) {
    unauthorized(res);
    return false;
  }
  return true;
}

async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_REQUEST_BODY_BYTES) {
      throw new SessionStoreError("RequestTooLarge", "request body is too large");
    }
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new SessionStoreError("InvalidJson", "request body must be valid JSON");
  }
}

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  return "application/octet-stream";
}

async function serveStatic(req, res, options) {
  const { mountPath, publicRoot, defaultFile } = options;
  let rel = req.url?.split("?")[0] || "/";
  if (rel === mountPath || rel === `${mountPath}/`) {
    rel = `${mountPath}/${defaultFile}`;
  }
  if (!rel.startsWith(`${mountPath}/`)) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }
  const filePath = path.join(publicRoot, rel.replace(`${mountPath}/`, ""));
  if (!filePath.startsWith(publicRoot)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  try {
    const data = await fs.readFile(filePath);
    res.writeHead(200, { "Content-Type": contentType(filePath) });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end("Not found");
  }
}

export function createLoopServer() {
  return createLoopServerWithStore({
    sessionStoreResolver: createSessionStoreResolver(),
  });
}

export function createSessionStoreResolver({
  env = process.env,
  fetchImpl = globalThis.fetch,
} = {}) {
  const durableRequired = durableSessionStoreRequired(env);
  const localStore = durableRequired
    ? null
    : createFileSessionStore({ rootDir: defaultSessionStoreRoot(env) });
  return function resolveSessionStore(req) {
    if (localStore) return localStore;
    return createSupabaseSessionStore({
      supabaseUrl: env.SUPABASE_URL || "",
      publishableKey: env.SUPABASE_PUBLISHABLE_KEY || "",
      accessToken: singleHeader(req.headers[USER_ACCESS_TOKEN_HEADER]),
      fetchImpl,
      sessionTtlSeconds: env.SOCRATINK_LOOP_SESSION_TTL_SECONDS,
    });
  };
}

export function createLoopServerWithStore({
  sessionStore = null,
  sessionStoreResolver = null,
  createSession = createSessionState,
  advance = advanceSession,
} = {}) {
  return http.createServer(async (req, res) => {
    try {
      const url = req.url?.split("?")[0] || "/";

      if (req.method === "GET" && url === "/health") {
        const fakeLlm = process.env.SOCRATINK_TUI_FAKE_LLM === "1";
        const geminiKey = (process.env.GEMINI_API_KEY || "").trim();
        const overrideAllowed = isModelOverrideAllowed(req);
        const active = activeLlm();
        json(res, 200, {
          status: "ok",
          app_version: LOOP_APP_VERSION,
          fake_llm: fakeLlm,
          llm_mode: fakeLlm ? "fake" : "live",
          gemini_configured: Boolean(geminiKey),
          llm_model: active.model,
          llm_provider: active.provider,
          llm_target: active.target || null,
          llm_override_allowed: overrideAllowed,
          ...(overrideAllowed ? { llm_options: buildLlmOptions() } : {}),
          feedback_configured: isFeedbackConfigured(),
        });
        return;
      }

      if (url.startsWith("/loop")) {
        await serveStatic(req, res, {
          mountPath: "/loop",
          publicRoot: LOOP_PUBLIC,
          defaultFile: "index.html",
        });
        return;
      }

      if (!checkAuth(req, res)) return;

      const resolveStore = () => {
        const resolved = sessionStore || sessionStoreResolver?.(req);
        if (!resolved) {
          throw new SessionStoreError(
            "StoreConfigurationError",
            "loop session storage is not configured",
          );
        }
        return resolved;
      };

      if (req.method === "POST" && url === "/api/session") {
        const payload = await readJson(req);
        const sourceLessDoorBootstrap = payload.sourceLessDoorBootstrap === true;
        let llm = null;
        if (payload.llm && isModelOverrideAllowed(req)) {
          const validated = validateLlmSelection(payload.llm);
          if (!validated.ok) {
            json(res, 400, { error: validated.error });
            return;
          }
          llm = validated.llm;
        }
        const sessionStore = resolveStore();
        const sessionId = crypto.randomUUID();
        const bridgeDiagnosticsDir = sessionStore.rootDir
          ? path.join(sessionStore.rootDir, sessionId, "bridge-diagnostics")
          : null;
        const session = await createSession({
          agentLookup,
          agentContracts,
          id: sessionId,
          llm,
          bridgeDiagnosticsDir,
          sourceLessDoorBootstrap,
        });
        const created = await sessionStore.create(session.id, {
          status: session.status,
          phase: session.phase,
          awaiting: session.awaiting,
          complete: false,
          caseComplete: false,
          llm,
          bridgeDiagnosticsDir,
          sourceLessDoorBootstrap,
        });
        const eventStart = session.events.length;
        const body = {
          ...await advance(session),
          sessionVersion: created.version + 1,
        };
        await sessionStore.appendEvents(
          session.id,
          session.events.slice(eventStart),
          { ...body, bridgeDiagnosticsDir },
          { expectedVersion: created.version },
        );
        json(res, 201, body);
        return;
      }

      const llmMatch = url.match(/^\/api\/session\/([^/]+)\/llm$/);
      if (req.method === "PATCH" && llmMatch) {
        if (!isModelOverrideAllowed(req)) {
          json(res, 403, { error: "model override not allowed" });
          return;
        }
        const sessionStore = resolveStore();
        const stored = await loadStoredSession(sessionStore, llmMatch[1], res);
        if (!stored) return;
        const payload = await readJson(req);
        const validated = validateLlmSelection(payload.llm ?? payload);
        if (!validated.ok) {
          json(res, 400, { error: validated.error });
          return;
        }
        const updated = await sessionStore.updateMetadata(
          llmMatch[1],
          { llm: validated.llm },
          { expectedVersion: stored.version },
        );
        json(res, 200, { llm: validated.llm, sessionVersion: updated.version });
        return;
      }

      const turnMatch = url.match(/^\/api\/session\/([^/]+)\/turn$/);
      if (req.method === "POST" && turnMatch) {
        const sessionStore = resolveStore();
        const stored = await loadStoredSession(sessionStore, turnMatch[1], res);
        if (!stored) return;
        const payload = await readJson(req);
        const requestId = assertRequestId(payload.requestId);
        if (!requestId) {
          throw new SessionStoreError(
            "InvalidRequestId",
            "requestId is required for every session turn",
          );
        }
        const requestHash = turnRequestHash(payload);
        const replayedResponse = replayForRequest(stored, requestId, requestHash);
        if (replayedResponse) {
          json(res, 200, replayedResponse);
          return;
        }
        const expectedVersion = assertExpectedVersion(payload.expectedVersion);
        if (expectedVersion !== stored.version) {
          const conflict = new SessionStoreError(
            "SessionConflict",
            "session changed after this prompt was shown",
          );
          conflict.currentVersion = stored.version;
          throw conflict;
        }
        const session = await loadSessionStateFromStore({
          stored,
          res,
          agentLookup,
          agentContracts,
          createSession,
        });
        if (!session) return;
        applyEmptyJournalMetadata(session, stored);
        const eventStart = session.events.length;
        const body = {
          ...await advance(session, payload.text),
          sessionVersion: expectedVersion + 1,
        };
        const committed = await sessionStore.appendEvents(
          session.id,
          session.events.slice(eventStart),
          body,
          {
            expectedVersion,
            requestId,
            requestHash,
            response: body,
          },
        );
        json(res, 200, committed.replayedResponse || body);
        return;
      }

      const getMatch = url.match(/^\/api\/session\/([^/]+)$/);
      if (req.method === "GET" && getMatch) {
        const sessionStore = resolveStore();
        const stored = await loadStoredSession(sessionStore, getMatch[1], res);
        if (!stored) return;
        const session = await loadSessionStateFromStore({
          stored,
          res,
          agentLookup,
          agentContracts,
          createSession,
        });
        if (!session) return;
        applyEmptyJournalMetadata(session, stored);
        session.status = stored.metadata.status || session.status;
        session.awaiting = stored.metadata.awaiting || session.awaiting;
        await materializeSessionRecord(session);
        json(res, 200, {
          ...sessionResponse(session, stored.metadata.transcript_tail || []),
          sessionVersion: stored.version,
        });
        return;
      }

      json(res, 404, { error: "not found" });
    } catch (error) {
      console.error(error);
      writeRequestError(res, error);
    }
  });
}

async function loadSessionStateFromStore({
  stored,
  res,
  agentLookup,
  agentContracts,
  createSession = createSessionState,
}) {
  try {
    return await createSession({
      agentLookup,
      agentContracts,
      id: stored.sessionId,
      events: stored.events,
      llm: stored.metadata.llm || null,
      bridgeDiagnosticsDir: stored.metadata.bridge_diagnostics_dir || null,
      sourceLessDoorBootstrap: Boolean(
        stored.metadata.source_less_door_bootstrap,
      ),
    });
  } catch (error) {
    if (error instanceof CannotRehydrateSession) {
      json(res, 409, {
        error: "session_resume_failed",
        code: error.code,
        message:
          "Persisted session cannot be resumed because required persisted facts are missing.",
        reason: error.message,
        details: error.details || {},
      });
      return null;
    }
    throw error;
  }
}

function applyEmptyJournalMetadata(session, stored) {
  if (stored.events.length > 0) return;
  if (stored.metadata.phase) session.phase = stored.metadata.phase;
  if (stored.metadata.status) session.status = stored.metadata.status;
  if (stored.metadata.awaiting) session.awaiting = stored.metadata.awaiting;
}

async function loadStoredSession(sessionStore, sessionId, res) {
  try {
    return await sessionStore.load(sessionId);
  } catch (error) {
    if (error instanceof SessionStoreError) {
      if (error.code === "SessionNotFound") {
        json(res, 404, { error: "session_not_found" });
        return null;
      }
      if (error.code === "InvalidSessionId") {
        json(res, 400, { error: error.message, code: error.code });
        return null;
      }
    }
    throw error;
  }
}

function turnRequestHash(payload) {
  return createHash("sha256")
    .update(JSON.stringify({
      text: payload.text ?? null,
      expectedVersion: payload.expectedVersion ?? null,
    }))
    .digest("hex");
}

function assertExpectedVersion(value) {
  if (!Number.isInteger(value) || value < 0) {
    throw new SessionStoreError(
      "InvalidExpectedVersion",
      "expectedVersion must be a nonnegative integer",
    );
  }
  return value;
}

function singleHeader(value) {
  return Array.isArray(value) ? value[0] : String(value || "");
}

function writeRequestError(res, error) {
  if (!(error instanceof SessionStoreError)) {
    json(res, 500, { error: "internal_error" });
    return;
  }
  if (["SessionConflict", "IdempotencyConflict"].includes(error.code)) {
    json(res, 409, {
      error: "session_conflict",
      code: error.code,
      message: error.message,
      ...(Number.isInteger(error.currentVersion)
        ? { currentVersion: error.currentVersion }
        : {}),
    });
    return;
  }
  if (error.code === "SessionNotFound") {
    json(res, 404, { error: "session_not_found" });
    return;
  }
  if (error.code === "StoreAuthenticationRequired") {
    json(res, 401, { error: "session_auth_required" });
    return;
  }
  if (["StoreConfigurationError", "StoreUnavailable"].includes(error.code)) {
    json(res, 503, { error: "session_store_unavailable", code: error.code });
    return;
  }
  if ([
    "RequestTooLarge",
    "SessionEventsLimitExceeded",
    "SessionMetadataLimitExceeded",
    "SessionResponseLimitExceeded",
  ].includes(error.code)) {
    json(res, 413, { error: "session_limit_exceeded", code: error.code });
    return;
  }
  json(res, 400, { error: error.message, code: error.code });
}

export function startLoopServer(port = Number(process.env.PORT || 8787), host = process.env.HOST || "") {
  const fakeLlm = process.env.SOCRATINK_TUI_FAKE_LLM === "1";
  const geminiConfigured = Boolean((process.env.GEMINI_API_KEY || "").trim());
  const server = createLoopServer();
  const listenArgs = host ? [port, host] : [port];
  server.listen(...listenArgs, () => {
    console.log(`[loop-server] listening on http://127.0.0.1:${port}/loop`);
    console.log(
      `[loop-server] llm_mode=${fakeLlm ? "FAKE (templates, no Gemini)" : "live"} ` +
        `gemini=${geminiConfigured ? "configured" : "MISSING"} ` +
        `model=${process.env.LLM_MODEL || "gemini-2.5-flash"}`,
    );
    if (fakeLlm) {
      console.warn(
        "[loop-server] SOCRATINK_TUI_FAKE_LLM=1 — route/eval use bridge templates; " +
          "hypothesis map will look templated. Unset and restart for live Gemini.",
      );
    } else if (!geminiConfigured) {
      console.warn(
        "[loop-server] GEMINI_API_KEY missing — bridge calls will fail on route/eval.",
      );
    }
  });
  return server;
}
