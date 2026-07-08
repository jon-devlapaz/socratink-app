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
