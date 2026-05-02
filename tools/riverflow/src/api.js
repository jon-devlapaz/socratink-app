const TOKEN = import.meta.env.VITE_GITHUB_TOKEN;
const OWNER = import.meta.env.VITE_GITHUB_OWNER;
const REPO = import.meta.env.VITE_GITHUB_REPO;
const BASE = `https://api.github.com/repos/${OWNER}/${REPO}`;

function headers() {
  return {
    Authorization: `Bearer ${TOKEN}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

async function gh(path, opts = {}) {
  const res = await fetch(path.startsWith('http') ? path : `${BASE}${path}`, {
    ...opts,
    headers: { ...headers(), ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub ${res.status} ${path}: ${text.slice(0, 300)}`);
  }
  return res.status === 204 ? null : res.json();
}

export const repoCoords = { owner: OWNER, repo: REPO };

export const listBranches = () => gh('/branches?per_page=100');

export const listCommits = (sha, perPage = 50) =>
  gh(`/commits?sha=${encodeURIComponent(sha)}&per_page=${perPage}`);

export const compareBranches = (base, head) =>
  gh(`/compare/${encodeURIComponent(base)}...${encodeURIComponent(head)}`);

export const listPulls = () => gh('/pulls?state=all&per_page=100');

export const createBranch = (name, sha) =>
  gh('/git/refs', {
    method: 'POST',
    body: JSON.stringify({ ref: `refs/heads/${name}`, sha }),
  });

export const createPull = ({ title, body, head, base }) =>
  gh('/pulls', {
    method: 'POST',
    body: JSON.stringify({ title, body, head, base }),
  });

export const mergePull = (number) =>
  gh(`/pulls/${number}/merge`, {
    method: 'PUT',
    body: JSON.stringify({ merge_method: 'merge' }),
  });

export const getCheckRuns = (sha) =>
  gh(`/commits/${sha}/check-runs?per_page=30`);

export const commitUrl = (sha) =>
  `https://github.com/${OWNER}/${REPO}/commit/${sha}`;
