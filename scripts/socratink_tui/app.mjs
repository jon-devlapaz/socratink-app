#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

import { deriveConceptStatus, deriveNodeTraining } from '../../public/js/training-derive.js';
import { createTrainingStore } from '../../public/js/training-store.js';

const REPO_ROOT = process.cwd();
const BRIDGE = path.join(REPO_ROOT, 'scripts/socratink_tui/bridge.py');
const AGENT_CONTRACTS_PATH = path.join(REPO_ROOT, 'scripts/socratink_tui/pedagogical_agents/contracts.json');
const PYTHON = process.env.PYTHON || path.join(REPO_ROOT, '.venv/bin/python');
const TRAINING_NOW = '2026-05-15T10:00:00.000Z';
const REPAIR_AT = '2026-05-15T10:10:00.000Z';
const STUDY_AT = '2026-05-15T10:12:00.000Z';
const GAP_AT = '2026-05-15T10:15:00.000Z';
const SPACED_AT = '2026-05-16T06:00:00.000Z';
const FINAL_NOW = '2026-05-16T06:05:00.000Z';

function parseArgs(argv) {
  const options = {
    scripted: null,
    logRawLlm: false,
    color: 'auto',
  };
  const args = [...argv.slice(2)];
  while (args.length) {
    const arg = args.shift();
    if (arg === '--scripted') {
      options.scripted = args.shift();
    } else if (arg === '--log-raw-llm') {
      options.logRawLlm = true;
    } else if (arg.startsWith('--color=')) {
      options.color = arg.slice('--color='.length);
      if (!['auto', 'always', 'never'].includes(options.color)) {
        throw new Error('--color must be auto, always, or never');
      }
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      throw new Error(`unexpected argument: ${arg}`);
    }
  }
  return options;
}

function usage() {
  return [
    'Usage: scripts/socratink-tui [--log-raw-llm] [--color=auto|always|never] [--scripted path.json]',
    '',
    'Runs a source-less terminal Socratink session using the existing Python LLM seam.',
    'Local env file: scripts/socratink_tui/.env',
  ].join('\n');
}

function useColor(mode) {
  if (mode === 'always') return true;
  if (mode === 'never') return false;
  if (process.env.NO_COLOR) return false;
  return Boolean(process.stdout.isTTY);
}

function makeSections(colorEnabled) {
  const colors = {
    reset: '\x1b[0m',
    ignition: '\x1b[35m',
    route: '\x1b[36m',
    cold: '\x1b[33m',
    study: '\x1b[34m',
    repair: '\x1b[31m',
    pressure: '\x1b[36m',
    spacing: '\x1b[90m',
    redrill: '\x1b[32m',
    evidence: '\x1b[32m',
  };
  return function section(kind, label) {
    const tag = `[${label}]`;
    return colorEnabled ? `${colors[kind]}${tag}${colors.reset}` : tag;
  };
}

function createMemoryStorage() {
  const writes = new Map();
  return {
    getItem(key) { return writes.has(key) ? writes.get(key) : null; },
    setItem(key, value) { writes.set(key, value); },
    removeItem(key) { writes.delete(key); },
  };
}

async function loadScripted(scriptPath) {
  if (!scriptPath) return null;
  return JSON.parse(await fs.readFile(scriptPath, 'utf8'));
}

async function loadAgentContracts() {
  return JSON.parse(await fs.readFile(AGENT_CONTRACTS_PATH, 'utf8'));
}

function makeAgentLookup(contracts) {
  const lookup = new Map();
  (contracts?.agents || []).forEach((agent) => {
    lookup.set(agent.id, agent);
  });
  return lookup;
}

function agentCall(agentLookup, id, call = {}) {
  const agent = agentLookup.get(id);
  if (!agent) throw new Error(`agent-contract-missing:${id}`);
  return {
    agent: agent.name,
    agent_id: agent.id,
    job: agent.job,
    required_outputs: agent.required_outputs,
    may_propose_events: agent.may_propose_events,
    truth_permission: agent.truth_permission,
    failure_mode_to_guard: agent.failure_mode_to_guard,
    ...call,
  };
}

const PROMPT_HELP = {
  concept: {
    title: 'Concept',
    body: 'Name the idea you want Socratink to build a provisional route around.',
  },
  learner_goal: {
    title: 'Learner goal',
    body: 'Say what you want to explain or do with the concept. This shapes relevance, not graph evidence.',
  },
  launch_attempt: {
    title: 'Launch attempt',
    body: 'Write your current model before seeing any route. Rough, incomplete, and uncertain is useful.',
  },
  cold_attempt: {
    title: 'Cold attempt',
    body: 'Reconstruct the current node from memory. This exposes the gap before any answer material appears.',
  },
  repair: {
    title: 'Repair dialogue',
    body: 'Fill the missing causal link in your own words: before state -> missing operation -> after state.',
  },
  repair_dialogue_turns: {
    title: 'Repair dialogue',
    body: 'Stay on the same bottleneck. Explain how the missing operation changes the before state into the after state.',
  },
  run_gap_drill: {
    title: 'Post-bridge transfer check',
    body: 'Choose whether to do a small graph-neutral transfer check after seeing the model bridge.',
  },
  gap_attempt: {
    title: 'Post-bridge transfer check',
    body: 'Apply the repaired link after comparison material. This keeps the link active but does not prove mastery.',
  },
  spaced_attempt: {
    title: 'Spaced re-drill',
    body: 'Reconstruct the mechanism again after spacing. Only spaced strong reconstruction can derive solidified.',
  },
};

function isHelpCommand(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized === '/help' || normalized === '/help/';
}

function printPromptHelp(key) {
  const help = PROMPT_HELP[key] || {
    title: 'This step',
    body: 'Answer in your own words. Type /help at any prompt to see this guidance.',
  };
  console.log(`[Help] ${help.title}: ${help.body}`);
}

async function makePrompt(scripted) {
  if (scripted) {
    const indexes = new Map();
    return {
      ask: async (key, label, fallback = '') => {
        while (true) {
          const scriptedValue = scripted[key];
          let value = scriptedValue ?? fallback;
          if (Array.isArray(scriptedValue)) {
            const index = indexes.get(key) || 0;
            value = scriptedValue[index] ?? fallback;
            indexes.set(key, index + 1);
          }
          console.log(`${label}${value}`);
          if (isHelpCommand(value)) {
            printPromptHelp(key);
            continue;
          }
          return String(value);
        }
      },
      close: () => {},
    };
  }
  const rl = readline.createInterface({ input, output });
  return {
    ask: async (key, label, fallback = '') => {
      const suffix = fallback ? ` (${fallback})` : '';
      while (true) {
        const answer = await rl.question(`${label}${suffix}: `);
        const trimmed = answer.trim();
        if (isHelpCommand(trimmed)) {
          printPromptHelp(key);
          continue;
        }
        return trimmed || fallback;
      }
    },
    close: () => rl.close(),
  };
}

const BRIDGE_MAX_BUFFER = 10 * 1024 * 1024;

function runBridge(action, payload) {
  const result = spawnSync(
    PYTHON,
    [BRIDGE, action],
    {
      cwd: REPO_ROOT,
      input: JSON.stringify(payload),
      encoding: 'utf8',
      maxBuffer: BRIDGE_MAX_BUFFER,
    },
  );
  if (result.error) {
    return {
      ok: false,
      error: result.error.code || 'BridgeSpawnError',
      message: result.error.message,
    };
  }
  const raw = (result.stdout || result.stderr || '').trim();
  let parsed;
  try {
    parsed = JSON.parse(raw || '{}');
  } catch {
    return {
      ok: false,
      error: 'BridgeNonJson',
      message: raw || 'bridge returned empty output',
    };
  }
  if (result.status !== 0) {
    return {
      ok: false,
      error: parsed.error || 'bridge-error',
      message: parsed.message || result.stderr || raw,
    };
  }
  return { ok: true, payload: parsed };
}

function callBridge(action, payload) {
  const result = runBridge(action, payload);
  if (!result.ok) {
    throw new Error(`${result.error}: ${result.message}`);
  }
  return result.payload;
}

function callBridgeResult(action, payload) {
  const result = runBridge(action, payload);
  if (!result.ok) {
    return result;
  }
  return { ok: true, payload: result.payload };
}

function isRetryableRouteError(error) {
  return error?.error === 'SmallestRouteCapExceeded'
    || String(error?.message || '').includes('SmallestRouteCapExceeded')
    || String(error?.message || '').includes('copies hidden mechanism');
}

function routeRetryEvent(error, attempt) {
  return {
    type: 'route_retry',
    attempt,
    error: error.error || 'route_generation_failed',
    message: error.message || '',
    graph_neutral: true,
    retry_guardrail: 'regenerate learner scaffold without copying hidden mechanism answer phrases',
  };
}

function generateRouteWithRetry({
  concept,
  learnerGoal,
  launchAttempt,
  logRawLlm,
  events,
  section,
}) {
  const retryReasons = [];
  const maxAttempts = 2;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const result = callBridgeResult('generate-route', {
      concept,
      learner_goal: learnerGoal || null,
      launch_attempt: launchAttempt,
      log_raw_llm: logRawLlm,
      route_attempt: attempt,
      route_retry_reason: retryReasons.at(-1)?.message || null,
    });
    if (result.ok) {
      return {
        route: result.payload,
        retryReasons,
      };
    }
    if (!isRetryableRouteError(result) || attempt === maxAttempts) {
      throw new Error(`${result.error || 'route-generation-failed'}: ${result.message || ''}`);
    }
    const event = routeRetryEvent(result, attempt);
    retryReasons.push({
      attempt,
      error: event.error,
      message: event.message,
    });
    events.push(event);
    console.log(`${section('route', 'Route Retry')} ${event.error}: ${event.message}`);
  }
  throw new Error('route-generation-failed');
}

function classifyForStore(evaluation) {
  if (evaluation.classification === 'solid') return 'strong';
  if (evaluation.classification === 'deep' || evaluation.classification === 'shallow') return 'partial';
  if (evaluation.classification === 'misconception') return 'wrong_direction';
  return 'thin';
}

function gapsForStore(evaluation) {
  if (!evaluation.gap_description) return [];
  return [{ mechanism: 'target mechanism', correction: evaluation.gap_description }];
}

function summarizeTraining(training, nodeIds, now) {
  const records = training?.node_records || {};
  const nodes = {};
  nodeIds.forEach((nodeId) => {
    const record = records[nodeId] || null;
    nodes[nodeId] = {
      ...deriveNodeTraining(record, { now }),
      attempt_count: Array.isArray(record?.attempts) ? record.attempts.length : 0,
      repair_count: Array.isArray(record?.repairs) ? record.repairs.length : 0,
    };
  });
  return {
    nodes,
    concept_status: deriveConceptStatus(training, nodeIds, { now }),
  };
}

function buildTargetedFeedback(evaluation, firstNode) {
  const cue = evaluation.gap_description
    || firstNode.blank_hint
    || firstNode.evidence_goal
    || `Say the key causal link behind ${firstNode.label} in your own words.`;
  return {
    repair_target: cue,
    before: firstNode.blank_hint || `Your current model has part of ${firstNode.label}.`,
    missing_operation: `missing operation in ${firstNode.label}`,
    after: firstNode.evidence_goal || 'The target mechanism works.',
    internal_bloom_lens: 'understand',
    question_style: 'direct',
    socratic_question: `What must happen before ${firstNode.evidence_goal || 'the result follows'}?`,
  };
}

function countWords(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean).length;
}

function isAnswerShapedScaffold(scaffold) {
  const missing = String(scaffold?.missing_operation || '').toLowerCase();
  const question = String(scaffold?.socratic_question || '').toLowerCase();
  const actionChainMarkers = [
    'observe',
    'compare',
    'update',
    'refine',
    'choose',
    'inspect',
    'evaluate',
  ];
  const markerCount = actionChainMarkers.filter((marker) => (
    missing.includes(marker) || question.includes(marker)
  )).length;
  return (
    countWords(missing) > 8
    || missing.includes(',')
    || /\band\b/.test(missing)
    || markerCount >= 3
  );
}

function prepareRepairScaffold(rawScaffold, evaluation, firstNode) {
  const fallback = buildTargetedFeedback(evaluation, firstNode);
  if (!rawScaffold) {
    return { scaffold: fallback, rejections: [] };
  }
  if (isAnswerShapedScaffold(rawScaffold)) {
    return {
      scaffold: fallback,
      rejections: [{
        reason: 'answer_shaped_scaffold',
        rejected_missing_operation: rawScaffold.missing_operation || '',
      }],
    };
  }
  return {
      scaffold: {
      ...rawScaffold,
      internal_bloom_lens: rawScaffold.internal_bloom_lens || fallback.internal_bloom_lens,
      question_style: rawScaffold.question_style || fallback.question_style,
    },
    rejections: [],
  };
}

function buildEvidenceHold({ finalState, spacedEvaluation, training, nodeId }) {
  if (spacedEvaluation?.classification !== 'solid' || finalState === 'solidified') {
    return null;
  }
  const attempts = training?.node_records?.[nodeId]?.attempts || [];
  const firstAttempt = attempts[0] || null;
  if (firstAttempt?.classification !== 'strong') {
    return {
      event: 'spaced_redrill',
      state: finalState,
      reason: (
        `The spaced answer was solid, but this node remains ${finalState} because ` +
        'the first attempt was not strong. Current derivation requires two strong ' +
        'reconstructions separated by spacing before solidified.'
      ),
    };
  }
  return {
    event: 'spaced_redrill',
    state: finalState,
    reason: (
      `The spaced answer was solid, but this node remains ${finalState} under ` +
      'the current training derivation contract.'
    ),
  };
}

function isUncertainRepair(text) {
  const normalized = String(text || '').trim().toLowerCase().replace(/[.!?]+$/g, '');
  if (!normalized) return true;
  return [
    'i am not sure',
    "i'm not sure",
    'idk',
    'not sure',
    'i do not know',
    "i don't know",
    'dont know',
    "don't know",
    'no idea',
    'unsure',
  ].includes(normalized);
}

function repairDialogueEvent({ gapId, turnIndex, repairText, repairScaffold, judge }) {
  return {
    type: 'repair_dialogue_turn',
    gap_id: gapId,
    turn_index: turnIndex,
    text: repairText,
    prompt_type: judge.support_level,
    support_level: judge.support_level,
    classification: judge.classification,
    gap_delta: {
      missing_operation: repairScaffold.missing_operation,
      causal_link_present: judge.causal_link_present,
      missing_operation_addressed: judge.missing_operation_addressed,
    },
    score_eligible: false,
    graph_neutral: true,
    causal_link_present: judge.causal_link_present,
    missing_operation_addressed: judge.missing_operation_addressed,
    echo_risk: judge.echo_risk,
    bridge_ready: judge.bridge_ready,
    next_dialogue_action: judge.next_dialogue_action,
    judge_reason: judge.judge_reason,
    next_prompt: judge.next_prompt,
    not_mastery_reason: judge.not_mastery_reason,
  };
}

function printColdAttemptBrief({ learnerGoal, firstNode }) {
  console.log('[Cold Attempt Brief]');
  console.log(`Node: ${firstNode.label}`);
  if (learnerGoal) console.log(`Goal: ${learnerGoal}`);
  console.log('Source: no source attached; route is provisional.');
  console.log('Try your current model before seeing the explanation.');
  console.log('Write 2-4 sentences. Causal guesses beat polished definitions.');
}

async function createSessionLogDir() {
  const root = process.env.SOCRATINK_TUI_LOG_ROOT
    || path.join(REPO_ROOT, '.qa-runs/socratink-tui');
  const stamp = new Date().toISOString().replaceAll(':', '-').replace(/\.\d{3}Z$/, 'Z');
  const dir = path.join(root, stamp);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

async function run(options) {
  const scripted = await loadScripted(options.scripted);
  const agentContracts = await loadAgentContracts();
  const agentLookup = makeAgentLookup(agentContracts);
  const prompt = await makePrompt(scripted);
  const section = makeSections(useColor(options.color));
  const logDir = await createSessionLogDir();
  const llmCalls = [];
  const events = [];
  const derived = [];
  const evidenceHolds = [];

  console.log('Socratink Terminal');
  console.log('==================');
  console.log('Source-less dogfood loop. Local session only.');
  console.log('');

  console.log(section('ignition', 'Ignition'));
  const concept = await prompt.ask('concept', 'Concept: ');
  const learnerGoal = await prompt.ask('learner_goal', 'Learner goal (optional): ');
  const launchAttempt = await prompt.ask('launch_attempt', 'Launch attempt: ');

  const storage = createMemoryStorage();
  const store = createTrainingStore({ storage });
  const conceptId = concept.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'source-less-concept';
  await store.setProvenance(conceptId, {
    source_mode: 'source_less',
    grounding: 'learner_sketch',
    source_ref: null,
  });
  await store.setSketch(conceptId, { text: launchAttempt, at: TRAINING_NOW });
  events.push({ type: 'launch_attempt', text: launchAttempt });

  console.log('');
  console.log(section('route', 'Route'));
  console.log('Generating Smallest actionable route...');
  const routeResult = generateRouteWithRetry({
    concept,
    learnerGoal,
    launchAttempt,
    logRawLlm: options.logRawLlm,
    events,
    section,
  });
  const route = routeResult.route;
  llmCalls.push(agentCall(agentLookup, 'route', { stage: 'route_generated', ...route.llm_call }));
  events.push({ type: 'route_generated' });

  const firstNode = route.first_node;
  const nodeIds = [firstNode.id];
  llmCalls.push(agentCall(agentLookup, 'cold_attempt', {
    stage: 'cold_attempt_prompt',
    provider: 'orchestrator',
    model: 'contract',
    latency_ms: 0,
    usage: { input_tokens: 0, output_tokens: 0 },
  }));
  console.log(`Smallest actionable route: ${firstNode.label}`);
  console.log(firstNode.learner_prompt);

  console.log('');
  printColdAttemptBrief({ learnerGoal, firstNode });
  console.log('');
  console.log(section('cold', 'Cold Attempt'));
  const coldAttempt = await prompt.ask('cold_attempt', 'Cold attempt: ');
  const cold = callBridge('evaluate-attempt', {
    knowledge_map: route.provisional_map,
    node_id: firstNode.id,
    node_label: firstNode.label,
    node_mechanism: firstNode.mechanism,
    learner_text: coldAttempt,
    drill_mode: 'cold_attempt',
    log_raw_llm: options.logRawLlm,
  });
  llmCalls.push(agentCall(agentLookup, 'evidence_judge', { stage: 'cold_attempt', ...cold.llm_call }));
  await store.appendAttempt(conceptId, firstNode.id, {
    id: 'cold-1',
    at: TRAINING_NOW,
    user_text: coldAttempt,
    classification: classifyForStore(cold.evaluation),
    gaps: gapsForStore(cold.evaluation),
    grader_version: cold.llm_call.model || 'tui',
  });
  events.push({ type: 'cold_attempt', text: coldAttempt, evaluation: cold.evaluation });
  derived.push({ event: 'cold_attempt', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });
  console.log(cold.evaluation.agent_response);
  console.log(`${section('evidence', 'Evidence')} ${derived.at(-1).nodes[firstNode.id].state}`);

  if (cold.evaluation.classification === 'solid') {
    console.log('');
    console.log(section('evidence', 'Strong Cold Path'));
    console.log('Repair skipped for now. The graph still waits for spaced reconstruction before solidified.');
    events.push({
      type: 'strong_cold_path',
      reason: 'cold_reconstruction_solid',
      graph_neutral: true,
      next_step: 'spaced_redrill',
    });
    derived.push({ event: 'strong_cold_path', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });
  } else {
    console.log('');
    console.log(section('study', 'Delta'));
    const scaffoldResult = callBridge('repair-scaffold', {
      node_label: firstNode.label,
      node_mechanism: firstNode.mechanism,
      learner_text: coldAttempt,
      gap_description: cold.evaluation.gap_description || null,
      evidence_goal: firstNode.evidence_goal || null,
      blank_hint: firstNode.blank_hint || null,
      log_raw_llm: options.logRawLlm,
    });
    llmCalls.push(agentCall(agentLookup, 'delta', { stage: 'repair_scaffold', ...scaffoldResult.llm_call }));
    const scaffoldReview = prepareRepairScaffold(
      scaffoldResult.repair_scaffold,
      cold.evaluation,
      firstNode,
    );
    const repairScaffold = scaffoldReview.scaffold;
    console.log(`Gap logged: ${repairScaffold.repair_target}`);
    console.log(`  Before: ${repairScaffold.before}`);
    console.log(`  Missing operation: ${repairScaffold.missing_operation}`);
    console.log(`  After: ${repairScaffold.after}`);
    console.log('');
    console.log(section('repair', 'Socratic Repair Drill'));
    console.log(repairScaffold.socratic_question);
    await store.setStudyRevealed(conceptId, firstNode.id, STUDY_AT);
    events.push({
      type: 'gap_identified',
      surface: 'delta',
      cue: repairScaffold.repair_target,
      gap_log: {
        before: repairScaffold.before,
        missing_operation: repairScaffold.missing_operation,
        after: repairScaffold.after,
        internal_bloom_lens: repairScaffold.internal_bloom_lens,
        question_style: repairScaffold.question_style,
      },
      repair_scaffold: repairScaffold,
      scaffold_rejections: scaffoldReview.rejections,
      prompt: repairScaffold.socratic_question,
      graph_neutral: true,
      training_store_note: 'uses study_revealed_at internally to unlock repair without revealing model bridge',
    });
    derived.push({ event: 'gap_identified', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });

    console.log('');
    console.log(section('repair', 'Own-Words Repair'));
    llmCalls.push(agentCall(agentLookup, 'repair', {
      stage: 'repair_prompt',
      provider: 'orchestrator',
      model: 'contract',
      latency_ms: 0,
      usage: { input_tokens: 0, output_tokens: 0 },
    }));
    const gapId = `gap-${firstNode.id}-1`;
    const maxRepairTurns = 3;
    let repair = '';
    let bridgeReady = false;
    let abandonReason = null;
    let nextPrompt = null;
    for (let turnIndex = 1; turnIndex <= maxRepairTurns; turnIndex += 1) {
      console.log(section('repair', 'Repair Dialogue'));
      const repairKey = scripted?.repair_dialogue_turns ? 'repair_dialogue_turns' : 'repair';
      const label = turnIndex === 1
        ? 'Fill the missing link: '
        : `${nextPrompt || repairScaffold.next_prompt || 'Try the same missing link again'}: `;
      repair = await prompt.ask(repairKey, label);
      if (isUncertainRepair(repair)) {
        abandonReason = 'uncertain_nonrepair';
        break;
      }
      const dialogue = callBridge('repair-dialogue', {
        node_label: firstNode.label,
        node_mechanism: firstNode.mechanism,
        gap_id: gapId,
        missing_operation: repairScaffold.missing_operation,
        before: repairScaffold.before,
        after: repairScaffold.after,
        learner_text: repair,
        turn_index: turnIndex,
        log_raw_llm: options.logRawLlm,
      });
      llmCalls.push(agentCall(agentLookup, 'repair', { stage: 'repair_dialogue', ...dialogue.llm_call }));
      const judge = dialogue.repair_dialogue;
      if (judge.next_prompt) {
        nextPrompt = judge.next_prompt;
      }
      events.push(repairDialogueEvent({
        gapId,
        turnIndex,
        repairText: repair,
        repairScaffold,
        judge,
      }));
      console.log(`Bridge readiness: ${judge.bridge_ready ? 'ready' : 'not yet'}`);
      console.log(judge.judge_reason);
      if (judge.bridge_ready) {
        bridgeReady = true;
        break;
      }
      if (judge.next_prompt) {
        console.log(judge.next_prompt);
      }
      if (judge.next_dialogue_action === 'abandon') {
        abandonReason = 'dialogue_abandoned';
        break;
      }
    }
    if (!bridgeReady) {
      const abandonedEvent = {
        type: 'repair_abandoned',
        text: repair,
        reason: abandonReason || 'unresolved_gap',
        graph_neutral: true,
        next_step: 'micro_scaffold',
      };
      events.push(abandonedEvent);
      derived.push({ event: 'repair_abandoned', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });
      console.log(`${section('repair', 'Repair Abandoned')} No model bridge yet. The gap is still unresolved; uncertainty is useful, but it is not repair evidence.`);

      const session = {
        source_mode: 'source_less',
        concept,
        learner_goal: learnerGoal || null,
        concept_id: conceptId,
        route: {
          provisional_map: route.provisional_map,
          first_node: firstNode,
          retry_count: routeResult.retryReasons.length,
          retry_reasons: routeResult.retryReasons,
        },
        product_loop: {
          repair_position: 'before_model_bridge',
          bridge_gate: 'before -> missing operation -> after',
          graph_truth: 'only spaced strong reconstruction may derive solidified',
          graph_neutral_events: ['gap_identified', 'repair_dialogue_turn', 'repair_abandoned'],
        },
        agent_contract: {
          orchestrator: agentContracts.architecture.orchestrator,
          truth_contract: agentContracts.architecture.truth_contract,
          state_owner: agentContracts.architecture.state_owner,
        },
        events,
        derived,
        evidence_holds: evidenceHolds,
        llm_calls: llmCalls,
        training: await store.loadTraining(conceptId),
      };
      await fs.writeFile(path.join(logDir, 'session.json'), JSON.stringify(session, null, 2));
      console.log(`\nSaved log: ${path.join(logDir, 'session.json')}`);
      prompt.close();
      return;
    }
    await store.appendRepair(conceptId, firstNode.id, {
      id: 'repair-1',
      at: REPAIR_AT,
      text: repair,
    });
    events.push({ type: 'repair', text: repair });
    derived.push({ event: 'repair', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });

    console.log('');
    console.log(section('study', 'Model Bridge'));
    llmCalls.push(agentCall(agentLookup, 'model_bridge', {
      stage: 'model_bridge',
      provider: 'orchestrator',
      model: 'contract',
      latency_ms: 0,
      usage: { input_tokens: 0, output_tokens: 0 },
    }));
    console.log(firstNode.mechanism);
    events.push({
      type: 'model_bridge',
      text: firstNode.mechanism,
      graph_neutral: true,
    });
    derived.push({ event: 'model_bridge', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });

    const runGap = scripted ? Boolean(scripted.run_gap_drill) : (await prompt.ask('run_gap_drill', '\nPost-bridge transfer check? y/N: ', 'n')).toLowerCase().startsWith('y');
    if (runGap) {
      console.log('');
      console.log(section('pressure', 'Post-Bridge Transfer Check'));
      const pressurePrompt = `Post-bridge transfer check (${repairScaffold.missing_operation}): `;
      const gapAttempt = await prompt.ask('gap_attempt', pressurePrompt);
      const gap = callBridge('evaluate-attempt', {
        knowledge_map: route.provisional_map,
        node_id: firstNode.id,
        node_label: firstNode.label,
        node_mechanism: firstNode.mechanism,
        learner_text: gapAttempt,
        repair_drill_context: repair,
        drill_mode: 'gap_drill',
        log_raw_llm: options.logRawLlm,
      });
      llmCalls.push(agentCall(agentLookup, 'evidence_judge', { stage: 'gap_drill', ...gap.llm_call }));
      events.push({
        type: 'post_bridge_transfer_check',
        text: gapAttempt,
        prompt: pressurePrompt.trim(),
        target_missing_operation: repairScaffold.missing_operation,
        evaluation: gap.evaluation,
        graph_neutral: true,
        at: GAP_AT,
      });
      derived.push({ event: 'post_bridge_transfer_check', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, TRAINING_NOW) });
      console.log(gap.evaluation.agent_response);
    }
  }

  console.log('');
  console.log(section('spacing', 'Spacing'));
  console.log('Spacing advanced: 20 hours');
  events.push({ type: 'spacing_advanced', from: TRAINING_NOW, to: SPACED_AT });
  derived.push({ event: 'spacing_advanced', ...summarizeTraining(await store.loadTraining(conceptId), nodeIds, FINAL_NOW) });

  console.log('');
  console.log(section('redrill', 'Spaced Re-Drill'));
  llmCalls.push(agentCall(agentLookup, 'redrill', {
    stage: 'spaced_prompt',
    provider: 'orchestrator',
    model: 'contract',
    latency_ms: 0,
    usage: { input_tokens: 0, output_tokens: 0 },
  }));
  const spacedAttempt = await prompt.ask('spaced_attempt', 'Spaced re-drill: ');
  const spaced = callBridge('evaluate-attempt', {
    knowledge_map: route.provisional_map,
    node_id: firstNode.id,
    node_label: firstNode.label,
    node_mechanism: firstNode.mechanism,
    learner_text: spacedAttempt,
    drill_mode: 'spaced_redrill',
    log_raw_llm: options.logRawLlm,
  });
  llmCalls.push(agentCall(agentLookup, 'evidence_judge', { stage: 'spaced_redrill', ...spaced.llm_call }));
  await store.appendAttempt(conceptId, firstNode.id, {
    id: 'spaced-1',
    at: SPACED_AT,
    user_text: spacedAttempt,
    classification: classifyForStore(spaced.evaluation),
    gaps: gapsForStore(spaced.evaluation),
    grader_version: spaced.llm_call.model || 'tui',
  });
  events.push({ type: 'spaced_redrill', text: spacedAttempt, evaluation: spaced.evaluation });
  const finalTraining = await store.loadTraining(conceptId);
  derived.push({ event: 'spaced_redrill', ...summarizeTraining(finalTraining, nodeIds, FINAL_NOW) });

  const finalState = derived.at(-1).nodes[firstNode.id].state;
  console.log(spaced.evaluation.agent_response);
  console.log(`${section('evidence', 'Evidence')} ${finalState}`);
  const evidenceHold = buildEvidenceHold({
    finalState,
    spacedEvaluation: spaced.evaluation,
    training: finalTraining,
    nodeId: firstNode.id,
  });
  if (evidenceHold) {
    evidenceHolds.push(evidenceHold);
    console.log(`${section('evidence', 'Evidence Hold')} ${evidenceHold.reason}`);
  }
  console.log(`\nSaved log: ${path.join(logDir, 'session.json')}`);

  const session = {
    source_mode: 'source_less',
    concept,
    learner_goal: learnerGoal || null,
    concept_id: conceptId,
    route: {
      provisional_map: route.provisional_map,
      first_node: firstNode,
      retry_count: routeResult.retryReasons.length,
      retry_reasons: routeResult.retryReasons,
    },
    product_loop: {
      repair_position: 'before_model_bridge',
      strong_cold_path: cold.evaluation.classification === 'solid' ? 'skip_repair_until_spacing' : 'not_taken',
      graph_truth: 'only spaced strong reconstruction may derive solidified',
      graph_neutral_events: cold.evaluation.classification === 'solid'
        ? ['strong_cold_path']
        : ['gap_identified', 'repair_dialogue_turn', 'repair', 'model_bridge', 'post_bridge_transfer_check'],
    },
    agent_contract: {
      orchestrator: agentContracts.architecture.orchestrator,
      truth_contract: agentContracts.architecture.truth_contract,
      state_owner: agentContracts.architecture.state_owner,
    },
    events,
    derived,
    evidence_holds: evidenceHolds,
    llm_calls: llmCalls,
    training: await store.loadTraining(conceptId),
  };
  await fs.writeFile(path.join(logDir, 'session.json'), JSON.stringify(session, null, 2));
  prompt.close();
}

async function main() {
  try {
    const options = parseArgs(process.argv);
    if (options.help) {
      console.log(usage());
      return;
    }
    await run(options);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

await main();
