"""Learner-state merge and spaced-reconstruction logic."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests._helpers.node_runner import run_node_module

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_merge_learner_state_unions_evidence_without_dropping_attempts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          mergeLearnerState,
          mergeTrainingRecords,
        } from './public/js/learner-state-sync.js';

        const checkedOnlyLocally = mergeTrainingRecords(
          { concept_id: 'checked', node_records: { n1: { repair_checked_at: '2026-07-08T11:00:00.000Z' } } },
          { concept_id: 'checked', node_records: { n1: {} } },
        );
        assert.equal(
          checkedOnlyLocally.node_records.n1.repair_checked_at,
          '2026-07-08T11:00:00.000Z',
        );

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
def test_identified_hydration_preserves_repair_check_round_trip() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          CONCEPTS_STORE_KEY,
          hydrateAndSyncLearnerState,
        } from './public/js/learner-state-sync.js';

        const trainingKey = 'socratink:training:v1:c1';
        const checkedAt = '2026-07-08T10:20:00.000Z';
        const mem = new Map([
          [CONCEPTS_STORE_KEY, JSON.stringify([{ id: 'c1', name: 'Local concept' }])],
          [trainingKey, JSON.stringify({
            concept_id: 'c1',
            schema_version: 1,
            grounding: 'ungrounded',
            node_records: {
              n1: {
                attempts: [{
                  id: 'a1',
                  at: '2026-07-08T10:00:00.000Z',
                  user_text: 'local attempt',
                  classification: 'partial',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [{
                  id: 'r1',
                  at: '2026-07-08T10:10:00.000Z',
                  text: 'local repair',
                }],
                study_revealed_at: '2026-07-08T10:05:00.000Z',
                repair_checked_at: checkedAt,
              },
            },
          })],
        ]);
        const storage = {
          getItem(key) { return mem.has(key) ? mem.get(key) : null; },
          setItem(key, value) { mem.set(key, String(value)); },
          key(index) { return [...mem.keys()][index] || null; },
          get length() { return mem.size; },
        };

        let remote = {
          concepts: [{ id: 'c1', name: 'Remote concept' }],
          training: {
            c1: {
              concept_id: 'c1',
              schema_version: 1,
              grounding: 'ungrounded',
              node_records: {
                n1: {
                  attempts: [],
                  repairs: [],
                  study_revealed_at: null,
                },
              },
            },
          },
        };
        const fetchImpl = async (_url, options = {}) => {
          if (!options.method || options.method === 'GET') {
            return { status: 200, ok: true, async json() { return remote; } };
          }
          remote = JSON.parse(options.body);
          return { status: 200, ok: true, async json() { return remote; } };
        };

        const first = await hydrateAndSyncLearnerState({
          storage,
          fetchImpl,
          isIdentified: true,
        });
        assert.equal(first.state.training.c1.node_records.n1.repair_checked_at, checkedAt);
        assert.equal(JSON.parse(mem.get(trainingKey)).node_records.n1.repair_checked_at, checkedAt);
        assert.equal(remote.training.c1.node_records.n1.repair_checked_at, checkedAt);

        const second = await hydrateAndSyncLearnerState({
          storage,
          fetchImpl,
          isIdentified: true,
        });
        assert.equal(second.state.training.c1.node_records.n1.repair_checked_at, checkedAt);
        """
    )
    assert result.returncode == 0, result.stderr


def test_evidence_writes_schedule_identified_state_push() -> None:
    app_js = (REPO_ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
    for method in (
        "appendAttempt",
        "setStudyRevealed",
        "appendRepair",
        "saveTraining",
        "markRepairChecked",
    ):
        start = app_js.index(f"trainingStore.{method} = async")
        end = app_js.index("\n  };", start)
        assert "scheduleLearnerStatePush();" in app_js[start:end], method


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_list_due_for_spaced_logic() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          listDueForSpaced,
          dueConceptIdSet,
          dueItemsForConcept,
          collectDrillableNodeIds,
        } from './public/js/due-for-spaced.js';
        import { parseConceptGraphData } from './public/js/concept-status.js';

        const objectGraphData = { backbone: [], clusters: [] };
        assert.deepEqual(parseConceptGraphData({ graphData: JSON.stringify(objectGraphData) }), objectGraphData);
        assert.equal(parseConceptGraphData({ graphData: objectGraphData }), objectGraphData);
        assert.equal(parseConceptGraphData({ graphData: '{not-json' }), null);
        assert.equal(parseConceptGraphData({}), null);

        const concepts = [{
          id: 'c1',
          name: 'Thermostat',
          graphData: JSON.stringify({
            metadata: { id: 'core', label: 'Feedback loop' },
            backbone: [
              { id: 'sensor', label: 'Sensor reading' },
              { id: 'actuator', label: 'Actuator' },
            ],
            clusters: [],
          }),
        }];

        const trainingByConceptId = {
          c1: {
            concept_id: 'c1',
            node_records: {
              // metadata.id is not a route entry — must not appear as due.
              core: {
                attempts: [{
                  id: 'a0',
                  at: '2026-07-06T00:00:00.000Z',
                  user_text: 'strong core',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [],
                study_revealed_at: '2026-07-06T00:10:00.000Z',
              },
              sensor: {
                attempts: [{
                  id: 'a1',
                  at: '2026-07-07T00:00:00.000Z',
                  user_text: 'strong sensor',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [],
                study_revealed_at: '2026-07-07T00:10:00.000Z',
              },
              actuator: {
                attempts: [{
                  id: 'a2',
                  at: '2026-07-07T01:00:00.000Z',
                  user_text: 'strong actuator',
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
        assert.equal(due[0].node_id, 'sensor');
        assert.equal(due[0].node_label, 'Sensor reading');
        assert.deepEqual([...dueConceptIdSet(due)], ['c1']);
        assert.equal(dueItemsForConcept(due, 'c1').length, 2);
        assert.ok(!due.some((item) => item.node_id === 'core'));

        // Scaffolded clusters win over backbone when deriving drillable IDs.
        const clusterGraph = {
          metadata: { id: 'core', label: 'Core' },
          backbone: [{ id: 'bb1', label: 'Backbone only' }],
          clusters: [{
            id: 'cl1',
            label: 'Cluster',
            subnodes: [{
              id: 'sn1',
              label: 'Subnode one',
              learner_scaffold: { task_label: 'Subnode one', task_cue: 'cue' },
            }],
          }],
        };
        assert.deepEqual(collectDrillableNodeIds(clusterGraph), ['sn1']);
        assert.deepEqual(
          collectDrillableNodeIds({
            metadata: { id: 'core' },
            backbone: [{ id: 'bb1', label: 'Backbone' }],
            clusters: [{ id: 'cl1', subnodes: [{ id: 'sn1', label: 'Ignored sub' }] }],
          }),
          ['bb1'],
        );
        """
    )
    assert result.returncode == 0, result.stderr
