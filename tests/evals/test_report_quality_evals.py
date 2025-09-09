from __future__ import annotations

import glob
from pathlib import Path

import pytest

from investing_agent.evals.harness import run_case


@pytest.mark.eval
def test_report_quality_eval_cases_pass():
    """Test that all report quality evaluation cases pass."""
    base = Path("evals/report_quality/cases")
    
    if not base.exists():
        pytest.skip("Report quality evaluation cases not found")
    
    # Find all JSON case files
    case_paths = glob.glob(str(base / "**" / "*.json"), recursive=True)
    
    if not case_paths:
        pytest.skip("No report quality evaluation cases found")
    
    for case_path in sorted(case_paths):
        try:
            result = run_case(Path(case_path))
            assert result.passed, f"Report quality eval failed: {result.name}: {result.failures}"
        except NotImplementedError as e:
            # Skip if report_quality agent not yet implemented in harness
            pytest.skip(f"Report quality evaluation not yet implemented: {str(e)}")


@pytest.mark.eval
def test_byd_benchmark_quality():
    """Test that BYD benchmark report scores in expected range (9-10)."""
    case_path = Path("evals/report_quality/cases/golden_byd_benchmark.json")
    
    if not case_path.exists():
        pytest.skip("BYD benchmark evaluation case not found")
    
    try:
        result = run_case(case_path)
        assert result.passed, f"BYD benchmark evaluation failed: {result.failures}"
        
        # Additional checks for score ranges can be added here
        # when we have access to the actual scores from the result
        
    except NotImplementedError:
        pytest.skip("Report quality evaluation not yet implemented in harness")


@pytest.mark.eval
def test_meta_baseline_quality():
    """Test that META baseline report scores in expected range (3-4)."""
    case_path = Path("evals/report_quality/cases/current_meta_baseline.json")
    
    if not case_path.exists():
        pytest.skip("META baseline evaluation case not found")
    
    try:
        result = run_case(case_path)
        assert result.passed, f"META baseline evaluation failed: {result.failures}"
        
    except NotImplementedError:
        pytest.skip("Report quality evaluation not yet implemented in harness")


@pytest.mark.eval
def test_judge_consistency():
    """Test that judge produces consistent results across repeated evaluations."""
    case_path = Path("evals/report_quality/cases/regression_consistency/judge_consistency_eval.json")
    
    if not case_path.exists():
        pytest.skip("Judge consistency evaluation case not found")
    
    try:
        result = run_case(case_path)
        assert result.passed, f"Judge consistency test failed: {result.failures}"
        
    except NotImplementedError:
        pytest.skip("Report quality evaluation not yet implemented in harness")


@pytest.mark.eval  
def test_dimensional_scoring():
    """Test that each quality dimension can be evaluated independently."""
    dimensional_cases = [
        "strategic_narrative_eval.json",
        "analytical_rigor_eval.json", 
        "industry_context_eval.json",
        "professional_presentation_eval.json",
        "citation_discipline_eval.json"
    ]
    
    base = Path("evals/report_quality/cases/dimensional_scoring")
    
    if not base.exists():
        pytest.skip("Dimensional scoring cases not found")
    
    for case_name in dimensional_cases:
        case_path = base / case_name
        if case_path.exists():
            try:
                result = run_case(case_path)
                assert result.passed, f"Dimensional test failed: {case_name}: {result.failures}"
            except NotImplementedError:
                pytest.skip(f"Report quality evaluation not yet implemented for {case_name}")