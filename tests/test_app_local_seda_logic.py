"""Logic contracts for app-local SEDA entry and session APIs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loop_backend_proxy import _MAX_LOOP_REQUEST_BODY_BYTES
from tests._helpers.node_runner import run_node_module


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_turn_size_helper_matches_proxy_and_serialized_utf8() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          MAX_SEDA_REQUEST_BODY_BYTES,
          createSedaTurnSubmission,
          sedaTurnRequestBodyBytes,
          sedaTurnTextFitsRequest,
        } from './public/js/ai_service.js';

        const requestId = '00000000-0000-4000-8000-000000000000';
        const expectedVersion = 1;
        const empty = createSedaTurnSubmission('', expectedVersion, requestId);
        const overhead = sedaTurnRequestBodyBytes(empty);
        const exactText = 'x'.repeat(MAX_SEDA_REQUEST_BODY_BYTES - overhead);

        assert.equal(
          sedaTurnRequestBodyBytes(
            createSedaTurnSubmission(exactText, expectedVersion, requestId),
          ),
          MAX_SEDA_REQUEST_BODY_BYTES,
        );
        assert.equal(sedaTurnTextFitsRequest(exactText, expectedVersion), true);
        assert.equal(sedaTurnTextFitsRequest(`${exactText}x`, expectedVersion), false);
        assert.ok(
          sedaTurnRequestBodyBytes(
            createSedaTurnSubmission('é', expectedVersion, requestId),
          ) > sedaTurnRequestBodyBytes(
            createSedaTurnSubmission('e', expectedVersion, requestId),
          ),
        );
        assert.ok(
          sedaTurnRequestBodyBytes(
            createSedaTurnSubmission('"', expectedVersion, requestId),
          ) > sedaTurnRequestBodyBytes(
            createSedaTurnSubmission('x', expectedVersion, requestId),
          ),
        );
        console.log(MAX_SEDA_REQUEST_BODY_BYTES);
        """
    )
    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) == _MAX_LOOP_REQUEST_BODY_BYTES


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_visible_prompt_strips_context_labels() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { visibleSedaPromptFromResponse } from './public/js/seda-visible-prompt.js';

        const prompt = visibleSedaPromptFromResponse({
          awaiting: { key: 'cold_attempt' },
          learnerTranscript: [
            {
              text: 'Concept: vaccines create immune memory Try your first explanation. Messy is fine.',
            },
            {
              text: 'Concept: vaccines create immune memory Learner goal: I want to explain why vaccines create immune memory. In your own words, why does a safe preview make the later response faster?',
            },
          ],
        });

        assert.equal(
          prompt,
          'Try your first explanation. Messy is fine.\\nIn your own words, why does a safe preview make the later response faster?'
        );
        assert.equal(prompt.includes('Concept:'), false);
        assert.equal(prompt.includes('Learner goal:'), false);

        const complete = visibleSedaPromptFromResponse({
          caseComplete: true,
          record: {
            derived: [{ nodes: { n1: { state: 'solidified' } } }],
          },
        });
        assert.equal(complete, 'Your attempt is on record. Study is ready.');
        assert.doesNotMatch(complete, /solidified|primed|complete/i);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_visible_prompt_drops_setup_log_lines() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { visibleSedaPromptFromResponse } from './public/js/seda-visible-prompt.js';

        const prompt = visibleSedaPromptFromResponse({
          awaiting: {
            key: 'cold_attempt',
            ctaText: 'In your own words, why does a safe preview make the later response faster?',
          },
          learnerTranscript: [
            { level: 'log', text: 'Concept: vaccines create immune memory' },
            { level: 'log', text: 'Learner goal: I want to explain why vaccines create immune memory.' },
          ],
        });

        assert.equal(
          prompt,
          'In your own words, why does a safe preview make the later response faster?'
        );
        assert.equal(prompt.includes('Concept:'), false);
        assert.equal(prompt.includes('Learner goal:'), false);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_surface_maps_outer_repair_bridge_and_transfer_beats() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { sedaSurfaceFromResponse } from './public/js/seda-visible-prompt.js';

        const events = [
          { type: 'cold_attempt', text: 'The query compares with keys.' },
          {
            type: 'gap_identified',
            repair_scaffold: { socratic_question: 'What turns that comparison into a weighted result?' },
          },
        ];
        const repair = sedaSurfaceFromResponse({
          events,
          awaiting: { key: 'repair', ctaText: 'What turns that comparison into a weighted result?' },
        });
        assert.equal(repair.mode, 'repair');
        assert.equal(repair.originalText, 'The query compares with keys.');
        assert.equal(repair.gapText, 'What turns that comparison into a weighted result?');

        const bridgeEvents = [...events, { type: 'repair', text: 'Similarity becomes a weight.' }, {
            type: 'model_bridge', text: 'Attention normalizes similarities into weights.'
          }];
        const ready = sedaSurfaceFromResponse({
          events: [...events, { type: 'repair', text: 'Similarity becomes a weight.' }],
          awaiting: { key: 'continue' },
        });
        assert.equal(ready.mode, 'repair-ready');
        assert.equal(ready.repairText, 'Similarity becomes a weight.');

        const bridge = sedaSurfaceFromResponse({
          events: bridgeEvents,
          awaiting: { key: 'run_gap_drill' },
        });
        assert.equal(bridge.mode, 'bridge');
        assert.equal(bridge.repairText, 'Similarity becomes a weight.');
        assert.equal(bridge.bridgeText, 'Attention normalizes similarities into weights.');

        assert.equal(sedaSurfaceFromResponse({
          events: bridgeEvents,
          awaiting: { key: 'gap_attempt' },
        }).mode, 'transfer');
        assert.equal(sedaSurfaceFromResponse({
          awaiting: { key: 'spaced_attempt' },
        }).mode, 'settle');

        const recovery = sedaSurfaceFromResponse({
          awaiting: {
            key: 'repair_recovery',
            ctaText: 'Name only the first cause you can see.',
          },
        });
        assert.equal(recovery.mode, 'recovery');
        assert.equal(recovery.prompt, 'Name only the first cause you can see.');

        const complete = sedaSurfaceFromResponse({
          caseComplete: true,
          awaiting: null,
        });
        assert.equal(complete.mode, 'complete');
        assert.deepEqual(complete.completionAction, { kind: 'study' });
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_auth_entry_session_redirect_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { requireAppEntrySession } from './public/js/auth.js';

        const warnings = [];
        console.warn = (...args) => warnings.push(args);

        const redirects = [];
        const redirected = await requireAppEntrySession({
          fetchSession: async () => null,
          redirect: () => redirects.push('login'),
          waitAfterRedirect: false,
        });
        assert.equal(redirected, false);
        assert.deepEqual(redirects, ['login']);

        redirects.length = 0;
        const blocked = requireAppEntrySession({
          fetchSession: async () => null,
          redirect: () => redirects.push('login'),
        });
        await Promise.resolve();
        assert.deepEqual(redirects, ['login']);
        blocked.then(
          () => assert.fail('default redirect path should stay blocked'),
          () => assert.fail('default redirect path should not reject')
        );

        redirects.length = 0;
        const afterFailure = await requireAppEntrySession({
          fetchSession: async () => { throw new Error('session failed'); },
          redirect: () => redirects.push('login'),
          waitAfterRedirect: false,
        });
        assert.equal(afterFailure, false);
        assert.equal(warnings.length, 1);
        assert.deepEqual(redirects, ['login']);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_session_client_uses_app_boundary() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          MAX_SEDA_REQUEST_BODY_BYTES,
          createSedaSession,
          createSedaTurnSubmission,
          getSedaSession,
          sedaTurnRequestBodyBytes,
          sendSedaTurn,
        } from './public/js/ai_service.js';

        const calls = [];
        globalThis.fetch = async (url, options = {}) => {
          calls.push({ url, options });
          return new Response(JSON.stringify({ sessionId: 'session-1' }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          });
        };

        await createSedaSession({ sourceLessDoorBootstrap: true });
        await createSedaSession({ northStarIntake: true });
        await getSedaSession('session/1');
        const firstSubmission = createSedaTurnSubmission('first attempt', 4);
        await sendSedaTurn('session/1', firstSubmission);
        await sendSedaTurn('session/1', firstSubmission);
        const nextSubmission = createSedaTurnSubmission('next attempt', 5);
        await sendSedaTurn('session/1', nextSubmission);

        assert.equal(calls[0].url, '/api/session');
        assert.equal(calls[0].options.method, 'POST');
        assert.deepEqual(JSON.parse(calls[0].options.body), { sourceLessDoorBootstrap: true });
        assert.deepEqual(JSON.parse(calls[1].options.body), { northStarIntake: true });
        assert.equal(calls[2].url, '/api/session/session%2F1');
        assert.equal(calls[2].options.method, 'GET');
        assert.equal(calls[3].url, '/api/session/session%2F1/turn');
        assert.equal(calls[3].options.method, 'POST');
        const firstBody = JSON.parse(calls[3].options.body);
        const retryBody = JSON.parse(calls[4].options.body);
        const nextBody = JSON.parse(calls[5].options.body);
        assert.match(firstBody.requestId, /^[0-9a-f-]{36}$/i);
        assert.deepEqual(firstBody, retryBody);
        assert.equal(firstBody.text, 'first attempt');
        assert.equal(firstBody.expectedVersion, 4);
        assert.equal(nextBody.text, 'next attempt');
        assert.equal(nextBody.expectedVersion, 5);
        assert.notEqual(nextBody.requestId, firstBody.requestId);
        assert.throws(
          () => sendSedaTurn('session/1', {
            text: 'bad id', requestId: 'not-a-uuid', expectedVersion: 5,
          }),
          /requestId UUID/,
        );
        assert.throws(
          () => createSedaTurnSubmission('bad version', -1),
          /expectedVersion/,
        );
        const sizeProbe = createSedaTurnSubmission(
          '',
          5,
          '00000000-0000-4000-8000-000000000000',
        );
        const oversizedText = 'x'.repeat(
          MAX_SEDA_REQUEST_BODY_BYTES - sedaTurnRequestBodyBytes(sizeProbe) + 1,
        );
        const callCountBeforeOversizedTurn = calls.length;
        assert.throws(
          () => sendSedaTurn('session/1', {
            ...sizeProbe,
            text: oversizedText,
          }),
          (error) => error.code === 'seda_turn_too_large',
        );
        assert.equal(calls.length, callCountBeforeOversizedTurn);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_http_session_accepts_blank_optional_learner_goal() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { createHttpPrompt } from './lib/loop-server/http-prompt.mjs';

        const session = {
          awaiting: { key: 'learner_goal' },
          pendingInput: '',
          events: [],
        };
        const value = await createHttpPrompt({
          cache: new Map(),
          askCounts: new Map(),
          session,
        }).ask('learner_goal', 'Learner goal (optional): ');

        assert.equal(value, '');
        assert.equal(session.pendingInput, null);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_door_bootstrap_routes_weak_nonempty_sketch_without_weakening_default_loop() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { handleSubstrateGate } from './lib/seda/handlers/substrate-gate.mjs';

        const agentLookup = new Map([['substrate_gate', {
          id: 'substrate_gate', name: 'Substrate gate', job: 'Judge substrate',
          required_outputs: [], may_propose_events: [], truth_permission: 'graph-neutral',
          failure_mode_to_guard: 'answer leakage',
        }]]);
        let bridgeCalls = 0;
        const bridge = {
          callBridgeResult: () => {
            bridgeCalls += 1;
            return ({
            ok: true,
            payload: {
              substrate_gate: {
                substrate_adequate: false,
                graph_neutral: true,
                score_eligible: false,
                classification: 'slow',
                seed_text: 'Name one starting link.',
                refinement_prompt: 'Add one link in your own words.',
              },
              llm_call: {},
            },
            });
          },
        };
        const ctx = {
          launchAttempt: 'I only remember that something stays behind.',
          concept: 'Immune memory', learnerGoal: '', agentLookup,
          section: (_kind, label) => label,
          composerCta: null,
        };
        let asks = 0;
        const prompt = { ask: async () => { asks += 1; throw new Error('refinement-required'); } };

        const bootstrapEvents = [];
        await handleSubstrateGate({
          events: bootstrapEvents, bridge, prompt, ctx: { ...ctx },
          options: { sourceLessDoorBootstrap: true },
        });
        assert.equal(asks, 0);
        assert.equal(bootstrapEvents.at(-1).type, 'substrate_confirmed');
        assert.equal(bootstrapEvents.at(-1).adequacy, 'minimal');
        assert.equal(bootstrapEvents.at(-1).graph_neutral, true);
        assert.equal(bootstrapEvents.at(-1).score_eligible, false);
        assert.equal(bridgeCalls, 0, 'Door bootstrap skips a duplicate substrate call');

        const defaultEvents = [];
        await assert.rejects(
          handleSubstrateGate({
            events: defaultEvents, bridge, prompt, ctx: { ...ctx }, options: {},
          }),
          /refinement-required/,
        );
        assert.equal(asks, 1);
        assert.equal(bridgeCalls, 1);
        assert.equal(defaultEvents.at(-1).type, 'substrate_seed_offered');
        assert.equal(defaultEvents.some((event) => event.type === 'substrate_confirmed'), false);

        const emptyEvents = [];
        await assert.rejects(
          handleSubstrateGate({
            events: emptyEvents, bridge, prompt,
            ctx: { ...ctx, launchAttempt: '   ' },
            options: { sourceLessDoorBootstrap: true },
          }),
          /refinement-required/,
        );
        assert.equal(asks, 2);
        assert.equal(bridgeCalls, 2);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_source_less_route_response_is_versioned_and_fails_closed() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { sessionResponse } from './lib/loop-server/session.mjs';
        import { validateRoutePayload } from './lib/seda/bridge-fail-closed.mjs';

        const route = {
          first_node: {
            id: 'c9_s1', label: 'Memory target', mechanism: 'Memory cells persist.',
            learner_prompt: 'Why is the later response faster?',
          },
          provisional_map: {
            metadata: { core_thesis: 'Memory changes a later response.' },
            backbone: [{ id: 'b9', principle: 'A retained change affects the next response.' }],
            clusters: [{ id: 'c9', subnodes: [{ id: 'c9_s1', label: 'Memory target' }] }],
          },
        };
        assert.equal(validateRoutePayload(route), null);
        assert.equal(
          validateRoutePayload({ ...route, first_node: { ...route.first_node, mechanism: '' } }),
          'missing first_node.mechanism',
        );
        assert.equal(
          validateRoutePayload({ ...route, first_node: { ...route.first_node, id: 9 } }),
          'missing first_node.id',
        );
        assert.equal(
          validateRoutePayload({ ...route, first_node: { ...route.first_node, label: true } }),
          'missing first_node.label',
        );
        assert.equal(
          validateRoutePayload({
            ...route,
            provisional_map: {
              ...route.provisional_map,
              clusters: [{ id: 'c9', subnodes: [{ id: 'different' }] }],
            },
          }),
          'first_node.id is absent from provisional_map',
        );

        const baseSession = {
          id: 'session-1', status: 'awaiting_input', phase: 'cold_attempt',
          awaiting: { key: 'cold_attempt', label: 'First question: ' },
          transcript: [], events: [], llmCalls: [], llm: null,
          bridgeDiagnosticsDir: null, record: null, ctx: { composerCta: null },
        };
        const ready = sessionResponse({
          ...baseSession,
          events: [
            { type: 'launch_attempt', text: 'My sketch.' },
            { type: 'route_generated', ...route },
          ],
        });
        assert.deepEqual(ready.sourceLessRoute, {
          contractVersion: 1,
          status: 'ready',
          firstNode: route.first_node,
          provisionalMap: route.provisional_map,
        });

        const unavailable = sessionResponse({
          ...baseSession,
          phase: 'idle', awaiting: { key: 'cmd', label: '> ' },
          events: [
            { type: 'launch_attempt', text: 'My sketch.' },
            { type: 'bridge_error', phase: 'route', action: 'generate-route' },
          ],
        });
        assert.equal(unavailable.sourceLessRoute.status, 'route_unavailable');
        assert.equal(unavailable.sourceLessRoute.code, 'route_unavailable');
        assert.equal(unavailable.sourceLessRoute.reason, 'generation_failed');
        assert.equal(unavailable.sourceLessRoute.contractVersion, 1);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_http_post_intake_and_get_rehydrate_preserve_exact_reconstruction() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import fs from 'node:fs/promises';
        import os from 'node:os';
        import path from 'node:path';
        import { randomUUID } from 'node:crypto';

        process.env.SOCRATINK_TUI_FAKE_LLM = '1';
        const [{ createLoopServerWithStore }, { createFileSessionStore }] = await Promise.all([
          import('./lib/loop-server/http-server.mjs'),
          import('./lib/loop-server/session-store.mjs'),
        ]);
        const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), 'socratink-route-contract-'));
        const store = createFileSessionStore({ rootDir });
        const server = createLoopServerWithStore({ sessionStore: store });
        await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
        const address = server.address();
        const base = `http://127.0.0.1:${address.port}`;
        const post = async (url, body) => {
          const response = await fetch(`${base}${url}`, {
            method: 'POST', headers: { 'content-type': 'application/json' },
            body: JSON.stringify(body),
          });
          const text = await response.text();
          assert.equal(response.ok, true, text);
          return JSON.parse(text);
        };

        try {
          const legacy = await post('/api/session', {});
          assert.equal(legacy.awaiting.key, 'cmd');
          const started = await post('/api/session', { northStarIntake: true });
          assert.equal(started.awaiting.key, 'source');
          const sessionId = started.sessionId;
          let expectedVersion = started.sessionVersion;
          const turn = async (text) => {
            const result = await post(`/api/session/${sessionId}/turn`, {
              text, requestId: randomUUID(), expectedVersion,
            });
            expectedVersion = result.sessionVersion;
            return result;
          };
          const source = 'Memory B cells persist after an initial exposure.';
          const target = 'Why does a second exposure trigger a faster response?';
          const attempt = 'The body remembers the pathogen and reacts sooner.';
          const repair = 'Memory B cells persist, recognize the pathogen, and expand quickly.';

          const sourced = await turn(source);
          assert.equal(sourced.awaiting.key, 'target');
          assert.equal(JSON.stringify(sourced).includes(source), false);
          assert.equal(Object.hasOwn(sourced.events[0], 'text'), false);

          const targeted = await turn(target);
          assert.equal(targeted.awaiting.key, 'initial_reconstruction');
          const reconstructed = await turn(attempt);
          assert.equal(reconstructed.awaiting.key, 'evaluate_reconstruction_gap');
          assert.equal(reconstructed.savedReconstruction.target, target);
          assert.equal(reconstructed.savedReconstruction.explanation, attempt);
          assert.equal(
            reconstructed.events.find(
              (event) => event.type === 'initial_reconstruction_submitted',
            ).text,
            attempt,
          );

          const evaluated = await turn('');
          assert.equal(evaluated.awaiting.key, 'initial_repair');
          assert.equal(evaluated.reconstructionRepair.status, 'ready');
          const repaired = await turn(repair);
          assert.equal(repaired.awaiting.key, 'initial_repair_saved');
          assert.equal(repaired.awaiting.readOnly, true);
          assert.equal(repaired.reconstructionRepair.status, 'saved');
          assert.equal(repaired.reconstructionRepair.repair, repair);

          const rehydratedResponse = await fetch(`${base}/api/session/${sessionId}`);
          const rehydratedText = await rehydratedResponse.text();
          assert.equal(rehydratedResponse.ok, true, rehydratedText);
          const rehydrated = JSON.parse(rehydratedText);
          assert.equal(rehydrated.awaiting.key, 'initial_repair_saved');
          assert.deepEqual(rehydrated.savedReconstruction, repaired.savedReconstruction);
          assert.deepEqual(rehydrated.reconstructionRepair, repaired.reconstructionRepair);
          assert.equal(JSON.stringify(rehydrated).includes(source), false);
          assert.equal(
            rehydrated.events.find(
              (event) => event.type === 'initial_reconstruction_submitted',
            ).text,
            attempt,
          );
          const stored = await store.load(sessionId);
          assert.equal(stored.events[0].text, source);
          assert.equal(
            stored.events.find(
              (event) => event.type === 'initial_reconstruction_submitted',
            ).text,
            attempt,
          );
        } finally {
          await new Promise((resolve) => server.close(resolve));
          await fs.rm(rootDir, { recursive: true, force: true });
        }
        """
    )
    assert result.returncode == 0, result.stderr
