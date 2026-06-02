#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';

if (
  !process.env.SOCRATINK_KERNEL_NO_WARNINGS
  && !process.execArgv.includes('--no-warnings')
) {
  const result = spawnSync(
    process.execPath,
    ['--no-warnings', ...process.argv.slice(1)],
    {
      env: { ...process.env, SOCRATINK_KERNEL_NO_WARNINGS: '1' },
      stdio: 'inherit',
    },
  );
  process.exit(result.status ?? 1);
}

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
const FIXTURE_ALIASES = new Map([
  ['source-backed', path.join(REPO_ROOT, 'tests/fixtures/cli-kernel/source_backed_repair_loop.json')],
  ['source-less', path.join(REPO_ROOT, 'tests/fixtures/cli-kernel/source_less_solidification_loop.json')],
]);

function usage() {
  return [
    'Usage: scripts/cli-kernel-harness.mjs [--json|--tui-static] <source-backed|source-less|fixture.json>',
    '',
    'Examples:',
    '  scripts/cli-kernel-harness.mjs source-less',
    '  scripts/cli-kernel-harness.mjs source-backed',
    '  scripts/cli-kernel-harness.mjs --json source-less',
  ].join('\n');
}

function createMemoryStorage() {
  const writes = new Map();
  return {
    getItem(key) {
      return writes.has(key) ? writes.get(key) : null;
    },
    setItem(key, value) {
      writes.set(key, value);
    },
    removeItem(key) {
      writes.delete(key);
    },
  };
}

function requireObject(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label}-required`);
  }
  return value;
}

function extractNodeIds(concept) {
  const graph = concept?.graph || concept?.graphData || concept;
  if (Array.isArray(concept?.node_ids)) return concept.node_ids;
  if (Array.isArray(graph?.node_ids)) return graph.node_ids;
  if (Array.isArray(graph?.nodes)) {
    return graph.nodes.map((node) => node?.id).filter(Boolean);
  }
  if (Array.isArray(graph?.clusters)) {
    return graph.clusters.flatMap((cluster) => {
      const ids = [];
      if (cluster?.id) ids.push(cluster.id);
      if (Array.isArray(cluster?.subnodes)) {
        ids.push(...cluster.subnodes.map((node) => node?.id).filter(Boolean));
      }
      return ids;
    });
  }
  throw new Error('concept-node-ids-required');
}

function eventAttempt(event) {
  const attempt = requireObject(event.attempt, 'attempt');
  return attempt;
}

function eventRepair(event) {
  const repair = requireObject(event.repair, 'repair');
  return repair;
}

async function applyEvent(store, conceptId, event) {
  const type = event?.type;
  const nodeId = event?.node_id;
  if (!type) throw new Error('event-type-required');
  if (!nodeId) throw new Error('event-node-id-required');

  if (type === 'cold_attempt' || type === 'spaced_redrill') {
    await store.appendAttempt(conceptId, nodeId, eventAttempt(event));
    return;
  }
  if (type === 'study_reveal') {
    await store.setStudyRevealed(conceptId, nodeId, event.at);
    return;
  }
  if (type === 'repair') {
    await store.appendRepair(conceptId, nodeId, eventRepair(event));
    return;
  }
  if (type === 'gap_drill_noop') {
    return;
  }
  throw new Error(`event-type-unsupported:${type}`);
}

function summarizeNode(record, now, deriveNodeTraining) {
  const derived = deriveNodeTraining(record || null, { now });
  return {
    ...derived,
    attempt_count: Array.isArray(record?.attempts) ? record.attempts.length : 0,
    repair_count: Array.isArray(record?.repairs) ? record.repairs.length : 0,
    study_revealed_at: record?.study_revealed_at || null,
  };
}

function summarizeTraining(training, nodeIds, now, deriveNodeTraining, deriveConceptStatus) {
  const records = training?.node_records || {};
  const nodes = {};
  nodeIds.forEach((nodeId) => {
    nodes[nodeId] = summarizeNode(records[nodeId] || null, now, deriveNodeTraining);
  });
  return {
    nodes,
    concept_status: deriveConceptStatus(training, nodeIds, { now }),
  };
}

async function runFixture(fixturePath) {
  const { deriveConceptStatus, deriveNodeTraining } = await import('../public/js/training-derive.js');
  const { createTrainingStore } = await import('../public/js/training-store.js');

  const fixture = JSON.parse(await fs.readFile(fixturePath, 'utf8'));
  const concept = requireObject(fixture.concept, 'concept');
  const conceptId = concept.id || fixture.training?.concept_id;
  if (!conceptId) throw new Error('concept-id-required');
  const nodeIds = extractNodeIds(concept);
  const events = Array.isArray(fixture.events) ? fixture.events : [];
  const now = fixture.now || new Date().toISOString();

  const storage = createMemoryStorage();
  const store = createTrainingStore({ storage });
  const initialTraining = fixture.training || {
    concept_id: conceptId,
    schema_version: 1,
    node_records: {},
  };
  await store.saveTraining({ ...initialTraining, concept_id: conceptId });

  const trace = [];
  async function capture(event) {
    const training = await store.loadTraining(conceptId);
    trace.push({
      event,
      ...summarizeTraining(training, nodeIds, now, deriveNodeTraining, deriveConceptStatus),
    });
  }

  await capture('initial');
  for (const event of events) {
    await applyEvent(store, conceptId, event);
    await capture(event.type);
  }

  const training = await store.loadTraining(conceptId);
  return {
    concept_id: conceptId,
    source_mode: training?.source_mode || null,
    grounding: training?.grounding || null,
    node_ids: nodeIds,
    trace,
    training,
  };
}

function parseArgs(argv) {
  const options = {
    format: 'tui',
    fixture: null,
  };
  argv.slice(2).forEach((arg) => {
    if (arg === '--json') {
      options.format = 'json';
      return;
    }
    if (arg === '--tui-static') {
      options.format = 'tui-static';
      return;
    }
    if (arg === '--help' || arg === '-h') {
      options.format = 'help';
      return;
    }
    if (!options.fixture) {
      options.fixture = arg;
      return;
    }
    throw new Error(`unexpected-argument:${arg}`);
  });
  return options;
}

function resolveFixture(value) {
  if (!value) return null;
  return FIXTURE_ALIASES.get(value) || value;
}

function stateLabel(state) {
  return state || 'no evidence';
}

function nextLabel(nextAction) {
  return nextAction || 'none';
}

function finalTruthLine(output) {
  const states = output.trace.flatMap((step) => (
    Object.values(step.nodes).map((node) => node.state)
  ));
  if (!states.includes('solidified')) {
    return 'No solidified state recorded; study, repair, and gap drill stayed graph-neutral.';
  }
  return 'Only spaced strong reconstruction produced solidified.';
}

function formatNodeLine(nodeId, node) {
  return [
    nodeId.padEnd(17),
    stateLabel(node.state).padEnd(15),
    `next ${nextLabel(node.next_action).padEnd(14)}`,
    `Attempts: ${node.attempt_count}`,
    `Repairs: ${node.repair_count}`,
  ].join('  ');
}

function renderTuiScreen(output, selectedIndex) {
  const selected = output.trace[selectedIndex];
  const finalBadge = output.trace.at(-1)?.concept_status?.badge || 'none';
  const lines = [
    'Socratink Kernel TUI',
    '====================',
    `Concept: ${output.concept_id}`,
    `Mode: ${output.source_mode || 'unknown'} / ${output.grounding || 'unknown'}`,
    `Final badge: ${finalBadge}`,
    '',
    'Controls: up/down or j/k step through events, q quits',
    '',
    'Event Trace',
  ];

  output.trace.forEach((step, index) => {
    const marker = index === selectedIndex ? '>' : ' ';
    lines.push(`${marker} ${step.event}`);
  });

  lines.push('', 'Selected State');
  Object.entries(selected.nodes).forEach(([nodeId, node]) => {
    lines.push(formatNodeLine(nodeId, node));
  });

  lines.push('', 'Graph Truth');
  lines.push(finalTruthLine(output));

  return lines.join('\n');
}

function runTui(output) {
  let selectedIndex = output.trace.length - 1;

  function draw() {
    process.stdout.write('\x1b[?25l\x1b[2J\x1b[H');
    process.stdout.write(renderTuiScreen(output, selectedIndex));
  }

  function exit() {
    if (process.stdin.isTTY) process.stdin.setRawMode(false);
    process.stdout.write('\x1b[?25h\n');
    process.exit(0);
  }

  readline.emitKeypressEvents(process.stdin);
  if (process.stdin.isTTY) process.stdin.setRawMode(true);
  process.stdin.on('keypress', (_str, key = {}) => {
    if (key.name === 'q' || (key.ctrl && key.name === 'c')) exit();
    if (key.name === 'up' || key.name === 'k') {
      selectedIndex = Math.max(0, selectedIndex - 1);
      draw();
    }
    if (key.name === 'down' || key.name === 'j') {
      selectedIndex = Math.min(output.trace.length - 1, selectedIndex + 1);
      draw();
    }
  });
  draw();
  process.stdin.resume();
}

async function main(argv) {
  let options;
  try {
    options = parseArgs(argv);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    console.error(usage());
    process.exitCode = 2;
    return;
  }

  if (options.format === 'help') {
    console.log(usage());
    return;
  }

  const fixturePath = resolveFixture(options.fixture);
  if (!fixturePath) {
    console.error(usage());
    process.exitCode = 2;
    return;
  }

  try {
    const output = await runFixture(fixturePath);
    if (options.format === 'json') {
      console.log(JSON.stringify(output, null, 2));
      return;
    }
    if (options.format === 'tui-static' || !process.stdout.isTTY) {
      console.log(renderTuiScreen(output, output.trace.length - 1));
      return;
    }
    runTui(output);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

await main(process.argv);
