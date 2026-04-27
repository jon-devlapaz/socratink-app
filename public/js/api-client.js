// public/js/api-client.js
// HTTP client for the socratink backend.
//
// Every export returns parsed JSON on 2xx, or throws on non-ok / network error.
// Callers handle errors per their UX needs (silent for runtime-config refresh,
// throw-and-show for user-initiated actions like /api/extract-url and /api/drill).
//
// This module owns ZERO browser state — it does not read localStorage, cookies,
// or window. Callers pass any tokens (e.g. api_key) explicitly. Keeping the
// HTTP layer pure makes Phase 4-style backend changes (typed request/result
// objects) trivial without rewriting frontend storage logic. Note that
// ai_service.js (Phase 2.1) still reads localStorage directly — that is
// tech debt from an earlier phase, not a pattern to perpetuate here.

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json();
}

async function postJson(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    const err = new Error(`POST ${path} failed: ${response.status}: ${errText}`);
    err.status = response.status;
    err.responseText = errText;
    throw err;
  }
  return response.json();
}

export async function getHealth() {
  return getJson('/api/health');
}

export async function extractUrl({ url }) {
  // Special-case: preserve the original `payload.detail || 'Failed to fetch page.'`
  // error contract because the caller renders that exact string to the user.
  // Cannot use the generic postJson helper here without losing that contract.
  const response = await fetch('/api/extract-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || 'Failed to fetch page.');
  }
  return payload;
}

export async function runRepairReps(body) {
  return postJson('/api/repair-reps', body);
}

export async function runDrillTurn(body) {
  return postJson('/api/drill', body);
}

export async function loadLibraryConcept(filename) {
  // Static asset path served by FastAPI's StaticFiles mount, not /api/*.
  return getJson(`/data/library/${filename}`);
}
