import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { eventBuilders } from "../seda/event-facts.mjs";

const MAX_DIAGNOSTIC_TEXT_CHARS = 20_000;
const DEFAULT_BRIDGE_TIMEOUT_MS = 45_000;
const DEFAULT_BRIDGE_MAX_CONCURRENCY = 4;
const DEFAULT_BRIDGE_MAX_QUEUE = 16;
const DEFAULT_BRIDGE_MAX_OUTPUT_BYTES = 1024 * 1024;
const SECRET_ENV_KEYS = /(?:API|TOKEN|KEY|SECRET|PASSWORD|AUTH)/i;
const bridgeLimiter = { active: 0, queue: [] };

function truncate(value, limit = MAX_DIAGNOSTIC_TEXT_CHARS) {
  const text = String(value ?? "");
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}\n...[truncated ${text.length - limit} chars]`;
}

function redactValue(key, value) {
  if (value == null) return value;
  if (SECRET_ENV_KEYS.test(key)) return "[redacted]";
  return value;
}

function diagnosticEnv(env) {
  const source = env || process.env;
  const keys = [
    "LLM_PROVIDER",
    "LLM_TARGET",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_ROUTER_BASE_URL",
    "LM_STUDIO_BASE_URL",
    "PERSONA_LLM_PROVIDER",
    "PERSONA_LLM_TARGET",
    "PERSONA_LLM_MODEL",
    "PERSONA_LLM_BASE_URL",
  ];
  return Object.fromEntries(
    keys
      .filter((key) => source[key] != null)
      .map((key) => [key, redactValue(key, source[key])]),
  );
}

function diagnosticId(action) {
  const stamp = new Date().toISOString().replaceAll(":", "-");
  const safeAction = String(action || "bridge").replace(/[^a-z0-9_-]+/gi, "-");
  const suffix = Math.random().toString(16).slice(2, 8);
  return `${stamp}-${safeAction}-${suffix}`;
}

function writeDiagnostic({
  diagnosticsDir,
  action,
  payload,
  result,
  parsed,
  spawnEnv,
  transportError = null,
  durationMs = null,
  timeoutMs = null,
}) {
  if (!diagnosticsDir) return null;
  fs.mkdirSync(diagnosticsDir, { recursive: true });
  const id = diagnosticId(action);
  const filePath = path.join(diagnosticsDir, `${id}.json`);
  const diagnostic = {
    id,
    created_at: new Date().toISOString(),
    action,
    status: result.status,
    signal: result.signal || null,
    error: transportError?.error || parsed?.error || (parsed ? null : "BridgeNonJson"),
    message:
      transportError?.message ||
      parsed?.message ||
      (parsed ? "" : "bridge returned non-json output"),
    duration_ms: durationMs,
    timeout_ms: timeoutMs,
    env: diagnosticEnv(spawnEnv),
    request: {
      keys: Object.keys(payload || {}).sort(),
      log_raw_llm: Boolean(payload?.log_raw_llm),
    },
    bridge: {
      stderr: truncate(result.stderr || ""),
      stdout: truncate(result.stdout || ""),
      parsed: parsed
        ? {
            error: parsed.error || null,
            message: parsed.message || null,
            diagnostic: parsed.diagnostic
              ? {
                  ...parsed.diagnostic,
                  raw_text: truncate(parsed.diagnostic.raw_text || ""),
                }
              : null,
          }
        : null,
    },
  };
  fs.writeFileSync(filePath, `${JSON.stringify(diagnostic, null, 2)}\n`, "utf8");
  return { id, path: filePath };
}

function normalizeTimeoutMs(raw) {
  if (raw == null || raw === "") return DEFAULT_BRIDGE_TIMEOUT_MS;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) return DEFAULT_BRIDGE_TIMEOUT_MS;
  return value;
}

function callTimeoutMs(raw, configuredTimeoutMs) {
  if (raw == null || raw === "") return configuredTimeoutMs;
  const requestedTimeoutMs = normalizeTimeoutMs(raw);
  if (requestedTimeoutMs === 0) return configuredTimeoutMs;
  if (configuredTimeoutMs === 0) return requestedTimeoutMs;
  return Math.min(requestedTimeoutMs, configuredTimeoutMs);
}

function normalizeInteger(raw, fallback, { allowZero = false } = {}) {
  if (raw == null || raw === "") return fallback;
  const value = Number(raw);
  const minimum = allowZero ? 0 : 1;
  if (!Number.isInteger(value) || value < minimum) return fallback;
  return value;
}

function releaseBridgeSlot() {
  bridgeLimiter.active = Math.max(0, bridgeLimiter.active - 1);
  const nextIndex = bridgeLimiter.queue.findIndex(
    (waiter) => bridgeLimiter.active < waiter.maxConcurrency,
  );
  if (nextIndex < 0) return;
  const [next] = bridgeLimiter.queue.splice(nextIndex, 1);
  clearTimeout(next.timeoutHandle);
  bridgeLimiter.active += 1;
  next.resolve({ ok: true, release: releaseBridgeSlot });
}

function acquireBridgeSlot({ maxConcurrency, maxQueue, timeoutMs }) {
  if (bridgeLimiter.active < maxConcurrency) {
    bridgeLimiter.active += 1;
    return Promise.resolve({ ok: true, release: releaseBridgeSlot });
  }
  if (bridgeLimiter.queue.length >= maxQueue) {
    return Promise.resolve({
      ok: false,
      error: "BridgeBusy",
      message: "bridge concurrency limit reached",
    });
  }
  return new Promise((resolve) => {
    const waiter = {
      maxConcurrency,
      resolve,
      timeoutHandle: null,
    };
    if (timeoutMs > 0) {
      waiter.timeoutHandle = setTimeout(() => {
        const index = bridgeLimiter.queue.indexOf(waiter);
        if (index >= 0) bridgeLimiter.queue.splice(index, 1);
        resolve({
          ok: false,
          error: "BridgeTimeout",
          message: `bridge subprocess timed out after ${timeoutMs}ms`,
        });
      }, timeoutMs);
    }
    bridgeLimiter.queue.push(waiter);
  });
}

export function createBridgeClient({
  workspaceRoot,
  bridgePath,
  python,
  envOverrides = null,
  diagnosticsDir = null,
  timeoutMs = process.env.SOCRATINK_BRIDGE_TIMEOUT_MS,
  maxConcurrency = process.env.SOCRATINK_BRIDGE_MAX_CONCURRENCY,
  maxQueue = process.env.SOCRATINK_BRIDGE_MAX_QUEUE,
  maxOutputBytes = process.env.SOCRATINK_BRIDGE_MAX_OUTPUT_BYTES,
}) {
  const bridgeTimeoutMs = normalizeTimeoutMs(timeoutMs);
  const bridgeMaxConcurrency = normalizeInteger(
    maxConcurrency,
    DEFAULT_BRIDGE_MAX_CONCURRENCY,
  );
  const bridgeMaxQueue = normalizeInteger(
    maxQueue,
    DEFAULT_BRIDGE_MAX_QUEUE,
    { allowZero: true },
  );
  const bridgeMaxOutputBytes = normalizeInteger(
    maxOutputBytes,
    DEFAULT_BRIDGE_MAX_OUTPUT_BYTES,
  );
  const spawnEnv =
    envOverrides && Object.keys(envOverrides).length
      ? { ...process.env, ...envOverrides }
      : null;
  async function runBridge(action, payload, callOptions = {}) {
    const startedAt = Date.now();
    const activeTimeoutMs = callTimeoutMs(
      callOptions.timeoutMs,
      bridgeTimeoutMs,
    );
    const slot = await acquireBridgeSlot({
      maxConcurrency: bridgeMaxConcurrency,
      maxQueue: bridgeMaxQueue,
      timeoutMs: activeTimeoutMs,
    });
    let slotError = null;
    let result;
    if (!slot.ok) {
      slotError = slot;
      result = {
        status: null,
        signal: null,
        stdout: "",
        stderr: "",
        timedOut: slot.error === "BridgeTimeout",
        outputLimitExceeded: false,
      };
    } else {
      const queuedMs = Date.now() - startedAt;
      const processTimeoutMs = activeTimeoutMs > 0
        ? Math.max(1, activeTimeoutMs - queuedMs)
        : 0;
      try {
        result = await new Promise((resolve) => {
          let stdout = "";
          let stderr = "";
          let stdoutBytes = 0;
          let stderrBytes = 0;
          let spawnError = null;
          let timedOut = false;
          let outputLimitExceeded = false;
          let timeoutHandle = null;
          let forceKillHandle = null;

          const child = spawn(python, [bridgePath, action], {
            cwd: workspaceRoot,
            stdio: ["pipe", "pipe", "pipe"],
            ...(spawnEnv ? { env: spawnEnv } : {}),
          });
          const terminateChild = () => {
            child.kill("SIGTERM");
            forceKillHandle ||= setTimeout(
              () => child.kill("SIGKILL"),
              1_000,
            );
          };
          const appendOutput = (current, usedBytes, chunk) => {
            const buffer = Buffer.from(chunk);
            const remaining = Math.max(0, bridgeMaxOutputBytes - usedBytes);
            const kept = buffer.subarray(0, remaining);
            return {
              text: current + kept.toString("utf8"),
              bytes: usedBytes + kept.length,
              exceeded: buffer.length > remaining,
            };
          };

          child.stdout.setEncoding("utf8");
          child.stderr.setEncoding("utf8");
          child.stdout.on("data", (chunk) => {
            const next = appendOutput(stdout, stdoutBytes, chunk);
            stdout = next.text;
            stdoutBytes = next.bytes;
            if (next.exceeded && !outputLimitExceeded) {
              outputLimitExceeded = true;
              terminateChild();
            }
          });
          child.stderr.on("data", (chunk) => {
            const next = appendOutput(stderr, stderrBytes, chunk);
            stderr = next.text;
            stderrBytes = next.bytes;
            if (next.exceeded && !outputLimitExceeded) {
              outputLimitExceeded = true;
              terminateChild();
            }
          });
          child.on("error", (error) => {
            spawnError = error;
          });
          child.stdin.on("error", (error) => {
            if (error?.code !== "EPIPE") spawnError ||= error;
          });
          child.on("close", (status, signal) => {
            if (timeoutHandle) clearTimeout(timeoutHandle);
            if (forceKillHandle) clearTimeout(forceKillHandle);
            resolve({
              status,
              signal,
              stdout,
              stderr: stderr || spawnError?.message || "",
              timedOut,
              outputLimitExceeded,
            });
          });

          if (processTimeoutMs > 0) {
            timeoutHandle = setTimeout(() => {
              timedOut = true;
              terminateChild();
            }, processTimeoutMs);
          }

          child.stdin.end(JSON.stringify(payload));
        });
      } finally {
        slot.release();
      }
    }
    const durationMs = Date.now() - startedAt;
    const timedOut = result.timedOut === true;
    let transportError = null;
    if (slotError) {
      transportError = {
        error: slotError.error,
        message: slotError.message,
        ...(slotError.error === "BridgeTimeout"
          ? { timeout_ms: activeTimeoutMs }
          : {}),
        duration_ms: durationMs,
      };
    } else if (timedOut) {
      transportError = {
        error: "BridgeTimeout",
        message: `bridge subprocess timed out after ${activeTimeoutMs}ms`,
        timeout_ms: activeTimeoutMs,
        duration_ms: durationMs,
      };
    } else if (result.outputLimitExceeded) {
      transportError = {
        error: "BridgeOutputTooLarge",
        message: `bridge output exceeded ${bridgeMaxOutputBytes} bytes`,
        duration_ms: durationMs,
      };
    }
    let parsed;
    try {
      parsed = JSON.parse(result.stdout || "{}");
    } catch {
      parsed = null;
    }
    const diagnostic =
      transportError || !parsed || result.status !== 0
        ? writeDiagnostic({
            diagnosticsDir,
            action,
            payload,
            result,
            parsed,
            spawnEnv,
            transportError,
            durationMs,
            timeoutMs: activeTimeoutMs,
          })
        : null;
    return {
      parsed,
      status: result.status,
      stderr: result.stderr,
      diagnostic,
      transportError,
      duration_ms: durationMs,
    };
  }

  async function callBridge(action, payload, callOptions = {}) {
    const result = await runBridge(action, payload, callOptions);
    if (result.transportError) {
      const bridgeError = new Error(result.transportError.message);
      bridgeError.error = result.transportError.error;
      bridgeError.action = action;
      bridgeError.diagnostic = result.diagnostic;
      bridgeError.duration_ms = result.duration_ms;
      bridgeError.timeout_ms = result.transportError.timeout_ms;
      throw bridgeError;
    }
    if (!result.parsed) {
      const bridgeError = new Error("bridge returned non-json output");
      bridgeError.error = "BridgeNonJson";
      bridgeError.action = action;
      bridgeError.diagnostic = result.diagnostic;
      throw bridgeError;
    }
    if (result.status !== 0) {
      const bridgeError = new Error(
        result.parsed.message || result.stderr || "bridge exited nonzero",
      );
      bridgeError.error = result.parsed.error || "BridgeExitNonZero";
      bridgeError.action = action;
      bridgeError.diagnostic = result.diagnostic;
      throw bridgeError;
    }
    return result.parsed;
  }

  async function callBridgeResult(action, payload, callOptions = {}) {
    const result = await runBridge(action, payload, callOptions);
    if (result.transportError) {
      return {
        ok: false,
        error: result.transportError.error,
        message: result.transportError.message,
        diagnostic: result.diagnostic,
        duration_ms: result.duration_ms,
        timeout_ms: result.transportError.timeout_ms,
      };
    }
    if (!result.parsed) {
      return {
        ok: false,
        error: "BridgeNonJson",
        message: "bridge returned non-json output",
        diagnostic: result.diagnostic,
        duration_ms: result.duration_ms,
      };
    }
    if (result.status !== 0) {
      return {
        ok: false,
        error: result.parsed.error || "BridgeExitNonZero",
        message:
          result.parsed.message || result.stderr || "bridge exited nonzero",
        diagnostic: result.diagnostic,
        duration_ms: result.duration_ms,
      };
    }
    return { ok: true, payload: result.parsed };
  }

  return { callBridge, callBridgeResult };
}

export function isRetryableRouteError(error) {
  return (
    error?.error === "SmallestRouteCapExceeded" ||
    String(error?.message || "").includes("SmallestRouteCapExceeded") ||
    String(error?.message || "").includes("copies hidden mechanism")
  );
}

export function routeRetryEvent(error, attempt) {
  return eventBuilders.routeRetry({
    attempt,
    error: error.error || "route_generation_failed",
    message: error.message || "",
    retry_guardrail:
      "regenerate learner scaffold without copying hidden mechanism answer phrases",
  });
}
