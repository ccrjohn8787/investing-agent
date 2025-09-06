## Project Rules for Agents

This document defines conventions and guardrails for agents in this project.

### LLM Boundaries
- Only the following agents may use an LLM: News, Writer, Critic.
- Numeric work (parsing, transforms, statistics, valuation, sensitivity) must be implemented in code, not via LLM.
- LLM determinism: `temperature=0`, `top_p=1`, `seed=2025`.
- Any LLM usage must be logged (model id, parameters) and reflected in the manifest (`models` section).

### Contracts
Every agent must declare a clear contract:
- Input schema: Pydantic model(s) or typed dataclasses defining required/optional fields.
- Output schema: Pydantic model(s) for stable downstream consumption.
- Operational policy: timeouts, retries/backoff, max tokens/latency budgets.
- Caching: stable cache keys incorporating (a) input payload hash, (b) code sha, (c) model id/params.
- Provenance hooks: ability to attach snapshot IDs (from the manifest) to outputs for traceability.

### Documentation
- Any module implementing non‑trivial math must include:
  - A top‑level docstring summarizing notation, equations, and assumptions.
  - A corresponding section in `docs/VALUATION_MATH.md`.
- Keep the docstring and the markdown section in sync when math evolves.

### Citations
- Every claim in reports must map to:
  - Snapshot IDs in the manifest (`snapshots`), or
  - Tables/series computed within the report (and reproducible from inputs).
- When referencing an external figure/table, include the snapshot `content_sha256` or a stable row filter.

### Testing
- Each agent should have unit tests for core behavior and failure modes.
- Integration tests should cover end‑to‑end flows across multiple agents.
- Maintain golden fixtures for canary tickers/runs to detect regressions.

### Eval‑First Requirement (LLM‑adjacent agents)
- No eval, no agent: before implementing or changing an agent that consumes or produces LLM output (News, Writer, Critic, Router when LLM‑assisted), add eval cases under `evals/<agent>/cases/` and a pytest wrapper under `tests/evals/`.
- Evals define expected behaviors and pass thresholds (e.g., citation coverage, forbidden content rules, structure checks). CI will run `pytest -m eval` and block merges on failures.
- LLM calls in evals must use cassettes (no live calls in CI). Include model id and parameters in the cassette metadata and manifest when applicable.

### Prompts & Models (Design and Governance)
- Prompts and model choices are product surface area:
  - Store prompts under `prompts/<agent>/` and document them in `docs/PROMPTS.md`.
  - Pin model IDs (e.g., `gpt-4.1-mini`) and parameters (`temperature=0`, `top_p=1`, `seed=2025`).
  - Record model ids/params in the run manifest (`models` block) and in eval cassettes.
- PR requirements for prompt/model changes:
  - Update or add eval cases demonstrating intended behavior and thresholds.
  - Include diffs to prompt files and a summary of changes in the PR description.
  - Attach or paste eval results (pass/fail deltas) and note any threshold adjustments.
  - Seek explicit reviewer sign‑off for prompt changes (`@maintainers`), even if code is unchanged.
- Determinism:
  - All LLM calls configured with deterministic params; any use of sampling or tools must still be reproducible and captured in cassettes.
  - Numeric outputs from LLMs are advisory only; conversions into `InputsI` must pass code validation and bounds.

### Failure Policy
- On upstream failures (network, parse, rate limit), degrade gracefully:
  - Prefer previously cached inputs/artifacts if available.
  - Annotate the report with the failure cause, fallback used, and missing sections.
- Never silently drop sections without adding context to the report and logs.

---

### Agent Contract Template

Use this template when creating or updating an agent.

- Name: <Agent Name>
- Purpose: <What it does and why it exists>
- Input schema: <Pydantic model(s) + parameters>
- Output schema: <Pydantic model(s) or return type>
- Parameters: <knobs/deltas/steps, defaults>
- Timeouts/Retry: <limits + backoff policy>
- Caching: <key formula (input hash + params + code sha), storage path>
- Provenance: <how snapshots/IDs are attached or referenced>
- Logging: <event types written to run.jsonl; fields included>
- Tests: <unit coverage points + integration coverage>
- Failure: <graceful degradation and annotations>

---

## Existing Agents

### Contribution & Review Policy (Git Workflow)
- No pushes to any remote (e.g., `origin`) without explicit approval from the maintainer (you) or a designated reviewer. The assistant MUST NOT execute `git push` unless explicitly instructed in the session.
- Default workflow:
  - Develop changes on a feature branch (not `main`).
  - Make focused commits locally and open a Pull Request (PR).
  - Attach eval results (including `pytest -m eval`), CI status, and a brief summary of changes.
  - Request approval from the maintainer or another designated agent/reviewer.
- Merges to `main` only after:
  - Reviewer approval.
  - All CI checks (lint, mypy, unit tests, evals) pass.
  - Any prompt/model changes include updated evals and cassettes per policy.
- Direct commits to `main` are prohibited.
- For agent operations: never call `git push` or set upstream without explicit approval in the session. When in doubt, stop and ask.

### Valuation (Builder)
- Name: Valuation Builder (`investing_agent/agents/valuation.py::build_inputs_from_fundamentals`)
- Purpose: Converts parsed fundamentals and macro settings into kernel `InputsI` with optional user‑provided driver paths.
- Input schema: `Fundamentals`; Parameters: `horizon`, `stable_growth`, `stable_margin`, `beta`, `macro`, `discounting`, optional `sales_growth_path`, `oper_margin_path`, `sales_to_capital_path`.
- Output schema: `InputsI` (validated equal path lengths via `horizon()`).
- Parameters: defaults derive from fundamentals (CAGR, TTM margins); WACC from macro (rf + (ERP + country) × beta).
- Timeouts/Retry: N/A (pure local compute).
- Caching: Suggested key = sha256({fundamentals, macro, overrides}) with code sha; stored as `out/<TICKER>/inputs.json`.
- Provenance: Builder relies on fundamentals parsed from SEC snapshot; manifest should include EDGAR snapshot metadata.
- Logging: `eventlog` entry `build_inputs` with input/output shas and duration.
- Tests: `tests/unit/test_builder_overrides_and_writer.py` (override behavior, trending vs verbatim).
- Failure: If overrides inconsistent (length mismatch handled by trend/clip), validation enforces horizon; raise with clear message.

### Sensitivity
- Name: Sensitivity (`investing_agent/agents/sensitivity.py::compute_sensitivity`)
- Purpose: Grid sensitivity over growth and margin paths, returning value‑per‑share matrix.
- Input schema: `InputsI`; Parameters: `growth_delta`, `margin_delta`, `steps` (tuple[int,int]).
- Output schema: `SensitivityResult` with `grid`, `growth_axis`, `margin_axis`, `base_value_per_share`.
- Timeouts/Retry: N/A (pure local compute).
- Caching: Key = sha256({InputsI, growth_delta, margin_delta, steps}); ephemeral.
- Provenance: Not applicable; derived from InputsI.
- Logging: `eventlog` entry `sensitivity` with grid shape and duration.
- Tests: `tests/unit/test_sensitivity.py` (monotonicity), writer tests for integration.
- Failure: Clamp margins/growth to reasonable bounds inside loop to avoid invalid kernel inputs.

### Writer (Markdown/HTML)
- Name: Writer (`investing_agent/agents/writer.py::render_report`, `investing_agent/agents/html_writer.py::render_html_report`)
- Purpose: Produce human‑readable reports (Markdown/HTML) from inputs, valuation outputs, and optional charts.
- Input schema: `InputsI`, `ValuationV`; Optional: sensitivity/driver charts, `Fundamentals`, `companyfacts_json` (HTML).
- Output schema: `str` (Markdown or HTML content).
- Parameters: N/A; uses supplied bytes for charts.
- Timeouts/Retry: N/A (pure formatting/compute).
- Caching: Artifacts saved to `out/<TICKER>/report.md` and `report.html`; shas recorded in manifest.
- Provenance: Embeds parsed fundamentals; HTML includes collapsible raw companyfacts JSON; citations should reference manifest snapshots.
- Logging: `eventlog` entries `writer_md` / `writer_html` with byte counts and duration.
- Tests: `tests/unit/test_builder_overrides_and_writer.py` (sections appear), `tests/unit/test_html_and_cli_parse.py` (HTML sections present).
- Failure: If charts/fundamentals absent, degrade gracefully (omit sections) and annotate.
- References: Summary bullets include inline tokens like `[ref:computed:valuation.value_per_share;table:Per-Year Detail;snap:<sha>]` to map claims to computed tables or snapshot IDs.

### Critic
- Name: Critic (`investing_agent/agents/critic.py::check_report`)
- Purpose: Deterministic hygiene checks on reports; validates structure, numbers appear, citations, and now resolves inline reference tokens.
- Reference resolution: Parses `[ref:...]` tokens and verifies:
  - `table:`/`section:` refer to present sections (e.g., `## Per-Year Detail`).
  - `snap:` hashes match known snapshot shas (from `InputsI.provenance.content_sha256`).
  - `computed:` keys are recognized (valuation fields).

### Market
- Name: Market (`investing_agent/agents/market.py::apply`)
- Purpose: Bounded multi‑driver least‑squares to reconcile intrinsic value with a target (e.g., last close) under scenario weights/bounds.
- Input schema: `InputsI`; Parameters: `target_value_per_share` (or `context.target_price`), optional `weights`, `bounds`, `steps`.
- Output schema: `InputsI` (nudged driver paths and stable values; terminal constraints respected).
- Determinism: coarse grid search with fixed steps; idempotent given inputs and params.
- Tests/Evals: `tests/unit/test_market_solver.py`, `evals/market/cases/`.

### Comparables
- Name: Comparables (`investing_agent/agents/comparables.py::apply`)
- Purpose: Minimal peer policy — move stable margin toward peer median within a cap (bps), no LLM math.
- Input schema: `InputsI`, `peers: list[dict]` with `stable_margin`, `policy.cap_bps`.
- Output schema: `InputsI` (updated stable margin within bounds).
- Tests/Evals: `tests/unit/test_consensus.py`, `evals/comparables/cases/`.

### Consensus
- Name: Consensus (`investing_agent/agents/consensus.py::apply`)
- Purpose: Map near‑term consensus/guidance into `InputsI` while clamping long‑term drivers.
- Input schema: `InputsI`, `consensus_data` dict supporting either:
  - Arrays `revenue` and `ebit` (map to growth/margin per year), and/or
  - Arrays `growth` and `margin` (directly override first N years)
- Output schema: `InputsI` (updated paths; per‑element bounds enforced; optional smoothing to stable).
- Provenance: Caller records consensus snapshot in manifest (`source=url/path`, `retrieved_at`, `content_sha256`).
- Tests/Evals: `tests/unit/test_consensus.py`, `evals/consensus/cases/`.

### News
- Name: News (`investing_agent/agents/news.py` + `investing_agent/connectors/news.py`)
- Purpose: Retrieve recent valuation-relevant news and propose bounded impacts to drivers.
- Input schema: `ticker`, optional `asof`, optional source list; code takes `InputsI` + scenario caps to inform clamping.
- Output schema: `NewsBundle`, `NewsSummary` (facts + impacts), and an updated `InputsI` after ingestion.
- Retrieval: Deterministic RSS/Atom (e.g., Yahoo Finance); snapshots recorded in manifest.
- LLM: Optional, deterministic (temp=0, top_p=1, seed=2025) for proposal generation; numeric changes always clamped in code.
- Tests/Evals: unit tests for ingestion and heuristics; eval cases; LLM cassettes before enabling live calls in CI.
