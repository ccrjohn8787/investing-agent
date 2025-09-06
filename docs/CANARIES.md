Golden Canaries

Purpose
- Detect regressions by running deterministic, seeded inputs through the pipeline and comparing artifact hashes.

Layout
- `canaries/<TICKER>/inputs.json` — seeded `InputsI` JSON
- `canaries/<TICKER>/golden.json` — expected artifact hashes (see writer below)

Artifacts to hash
- `valuation` — JSON of `ValuationV`
- `report.md` — Markdown report text
- Optionally: `series.csv`, `fundamentals.csv`, `report.html`

Updating goldens
- Generate artifacts locally and write/update `golden.json` with `scripts/write_canary.py`:
  - `python scripts/write_canary.py canaries/SYN`
  - Or via Make: `make golden PATH=canaries/SYN`
  - Review diff and commit.

CI gating
- `tests/acceptance/test_canaries_golden.py` will:
  - Load `inputs.json`, compute valuation and render report
  - Run Critic checks to ensure hygiene
  - Compute sha256 for selected artifacts and compare with `golden.json`
- If `golden.json` is missing, the test is skipped (add golden to enable gating)
- Use `make golden_check` to run only the canary acceptance gate.
