from __future__ import annotations

from tests._helpers.node_runner import run_node_module


def test_simulate_phase_chain_preserves_routing_contract() -> None:
    result = run_node_module(
        r"""
        import assert from "node:assert/strict";
        import { simulatePhaseChain } from "./lib/seda/routing-proofs.mjs";

        const events = [
          { type: "launch_attempt" },
          { type: "repair_state_bucketed" },
          { type: "repair_cap_selected" },
          { type: "repair_recovery_started" },
          { type: "repair_recovery_turn" },
          { type: "repair_hint_requested" },
          { type: "route_retry" },
          { type: "route_generated" },
          { type: "cold_attempt", evaluation: { classification: "solid" } },
          {
            type: "repair_dialogue_turn",
            bridge_ready: false,
            next_dialogue_action: "abandon",
            turn_index: 2,
          },
          { type: "repair_abandoned", next_step: "recovery_prompt" },
          { type: "repair_recovery_closed", next_phase: "repair" },
          { type: "idle_exit" },
        ];
        const original = structuredClone(events);

        assert.deepEqual(simulatePhaseChain(events), {
          ok: true,
          phases: [
            { afterEventIndex: 0, eventType: "launch_attempt", nextPhase: "substrate_gate" },
            { afterEventIndex: 7, eventType: "route_generated", nextPhase: "cold_attempt" },
            { afterEventIndex: 8, eventType: "cold_attempt", nextPhase: "strong_cold_path" },
            { afterEventIndex: 9, eventType: "repair_dialogue_turn", nextPhase: "repair_abandoned" },
            { afterEventIndex: 10, eventType: "repair_abandoned", nextPhase: "repair_recovery" },
            { afterEventIndex: 11, eventType: "repair_recovery_closed", nextPhase: "repair" },
            { afterEventIndex: 12, eventType: "idle_exit", nextPhase: null },
          ],
          terminalPhase: null,
        });
        assert.deepEqual(events, original);

        assert.deepEqual(
          simulatePhaseChain([{ type: "launch_attempt" }, { type: "future_event" }]),
          {
            ok: false,
            phases: [
              { afterEventIndex: 0, eventType: "launch_attempt", nextPhase: "substrate_gate" },
            ],
            terminalPhase: null,
            error: "unknown event type: future_event",
          },
        );
        assert.deepEqual(
          simulatePhaseChain([
            { type: "launch_attempt" },
            { type: "repair_state_bucketed" },
          ]),
          {
            ok: false,
            phases: [
              { afterEventIndex: 0, eventType: "launch_attempt", nextPhase: "substrate_gate" },
            ],
            terminalPhase: null,
            error: "unknown event type: repair_state_bucketed",
          },
        );
        """
    )
    assert result.returncode == 0, result.stderr
