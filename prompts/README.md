## Prompts Directory

Prompts for LLM‑adjacent agents live here, organized per agent:

- `prompts/news/` — extraction and summarization prompts
- `prompts/writer/` — style/format (if we opt into LLM assistance)
- `prompts/critic/` — constraints and blocking criteria
- `prompts/router/` — optional LLM router prompts (deterministic rule‑based preferred)

Each prompt file should include:
- Header with model id and deterministic parameters
- Brief intent description and expected output schema
- Link to the corresponding eval cases under `evals/<agent>/cases/`

