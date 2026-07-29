"""Logic contracts for JavaScript application modules."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests._helpers.node_runner import run_node_module

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_REQUIRED = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node not on PATH",
)


@NODE_REQUIRED
def test_drill_verdict_logic_keeps_seda_transitions_specific() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          nextSedaPromptAfterVerdict,
          verdictCopy,
        } from './public/js/drill-verdict.js';

        const duplicateFallback = nextSedaPromptAfterVerdict(
          'Same question?',
          'Same question?',
          'I guessed with my own words.'
        );
        assert.equal(
          duplicateFallback,
          'You wrote: «I guessed with my own words.». Now: name the missing link in one sentence.'
        );
        assert.notEqual(duplicateFallback, 'Same question?');
        assert.equal(
          nextSedaPromptAfterVerdict(
            'Explain the mechanism.',
            'Same question?',
            'My rough answer.'
          ),
          'You wrote: «My rough answer.». Now: Explain the mechanism.'
        );

        const partialVerdict = verdictCopy({
          classification: 'partial',
          userText: 'The query compares with keys.',
        });
        assert.match(partialVerdict, /Checked • Partly there •/);
        assert.doesNotMatch(partialVerdict, /partial/i);
        assert.match(partialVerdict, /Study will target the missing link\\./);

        const unsafeFeedback = verdictCopy({
          classification: 'partial',
          userText: 'A rough answer.',
          specificFeedback: 'Classification: shallow. Score 2.',
        });
        assert.doesNotMatch(
          unsafeFeedback,
          /Classification|shallow|Score 2/i
        );

        assert.equal(
          verdictCopy({
            userText: 'The query compares with keys.',
            sedaComplete: true,
          }),
          'Checked • Recorded • Your attempt is on record. • Study is ready.'
        );
        assert.equal(
          verdictCopy({
            userText: 'I need one more cue.',
            recordable: false,
          }),
          'Response received • Keep going • Your line: “I need one more cue.” • Use the next question to add one cause-and-effect link.'
        );
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_html_escape_logic_handles_untrusted_values() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { escHtml } from './public/js/html.js';

        assert.equal(escHtml(`<&>"'`), '&lt;&amp;&gt;&quot;&#39;');
        assert.equal(escHtml(null), '');
        assert.equal(escHtml(42), '42');
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_countdown_timer_logic_preserves_time_and_completion() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          createCountdownTimer,
          formatTimerSeconds,
        } from './public/js/app-timer.js';

        assert.equal(formatTimerSeconds(24 * 60 * 60), '24:00:00');
        assert.equal(formatTimerSeconds(3661), '01:01:01');
        assert.equal(formatTimerSeconds(3), '00:00:03');

        let intervalCallback = null;
        const cleared = [];
        const completions = [];
        const output = { textContent: '' };
        const timer = createCountdownTimer({
          timerDisplay: output,
          initialSeconds: 10,
          onComplete() {
            completions.push(timer.getTimeLeft());
          },
          setIntervalRef(callback, delay) {
            intervalCallback = callback;
            assert.equal(delay, 1000);
            return 'interval-1';
          },
          clearIntervalRef(intervalId) {
            cleared.push(intervalId);
          },
        });

        timer.start(2);
        assert.equal(timer.getTimeLeft(), 2);
        intervalCallback();
        assert.equal(timer.getTimeLeft(), 1);
        intervalCallback();
        assert.equal(timer.getTimeLeft(), 0);
        assert.deepEqual(completions, [0]);
        assert.deepEqual(cleared, [null, 'interval-1']);
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_launch_input_logic_normalizes_goal_and_topic_shapes() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          buildPendingShellFromDoorInput,
        } from './public/js/launch-pad.js';

        const goalShell = buildPendingShellFromDoorInput(
          ' I want to understand why sodium rushing into a neuron starts an electrical signal. '
        );
        assert.equal(
          goalShell.name,
          'sodium rushing into a neuron starts an electrical signal'
        );
        assert.equal(
          goalShell.goal,
          'I want to understand why sodium rushing into a neuron starts an electrical signal.'
        );

        const topicShell = buildPendingShellFromDoorInput(
          'How sodium channels create an action potential'
        );
        assert.equal(
          topicShell.name,
          'How sodium channels create an action potential'
        );
        assert.equal(topicShell.goal, '');
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_concept_create_logic_sends_learner_goal() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { submitConceptCreate } from './public/js/ai_service.js';

        let capturedBody = null;
        globalThis.fetch = async (_url, options) => {
          capturedBody = JSON.parse(options.body);
          return new Response(JSON.stringify({ provisional_map: {} }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          });
        };

        await submitConceptCreate({
          name: 'Sodium channels',
          learnerGoal: 'I want to explain why sodium starts the signal.',
          startingSketch: 'sodium moves into the neuron and starts a signal somehow',
          source: null,
        });

        assert.equal(capturedBody.name, 'Sodium channels');
        assert.equal(
          capturedBody.learner_goal,
          'I want to explain why sodium starts the signal.'
        );
        assert.equal(
          capturedBody.starting_sketch,
          'sodium moves into the neuron and starts a signal somehow'
        );
        assert.equal(capturedBody.source, null);
        """
    )
    assert result.returncode == 0, result.stderr


def test_frontend_ai_calls_do_not_forward_browser_gemini_key() -> None:
    for rel_path in (
        "public/js/ai_service.js",
        "public/js/app.js",
        "public/js/launch-pad.js",
    ):
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "gemini_key" not in text, rel_path


@NODE_REQUIRED
def test_phase_b_session_logic_preserves_storage_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          getDefaultPhaseBSessionState,
          getPhaseBSessionStorageKey,
          loadPhaseBSessionState,
          persistPhaseBResumeState,
          persistPhaseBSessionState,
          loadPhaseBResumeState,
        } from './public/js/phase-b-session.js';

        const backing = new Map();
        const storage = {
          getItem(key) {
            return backing.has(key) ? backing.get(key) : null;
          },
          setItem(key, value) {
            backing.set(key, String(value));
          },
          removeItem(key) {
            backing.delete(key);
          },
        };

        assert.deepEqual(getDefaultPhaseBSessionState(), {
          startedAt: null,
          nodesDrilled: 0,
          visitedNodeIds: [],
          retriesByNode: {},
          events: [],
        });
        assert.equal(
          getPhaseBSessionStorageKey('concept-1'),
          'learnops-phase-b-session:concept-1'
        );

        persistPhaseBSessionState(
          {
            startedAt: '2026-05-13T10:00:00.000Z',
            nodesDrilled: 99,
            visitedNodeIds: ['a', '', 'b'],
            retriesByNode: { a: 1 },
            events: [{ type: 'study' }],
          },
          { conceptId: 'concept-1', storage }
        );
        assert.deepEqual(
          loadPhaseBSessionState({ conceptId: 'concept-1', storage }),
          {
            startedAt: '2026-05-13T10:00:00.000Z',
            nodesDrilled: 2,
            visitedNodeIds: ['a', 'b'],
            retriesByNode: { a: 1 },
            events: [{ type: 'study' }],
          }
        );

        persistPhaseBResumeState(
          { conceptId: 'c', nodeId: 'n', mode: 'study' },
          { storage }
        );
        assert.deepEqual(
          loadPhaseBResumeState({ storage }),
          { conceptId: 'c', nodeId: 'n', mode: 'study' }
        );
        persistPhaseBResumeState(null, { storage });
        assert.equal(loadPhaseBResumeState({ storage }), null);
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_concept_entry_logic_derives_route_progression() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveConceptEntryViewState,
          deriveConceptEntries,
        } from './public/js/concept-page-view.js';

        const entries = deriveConceptEntries({
          clusters: [{
            id: 'c1',
            label: 'Mechanism cluster',
            subnodes: [
              { id: 'gate', label: 'Sodium gate' },
              { id: 'spread', label: 'Signal spread' },
            ],
          }],
        });
        assert.deepEqual(entries.map((entry) => entry.id), ['gate', 'spread']);
        assert.deepEqual(deriveConceptEntryViewState(entries, 0, null), {
          id: 'gate',
          attempted: false,
          state: 'ready to reconstruct',
          nextAction: 'cold_attempt',
        });
        assert.deepEqual(deriveConceptEntryViewState(entries, 1, null), {
          id: 'spread',
          attempted: false,
          state: 'locked',
          nextAction: null,
        });
        assert.equal(
          deriveConceptEntryViewState(entries, 0, {
            node_records: {
              gate: {
                attempts: [{
                  at: '2026-05-21T00:00:00Z',
                  classification: 'partial',
                }],
              },
            },
          }).state,
          'primed'
        );
        """
    )
    assert result.returncode == 0, result.stderr


@NODE_REQUIRED
def test_source_less_progression_logic_preserves_comparison_seams() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveSourceLessViewMode,
        } from './public/js/concept-page-view.js';

        assert.equal(deriveSourceLessViewMode({
          attempted: false,
          record: null,
          next_action: 'cold_attempt',
        }), 'cold-surface');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'study',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            repairs: [],
          },
        }), 'saved-draft-study-gate');

        const revealed = {
          attempted: true,
          next_action: 'repair',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            study_revealed_at: '2026-05-21T10:05:00.000Z',
            repairs: [],
          },
        };
        assert.equal(
          deriveSourceLessViewMode(
            revealed,
            { comparisonAcknowledged: false }
          ),
          'post-reveal-comparison'
        );
        assert.equal(
          deriveSourceLessViewMode(
            revealed,
            { comparisonAcknowledged: true }
          ),
          'expanded-workspace'
        );
        """
    )
    assert result.returncode == 0, result.stderr
