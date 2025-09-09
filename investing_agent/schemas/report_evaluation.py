from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QualityDimension(BaseModel):
    """Individual quality dimension scoring with detailed feedback."""
    name: str
    score: float = Field(ge=0.0, le=10.0, description="Score from 0-10")
    reasoning: str = Field(description="Detailed explanation of the score")
    evidence: List[str] = Field(default_factory=list, description="Specific examples supporting the score")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Actionable recommendations")


class ReportQualityResult(BaseModel):
    """Complete evaluation result for a report."""
    overall_score: float = Field(ge=0.0, le=10.0, description="Weighted average of dimension scores")
    dimensions: List[QualityDimension] = Field(description="Individual dimension evaluations")
    comparative_analysis: Optional[str] = Field(None, description="Comparison with benchmark reports")
    recommendations: List[str] = Field(default_factory=list, description="High-level improvement recommendations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Evaluation context and parameters")


class EvaluationRubric(BaseModel):
    """Scoring criteria and benchmarks for report evaluation."""
    dimension_name: str
    scoring_criteria: Dict[str, str] = Field(description="Score ranges (e.g., '9-10', '7-8') to criteria description")
    benchmark_examples: Dict[str, str] = Field(default_factory=dict, description="Reference examples for each score level")
    weight: float = Field(default=1.0, description="Weight in overall score calculation")


class MetaEvaluationResult(BaseModel):
    """Results from evaluating the evaluator (judge quality assessment)."""
    judge_human_correlation: float = Field(description="Correlation coefficient with human expert scores")
    discrimination_accuracy: float = Field(description="Accuracy in distinguishing high vs low quality reports")
    consistency_variance: float = Field(description="Score variance across repeated evaluations")
    calibration_metrics: Dict[str, float] = Field(default_factory=dict, description="Various calibration statistics")
    validation_reports: List[str] = Field(default_factory=list, description="Reports used for validation")


class EvaluationCase(BaseModel):
    """Configuration for a specific evaluation test case."""
    name: str
    category: str = Field(description="One of: baseline, dimensional, regression, edge_case")
    report_path: str = Field(description="Path to report being evaluated")
    expected_score_range: Optional[Dict[str, List[float]]] = Field(None, description="Expected score ranges per dimension")
    benchmark_comparison: Optional[str] = Field(None, description="Reference report for comparison")
    test_focus: List[str] = Field(default_factory=list, description="Specific aspects being tested")


class QualityEvaluationConfig(BaseModel):
    """Configuration for quality evaluation system."""
    min_overall_score: float = Field(default=6.0)
    min_dimension_score: float = Field(default=5.0)
    require_human_validation: bool = Field(default=True, description="Require human validation for scores > 8.0")
    fail_on_judge_error: bool = Field(default=True)
    dimension_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "strategic_narrative": 0.25,
            "analytical_rigor": 0.25,
            "industry_context": 0.20,
            "professional_presentation": 0.15,
            "citation_discipline": 0.15
        }
    )