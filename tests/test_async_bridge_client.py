"""Focused transport proofs for the app-local Python bridge client."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_node_module(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_async_callers_accept_synchronous_bridge_fakes() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { callBridgeSafely } from './lib/seda/bridge-fail-closed.mjs';
        import { generateRouteWithRetry } from './lib/seda/route-generation.mjs';

        const safe = await callBridgeSafely({
          bridge: { callBridgeResult: () => ({ ok: true, payload: { value: 1 } }) },
          action: 'fake',
          payload: {},
        });
        assert.deepEqual(safe, { ok: true, payload: { value: 1 } });

        let callOptions = null;
        const route = await generateRouteWithRetry({
          callBridgeResult: (_action, _payload, options) => {
            callOptions = options;
            return {
              ok: true,
              payload: {
                provisional_map: {
                  backbone: [{ id: 'b1' }],
                  clusters: [{ id: 'c1', subnodes: [{ id: 'c1_s1' }] }],
                },
                first_node: {
                  id: 'c1_s1',
                  label: 'Target',
                  learner_prompt: 'Explain it.',
                  mechanism: 'A changes B.',
                },
              },
            };
          },
          concept: 'Target',
          learnerGoal: null,
          launchAttempt: 'My sketch',
          events: [],
          section: () => '',
        });
        assert.equal(route.route.first_node.id, 'c1_s1');
        assert.deepEqual(callOptions, { timeoutMs: 25_000 });
        """
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_repeated_route_guardrail_failure_stays_fail_closed() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { generateRouteWithRetry } from './lib/seda/route-generation.mjs';

        const events = [];
        let calls = 0;
        const routeResult = await generateRouteWithRetry({
          callBridgeResult: () => {
            calls += 1;
            return {
              ok: false,
              error: 'SmallestRouteCapExceeded',
              message: 'route copies hidden mechanism answer phrases',
            };
          },
          concept: 'Target',
          learnerGoal: null,
          launchAttempt: 'My guess may be wrong.',
          events,
          section: () => '',
        });

        assert.equal(calls, 2);
        assert.equal(routeResult.route, null);
        assert.equal(routeResult.retryReasons.length, 2);
        assert.equal(routeResult.bridgeError.type, 'bridge_error');
        assert.equal(routeResult.bridgeError.phase, 'route');
        assert.equal(routeResult.bridgeError.action, 'generate-route');
        assert.equal(routeResult.bridgeError.retryable, true);
        assert.equal(routeResult.bridgeError.attempts, 2);
        assert.deepEqual(events.map((event) => event.type), ['route_retry']);
        assert.doesNotMatch(JSON.stringify(routeResult), /My guess may be wrong/);
        """
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_bridge_subprocess_does_not_block_the_node_event_loop(tmp_path: Path) -> None:
    bridge = tmp_path / "delayed_bridge.py"
    bridge.write_text(
        """
import json
import sys
import time

json.load(sys.stdin)
time.sleep(0.25)
print(json.dumps({"bridge": "ready"}))
""".strip()
    )

    result = run_node_module(
        f"""
        import assert from 'node:assert/strict';
        import {{ createBridgeClient }} from './lib/bridge/client.mjs';

        const client = createBridgeClient({{
          workspaceRoot: {json.dumps(str(tmp_path))},
          bridgePath: {json.dumps(str(bridge))},
          python: {json.dumps(sys.executable)},
          timeoutMs: 2_000,
          maxConcurrency: 1,
          maxQueue: 0,
        }});
        let ticks = 0;
        const timer = setInterval(() => {{ ticks += 1; }}, 10);
        const firstCall = client.callBridgeResult('delayed', {{}});
        await new Promise((resolve) => setTimeout(resolve, 30));
        const overflow = await client.callBridgeResult('delayed', {{}});
        const response = await firstCall;
        clearInterval(timer);

        assert.equal(overflow.ok, false);
        assert.equal(overflow.error, 'BridgeBusy');
        assert.equal(response.ok, true);
        assert.equal(response.payload.bridge, 'ready');
        assert.ok(ticks >= 5, `event loop only advanced ${{ticks}} times`);
        """
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_bridge_timeout_kills_child_and_writes_fail_closed_diagnostic(
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "stuck_bridge.py"
    bridge.write_text(
        """
import json
import signal
import sys
import time

json.load(sys.stdin)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print("started", flush=True)
time.sleep(5)
""".strip()
    )
    diagnostics = tmp_path / "diagnostics"

    result = run_node_module(
        f"""
        import assert from 'node:assert/strict';
        import {{ createBridgeClient }} from './lib/bridge/client.mjs';

        const client = createBridgeClient({{
          workspaceRoot: {json.dumps(str(tmp_path))},
          bridgePath: {json.dumps(str(bridge))},
          python: {json.dumps(sys.executable)},
          diagnosticsDir: {json.dumps(str(diagnostics))},
          timeoutMs: 2_000,
        }});
        const startedAt = Date.now();
        const response = await client.callBridgeResult(
          'stuck',
          {{}},
          {{ timeoutMs: 50 }},
        );

        assert.equal(response.ok, false);
        assert.equal(response.error, 'BridgeTimeout');
        assert.equal(response.timeout_ms, 50);
        assert.ok(response.duration_ms >= 50);
        assert.ok(Date.now() - startedAt < 2_500);
        assert.ok(response.diagnostic?.path);
        """
    )

    assert result.returncode == 0, result.stderr
    diagnostic_paths = list(diagnostics.glob("*.json"))
    assert len(diagnostic_paths) == 1
    diagnostic = json.loads(diagnostic_paths[0].read_text())
    assert diagnostic["error"] == "BridgeTimeout"
    assert diagnostic["signal"] == "SIGKILL"
    assert diagnostic["bridge"]["stdout"].strip() == "started"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_bridge_output_is_bounded_and_fails_closed(tmp_path: Path) -> None:
    bridge = tmp_path / "noisy_bridge.py"
    bridge.write_text(
        """
import json
import sys

json.load(sys.stdin)
print(json.dumps({"payload": "x" * 10_000}), flush=True)
""".strip()
    )

    result = run_node_module(
        f"""
        import assert from 'node:assert/strict';
        import {{ createBridgeClient }} from './lib/bridge/client.mjs';

        const client = createBridgeClient({{
          workspaceRoot: {json.dumps(str(tmp_path))},
          bridgePath: {json.dumps(str(bridge))},
          python: {json.dumps(sys.executable)},
          timeoutMs: 2_000,
          maxOutputBytes: 128,
        }});
        const response = await client.callBridgeResult('noisy', {{}});

        assert.equal(response.ok, false);
        assert.equal(response.error, 'BridgeOutputTooLarge');
        """
    )

    assert result.returncode == 0, result.stderr
