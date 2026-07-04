# Test helpers

`tests/_helpers/` holds reusable test-only helpers that are safe for multiple
test modules to import.

- `node_runner.py`: runs inline Node ES modules from the repo root
- `provisional_map_factory.py`: builds ProvisionalMap fixtures for route tests
- `run_sketch_parity.mjs`: runs the JavaScript sketch-validation parity check

Keep helpers here when the alternative is copying setup code between tests.
