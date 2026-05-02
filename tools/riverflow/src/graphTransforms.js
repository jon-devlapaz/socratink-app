export const BRANCH_PALETTE = [
  '#b4a9d9',
  '#d8a867',
  '#c79188',
  '#a3b39b',
  '#a594c1',
  '#cbb38b',
  '#9d8aaf',
];

export const EMPTY_TRANSITIONS = Object.freeze({
  newPRs: new Set(),
  mergedPRs: new Set(),
  branchTipChanges: new Set(),
});

export function assignLane(index) {
  const step = Math.floor(index / 2) + 1;
  return index % 2 === 0 ? step : -step;
}

export function computeGraph({ mainCommits, branchData, pulls, ciCache, mainBranch }) {
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
    .filter((b) => b.name !== mainBranch)
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

export function computeTransitions(prev, curr) {
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

export function mergeTransitions(a, b) {
  return {
    newPRs: new Set([...a.newPRs, ...b.newPRs]),
    mergedPRs: new Set([...a.mergedPRs, ...b.mergedPRs]),
    branchTipChanges: new Set([...a.branchTipChanges, ...b.branchTipChanges]),
  };
}
