import { useCallback, useEffect, useRef, useState } from 'react';
import {
  listBranches,
  listCommits,
  compareBranches,
  listPulls,
  getCheckRuns,
} from './api.js';

function aggregateCheckRuns(payload) {
  if (!payload || !payload.check_runs || payload.check_runs.length === 0) {
    return null;
  }
  const runs = payload.check_runs;
  if (runs.some((r) => r.status !== 'completed')) return 'pending';
  const bad = new Set(['failure', 'timed_out', 'cancelled', 'action_required']);
  if (runs.some((r) => bad.has(r.conclusion))) return 'failure';
  return 'success';
}

const MAIN = import.meta.env.VITE_MAIN_BRANCH || 'main';
const POLL_MS = 30_000;
const PER_BRANCH_CAP = 50;

// Warm jewel tones from the socratink family — lavender, amber, rose,
// sage, violet, sand, lilac. Avoiding cool blues and neon greens.
const BRANCH_PALETTE = [
  '#b4a9d9',
  '#d8a867',
  '#c79188',
  '#a3b39b',
  '#a594c1',
  '#cbb38b',
  '#9d8aaf',
];

const EMPTY_TRANSITIONS = Object.freeze({
  newPRs: new Set(),
  mergedPRs: new Set(),
  branchTipChanges: new Set(),
});

function assignLane(index) {
  const step = Math.floor(index / 2) + 1;
  return index % 2 === 0 ? step : -step;
}

function computeGraph({ mainCommits, branchData, pulls, ciCache }) {
  const main = [...mainCommits].reverse().map((c, i) => ({
    sha: c.sha,
    short: c.sha.slice(0, 7),
    message: c.commit.message,
    author: c.commit.author?.name,
    date: c.commit.author?.date,
    x: i,
    y: 0,
    lane: 0,
    onMain: true,
    ci: ciCache?.get(c.sha) ?? null,
  }));
  const mainShaToX = new Map(main.map((n) => [n.sha, n.x]));
  const mainTipX = main.length - 1;

  const branches = branchData
    .filter((b) => b.name !== MAIN)
    .map((b, i) => {
      const lane = assignLane(i);
      const color = BRANCH_PALETTE[i % BRANCH_PALETTE.length];
      const mergeBaseSha = b.mergeBase;
      const forkX = mainShaToX.has(mergeBaseSha)
        ? mainShaToX.get(mergeBaseSha)
        : 0;

      const aheadCommits = (b.aheadCommits || []).map((c, idx) => ({
        sha: c.sha,
        short: c.sha.slice(0, 7),
        message: c.commit.message,
        author: c.commit.author?.name,
        date: c.commit.author?.date,
        x: forkX + idx + 1,
        y: lane,
        lane,
        onMain: false,
        branch: b.name,
        ci: ciCache?.get(c.sha) ?? null,
      }));

      const tip = aheadCommits[aheadCommits.length - 1] || {
        sha: b.headSha,
        short: b.headSha.slice(0, 7),
        x: forkX,
        y: lane,
      };

      return {
        name: b.name,
        color,
        lane,
        forkX,
        mergeBaseSha,
        commits: aheadCommits,
        tip,
        ahead: aheadCommits.length,
        behind: mainTipX - forkX,
        headSha: b.headSha,
      };
    });

  const branchByName = new Map(branches.map((b) => [b.name, b]));
  const annotatedPulls = pulls
    .map((p) => ({
      number: p.number,
      title: p.title,
      state: p.state,
      merged: !!p.merged_at,
      head: p.head?.ref,
      base: p.base?.ref,
      url: p.html_url,
      branch: branchByName.get(p.head?.ref) || null,
    }))
    .filter((p) => p.state === 'open' || p.merged);

  return { main, branches, pulls: annotatedPulls, mainTipX };
}

function computeTransitions(prev, curr) {
  if (!prev) return EMPTY_TRANSITIONS;
  const prevPRs = new Map(prev.pulls.map((p) => [p.number, p]));
  const newPRs = new Set();
  const mergedPRs = new Set();
  for (const p of curr.pulls) {
    const prior = prevPRs.get(p.number);
    if (!prior) {
      // Reconciliation guard: if prev contained an optimistic PR for the same
      // head→base, this real PR is its replacement, not a fresh observation.
      const replacingOptimistic = prev.pulls.some(
        (pp) => pp.optimistic && pp.head === p.head && pp.base === p.base,
      );
      if (!replacingOptimistic) newPRs.add(p.number);
    } else if (prior.state === 'open' && !prior.merged && p.merged) {
      mergedPRs.add(p.number);
    }
  }
  const prevBranchHeads = new Map(prev.branches.map((b) => [b.name, b.headSha]));
  const branchTipChanges = new Set();
  for (const b of curr.branches) {
    const priorSha = prevBranchHeads.get(b.name);
    if (priorSha && priorSha !== b.headSha) branchTipChanges.add(b.name);
  }
  return { newPRs, mergedPRs, branchTipChanges };
}

function mergeTransitions(a, b) {
  return {
    newPRs: new Set([...a.newPRs, ...b.newPRs]),
    mergedPRs: new Set([...a.mergedPRs, ...b.mergedPRs]),
    branchTipChanges: new Set([...a.branchTipChanges, ...b.branchTipChanges]),
  };
}

export function useGitGraph() {
  const [graph, setGraph] = useState(null);
  const [transitions, setTransitions] = useState(EMPTY_TRANSITIONS);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const inFlight = useRef(false);
  const prevSnapshot = useRef(null);
  const graphRef = useRef(null);
  const ciCache = useRef(new Map());

  useEffect(() => {
    graphRef.current = graph;
  }, [graph]);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const [branches, mainCommits, pulls] = await Promise.all([
        listBranches(),
        listCommits(MAIN, PER_BRANCH_CAP),
        listPulls(),
      ]);

      const nonMain = branches.filter((b) => b.name !== MAIN);
      const compares = await Promise.all(
        nonMain.map(async (b) => {
          try {
            const cmp = await compareBranches(MAIN, b.name);
            return {
              name: b.name,
              headSha: b.commit.sha,
              mergeBase: cmp.merge_base_commit?.sha,
              aheadCommits: cmp.commits || [],
            };
          } catch (e) {
            return {
              name: b.name,
              headSha: b.commit.sha,
              mergeBase: null,
              aheadCommits: [],
              compareError: e.message,
            };
          }
        }),
      );

      // Refresh CI for tip-ish commits (last 3 main + each branch tip).
      // Older commits keep their cached value; never expire.
      const tipShas = new Set();
      for (let i = 0; i < Math.min(3, mainCommits.length); i++) {
        tipShas.add(mainCommits[i].sha);
      }
      for (const cmp of compares) tipShas.add(cmp.headSha);
      const ciResults = await Promise.all(
        [...tipShas].map(async (sha) => {
          try {
            const data = await getCheckRuns(sha);
            return [sha, aggregateCheckRuns(data)];
          } catch {
            return [sha, null];
          }
        }),
      );
      for (const [sha, state] of ciResults) {
        if (state !== null) ciCache.current.set(sha, state);
      }

      const next = computeGraph({
        mainCommits,
        branchData: compares,
        pulls,
        ciCache: ciCache.current,
      });
      const diff = computeTransitions(prevSnapshot.current, next);
      prevSnapshot.current = next;
      setGraph(next);
      setTransitions(diff);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // Optimistic updates: apply locally and update prevSnapshot so the
  // reconciling poll won't re-trigger the same animation.
  const addOptimistic = useCallback((item) => {
    const current = graphRef.current;
    if (!current) return;

    if (item.kind === 'branch') {
      const mainShaToX = new Map(current.main.map((n) => [n.sha, n.x]));
      const forkX = mainShaToX.has(item.fromSha)
        ? mainShaToX.get(item.fromSha)
        : current.mainTipX;
      const lane = assignLane(current.branches.length);
      const color = BRANCH_PALETTE[current.branches.length % BRANCH_PALETTE.length];
      const newBranch = {
        name: item.name,
        color,
        lane,
        forkX,
        mergeBaseSha: item.fromSha,
        commits: [],
        tip: { sha: item.fromSha, short: item.fromSha.slice(0, 7), x: forkX, y: lane },
        ahead: 0,
        behind: current.mainTipX - forkX,
        headSha: item.fromSha,
        optimistic: true,
      };
      const next = { ...current, branches: [...current.branches, newBranch] };
      prevSnapshot.current = next;
      setGraph(next);
      // No transition signal — opacity 0.6 is the only "pending" cue.
      return;
    }

    if (item.kind === 'pr') {
      const branch = current.branches.find((b) => b.name === item.head) || null;
      const optimisticNumber = -Date.now();
      const newPR = {
        number: optimisticNumber,
        title: item.title,
        state: 'open',
        merged: false,
        head: item.head,
        base: item.base,
        url: null,
        branch,
        optimistic: true,
      };
      const next = { ...current, pulls: [...current.pulls, newPR] };
      prevSnapshot.current = next;
      setGraph(next);
      setTransitions((t) =>
        mergeTransitions(t, {
          newPRs: new Set([optimisticNumber]),
          mergedPRs: new Set(),
          branchTipChanges: new Set(),
        }),
      );
      return;
    }

    if (item.kind === 'merge') {
      const pulls = current.pulls.map((p) =>
        p.number === item.number
          ? { ...p, merged: true, state: 'closed', optimistic: true }
          : p,
      );
      const next = { ...current, pulls };
      prevSnapshot.current = next;
      setGraph(next);
      setTransitions((t) =>
        mergeTransitions(t, {
          newPRs: new Set(),
          mergedPRs: new Set([item.number]),
          branchTipChanges: new Set(),
        }),
      );
      return;
    }
  }, []);

  return { graph, error, loading, refresh, addOptimistic, transitions };
}
