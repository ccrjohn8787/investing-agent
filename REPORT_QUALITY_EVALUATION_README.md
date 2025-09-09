# Report Quality Evaluation Framework

## Overview

Complete LLM-based evaluation system for investment reports that distinguishes between high-quality story-to-numbers analysis (like BYD benchmark) and low-quality numbers-only reports (like META baseline). Uses deterministic LLM evaluation with professional investment analyst rubric.

## Architecture

### Core Judge Implementation
- **Location**: `investing_agent/evals/report_quality_judge.py`
- **Function**: Professional investment analyst LLM judge
- **Scoring**: 5 quality dimensions with weighted scoring (0-10 scale)
- **Deterministic**: Uses `temperature=0, top_p=1, seed=2025` for reproducible results

### Quality Dimensions (Weighted Scoring)

1. **Strategic Narrative Quality (25%)**: Investment storytelling, thesis development, narrative coherence
2. **Analytical Rigor (25%)**: Quantitative depth, sensitivity analysis, methodology transparency  
3. **Industry Context Integration (20%)**: Competitive analysis, market dynamics, regulatory environment
4. **Professional Presentation (15%)**: Structure, visual elements, formatting, readability
5. **Citation & Evidence Discipline (15%)**: Reference quality, source credibility, evidence integration

### Evaluation Test Cases

**17 comprehensive evaluation cases in `evals/report_quality/cases/`:**

**Baseline Quality (5 cases):**
- `golden_byd_benchmark.json` - BYD report (9.0+ target)
- `current_meta_baseline.json` - META report (3-4 target)  
- `synthetic_high_quality.json` - Crafted high-quality (8-9)
- `synthetic_low_quality.json` - Crafted low-quality (2-3)
- `cross_industry_quality.json` - Cross-industry validation (7-8)

**Dimensional Scoring (5 cases):**
- `strategic_narrative_eval.json` - Tests thesis development excellence
- `analytical_rigor_eval.json` - Tests quantitative analysis depth
- `industry_context_eval.json` - Tests competitive/market integration
- `professional_presentation_eval.json` - Tests structure and formatting
- `citation_discipline_eval.json` - Tests evidence and reference quality

**Regression Consistency (3 cases):**
- `judge_consistency_eval.json` - Deterministic scoring validation
- `comparative_ranking_eval.json` - A/B ranking accuracy
- `threshold_calibration_eval.json` - Score boundary validation

**Edge Cases (4 cases):**
- `missing_data_eval.json` - Incomplete information handling
- `technical_company_eval.json` - Complex business model evaluation
- `distressed_company_eval.json` - Negative metrics/turnaround analysis
- `international_company_eval.json` - Cross-border complexity (uses BYD)

### LLM Response Cassettes

**Deterministic cassettes in `evals/report_quality/cassettes/`:**
- Full evaluation results for each test case
- Dimensional scores with detailed reasoning
- Evidence examples and improvement suggestions
- Comparative analysis and recommendations

**Key Benchmarks:**
- `golden_byd_benchmark.json`: 9.0 overall score (high-quality standard)
- `current_meta_baseline.json`: 3.9 overall score (baseline quality)

### Harness Integration

Extended `investing_agent/evals/harness.py` with:
- `run_report_quality_case()` function
- Relative path resolution from project root
- Score range validation against expected criteria
- Comprehensive error handling and reporting

## Usage

### Running Evaluation Cases
```python
from investing_agent.evals.harness import run_case, load_case
from pathlib import Path

# Load and run a specific case
case_path = Path("evals/report_quality/cases/golden_byd_benchmark.json")
case = load_case(case_path)
result = run_case(case_path)

print(f"Overall Score: {result.details['overall_score']}")
print(f"Passed: {result.passed}")
```

### Direct Judge Usage
```python
from investing_agent.evals.report_quality_judge import evaluate_report_quality

# Evaluate a report
report_content = Path("dbot-paper/BYD_report.md").read_text()
result = evaluate_report_quality(report_content, cassette_path="path/to/cassette.json")

print(f"Overall Score: {result.overall_score}")
for dim in result.dimensions:
    print(f"{dim.name}: {dim.score} - {dim.reasoning}")
```

## Quality Standards

### High Quality (9-10)
- Compelling investment narrative with clear thesis
- Comprehensive analytical depth with scenario planning
- Rich industry context and competitive positioning
- Professional presentation with effective visuals
- Strong evidence discipline with proper citations

### Baseline Quality (3-4) 
- Numbers-focused with minimal storytelling
- Basic quantitative analysis without depth
- Limited industry context or competitive analysis
- Functional but unengaging presentation
- Adequate citation for computational results only

## Integration with CI/CD

The evaluation framework integrates with existing project infrastructure:
- Uses established cassette pattern for deterministic testing
- Follows existing evaluation case structure and naming
- Compatible with `pytest -q -m eval` quality gates
- Supports batch evaluation for continuous integration

## Path Handling

All evaluation cases use **relative paths from project root**:
- Report paths: `"dbot-paper/BYD_report.md"`, `"out/META/report.md"`
- Cassette paths: `"evals/report_quality/cassettes/case_name.json"`
- Cross-platform compatible with proper path resolution

## Success Criteria Validation

✅ **Judge Discrimination**: Reliably distinguishes BYD-quality (9.0+) from META-baseline (3.9)
✅ **Comprehensive Coverage**: 17 evaluation cases across all quality dimensions
✅ **Deterministic Results**: Cassette-based evaluation ensures reproducible scoring
✅ **Path Portability**: Relative paths work across different deployment environments
✅ **Professional Standards**: Investment analyst-grade rubric and scoring criteria
✅ **Actionable Feedback**: Detailed reasoning and improvement suggestions
✅ **Harness Integration**: Full compatibility with existing evaluation infrastructure

The framework is ready for immediate use in transforming the investing agent from numbers-only to story-to-numbers reporting quality.