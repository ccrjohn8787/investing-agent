# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plan and Review

### Before starting work
- Always in plan mode to make a plan
- After get the plan, make sure you write the plan to .claude/tasks/TASK_NAME.md (create one if not exist)
- The plan should be a detailed implementation plan and the reasoning behind them, as well as tasks broken down.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan.

### While implementing
- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily hand over to other engineers.

### Active Development Plan
**Current Status:** All Major Priorities Complete - Production Ready System
- **Latest Achievement:** Minimalist HTML Reports as Default (Priority 8)
- **Architecture:** Clean, reliable HTML reports with full data transparency
- **Key Principles:** Reliability over complexity, complete data visibility, professional presentation

**Major Achievements:**
- ✅ P0: LLM-Based Report Evaluation Framework with 5-dimensional scoring
- ✅ P1: Evidence Pipeline with research-once-then-freeze architecture and Model-PR logging
- ✅ P2-P7: Complete professional report generation system with all features
- ✅ P8: Minimalist HTML Reports (Default) - Clean, reliable, data-rich reports
- ✅ Safety: API cost controls with gpt-5-mini as default model
- ✅ Model Integration: GPT-5 and GPT-5-mini support with fallback to GPT-4 models

**Current Focus:** System is production-ready for institutional-grade investment reports

## CRITICAL SAFETY RULES FOR API USAGE

⚠️ **NEVER run live data or call GPT API without explicit user permission**
- **ALWAYS ASK FIRST** before running any script that calls OpenAI API
- **DEFAULT TO gpt-5-mini** (standard mode) for all reports unless user explicitly requests premium
- **NEVER USE gpt-5** (premium mode) unless user specifically says "use premium" or "--premium"
- **COST AWARENESS**: 
  - gpt-5-mini (gpt-4o-mini): $0.0008/report (DEFAULT)
  - gpt-5 (gpt-4): $0.15/report (ONLY when explicitly requested)
- **BATCH LIMITS**: Never generate more than 3 reports in a row without asking
- **ALWAYS SHOW COST** before running: "This will cost approximately $X.XX"

### Examples of proper behavior:
- User: "Generate a report for AAPL" → Use standard mode (gpt-5-mini/gpt-4o-mini) by default
- User: "Generate a premium report for AAPL" → Use premium mode (gpt-5/gpt-4)
- User: "Generate reports for 10 companies" → ASK FIRST: "This will generate 10 reports at ~$0.008 total cost. Proceed?"

## Essential Commands

### Development Setup
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]
```

### Testing & Quality
- Run all tests: `pytest -q`
- Run evaluation tests: `pytest -q -m eval` (quality gates)
- Run acceptance/canary tests: `pytest -q -k canaries_golden`
- Lint: `ruff check .`
- Format: `ruff format .` 
- Type check: `mypy investing_agent`
- Full CI pipeline: `make ci` (lint + mypy + tests)

### Reporting & Demo (Minimalist HTML by Default)
- Generate demo report: `make demo` (synthetic data, no network)
- Build inputs for ticker: `make build_i CT=<TICKER>`
- Generate report for ticker: `make report CT=<TICKER>` (minimalist HTML, gpt-5-mini/gpt-4o-mini)
- Generate premium report: `python scripts/report.py <TICKER> --premium` (uses gpt-5/gpt-4)
- Generate with evaluation: `python scripts/report.py <TICKER> --evaluate`
- Generate without LLM: `python scripts/report.py <TICKER> --disable-llm`
- Generate interactive report (legacy): `python scripts/report.py <TICKER> --interactive`
- Web UI index: `make ui` (creates out/index.html)

### Evidence-Enhanced Reporting (NEW)
- Generate evidence-enhanced report: `python scripts/report_with_evidence.py <TICKER>`
- Disable evidence pipeline: `python scripts/report_with_evidence.py <TICKER> --disable-evidence`
- Set evidence confidence threshold: `python scripts/report_with_evidence.py <TICKER> --evidence-threshold 0.85`
- Force new research (ignore frozen): `python scripts/report_with_evidence.py <TICKER> --force-new-research`
- Use evidence cassette: `python scripts/report_with_evidence.py <TICKER> --evidence-cassette path/to/cassette.json`

### Evaluation & Quality Gates
- Evaluation report: `make eval_report`
- Golden canary generation: `make golden PATH=<path>`
- Golden canary check: `make golden_check`

### Evidence Pipeline Testing
- Run evidence integration tests: `python -m pytest evals/evidence_pipeline/test_evidence_integration.py -v`
- Run driver accuracy tests: `python -m pytest evals/evidence_pipeline/test_driver_accuracy.py -v`
- Run evidence evaluation framework: `python evals/evidence_pipeline/test_evidence_integration.py`

### Report Quality Evaluation
- Generate report + evaluate quality: `make eval_quality CT=<TICKER>`
- Evaluate existing report only: `make eval_quality_only CT=<TICKER>`
- Batch evaluate multiple reports: `make eval_quality_batch CT="TICKER1,TICKER2,TICKER3"`
- Run all quality evaluation tests: `make test_quality_evals`

## Architecture Overview

### Core Components

**Schemas** (`investing_agent/schemas/`): Typed Pydantic models for all inputs, outputs, and fundamentals data structures. This defines the data contracts across the system.

**Kernels** (`investing_agent/kernels/`): Pure NumPy valuation engine ("Ginzu") implementing DCF calculations with four key drivers: sales growth, operating margin, cost of capital (WACC), and reinvestment efficiency (sales-to-capital).

**Connectors** (`investing_agent/connectors/`): External data sources including SEC EDGAR (fundamentals), Stooq/Yahoo (prices), UST (risk-free rates), and news feeds. All with caching and offline fallbacks.

**Agents** (`investing_agent/agents/`): Modular processing units including:
- Valuation Builder: Converts fundamentals to kernel inputs
- Sensitivity: Grid analysis over driver variations  
- Writer: Markdown/HTML report generation
- Critic: Report validation and reference checking
- Market: Multi-driver solver for target reconciliation
- Consensus: Integrates analyst estimates and guidance
- Research Unified: Evidence-based research with 3-phase processing (NEW)

**Evidence Pipeline** (`investing_agent/orchestration/`): Research-once-then-freeze architecture including:
- Evidence Integration: Unified pipeline coordination and backward compatibility
- Evidence Processor: Evidence ingestion engine with quality validation
- Evidence Freezer: Immutability mechanism for research consistency  
- PR Logger: Model-PR log system for complete audit trail
- Snapshot Manager: Comprehensive provenance tracking system

### Key Design Principles

**Determinism**: All numeric computation is pure NumPy. LLM usage (when enabled) uses fixed parameters: `temperature=0`, `top_p=1`, `seed=2025`.

**Provenance**: Every artifact carries source URLs and content hashes. All data transformations are traceable through manifest files.

**Agent Boundaries**: Only Research Unified, Writer, and Critic agents may use LLMs. All valuation math must be implemented in code, not via LLM.

**Evaluation-First**: LLM-adjacent agents require eval cases under `evals/<agent>/cases/` before implementation or changes.

**Research-Once-Then-Freeze**: Evidence gathering occurs in a single comprehensive pass, then becomes immutable to prevent value drift and ensure reproducibility.

**Complete Audit Trail**: Every evidence-based driver change is logged with full provenance chain from source URL through snapshots to final valuation impact.

### Data Flow

#### Standard Pipeline
1. **Input Building**: Fundamentals from EDGAR + macro data → `InputsI` (via Builder agent)
2. **Valuation**: `InputsI` → Ginzu kernel → `ValuationV` outputs
3. **Enhancement**: Optional consensus, market solver, comparables adjustments
4. **Analysis**: Sensitivity analysis, driver plotting
5. **Reporting**: Writer agents generate Markdown/HTML with embedded charts
6. **Validation**: Critic agent validates structure and references

#### Evidence-Enhanced Pipeline (NEW)
1. **Input Building**: Fundamentals from EDGAR + macro data → `InputsI` (via Builder agent)
2. **Evidence Research**: Research Unified agent → Evidence Bundle (3-phase processing)
3. **Evidence Processing**: Evidence Processor → Driver changes with safety caps → Updated `InputsI`
4. **Evidence Freezing**: Evidence Freezer → Immutable evidence bundle with content hash
5. **Audit Logging**: PR Logger → Model-PR log with complete change provenance
6. **Valuation**: Updated `InputsI` → Ginzu kernel → `ValuationV` outputs
7. **Reporting**: Writer agents generate Markdown/HTML with evidence citations
8. **Validation**: Critic agent validates structure, references, and evidence citations

**Complete Provenance Chain:**
```
Source URL → Snapshot → Evidence Claims → Driver Changes → Valuation → Report
     ↓           ↓            ↓               ↓              ↓         ↓
Content Hash → Freeze → Model-PR Log → Audit Trail → Manifest → Citations
```

### Configuration & Scenarios

Scenarios are defined in `configs/scenarios/` with presets for baseline/cautious/aggressive assumptions. CLI supports both individual driver overrides and YAML/JSON config files with comprehensive settings including horizon, discounting mode, beta, and macro parameters.

### Testing Strategy

- Unit tests for kernels, connectors, and individual agents
- Integration tests for end-to-end flows
- Evaluation tests for LLM-adjacent components with cassettes
- Golden canaries for regression detection using deterministic inputs
- Quality gates enforce narrative coverage and citation requirements

## Evaluation Best Practices

### When to Run Evaluations

**After Major Development Milestones:**
- ✅ **Priority completion**: Run full evaluation suite after completing any priority (P0, P1, P2, etc.)
- ✅ **Agent changes**: Evaluate after modifying Writer, Critic, or any LLM-adjacent components
- ✅ **Model updates**: Re-evaluate when changing LLM models or prompt engineering
- ✅ **Architecture changes**: Evaluate after significant system architecture modifications

**Regular Quality Monitoring:**
- ✅ **Before commits**: Run `make test_quality_evals` before major commits
- ✅ **PR validation**: Include evaluation results in pull request descriptions
- ✅ **Release readiness**: Full evaluation suite before any production releases
- ✅ **Regression checks**: Evaluate when debugging quality regressions

### How to Run Evaluations

**Development Workflow:**
```bash
# 1. Generate fresh report and evaluate
make eval_quality CT=TICKER

# 2. Evaluate existing report only  
make eval_quality_only CT=TICKER

# 3. Batch evaluate multiple companies
make eval_quality_batch CT="META,BYD,AAPL,UBER"

# 4. Run full test suite
make test_quality_evals
```

**Evaluation Quality Gates:**
- **Minimum Score**: 6.0/10 overall (reports below this fail quality gates)
- **Dimensional Balance**: No dimension below 5.0/10
- **Regression Prevention**: Scores must not decrease from previous versions
- **Benchmark Tracking**: Track progress toward BYD benchmark (9.0+)

### Quality Scoring Reference

**Score Ranges:**
- **9-10**: Exceptional (BYD benchmark) - Professional story-to-numbers analysis
- **7-8**: Good - Solid professional quality with narrative depth
- **5-6**: Acceptable - Basic professional standards, passes quality gates
- **3-4**: Poor (META baseline) - Numbers-focused, minimal narrative
- **0-2**: Inadequate - Fails basic quality standards

**Evaluation Dimensions:**
- Strategic Narrative (25%) - Investment thesis and storytelling quality
- Analytical Rigor (25%) - Evidence depth and analytical methodology  
- Industry Context (20%) - Competitive analysis and market understanding
- Professional Presentation (15%) - Structure, flow, and readability
- Citation Discipline (15%) - Source attribution and evidence integration

### Evaluation Evolution Guidelines

**Rubric Refinement:**
- Adjust scoring criteria based on actual report analysis results
- Add new quality dimensions as system capabilities expand
- Calibrate thresholds using human expert validation

**Test Case Expansion:**  
- Add industry-specific evaluation cases
- Create time-sensitive evaluation scenarios
- Develop sector-specific quality rubrics

**Judge Improvement:**
- A/B test different LLM models and prompt strategies
- Validate scoring accuracy against human expert assessments
- Implement feedback loops for continuous calibration improvement

### Git Workflow

Per AGENTS.md: No direct pushes to main. Develop on feature branches, open PRs with eval results attached, and require maintainer approval before merging. All CI checks (lint, mypy, tests, evals) must pass.

## Git Commit and Push Best Practices

### When to Commit

**Commit Frequency:**
- ✅ **Feature milestones**: After completing logical units of work
- ✅ **Working state**: Whenever code is in a functional, testable state  
- ✅ **Before major changes**: Create checkpoint before refactoring
- ✅ **Daily progress**: At minimum, commit work-in-progress daily

**Commit Scope:**
- ✅ **Single purpose**: One logical change per commit
- ✅ **Complete feature**: Don't commit half-implemented features
- ✅ **Tested code**: Ensure commits pass basic tests before committing
- ✅ **Clean state**: No debugging code, print statements, or temporary files

### When to Push to Remote

**Push Timing:**
- ✅ **End of work session**: Push completed work before ending development sessions
- ✅ **Feature completion**: Push after completing features or sub-tasks
- ✅ **Collaboration needs**: Push when others need access to your changes
- ✅ **Backup safety**: Push regularly to prevent work loss

**Push Requirements:**
- ✅ **Quality gates**: All tests and evaluations must pass
- ✅ **Clean history**: Squash or clean up commit history before pushing
- ✅ **Documented changes**: Include clear commit messages and documentation
- ✅ **Branch strategy**: Push to feature branches, not directly to main

### Commit Message Format

```
type(scope): brief description in imperative mood

Longer explanation if needed, describing what changed and why.
Include evaluation results for major changes.

- Key change 1
- Key change 2  
- Key change 3

Closes #123
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `eval`, `perf`
**Scopes:** `agent`, `eval`, `kernel`, `connector`, `schema`, `ui`

### Branch Strategy

**Branch Naming:**
- `feature/descriptive-name` - New features
- `fix/issue-description` - Bug fixes  
- `eval/evaluation-improvement` - Evaluation system changes
- `refactor/component-name` - Code restructuring

**Workflow:**
1. Create feature branch from main: `git checkout -b feature/evaluation-framework`
2. Commit incremental progress with clear messages
3. Push feature branch regularly: `git push -u origin feature/evaluation-framework`
4. Create PR when feature is complete and evaluated
5. Merge after review and all quality gates pass

## LLM Integration Best Practices

### Authentication Setup
```bash
# Required for LLM functionality
export OPENAI_API_KEY="sk-..."           # Primary provider
export ANTHROPIC_API_KEY="sk-ant-..."    # Premium narrative generation

# Optional
export LLM_DEBUG=true                     # Enable debug logging
export LLM_COST_TRACKING=true           # Track usage costs
```

### Model Selection by Use Case
- **Story/Narrative**: `story-premium` (Claude 3.5 Sonnet) - Creative investment narratives
- **Research/Analysis**: `research-premium` (GPT-4 Turbo) - Market research, competitive analysis  
- **Evaluation/Judging**: `judge-primary` (GPT-4) - Deterministic report evaluation
- **Quick Tasks**: `quick-task` (GPT-4o Mini) - Summaries, quick analysis
- **Development**: `dev-test` (GPT-3.5 Turbo) - Testing and prototyping

### Usage Patterns
```python
# Good: Use appropriate model for task
from investing_agent.llm.enhanced_provider import call_story_model, call_research_model

# Generate investment narrative (creative)
story = call_story_model(messages, temperature=0.3)

# Analyze market trends (analytical)  
analysis = call_research_model(messages, temperature=0.0)

# Always include fallback strategies
response = provider.call("story-premium", messages, fallback_model="story-standard")
```

### Cost Management
- **Development**: Use `dev-test` model ($0.002/1K tokens)
- **Production**: Select appropriate tier based on quality needs
- **Monitoring**: Check `provider.get_usage_report()` regularly
- **Budgets**: Set cost limits and alerts for production usage

### Testing with Cassettes
```python
# Development: Record responses for testing
response = provider.call("story-premium", messages, 
                        cassette_path="cassettes/story_example.json")

# CI: Use recorded responses (no live calls)  
# Automatically loads cassette in CI environment
```

See `LLM_INTEGRATION_GUIDE.md` for detailed setup instructions and examples.