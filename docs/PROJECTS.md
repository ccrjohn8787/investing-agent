## Project Breakdown and Interfaces

This document decomposes the roadmap into focused projects sized for delegation to execution agents. Each project defines its purpose, deliverables, primary interfaces (schemas and functions), and acceptance checks (eval/tests).

### P0 — Consensus Smoothing (M5 finalize)
- Purpose: Add configurable smoothing for consensus mapping (trend back to stable via slope/half-life), preserving bounds.
- Code: `investing_agent/agents/consensus.py`
- Interfaces:
  - Input: `InputsI`, `consensus_data: dict` (arrays `revenue/ebit` and/or `growth/margin`)
  - Output: `InputsI` (updated paths), deterministic
- Evals/Tests:
  - Extend `evals/consensus/cases/` with smoothing cases (`tail_to_stable`)
  - Unit tests ensure tail converges to stable and bounds adhered

### P1 — LLM Writer v1 (M12)
- Purpose: Generate narrative sections (JSON) as an overlay on code numbers; keep numeric integrity via tokens.
- New Schemas: `investing_agent/schemas/writer_llm.py`
- New Prompts: `prompts/writer/` (deterministic; document in `docs/PROMPTS.md`)
- New Module: `investing_agent/agents/writer_llm.py` (renderer + post-processor) [planned]
- Interfaces:
  - Input: NarrativeContext (compose from `InputsI`, `ValuationV`, selected tables/sections, optional InsightBundle)
  - Output: `WriterLLMOutput` (JSON) → merged by post-processor into final Markdown
  - CLI: `scripts/report.py --writer llm|code|hybrid`
- Evals/Tests:
  - Cases in `evals/writer_llm/cases/` using cassettes; wrapper in `tests/evals/test_writer_llm_evals.py`
  - Checks: required sections, min `[ref:]` token coverage, citations present

### P2 — Research v1 (M11.5)
- Purpose: Deterministically retrieve filings/news text and structure them; LLM summarization to InsightCards occurs under Writer agent.
- New Schemas: `investing_agent/schemas/research.py` (EvidenceSpan, InsightCard, InsightBundle)
- New Connectors (planned): `investing_agent/connectors/filings.py` (text snapshots with hashes)
- Interfaces:
  - Retrieval: functions to fetch and cache text; produce snapshot entries for manifest
  - Output: `InsightBundle` (cards) produced by Writer-LLM using retrieved texts
- Evals/Tests:
  - Cases in `evals/research/cases/` using cassettes; wrapper in `tests/evals/test_research_evals.py`
  - Checks: min cards, ≥1 snapshot per card, quotes present, drivers from allowed set

### P3 — Critic (LLM assist) (M12)
- Purpose: Optional LLM lint that flags unsupported claims or style issues; rule-based Critic remains the gate.
- Interfaces:
  - Input: Markdown report, `InputsI`, `ValuationV`, optional manifest
  - Output: Issues list (JSON) with severities; integrated into supervisor gating
- Evals/Tests:
  - Seeded violations; ensure detection without false negatives on core rules

### P4 — Router polish (M4 polish)
- Purpose: Implement final convergence criteria and integration test for loop behavior.
- Code: `investing_agent/agents/router.py`, `scripts/supervisor.py`
- Interfaces:
  - Configurable thresholds and flags via scenario `router.*`
  - Deterministic selection among {market, consensus, comparables, news, sensitivity, end}
- Evals/Tests:
  - Unit tests for route sequencing; integration test for stopping conditions

### P5 — Caching & Performance (M11)
- Purpose: Unify connector caching (text + JSON), add TTLs, prefer caches in offline mode; optional safe parallelism.
- Code: `investing_agent/connectors/http_cache.py` (extend), usages in EDGAR/UST/News/Prices
- Interfaces:
  - `fetch_text(url, ttl_seconds)` and JSON helper
  - Scenario-driven TTL defaults; manifest snapshots record cache state
- Evals/Tests:
  - Unit tests for cache hits/misses and TTL logic

### P6 — Golden Canaries (M9)
- Purpose: Expand goldens (2–3 tickers), include narrative JSON when LLM Writer enabled, and gate CI.
- Artifacts: `canaries/<TICKER>/inputs.json`, `golden.json`
- Interfaces:
  - `scripts/write_canary.py` extended to hash narrative JSON
- Evals/Tests:
  - `tests/acceptance/test_canaries_golden.py` compares hashes and runs Critic

## Coordination & Handoff
- Determinism: All LLM calls use cassettes in CI; live runs must log `models` in manifest with deterministic params.
- Contracts: Schemas above are the stable IO for cross-project handoffs; do not change without updating evals and prompts.
- Provenance: InsightCards and Writer sections must reference snapshot SHAs or computed-table tokens; Critic will enforce.

