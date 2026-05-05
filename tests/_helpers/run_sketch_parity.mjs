// tests/_helpers/run_sketch_parity.mjs
// Loads the shared parity fixture, runs the JS implementation, prints JSON rows.
// No deps — uses Node's built-in fs and URL handling.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { isSubstantiveSketch } from "../../public/js/sketch-validation.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(__dirname, "..", "fixtures", "sketch_validation_parity.json");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8"));

const rows = fixture.entries.map((entry, idx) => ({
  idx,
  text: entry.text,
  expected: entry.expected_substantive,
  actual: isSubstantiveSketch(entry.text),
}));

process.stdout.write(JSON.stringify(rows));
