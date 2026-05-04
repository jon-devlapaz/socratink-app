// public/js/telemetry.js
//
// Frontend telemetry emit point for the conversational concept-creation flow.
// Spec §5.4 lists the events. The events are observable in three places:
//
//   1. Browser console (`console.info('telemetry', { event, ...extra })`)
//   2. Bus listeners (`Bus.on('telemetry', fn)`) — for in-app debug overlays
//   3. Future: a /api/telemetry endpoint. Not wired in v1 — the helper takes
//      one shape so adding the network post is a one-line change later.
//
// Server-side telemetry (concept_create.lc.queried, .build_blocked, .ai_call,
// etc.) flows through Python's structured logger from main.py — that path is
// already shipped in Plan A. Client events use `origin: 'client'` so the
// dashboards can detect client/server validation drift.

import { Bus } from "./bus.js";

export function emitTelemetry(event, extra = {}) {
  if (typeof event !== "string" || !event) return;
  const payload = { event, ...extra };
  try {
    Bus.emit("telemetry", payload);
  } catch (err) {
    /* Bus is best-effort. Never let telemetry break the UI. */
  }
  // eslint-disable-next-line no-console
  console.info("telemetry", payload);
}
