import { useCallback, useEffect, useRef, useState } from 'react';
import {
  listBranches,
  listCommits,
  compareBranches,
  listPulls,
  getCheckRuns,
} from './api.js';
import {
  BRANCH_PALETTE,
  EMPTY_TRANSITIONS,
  assignLane,
  computeGraph,
  computeTransitions,
  mergeTransitions,
} from './graphTransforms.js';

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
        mainBranch: MAIN,
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
