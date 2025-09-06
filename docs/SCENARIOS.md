Scenario Configuration

Overview
- Scenarios provide deterministic, versioned knobs for report/supervisor runs.
- They are YAML or JSON files loaded via `--scenario <name|path>`.
- Use cases: set builder defaults, router gating, market solver weights/bounds, and comparables cap.

Schema (YAML)
```
id: baseline                # string id for manifest/eventlog
description: Baseline scenario

horizon: 10                 # builder horizon (optional)
discounting: midyear        # end|midyear (optional)
stable_growth: 0.03         # optional
stable_margin: 0.12         # optional
beta: 1.0                   # optional
macro:                      # optional
  erp: 0.05
  country_risk: 0.00

router:                     # toggles for agents
  enable_market: true
  enable_consensus: false
  enable_comparables: false
  enable_news: false

market_solver:              # bounded least-squares settings
  weights:
    growth: 1.0
    margin: 1.0
    s2c: 0.5
  bounds:
    growth: [-0.05, 0.05]
    margin: [-0.03, 0.03]
    s2c: [-0.5, 0.5]
  steps: [5, 5, 5]          # optional coarse grid resolution

comparables:                # peer policy caps
  cap_bps: 100              # move stable_margin ≤ 100 bps toward peer median per pass
```

Locations
- Presets live under `configs/scenarios/`: `baseline.yaml`, `cautious.yaml`, `aggressive.yaml`.
- Pass a file path to use a custom scenario anywhere.

CLI Usage
- Report:
  - `python scripts/report.py TICKER --scenario baseline --html`
  - Merges scenario into config; records scenario hash in manifest.
- Supervisor (router loop):
  - `python scripts/supervisor.py TICKER --scenario cautious --market-target last_close --html`
  - Gated by `router.*`; applies comparables with `comparables.cap_bps`.
- Batch:
  - `python scripts/run_batch.py plans/byd.yaml --run`
  - Batch plan may include a top-level `scenario: baseline` and/or per-job `scenario` overrides.

Determinism
- Scenario content is recorded in `manifest.artifacts.scenario` (sha) to bind runs to settings.
- All numeric effects remain code-only and reproducible.

