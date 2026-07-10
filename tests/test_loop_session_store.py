from __future__ import annotations

from tests._helpers.node_runner import run_node_module


def test_file_store_uses_cas_and_idempotent_turn_replay() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import os from "node:os";
        import path from "node:path";
        import fs from "node:fs/promises";
        import { createFileSessionStore } from "./lib/loop-server/session-store.mjs";

        const root = await fs.mkdtemp(path.join(os.tmpdir(), "socratink-store-test-"));
        const store = createFileSessionStore({ rootDir: root });
        const sessionId = "00000000-0000-4000-8000-000000000001";
        const requestId = "10000000-0000-4000-8000-000000000001";
        await store.create(sessionId, { sourceLessDoorBootstrap: true });

        const response = { sessionId, sessionVersion: 1, marker: "first" };
        const committed = await store.appendEvents(
          sessionId,
          [{ type: "cold_attempt", text: "first" }],
          { transcript: [{ level: "log", text: "first" }] },
          {
            expectedVersion: 0,
            requestId,
            requestHash: "hash-a",
            response,
          },
        );
        assert.equal(committed.version, 1);
        assert.equal(committed.events.length, 1);
        assert.equal(committed.metadata.source_less_door_bootstrap, true);
        assert.equal(committed.receipts.length, 1);

        const secondRequestId = "10000000-0000-4000-8000-000000000002";
        const secondResponse = { sessionId, sessionVersion: 2, marker: "second" };
        await store.appendEvents(
          sessionId,
          [{ type: "cold_attempt", text: "second" }],
          {},
          {
            expectedVersion: 1,
            requestId: secondRequestId,
            requestHash: "hash-b",
            response: secondResponse,
          },
        );
        const afterMetadataPatch = await store.updateMetadata(
          sessionId,
          { llm: { provider: "test" } },
          { expectedVersion: 2 },
        );
        assert.equal(afterMetadataPatch.receipts.length, 2);

        const replay = await store.appendEvents(
          sessionId,
          [{ type: "should_not_append" }],
          {},
          {
            expectedVersion: 0,
            requestId,
            requestHash: "hash-a",
            response,
          },
        );
        assert.deepEqual(replay.replayedResponse, response);
        assert.equal((await store.load(sessionId)).events.length, 2);

        await assert.rejects(
          store.appendEvents(sessionId, [], {}, {
            expectedVersion: 0,
            requestId,
            requestHash: "different-hash",
            response,
          }),
          (error) => error.code === "IdempotencyConflict",
        );
        await assert.rejects(
          store.appendEvents(sessionId, [], {}, {
            expectedVersion: 0,
            requestId: "10000000-0000-4000-8000-000000000003",
            requestHash: "hash-c",
            response,
          }),
          (error) => error.code === "SessionConflict",
        );

        const raceSession = "00000000-0000-4000-8000-000000000002";
        const raceRequest = "20000000-0000-4000-8000-000000000001";
        await store.create(raceSession);
        const raceResponse = { sessionId: raceSession, sessionVersion: 1 };
        const sameRequestResults = await Promise.all([
          store.appendEvents(raceSession, [{ type: "turn" }], {}, {
            expectedVersion: 0,
            requestId: raceRequest,
            requestHash: "same-hash",
            response: raceResponse,
          }),
          store.appendEvents(raceSession, [{ type: "turn" }], {}, {
            expectedVersion: 0,
            requestId: raceRequest,
            requestHash: "same-hash",
            response: raceResponse,
          }),
        ]);
        assert.equal((await store.load(raceSession)).events.length, 1);
        assert.equal(
          sameRequestResults.filter((entry) => entry.replayedResponse).length,
          1,
        );

        const conflictSession = "00000000-0000-4000-8000-000000000003";
        await store.create(conflictSession);
        const differentRequests = await Promise.allSettled([
          store.appendEvents(conflictSession, [{ type: "a" }], {}, {
            expectedVersion: 0,
            requestId: "30000000-0000-4000-8000-000000000001",
            requestHash: "a",
            response: { marker: "a" },
          }),
          store.appendEvents(conflictSession, [{ type: "b" }], {}, {
            expectedVersion: 0,
            requestId: "30000000-0000-4000-8000-000000000002",
            requestHash: "b",
            response: { marker: "b" },
          }),
        ]);
        assert.equal(differentRequests.filter((entry) => entry.status === "fulfilled").length, 1);
        assert.equal(differentRequests.filter((entry) => entry.status === "rejected").length, 1);
        assert.equal(differentRequests.find((entry) => entry.status === "rejected").reason.code, "SessionConflict");
        assert.equal((await store.load(conflictSession)).events.length, 1);

        await fs.rm(root, { recursive: true, force: true });
        """
    )

    assert result.returncode == 0, result.stderr


def test_file_store_bounds_recent_receipts_by_count_and_bytes() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import os from "node:os";
        import path from "node:path";
        import fs from "node:fs/promises";
        import {
          createFileSessionStore,
          SESSION_STORE_LIMITS,
        } from "./lib/loop-server/session-store.mjs";

        const root = await fs.mkdtemp(path.join(os.tmpdir(), "socratink-receipts-test-"));
        const store = createFileSessionStore({ rootDir: root });
        const countSession = "60000000-0000-4000-8000-000000000001";
        await store.create(countSession);
        for (let index = 0; index < 20; index += 1) {
          const suffix = String(index).padStart(12, "0");
          await store.appendEvents(countSession, [], {}, {
            expectedVersion: index,
            requestId: `61000000-0000-4000-8000-${suffix}`,
            requestHash: `hash-${index}`,
            response: { marker: index },
          });
        }
        const countBounded = await store.load(countSession);
        assert.equal(countBounded.receipts.length, SESSION_STORE_LIMITS.receiptEntries);
        assert.equal(
          countBounded.receipts[0].request_id,
          "61000000-0000-4000-8000-000000000004",
        );

        const bytesSession = "60000000-0000-4000-8000-000000000002";
        await store.create(bytesSession);
        for (let index = 0; index < 4; index += 1) {
          const suffix = String(index).padStart(12, "0");
          await store.appendEvents(bytesSession, [], {}, {
            expectedVersion: index,
            requestId: `62000000-0000-4000-8000-${suffix}`,
            requestHash: `large-${index}`,
            response: { marker: index, payload: "x".repeat(700 * 1024) },
          });
        }
        const byteBounded = await store.load(bytesSession);
        assert.ok(byteBounded.receipts.length < 4);
        assert.ok(
          Buffer.byteLength(JSON.stringify(byteBounded.receipts), "utf8")
            <= SESSION_STORE_LIMITS.receiptBytes,
        );
        assert.equal(byteBounded.receipts.at(-1).response.marker, 3);

        await fs.rm(root, { recursive: true, force: true });
        """
    )

    assert result.returncode == 0, result.stderr


def test_supabase_store_is_user_scoped_and_cas_safe() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import { createSupabaseSessionStore } from "./lib/loop-server/supabase-session-store.mjs";

        let row = null;
        const requests = [];
        const fakeFetch = async (url, options = {}) => {
          requests.push({ url: String(url), options });
          const method = options.method || "GET";
          const parsed = new URL(url);
          let body = null;
          if (method === "POST") {
            body = JSON.parse(options.body);
            assert.equal("user_id" in body, false);
            row = { ...body };
            return response(201, [row]);
          }
          if (method === "GET") return response(200, row ? [row] : []);
          if (method === "PATCH") {
            const expected = Number(parsed.searchParams.get("version").replace("eq.", ""));
            if (!row || row.version !== expected) return response(200, []);
            body = JSON.parse(options.body);
            row = { ...row, ...body };
            return response(200, [row]);
          }
          throw new Error(`unexpected ${method}`);
        };
        const response = (status, value) => ({
          ok: status >= 200 && status < 300,
          status,
          text: async () => JSON.stringify(value),
        });

        const store = createSupabaseSessionStore({
          supabaseUrl: "https://example.supabase.co",
          publishableKey: "sb_publishable_test",
          accessToken: "user-jwt",
          fetchImpl: fakeFetch,
          now: () => "2026-07-09T12:00:00.000Z",
        });
        const sessionId = "40000000-0000-4000-8000-000000000001";
        const requestId = "41000000-0000-4000-8000-000000000001";
        await store.create(sessionId);
        const replayBody = { sessionId, sessionVersion: 1, marker: "stored" };
        await store.appendEvents(sessionId, [{ type: "route_generated" }], {}, {
          expectedVersion: 0,
          requestId,
          requestHash: "payload-hash",
          response: replayBody,
        });
        const secondRequestId = "41000000-0000-4000-8000-000000000002";
        const secondReplayBody = { sessionId, sessionVersion: 2, marker: "second" };
        await store.appendEvents(sessionId, [{ type: "cold_attempt" }], {}, {
          expectedVersion: 1,
          requestId: secondRequestId,
          requestHash: "second-payload-hash",
          response: secondReplayBody,
        });
        await store.updateMetadata(
          sessionId,
          { llm: { provider: "test" } },
          { expectedVersion: 2 },
        );
        assert.equal(row.turn_receipts.length, 2);
        const replay = await store.appendEvents(sessionId, [{ type: "duplicate" }], {}, {
          expectedVersion: 0,
          requestId,
          requestHash: "payload-hash",
          response: replayBody,
        });
        assert.deepEqual(replay.replayedResponse, replayBody);
        assert.equal(row.events.length, 2);
        await assert.rejects(
          store.appendEvents(sessionId, [], {}, {
            expectedVersion: 0,
            requestId,
            requestHash: "different-payload",
            response: replayBody,
          }),
          (error) => error.code === "IdempotencyConflict",
        );

        const sameRaceId = "40000000-0000-4000-8000-000000000002";
        const sameRaceRequest = "42000000-0000-4000-8000-000000000001";
        await store.create(sameRaceId);
        const sameRaceBody = { sessionId: sameRaceId, sessionVersion: 1 };
        const sameRace = await Promise.all([
          store.appendEvents(sameRaceId, [{ type: "turn" }], {}, {
            expectedVersion: 0,
            requestId: sameRaceRequest,
            requestHash: "same-race",
            response: sameRaceBody,
          }),
          store.appendEvents(sameRaceId, [{ type: "turn" }], {}, {
            expectedVersion: 0,
            requestId: sameRaceRequest,
            requestHash: "same-race",
            response: sameRaceBody,
          }),
        ]);
        assert.equal(row.events.length, 1);
        assert.equal(sameRace.filter((entry) => entry.replayedResponse).length, 1);

        const conflictRaceId = "40000000-0000-4000-8000-000000000003";
        await store.create(conflictRaceId);
        const conflictRace = await Promise.allSettled([
          store.appendEvents(conflictRaceId, [{ type: "a" }], {}, {
            expectedVersion: 0,
            requestId: "43000000-0000-4000-8000-000000000001",
            requestHash: "a",
            response: { marker: "a" },
          }),
          store.appendEvents(conflictRaceId, [{ type: "b" }], {}, {
            expectedVersion: 0,
            requestId: "43000000-0000-4000-8000-000000000002",
            requestHash: "b",
            response: { marker: "b" },
          }),
        ]);
        assert.equal(conflictRace.filter((entry) => entry.status === "fulfilled").length, 1);
        assert.equal(conflictRace.filter((entry) => entry.status === "rejected").length, 1);
        assert.equal(conflictRace.find((entry) => entry.status === "rejected").reason.code, "SessionConflict");
        assert.equal(row.events.length, 1);

        for (const request of requests) {
          assert.equal(request.options.headers.authorization, "Bearer user-jwt");
          assert.equal(request.options.headers.apikey, "sb_publishable_test");
          assert.equal(JSON.stringify(request).includes("service_role"), false);
        }
        const patch = requests.find((request) => request.options.method === "PATCH");
        assert.match(patch.url, /version=eq%5C.0|version=eq\.0/);

        assert.throws(
          () => createSupabaseSessionStore({
            supabaseUrl: "https://example.supabase.co",
            publishableKey: "sb_secret_do_not_use",
            accessToken: "user-jwt",
          }),
          (error) => error.code === "StoreConfigurationError",
        );
        """
    )

    assert result.returncode == 0, result.stderr


def test_production_store_fails_closed_without_durable_config() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        const { createSessionStoreResolver } = await import("./lib/loop-server/http-server.mjs");
        const resolver = createSessionStoreResolver({
          env: {
            VERCEL: "1",
            SOCRATINK_LOOP_SESSION_STORE_DIR: "/tmp/must-not-be-used",
          },
        });
        assert.throws(
          () => resolver({ headers: {} }),
          (error) => error.code === "StoreConfigurationError",
        );
        """
    )

    assert result.returncode == 0, result.stderr


def test_console_capture_is_async_context_scoped() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import { withConsoleCapture } from "./lib/loop-server/console-capture.mjs";

        const a = [];
        const b = [];
        const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
        await Promise.all([
          withConsoleCapture(a, async () => {
            console.log("a-one");
            await delay(20);
            console.log("a-two");
          }),
          withConsoleCapture(b, async () => {
            await delay(5);
            console.log("b-one");
            await delay(20);
            console.log("b-two");
          }),
        ]);
        console.log("outside");

        assert.deepEqual(a.map((entry) => entry.text), ["a-one", "a-two"]);
        assert.deepEqual(b.map((entry) => entry.text), ["b-one", "b-two"]);
        assert.equal(a.some((entry) => entry.text === "outside"), false);
        assert.equal(b.some((entry) => entry.text === "outside"), false);
        """
    )

    assert result.returncode == 0, result.stderr


def test_http_session_bootstrap_and_turn_idempotency_contract() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import os from "node:os";
        import path from "node:path";
        import fs from "node:fs/promises";

        delete process.env.SOCRATINK_LOOP_API_KEY;
        const { createFileSessionStore } = await import("./lib/loop-server/session-store.mjs");
        const { createLoopServerWithStore } = await import("./lib/loop-server/http-server.mjs");
        const root = await fs.mkdtemp(path.join(os.tmpdir(), "socratink-http-store-"));
        const store = createFileSessionStore({ rootDir: root });
        const createCalls = [];
        let turnAdvanceCount = 0;
        const createSession = async (options) => {
          createCalls.push(options);
          return {
            id: options.id,
            events: [...(options.events || [])],
            status: "awaiting_input",
            phase: "ignition",
            awaiting: null,
            transcript: [],
          };
        };
        const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
        const advance = async (session, text) => {
          if (text !== undefined) {
            turnAdvanceCount += 1;
            await delay(15);
            session.events.push({ type: "turn", text });
          } else {
            session.events.push({ type: "start" });
          }
          return {
            sessionId: session.id,
            status: session.status,
            phase: session.phase,
            awaiting: session.awaiting,
            transcript: [],
            events: session.events,
            marker: text ?? "start",
          };
        };
        const server = createLoopServerWithStore({ sessionStore: store, createSession, advance });
        await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
        const base = `http://127.0.0.1:${server.address().port}`;
        const post = (url, body) => fetch(`${base}${url}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        });

        try {
          const started = await post("/api/session", { sourceLessDoorBootstrap: true });
          assert.equal(started.status, 201);
          const startedBody = await started.json();
          assert.equal(startedBody.sessionVersion, 1);
          const sessionId = startedBody.sessionId;
          assert.equal(createCalls[0].sourceLessDoorBootstrap, true);
          assert.equal((await store.load(sessionId)).metadata.source_less_door_bootstrap, true);

          const defaulted = await post("/api/session", { sourceLessDoorBootstrap: "true" });
          assert.equal(defaulted.status, 201);
          assert.equal(createCalls[1].sourceLessDoorBootstrap, false);

          const requestId = "50000000-0000-4000-8000-000000000001";
          const missingRequestId = await post(`/api/session/${sessionId}/turn`, {
            text: "missing request id",
            expectedVersion: 1,
          });
          assert.equal(missingRequestId.status, 400);
          assert.equal((await missingRequestId.json()).code, "InvalidRequestId");
          const missingVersion = await post(`/api/session/${sessionId}/turn`, {
            text: "missing version",
            requestId: "50000000-0000-4000-8000-000000000099",
          });
          assert.equal(missingVersion.status, 400);
          assert.equal((await missingVersion.json()).code, "InvalidExpectedVersion");
          const stale = await post(`/api/session/${sessionId}/turn`, {
            text: "stale answer",
            requestId: "50000000-0000-4000-8000-000000000098",
            expectedVersion: 0,
          });
          assert.equal(stale.status, 409);
          const staleBody = await stale.json();
          assert.equal(staleBody.code, "SessionConflict");
          assert.equal(staleBody.currentVersion, 1);
          assert.equal(turnAdvanceCount, 0);
          assert.equal((await store.load(sessionId)).events.length, 1);

          const first = await post(`/api/session/${sessionId}/turn`, {
            text: "first answer",
            requestId,
            expectedVersion: 1,
          });
          assert.equal(first.status, 200);
          const firstBody = await first.json();
          assert.equal(firstBody.sessionVersion, 2);
          assert.equal(createCalls.at(-1).sourceLessDoorBootstrap, true);
          const advancesAfterFirst = turnAdvanceCount;

          const second = await post(`/api/session/${sessionId}/turn`, {
            text: "second answer",
            requestId: "50000000-0000-4000-8000-000000000002",
            expectedVersion: 2,
          });
          assert.equal(second.status, 200);
          assert.equal((await second.json()).sessionVersion, 3);
          assert.equal(turnAdvanceCount, advancesAfterFirst + 1);
          const advancesAfterSecond = turnAdvanceCount;

          const replay = await post(`/api/session/${sessionId}/turn`, {
            text: "first answer",
            requestId,
            expectedVersion: 1,
          });
          assert.equal(replay.status, 200);
          assert.deepEqual(await replay.json(), firstBody);
          assert.equal(turnAdvanceCount, advancesAfterSecond);

          const reused = await post(`/api/session/${sessionId}/turn`, {
            text: "different answer",
            requestId,
            expectedVersion: 1,
          });
          assert.equal(reused.status, 409);
          assert.equal((await reused.json()).code, "IdempotencyConflict");
          assert.equal(turnAdvanceCount, advancesAfterSecond);

          const raceStart = await post("/api/session", {});
          const raceId = (await raceStart.json()).sessionId;
          const raceRequest = "51000000-0000-4000-8000-000000000001";
          const sameRace = await Promise.all([
            post(`/api/session/${raceId}/turn`, {
              text: "same", requestId: raceRequest, expectedVersion: 1,
            }),
            post(`/api/session/${raceId}/turn`, {
              text: "same", requestId: raceRequest, expectedVersion: 1,
            }),
          ]);
          assert.deepEqual(sameRace.map((entry) => entry.status), [200, 200]);
          assert.deepEqual(await sameRace[0].json(), await sameRace[1].json());
          assert.equal((await store.load(raceId)).events.length, 2);

          const differentRace = await Promise.all([
            post(`/api/session/${raceId}/turn`, {
              text: "a",
              requestId: "52000000-0000-4000-8000-000000000001",
              expectedVersion: 2,
            }),
            post(`/api/session/${raceId}/turn`, {
              text: "b",
              requestId: "52000000-0000-4000-8000-000000000002",
              expectedVersion: 2,
            }),
          ]);
          assert.deepEqual(differentRace.map((entry) => entry.status).sort(), [200, 409]);
          assert.equal((await store.load(raceId)).events.length, 3);

          process.env.NODE_ENV = "production";
          try {
            const unsealedProductionApi = await post("/api/session", {});
            assert.equal(unsealedProductionApi.status, 503);
            assert.equal(
              (await unsealedProductionApi.json()).error,
              "loop_api_key_required",
            );
          } finally {
            delete process.env.NODE_ENV;
          }
        } finally {
          await new Promise((resolve) => server.close(resolve));
          await fs.rm(root, { recursive: true, force: true });
        }
        """
    )

    assert result.returncode == 0, result.stderr
