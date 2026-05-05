// public/js/sketch-validation.js
//
// Substantiveness heuristic — JS port of models/sketch_validation.py.
// Verified against tests/fixtures/sketch_validation_parity.json by
// tests/test_frontend_sketch_validation.py. A divergence is a
// release-blocker per spec §5.3.
//
// Why /u everywhere: Python's \w is Unicode by default; JS's is ASCII-only.
// Without /u, the same input ("café résumé naïve …") would tokenize differently
// in the two languages and the parity fixture's unicode rows would silently
// fail. See models/sketch_validation.py "JS PORT NOTE" docstring.

export const MIN_SUBSTANTIVE_TOKENS = 8;

const DONT_KNOW_PATTERNS = [
  "idk",
  "i dont know",
  "i don't know",
  "no idea",
  "no clue",
  "dunno",
  "not sure",
];

const STOPWORDS = new Set(
  (
    "a an the and or but if of for in on at to from by with as is are was were " +
    "be been being do does did has have had this that these those it its"
  ).split(/\s+/)
);

const PUNCT_RE = /[^\p{L}\p{N}_\s]/gu;
const WHITESPACE_RE = /\s+/gu;
const REPEATED_CHAR_RE = /^(.)\1{4,}$/u;

function normalize(text) {
  let t = text.trim().toLowerCase();
  t = t.replace(PUNCT_RE, " ");
  t = t.replace(WHITESPACE_RE, " ");
  return t.trim();
}

function isDontKnow(normalized) {
  if (!normalized) return true;
  if (REPEATED_CHAR_RE.test(normalized)) return true;
  for (const pattern of DONT_KNOW_PATTERNS) {
    if (normalized === pattern) return true;
    if (normalized.startsWith(pattern + " ")) {
      const extra = normalized.slice(pattern.length + 1).split(/\s+/u).filter(Boolean);
      if (extra.length <= 3) return true;
    }
  }
  return false;
}

function countSubstantiveTokens(normalized) {
  const tokens = normalized.split(/\s+/u).filter((t) => t && t.length >= 2);
  let count = 0;
  for (const t of tokens) {
    if (!STOPWORDS.has(t)) count += 1;
  }
  return count;
}

export function isSubstantiveSketch(text) {
  if (text === null || text === undefined) return false;
  if (typeof text !== "string") return false;
  const normalized = normalize(text);
  if (!normalized) return false;
  if (isDontKnow(normalized)) return false;
  if (countSubstantiveTokens(normalized) < MIN_SUBSTANTIVE_TOKENS) return false;
  return true;
}
