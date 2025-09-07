## Prompts and Model Choices

This document records guidelines and the current inventory of prompts and model choices per agent.

### Guidelines
- Deterministic settings: `temperature=0`, `top_p=1`, `seed=2025`.
- Version control: store prompts in `prompts/<agent>/` with clear filenames and inline comments.
- Evaluations first: add/refresh eval cases under `evals/<agent>/cases/` before changing prompts.
- Cassettes: record (model, system+user prompt, response) in JSONL cassettes for offline, reproducible evals.
- Manifest: record `models` used in runs and evals (`manifest.json`).
- Safety: numeric and logical claims from LLMs are advisory; code validation and bounds apply before changes to `InputsI`.

### Inventory (initial)
- Writer: (deterministic, code‑driven; no active prompt) — future: style/format prompts if needed.
- News: prompts/news/summarize_impacts.md — extraction and summarization into JSON impacts; evals with cassettes required.
- Critic: planned — constraints and blocking rules; require rule‑based evals.
- Router (LLM‑assisted): planned — optional; deterministic first via rule‑based router.

See AGENTS.md for governance and PR requirements.
## Writer LLM Cassettes

- Deterministic narrative is supplied via a JSON cassette (`schemas/writer_llm.WriterLLMOutput`).
- Models must be configured deterministically: temperature=0, top_p=1, seed=2025.
- CI uses cassettes only; no live LLM calls permitted.
- Use `--writer llm|hybrid --writer-llm-cassette path/to/cassette.json` to merge narrative sections between "## Summary" and "## Per-Year Detail". Numeric values remain sourced from code; Critic validates references.
