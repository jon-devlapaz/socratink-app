#!/usr/bin/env node

import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const REPO_ROOT = process.cwd();
const TUI_DIR = path.join(REPO_ROOT, 'scripts/socratink_tui');
const CASES_PATH = path.join(TUI_DIR, 'learning_cases/cases.jsonl');
const CONTRACTS_PATH = path.join(TUI_DIR, 'pedagogical_agents/contracts.json');
const NOTES_PATH = path.join(TUI_DIR, 'NOTES.md');

function parseArgs(argv) {
  const options = { json: false, color: 'auto' };
  for (const arg of argv.slice(2)) {
    if (arg === '--json') {
      options.json = true;
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
    'Usage: scripts/socratink-dashboard [--json] [--color=auto|always|never]',
    '',
    'Summarizes the local Socratink TUI/harness product lab for founder review.',
  ].join('\n');
}

function useColor(mode) {
  if (mode === 'always') return true;
  if (mode === 'never') return false;
  if (process.env.NO_COLOR) return false;
  return Boolean(process.stdout.isTTY);
}

function makePaint(enabled) {
  const c = {
    reset: '\x1b[0m',
    title: '\x1b[35m',
    section: '\x1b[36m',
    good: '\x1b[32m',
    warn: '\x1b[33m',
    dim: '\x1b[90m',
  };
  return {
    title: (text) => (enabled ? `${c.title}${text}${c.reset}` : text),
    section: (text) => (enabled ? `${c.section}${text}${c.reset}` : text),
    good: (text) => (enabled ? `${c.good}${text}${c.reset}` : text),
    warn: (text) => (enabled ? `${c.warn}${text}${c.reset}` : text),
    dim: (text) => (enabled ? `${c.dim}${text}${c.reset}` : text),
  };
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function loadCases() {
  const raw = await fs.readFile(CASES_PATH, 'utf8');
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line) => JSON.parse(line));
}

function summarizeCases(cases) {
  return {
    total: cases.length,
    active_regression: cases.filter((c) => c.promotion_status === 'active_regression').length,
    golden: cases.filter((c) => c.case_type === 'golden').length,
    research: cases.filter((c) => c.case_type === 'research').length,
  };
}

async function loadTrace(caseRecord) {
  const session = await readJson(path.join(REPO_ROOT, caseRecord.session_log));
  const firstNodeId = session.route?.first_node?.id;
  return {
    case_id: caseRecord.case_id,
    concept: session.concept,
    event_count: Array.isArray(session.events) ? session.events.length : 0,
    final_state: firstNodeId ? session.derived?.at(-1)?.nodes?.[firstNodeId]?.state || null : null,
    event_order: Array.isArray(session.events) ? session.events.map((event) => event.type) : [],
  };
}

function notesContain(notes, text) {
  return notes.toLowerCase().includes(text.toLowerCase());
}

async function buildDashboard() {
  const [cases, contracts, notes] = await Promise.all([
    loadCases(),
    readJson(CONTRACTS_PATH),
    fs.readFile(NOTES_PATH, 'utf8'),
  ]);
  const traces = await Promise.all(cases.map(loadTrace));
  const latestTrace = traces.at(-1) || null;
  const routeRetryNeeded = notesContain(notes, 'route-generation retry')
    || notesContain(notes, 'route generator needs a recoverable retry path')
    || notesContain(notes, 'SmallestRouteCapExceeded');
  const routeRetryImplemented = notesContain(notes, 'Route Retry Implementation')
    || notesContain(notes, 'route retry/rewrite handling is implemented');
  const deepseekRerunComplete = notesContain(notes, 'DeepSeek Retry Rerun');
  const deepseekSignal = notesContain(notes, 'DeepSeek Simulated Learner Attempt')
    ? deepseekRerunComplete
      ? 'DeepSeek rerun completed; simulated learner still needs output-shape guardrails.'
      : 'DeepSeek simulated learner exposed learner-shape drift and route validation crashes.'
    : 'No DeepSeek simulated learner run logged yet.';

  return {
    title: 'Socratink Founder Dashboard',
    truth_contract: contracts.architecture.truth_contract,
    guardrails: [
      'Generation Before Recognition',
      'source_goal_context_not_evidence',
      'training_derivation',
      'model_bridge_after_generation',
      'spaced_strong_reconstruction_only_for_solidified',
    ],
    case_summary: summarizeCases(cases),
    case_ids: cases.map((c) => c.case_id),
    latest_trace: latestTrace,
    route_retry_status: routeRetryImplemented ? 'implemented' : 'needed',
    deepseek_rerun_status: deepseekRerunComplete ? 'complete' : 'pending',
    simulated_learner_status: deepseekSignal,
    next_product_target: deepseekRerunComplete
      ? 'Add simulated learner output-shape guardrails, then promote over-complete tutor answers into a harness case.'
      : routeRetryImplemented
        ? 'Rerun DeepSeek simulated learner against real route/evaluator seam and promote any new failure.'
      : routeRetryNeeded
        ? 'Add route retry/rewrite handling for SmallestRouteCapExceeded, then rerun DeepSeek simulated learner.'
      : 'Promote the next failed dogfood run into a replay case.',
    commands: {
      live_tui: 'scripts/socratink-tui',
      replay: 'scripts/socratink-harness replay',
      dashboard: 'scripts/socratink-dashboard',
    },
  };
}

function printDashboard(data, paint) {
  console.log(paint.title(data.title));
  console.log('============================');
  console.log('');

  console.log(paint.section('Truth Contract'));
  console.log(data.truth_contract);
  console.log('');

  console.log(paint.section('Harness Cases'));
  console.log(`Active regressions: ${paint.good(String(data.case_summary.active_regression))}`);
  console.log(`Golden cases: ${data.case_summary.golden}`);
  console.log(`Research cases: ${data.case_summary.research}`);
  console.log(`Total: ${data.case_summary.total}`);
  console.log('');

  console.log(paint.section('Latest Portable Trace'));
  if (data.latest_trace) {
    console.log(`${data.latest_trace.case_id}`);
    console.log(`Concept: ${data.latest_trace.concept}`);
    console.log(`Final state: ${data.latest_trace.final_state}`);
    console.log(`Events: ${data.latest_trace.event_order.join(' -> ')}`);
  } else {
    console.log(paint.warn('No replay traces found.'));
  }
  console.log('');

  console.log(paint.section('DeepSeek Simulated Learner'));
  console.log(data.simulated_learner_status);
  console.log(`Route retry: ${data.route_retry_status}`);
  console.log(`Rerun: ${data.deepseek_rerun_status}`);
  console.log('');

  console.log(paint.section('Next Product Target'));
  console.log(data.next_product_target);
  console.log('');

  console.log(paint.section('Commands'));
  console.log(`Run TUI: ${paint.dim(data.commands.live_tui)}`);
  console.log(`Replay cases: ${paint.dim(data.commands.replay)}`);
  console.log(`Refresh dashboard: ${paint.dim(data.commands.dashboard)}`);
}

async function main() {
  try {
    const options = parseArgs(process.argv);
    if (options.help) {
      console.log(usage());
      return;
    }
    const data = await buildDashboard();
    if (options.json) {
      console.log(JSON.stringify(data, null, 2));
      return;
    }
    printDashboard(data, makePaint(useColor(options.color)));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

await main();
