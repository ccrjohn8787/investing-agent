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

### Failure Policy
- On upstream failures (network, parse, rate limit), degrade gracefully:
  - Prefer previously cached inputs/artifacts if available.
  - Annotate the report with the failure cause, fallback used, and missing sections.
- Never silently drop sections without adding context to the report and logs.

