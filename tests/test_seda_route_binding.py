"""Source-less SEDA route binding contract."""

from __future__ import annotations

import shutil

import pytest

from tests._helpers.node_runner import run_node_module


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_route_rebinds_map_once_and_preserves_app_metadata() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          bindSourceLessSedaRoute,
          boundSourceLessSedaNodeId,
          boundSourceLessSedaSessionId,
          clearBoundSourceLessSedaRoute,
          hasBoundSourceLessSedaRoute,
        } from './public/js/seda-route-binding.js';

        const existingMap = {
          metadata: {
            core_thesis: 'Door map thesis',
            starting_map_context: 'My rough Door sketch.',
            source_mode: 'source_less',
            map_maturity: 'provisional',
            learner_goal: 'Explain the causal chain.',
          },
          backbone: [{ id: 'b1', principle: 'Door map principle.' }],
          clusters: [],
        };
        const data = {
          sessionId: 'session-9',
          awaiting: { key: 'cold_attempt' },
          sourceLessRoute: {
            contractVersion: 1,
            status: 'ready',
            firstNode: {
              id: 'c9_s1', label: 'Bound target',
              mechanism: 'Mechanism B happens before the result.',
              learner_prompt: 'Explain prompt B from memory.',
              evidence_goal: 'Name the link from B to the result.',
            },
            provisionalMap: {
              metadata: { core_thesis: 'SEDA route thesis' },
              backbone: [{ id: 'b9', principle: 'Route backbone.' }],
              clusters: [{
                id: 'c9', label: 'Route cluster',
                subnodes: [{ id: 'c9_s1', label: 'Stale route label' }],
              }],
            },
          },
          events: [{ type: 'route_generated', first_node: { id: 'wrong-node' } }],
        };

        const bound = bindSourceLessSedaRoute({
          data,
          existingMap,
          concept: {
            startingMapContext: 'My rough Door sketch.',
            learnerGoal: 'Explain the causal chain.',
            sourceMode: 'source_less',
          },
        });

        assert.equal(bound.nodeContext.id, 'c9_s1');
        assert.equal(bound.nodeContext.prompt, 'Explain prompt B from memory.');
        assert.equal(bound.nodeContext.detail, 'Mechanism B happens before the result.');
        const target = bound.graphData.clusters[0].subnodes[0];
        assert.equal(target.label, 'Bound target');
        assert.equal(target.study_note, 'Mechanism B happens before the result.');
        assert.equal(target.learner_scaffold.entry_prompt, 'Explain prompt B from memory.');
        assert.equal(bound.graphData.metadata.core_thesis, 'SEDA route thesis');
        assert.equal(bound.graphData.metadata.starting_map_context, 'My rough Door sketch.');
        assert.equal(bound.graphData.metadata.source_mode, 'source_less');
        assert.equal(bound.graphData.metadata.map_maturity, 'provisional');
        assert.equal(bound.graphData.metadata.learner_goal, 'Explain the causal chain.');
        assert.equal(hasBoundSourceLessSedaRoute(existingMap), false);
        assert.equal(hasBoundSourceLessSedaRoute(bound.graphData), true);
        assert.equal(boundSourceLessSedaNodeId(bound.graphData), 'c9_s1');
        assert.equal(boundSourceLessSedaSessionId(bound.graphData), 'session-9');
        assert.equal(data.sourceLessRoute.provisionalMap.clusters[0].subnodes[0].label, 'Stale route label');
        const cleared = clearBoundSourceLessSedaRoute(bound.graphData);
        assert.equal(hasBoundSourceLessSedaRoute(cleared), false);
        assert.equal(cleared.metadata.starting_map_context, 'My rough Door sketch.');
        assert.equal(cleared.metadata.route_status, 'pending_seda');
        assert.equal(cleared.metadata.graph_neutral, true);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_route_fails_closed_when_not_bindable() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { bindSourceLessSedaRoute } from './public/js/seda-route-binding.js';

        assert.throws(
          () => bindSourceLessSedaRoute({ data: { sessionId: 's', events: [] } }),
          /missing sourceLessRoute result/,
        );
        const baseRoute = {
          contractVersion: 1,
          status: 'ready',
          firstNode: {
            id: 'c9_s1', label: 'Target', mechanism: 'Mechanism B',
            learner_prompt: 'Prompt B',
          },
          provisionalMap: {
            metadata: {},
            backbone: [{ id: 'b9', principle: 'Route backbone.' }],
            clusters: [{ id: 'c9', subnodes: [{ id: 'different-node' }] }],
          },
        };
        assert.throws(
          () => bindSourceLessSedaRoute({ data: {
            sessionId: 's', awaiting: { key: 'cold_attempt' }, sourceLessRoute: baseRoute,
          } }),
          /first_node.id is absent/,
        );
        assert.throws(
          () => bindSourceLessSedaRoute({
            data: {
              sessionId: 's', awaiting: { key: 'cold_attempt' },
              sourceLessRoute: {
                ...baseRoute,
                firstNode: { ...baseRoute.firstNode, mechanism: '' },
              },
            },
          }),
          /missing first_node.mechanism/,
        );
        assert.throws(
          () => bindSourceLessSedaRoute({ data: {
            sessionId: 's', awaiting: { key: 'cold_attempt' },
            sourceLessRoute: {
              ...baseRoute,
              firstNode: { ...baseRoute.firstNode, id: 9 },
            },
          } }),
          /missing first_node.id/,
        );
        assert.throws(
          () => bindSourceLessSedaRoute({ data: {
            sessionId: 's', awaiting: { key: 'cold_attempt' },
            sourceLessRoute: {
              contractVersion: 1,
              status: 'route_unavailable',
              code: 'route_unavailable',
              reason: 'generation_failed',
            },
          } }),
          /generation_failed/,
        );
        """
    )
    assert result.returncode == 0, result.stderr
