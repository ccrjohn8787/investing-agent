"""Schemas for evaluation metrics storage and tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class EvaluationDimension(str, Enum):
    """Evaluation dimensions for report quality scoring."""
    
    STRATEGIC_NARRATIVE = "strategic_narrative"
    ANALYTICAL_RIGOR = "analytical_rigor"
    INDUSTRY_CONTEXT = "industry_context"
    PROFESSIONAL_PRESENTATION = "professional_presentation"
    CITATION_DISCIPLINE = "citation_discipline"


class QualityTrend(str, Enum):
    """Quality trend indicators."""
    
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


class EvaluationScore(BaseModel):
    """Individual dimension score with details."""
    
    dimension: EvaluationDimension
    score: float = Field(ge=0, le=10)
    max_score: float = Field(default=10.0)
    percentage: float = Field(ge=0, le=100)
    details: Optional[str] = None
    confidence: float = Field(ge=0, le=1, default=1.0)
    
    def model_post_init(self, __context) -> None:
        """Calculate percentage from score."""
        if self.max_score > 0:
            self.percentage = (self.score / self.max_score) * 100


class HardMetrics(BaseModel):
    """Hard metrics that gate quality checks."""
    
    evidence_coverage: float = Field(ge=0, le=1)
    citation_density: float = Field(ge=0)
    contradiction_rate: float = Field(ge=0, le=1)
    fixture_stability: bool = True
    numeric_accuracy: float = Field(ge=0, le=1, default=1.0)
    
    @property
    def passes_gates(self) -> bool:
        """Check if metrics pass quality gates."""
        return (
            self.evidence_coverage >= 0.80 and
            self.citation_density >= 0.70 and
            self.contradiction_rate <= 0.20 and
            self.fixture_stability
        )


class EvaluationResult(BaseModel):
    """Complete evaluation result for a report."""
    
    # Identification
    evaluation_id: str
    report_id: str
    ticker: str
    company: str
    
    # Timestamps
    report_timestamp: datetime
    evaluation_timestamp: datetime
    
    # Scoring
    dimensional_scores: List[EvaluationScore]
    overall_score: float = Field(default=0.0, ge=0, le=10)
    overall_percentage: float = Field(default=0.0, ge=0, le=100)
    
    # Metrics
    hard_metrics: HardMetrics
    passes_quality_gates: bool = False
    
    # Comparison
    benchmark_id: Optional[str] = "BYD_report_2024_11_04"
    benchmark_score: Optional[float] = 9.0
    score_vs_benchmark: Optional[float] = None
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    priority_improvements: List[str] = Field(default_factory=list)
    
    # Metadata
    evaluator_model: str = "gpt-4"
    evaluation_version: str = "1.0.0"
    evaluation_config: Dict[str, Any] = Field(default_factory=dict)
    
    def model_post_init(self, __context) -> None:
        """Calculate derived fields."""
        if self.dimensional_scores:
            self.overall_score = sum(s.score for s in self.dimensional_scores) / len(self.dimensional_scores)
            self.overall_percentage = (self.overall_score / 10.0) * 100
        
        if self.benchmark_score:
            self.score_vs_benchmark = self.overall_score - self.benchmark_score
        
        self.passes_quality_gates = self.hard_metrics.passes_gates and self.overall_score >= 6.0


class EvaluationHistory(BaseModel):
    """Historical evaluation results for a ticker."""
    
    ticker: str
    company: str
    evaluations: List[EvaluationResult]
    
    @property
    def latest_evaluation(self) -> Optional[EvaluationResult]:
        """Get the most recent evaluation."""
        if not self.evaluations:
            return None
        return max(self.evaluations, key=lambda e: e.evaluation_timestamp)
    
    @property
    def average_score(self) -> float:
        """Calculate average score across all evaluations."""
        if not self.evaluations:
            return 0.0
        return sum(e.overall_score for e in self.evaluations) / len(self.evaluations)
    
    @property
    def score_trend(self) -> QualityTrend:
        """Determine quality trend over time."""
        if len(self.evaluations) < 2:
            return QualityTrend.INSUFFICIENT_DATA
        
        recent = sorted(self.evaluations, key=lambda e: e.evaluation_timestamp)[-5:]
        if len(recent) < 2:
            return QualityTrend.INSUFFICIENT_DATA
        
        scores = [e.overall_score for e in recent]
        avg_first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        avg_second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        
        if avg_second_half > avg_first_half + 0.5:
            return QualityTrend.IMPROVING
        elif avg_second_half < avg_first_half - 0.5:
            return QualityTrend.DECLINING
        else:
            return QualityTrend.STABLE


class DimensionalAnalysis(BaseModel):
    """Analysis of performance across dimensions."""
    
    dimension: EvaluationDimension
    current_score: float
    target_score: float = 8.0
    gap: float = 0.0
    historical_scores: List[float] = Field(default_factory=list)
    trend: QualityTrend = QualityTrend.INSUFFICIENT_DATA
    
    def model_post_init(self, __context) -> None:
        """Calculate gap and trend."""
        self.gap = self.target_score - self.current_score
        
        if len(self.historical_scores) >= 3:
            recent = self.historical_scores[-3:]
            if recent[-1] > recent[0] + 0.5:
                self.trend = QualityTrend.IMPROVING
            elif recent[-1] < recent[0] - 0.5:
                self.trend = QualityTrend.DECLINING
            else:
                self.trend = QualityTrend.STABLE


class EvaluationSummary(BaseModel):
    """Summary statistics across multiple evaluations."""
    
    total_evaluations: int = 0
    average_score: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 10.0
    
    dimensional_summaries: Dict[EvaluationDimension, DimensionalAnalysis] = Field(default_factory=dict)
    
    passing_rate: float = 0.0  # Percentage passing quality gates
    improvement_rate: float = 0.0  # Percentage showing improvement
    
    top_performers: List[str] = Field(default_factory=list)  # Tickers with highest scores
    needs_attention: List[str] = Field(default_factory=list)  # Tickers needing improvement
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ImprovementRecommendation(BaseModel):
    """Specific improvement recommendation."""
    
    recommendation_id: str
    category: EvaluationDimension
    priority: int = Field(ge=1, le=5)  # 1 = highest priority
    
    title: str
    description: str
    expected_impact: float = Field(ge=0, le=10)  # Expected score improvement
    
    implementation_effort: str = Field(default="medium")  # low, medium, high
    implementation_guide: Optional[str] = None
    
    examples: List[str] = Field(default_factory=list)
    related_files: List[str] = Field(default_factory=list)
    
    status: str = Field(default="pending")  # pending, in_progress, completed
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class EvaluationConfig(BaseModel):
    """Configuration for evaluation runs."""
    
    # Model settings
    evaluator_model: str = "gpt-4"
    temperature: float = 0.0
    max_tokens: int = 4000
    
    # Thresholds
    min_quality_score: float = 6.0
    target_quality_score: float = 8.0
    excellence_threshold: float = 9.0
    
    # Weights for dimensional scoring
    dimension_weights: Dict[EvaluationDimension, float] = Field(
        default_factory=lambda: {
            EvaluationDimension.STRATEGIC_NARRATIVE: 0.25,
            EvaluationDimension.ANALYTICAL_RIGOR: 0.25,
            EvaluationDimension.INDUSTRY_CONTEXT: 0.20,
            EvaluationDimension.PROFESSIONAL_PRESENTATION: 0.15,
            EvaluationDimension.CITATION_DISCIPLINE: 0.15,
        }
    )
    
    # Evaluation options
    enable_benchmark_comparison: bool = True
    enable_recommendations: bool = True
    enable_trend_analysis: bool = True
    
    # Output options
    generate_detailed_report: bool = True
    save_to_database: bool = True
    send_notifications: bool = False


class EvaluationBatch(BaseModel):
    """Batch evaluation results."""
    
    batch_id: str
    batch_timestamp: datetime
    config: EvaluationConfig
    
    evaluations: List[EvaluationResult]
    summary: EvaluationSummary
    
    processing_time_seconds: float = 0.0
    total_cost_usd: float = 0.0
    
    def model_post_init(self, __context) -> None:
        """Generate summary from evaluations."""
        if not self.evaluations:
            return
        
        self.summary.total_evaluations = len(self.evaluations)
        self.summary.average_score = sum(e.overall_score for e in self.evaluations) / len(self.evaluations)
        self.summary.highest_score = max(e.overall_score for e in self.evaluations)
        self.summary.lowest_score = min(e.overall_score for e in self.evaluations)
        
        passing = sum(1 for e in self.evaluations if e.passes_quality_gates)
        self.summary.passing_rate = (passing / len(self.evaluations)) * 100
        
        # Top performers and needs attention
        sorted_evals = sorted(self.evaluations, key=lambda e: e.overall_score, reverse=True)
        self.summary.top_performers = [e.ticker for e in sorted_evals[:3] if e.overall_score >= 8.0]
        self.summary.needs_attention = [e.ticker for e in sorted_evals if e.overall_score < 6.0]