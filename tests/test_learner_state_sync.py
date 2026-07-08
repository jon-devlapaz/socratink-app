"""Learner-state merge + Linear-style due desk surfaces."""

from __future__ import annotations

import shutil

import pytest

from tests._helpers.node_runner import run_node_module


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_merge_learner_state_unions_evidence_without_dropping_attempts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { mergeLearnerState } from './public/js/learner-state-sync.js';

        const local = {
          concepts: [{ id: 'c1', name: 'Local', updated_at: '2026-07-08T12:00:00.000Z' }],
          training: {
            c1: {
              concept_id: 'c1',
              schema_version: 1,
              grounding: 'ungrounded',
              node_records: {
                n1: {
                  attempts: [{
                    id: 'a-local',
                    at: '2026-07-08T10:00:00.000Z',
                    user_text: 'local attempt',
                    classification: 'strong',
                    gaps: [],
                    grader_version: 'test',
                  }],
                  repairs: [],
                  study_revealed_at: '2026-07-08T10:05:00.000Z',
                },
              },
            },
          },
        };

        const remote = {
          concepts: [{ id: 'c1', name: 'Remote', updated_at: '2026-07-07T12:00:00.000Z' }, { id: 'c2', name: 'Only remote' }],
          training: {
            c1: {
              concept_id: 'c1',
              schema_version: 1,
              grounding: 'ungrounded',
              node_records: {
                n1: {
                  attempts: [{
                    id: 'a-remote',
                    at: '2026-07-07T10:00:00.000Z',
                    user_text: 'remote attempt',
                    classification: 'partial',
                    gaps: [],
                    grader_version: 'test',
                  }],
                  repairs: [],
                  study_revealed_at: '2026-07-07T10:05:00.000Z',
                },
              },
            },
          },
        };

        const merged = mergeLearnerState(local, remote);
        assert.equal(merged.concepts.length, 2);
        assert.equal(merged.concepts.find((c) => c.id === 'c1').name, 'Local');
        assert.equal(merged.training.c1.node_records.n1.attempts.length, 2);
        assert.equal(merged.training.c1.node_records.n1.study_revealed_at, '2026-07-07T10:05:00.000Z');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_list_due_for_spaced_and_linear_desk_surfaces() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          listDueForSpaced,
          dueConceptIdSet,
          dueItemsForConcept,
          renderReadyFilterHtml,
          renderDueSelectionHtml,
        } from './public/js/due-for-spaced.js';

        const concepts = [{
          id: 'c1',
          name: 'Thermostat',
          graphData: JSON.stringify({
            metadata: { id: 'core', label: 'Feedback loop' },
            backbone: [{ id: 'sensor', label: 'Sensor reading' }],
            clusters: [],
          }),
        }];

        const trainingByConceptId = {
          c1: {
            concept_id: 'c1',
            node_records: {
              core: {
                attempts: [{
                  id: 'a1',
                  at: '2026-07-07T00:00:00.000Z',
                  user_text: 'strong cold',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [],
                study_revealed_at: '2026-07-07T00:10:00.000Z',
              },
              sensor: {
                attempts: [{
                  id: 'a2',
                  at: '2026-07-07T01:00:00.000Z',
                  user_text: 'strong sensor',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [],
                study_revealed_at: '2026-07-07T01:10:00.000Z',
              },
            },
          },
        };

        const notDue = listDueForSpaced({
          concepts,
          trainingByConceptId,
          now: '2026-07-07T10:00:00.000Z',
        });
        assert.equal(notDue.length, 0);

        const due = listDueForSpaced({
          concepts,
          trainingByConceptId,
          now: '2026-07-08T00:00:00.000Z',
        });
        assert.equal(due.length, 2);
        assert.equal(due[0].node_id, 'core');
        assert.deepEqual([...dueConceptIdSet(due)], ['c1']);
        assert.equal(dueItemsForConcept(due, 'c1').length, 2);

        const filter = renderReadyFilterHtml({ count: 2, active: true });
        assert.match(filter, /desk-ready-filter/);
        assert.match(filter, /Ready/);
        assert.match(filter, /is-active/);
        assert.equal(renderReadyFilterHtml({ count: 0 }), '');

        const selection = renderDueSelectionHtml(dueItemsForConcept(due, 'c1'));
        assert.match(selection, /Feedback loop/);
        assert.match(selection, /Up next from memory/);
        assert.match(selection, />\\s*Reconstruct\\s*</);
        assert.match(selection, /2 nodes ready · oldest first/);
        assert.doesNotMatch(selection, /due-for-spaced__list/);
        assert.doesNotMatch(selection, /Reconstruct from memory/);
        assert.doesNotMatch(selection, />RECONSTRUCT</);
        """
    )
    assert result.returncode == 0, result.stderr
