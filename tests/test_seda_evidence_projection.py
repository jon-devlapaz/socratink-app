"""Contract for projecting completed SEDA records into visible evidence.

Product truth: the SEDA loop simulates spacing with fixed timestamps
(lib/seda/constants.mjs). Projection must re-stamp attempts to real time and
re-key them to the frontend node id, so a single sitting derives at most
`primed` and never `solidified`.
"""

from __future__ import annotations

import shutil

import pytest

from tests._helpers.node_runner import run_node_module


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_projection_restamps_and_rekeys_to_frontend_node() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectCompletedSedaRecord } from './public/js/seda-evidence-projection.js';

        const now = '2026-07-07T21:00:00.000Z';
        const next = projectCompletedSedaRecord({
          training: null,
          conceptId: 'frontend-concept',
          nodeId: 'frontend-node',
          sessionId: 'sess-1',
          now,
          record: {
            concept_id: 'backend-slug',
            training: {
              node_records: {
                'backend-node': {
                  attempts: [
                    { id: 'cold-1', at: '2026-05-15T10:00:00.000Z', user_text: 'first', classification: 'strong', gaps: [], grader_version: 'tui', kind: 'cold' },
                    { id: 'spaced-1', at: '2026-05-16T06:00:00.000Z', user_text: 'second', classification: 'strong', gaps: [], grader_version: 'tui', kind: 'spaced' },
                  ],
                  repairs: [],
                },
              },
            },
          },
        });

        assert.equal(next.concept_id, 'frontend-concept');
        const record = next.node_records['frontend-node'];
        assert.ok(record, 're-keyed to frontend node id');
        assert.equal(Object.keys(next.node_records).length, 1);
        assert.equal(record.attempts.length, 2);
        assert.equal(record.attempts[0].user_text, 'first');
        // Backend simulated timestamps must be discarded for real wall-clock time.
        assert.equal(record.attempts[0].at, now);
        assert.equal(record.attempts[1].at, now);
        assert.equal(record.attempts[0].classification, 'strong');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_projected_single_sitting_derives_primed_not_solidified() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectCompletedSedaRecord } from './public/js/seda-evidence-projection.js';
        import { deriveNodeTraining } from './public/js/training-derive.js';

        const now = '2026-07-07T21:00:00.000Z';
        const next = projectCompletedSedaRecord({
          training: null,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-1',
          now,
          record: {
            training: {
              node_records: {
                'backend-node': {
                  attempts: [
                    { id: 'cold-1', at: '2026-05-15T10:00:00.000Z', user_text: 'a', classification: 'strong', gaps: [], grader_version: 'tui', kind: 'cold' },
                    { id: 'spaced-1', at: '2026-05-16T06:00:00.000Z', user_text: 'b', classification: 'strong', gaps: [], grader_version: 'tui', kind: 'spaced' },
                  ],
                  repairs: [],
                },
              },
            },
          },
        });

        const derived = deriveNodeTraining(next.node_records['n'], { now });
        assert.notEqual(derived.state, 'solidified', 'single sitting must not solidify');
        assert.equal(derived.state, 'primed');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_projection_is_idempotent_per_session() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectCompletedSedaRecord } from './public/js/seda-evidence-projection.js';

        const record = {
          training: {
            node_records: {
              'backend-node': {
                attempts: [
                  { id: 'cold-1', at: '2026-05-15T10:00:00.000Z', user_text: 'a', classification: 'strong', gaps: [], grader_version: 'tui', kind: 'cold' },
                ],
                repairs: [],
              },
            },
          },
        };

        const first = projectCompletedSedaRecord({
          training: null, conceptId: 'c', nodeId: 'n', sessionId: 'sess-1', now: '2026-07-07T21:00:00.000Z', record,
        });
        const second = projectCompletedSedaRecord({
          training: first, conceptId: 'c', nodeId: 'n', sessionId: 'sess-1', now: '2026-07-07T21:05:00.000Z', record,
        });
        assert.equal(second, null, 'same session must not re-project');
        assert.equal(first.node_records['n'].attempts.length, 1);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_latest_seda_attempt_event_projects_before_case_complete() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectLatestSedaAttemptEvent } from './public/js/seda-evidence-projection.js';

        const first = projectLatestSedaAttemptEvent({
          training: null,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-1',
          now: '2026-07-09T05:00:00.000Z',
          data: {
            caseComplete: false,
            events: [{
              type: 'cold_attempt',
              text: 'I think queries compare against keys.',
              evaluation: {
                classification: 'solid',
                gaps: [],
                grader_version: 'seda-test',
              },
            }],
          },
        });
        const record = first.node_records.n;
        assert.equal(record.attempts.length, 1);
        assert.equal(record.attempts[0].id, 'seda-sess-1-event-0');
        assert.equal(record.attempts[0].classification, 'strong');
        assert.equal(record.attempts[0].kind, 'cold');
        assert.equal(record.attempts[0].at, '2026-07-09T05:00:00.000Z');
        assert.equal(record.study_revealed_at, undefined);

        const repeat = projectLatestSedaAttemptEvent({
          training: first,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-1',
          data: {
            events: [{
              type: 'cold_attempt',
              text: 'I think queries compare against keys.',
              evaluation: { classification: 'solid', gaps: [] },
            }],
          },
        });
        assert.equal(repeat, null, 'same event must not duplicate attempts');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_progress_projects_reveal_and_repair_but_not_transfer() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectLatestSedaAttemptEvent } from './public/js/seda-evidence-projection.js';

        const data = { events: [
          {
            type: 'cold_attempt',
            text: 'The query compares with keys.',
            evaluation: { classification: 'shallow', gap_description: 'Explain the weighting.' },
          },
          { type: 'gap_identified', graph_neutral: true },
          { type: 'repair_dialogue_turn', text: 'Similarity becomes a weight.', graph_neutral: true },
          { type: 'repair', text: 'Similarity becomes a normalized weight.', graph_neutral: true },
          { type: 'model_bridge', text: 'Similarities are normalized into weights.', graph_neutral: true },
          {
            type: 'post_bridge_transfer_check',
            text: 'The weights select relevant values.',
            graph_neutral: true,
            score_eligible: false,
          },
        ] };
        const projected = projectLatestSedaAttemptEvent({
          training: null,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-nested',
          now: '2026-07-15T12:00:00.000Z',
          data,
        });
        const record = projected.node_records.n;
        assert.equal(record.attempts.length, 1);
        assert.equal(record.study_revealed_at, '2026-07-15T12:00:00.000Z');
        assert.deepEqual(record.repairs.map(({ text }) => text), [
          'Similarity becomes a normalized weight.',
        ]);
        assert.equal(
          record.attempts.some((attempt) => attempt.user_text === 'The weights select relevant values.'),
          false,
          'graph-neutral transfer must not become mastery evidence',
        );
        assert.equal(projectLatestSedaAttemptEvent({
          training: projected,
          conceptId: 'c', nodeId: 'n', sessionId: 'sess-nested', data,
        }), null, 'same progress must be idempotent');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_completed_record_reconciles_early_cold_event_without_duplicate() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          projectCompletedSedaRecord,
          projectLatestSedaAttemptEvent,
        } from './public/js/seda-evidence-projection.js';
        import { deriveNodeTraining } from './public/js/training-derive.js';

        const early = projectLatestSedaAttemptEvent({
          training: null,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-1',
          now: '2026-07-09T05:00:00.000Z',
          data: { events: [{
            type: 'cold_attempt',
            text: 'Memory cells remain after exposure.',
            evaluation: { classification: 'solid', gaps: [] },
          }] },
        });
        const completedRecord = {
          training: { node_records: { backend: {
            attempts: [
              {
                user_text: 'Memory cells remain after exposure.',
                classification: 'strong', gaps: [], grader_version: 'seda',
              },
              {
                user_text: 'They respond faster on re-exposure.',
                classification: 'strong', gaps: [], grader_version: 'seda',
              },
            ],
            repairs: [],
          } } },
        };
        const reconciled = projectCompletedSedaRecord({
          training: early,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-1',
          now: '2026-07-09T05:05:00.000Z',
          record: completedRecord,
        });

        const attempts = reconciled.node_records.n.attempts;
        assert.equal(attempts.length, 2);
        assert.deepEqual(
          attempts.map((attempt) => attempt.id),
          ['seda-sess-1-0', 'seda-sess-1-1'],
        );
        assert.equal(
          attempts.filter((attempt) => attempt.user_text === 'Memory cells remain after exposure.').length,
          1,
        );
        assert.notEqual(
          deriveNodeTraining(reconciled.node_records.n, {
            now: '2026-07-09T05:05:00.000Z',
          }).state,
          'solidified',
        );
        assert.equal(projectCompletedSedaRecord({
          training: reconciled,
          conceptId: 'c', nodeId: 'n', sessionId: 'sess-1',
          record: completedRecord,
        }), null);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_shallow_early_attempt_matches_completed_classification_and_gap() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          projectCompletedSedaRecord,
          projectLatestSedaAttemptEvent,
        } from './public/js/seda-evidence-projection.js';
        import { deriveNodeTraining } from './public/js/training-derive.js';

        const gap = 'Name why the retained cells can respond sooner.';
        const early = projectLatestSedaAttemptEvent({
          training: null,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-shallow',
          now: '2026-07-09T05:00:00.000Z',
          data: { events: [{
            type: 'cold_attempt',
            text: 'Something remains after exposure.',
            evaluation: {
              classification: 'shallow',
              gap_description: gap,
              grader_version: 'seda',
            },
          }] },
        });
        const earlyAttempt = early.node_records.n.attempts[0];
        assert.equal(earlyAttempt.classification, 'partial');
        assert.deepEqual(earlyAttempt.gaps, [{
          mechanism: 'target mechanism', correction: gap,
        }]);
        assert.equal(
          deriveNodeTraining(early.node_records.n, {
            now: '2026-07-09T05:00:00.000Z',
          }).state,
          'primed',
        );

        const completed = projectCompletedSedaRecord({
          training: early,
          conceptId: 'c',
          nodeId: 'n',
          sessionId: 'sess-shallow',
          now: '2026-07-09T05:05:00.000Z',
          record: { training: { node_records: { backend: {
            attempts: [{
              user_text: 'Something remains after exposure.',
              classification: 'partial',
              gaps: [{ mechanism: 'target mechanism', correction: gap }],
              grader_version: 'seda',
            }],
            repairs: [],
          } } } },
        });
        const completedAttempt = completed.node_records.n.attempts[0];
        assert.equal(completedAttempt.classification, earlyAttempt.classification);
        assert.deepEqual(completedAttempt.gaps, earlyAttempt.gaps);
        assert.equal(
          deriveNodeTraining(completed.node_records.n, {
            now: '2026-07-09T05:05:00.000Z',
          }).state,
          'primed',
        );
        """
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_projection_returns_null_without_completed_record() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { projectCompletedSedaRecord } from './public/js/seda-evidence-projection.js';

        assert.equal(projectCompletedSedaRecord({ conceptId: 'c', nodeId: 'n', sessionId: 's', record: null }), null);
        assert.equal(projectCompletedSedaRecord({ conceptId: 'c', nodeId: 'n', sessionId: 's', record: { training: { node_records: {} } } }), null);
        assert.equal(projectCompletedSedaRecord({ conceptId: '', nodeId: 'n', sessionId: 's', record: { training: { node_records: { x: { attempts: [{}] } } } } }), null);
        """
    )
    assert result.returncode == 0, result.stderr
