// Build a fresh system instruction from the current graph snapshot.
// Called every turn — Gemini only sees what's actually on screen right now.

const TRIM = 80;

function clip(s) {
  if (!s) return '';
  const oneLine = s.split('\n')[0];
  return oneLine.length > TRIM ? oneLine.slice(0, TRIM) + '…' : oneLine;
}

export function buildSystemInstruction(graph, repoCoords, mainBranch) {
  const head =
    `You are riverflow's chat sidekick. The user is looking at a git ` +
    `visualization for ${repoCoords.owner}/${repoCoords.repo}. ` +
    `Be terse and technical. Reference SHAs (7-char) and branch names directly. ` +
    `If asked about something that isn't in the snapshot below, say so — do not ` +
    `invent commits, PRs, branches, dates, or CI states. No emoji.`;

  if (!graph) return head + '\n\n(graph not loaded yet)';

  const lines = [head, ''];

  const tip = graph.main[graph.main.length - 1];
  lines.push(
    `MAIN (${mainBranch}): ${graph.main.length} commits visible. ` +
      (tip ? `Tip: ${tip.short} "${clip(tip.message)}"` : ''),
  );

  if (graph.branches.length) {
    lines.push('', `BRANCHES (${graph.branches.length}):`);
    for (const b of graph.branches) {
      const tipCi = b.commits[b.commits.length - 1]?.ci || '-';
      lines.push(
        `- ${b.name}: +${b.ahead}/-${b.behind} ci=${tipCi} head=${b.headSha.slice(0, 7)}`,
      );
    }
  }

  const open = graph.pulls.filter((p) => p.state === 'open' && !p.merged);
  const merged = graph.pulls.filter((p) => p.merged);

  if (open.length) {
    lines.push('', `OPEN PRs (${open.length}):`);
    for (const p of open) {
      const num = p.number > 0 ? `#${p.number}` : '(pending)';
      lines.push(`- ${num} "${clip(p.title)}" ${p.head} → ${p.base}`);
    }
  }
  if (merged.length) {
    lines.push('', `RECENTLY MERGED (${Math.min(merged.length, 10)}):`);
    for (const p of merged.slice(0, 10)) {
      lines.push(`- #${p.number} "${clip(p.title)}" (${p.head} → ${p.base})`);
    }
  }

  // Most-recent main commits are the most useful context for "what just landed".
  lines.push('', 'RECENT MAIN COMMITS (newest first, up to 12):');
  const recent = [...graph.main].reverse().slice(0, 12);
  for (const c of recent) {
    const ci = c.ci ? ` [ci:${c.ci}]` : '';
    lines.push(`- ${c.short}${ci} "${clip(c.message)}" — ${c.author || 'unknown'}`);
  }

  return lines.join('\n');
}
