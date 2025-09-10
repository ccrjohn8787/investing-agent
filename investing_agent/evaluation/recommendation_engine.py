"""Recommendation engine for improving report quality."""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid

from investing_agent.schemas.evaluation_metrics import (
    EvaluationResult,
    EvaluationDimension,
    ImprovementRecommendation,
    EvaluationHistory,
    DimensionalAnalysis,
    QualityTrend,
)
from investing_agent.storage.metrics_storage import MetricsStorage


class RecommendationEngine:
    """Engine for generating actionable improvement recommendations."""
    
    def __init__(self, storage: Optional[MetricsStorage] = None):
        """Initialize recommendation engine.
        
        Args:
            storage: Metrics storage instance
        """
        self.storage = storage or MetricsStorage()
        
        # Define recommendation templates
        self.recommendation_templates = self._load_recommendation_templates()
    
    def _load_recommendation_templates(self) -> Dict[str, Dict]:
        """Load recommendation templates by dimension and issue."""
        return {
            EvaluationDimension.STRATEGIC_NARRATIVE: {
                "low_score": {
                    "title": "Enhance Strategic Narrative",
                    "description": "The strategic narrative needs strengthening to provide a compelling investment thesis",
                    "implementation_guide": """
                    1. Start with a clear investment thesis statement
                    2. Connect business strategy to valuation drivers
                    3. Provide forward-looking strategic insights
                    4. Use storytelling techniques to engage readers
                    5. Link all claims to evidence with [ev:xxx] citations
                    """,
                    "related_files": [
                        "prompts/writer/investment_thesis_professional.md",
                        "prompts/writer/forward_strategy_professional.md"
                    ],
                    "expected_impact": 2.0
                },
                "declining_trend": {
                    "title": "Reverse Strategic Narrative Decline",
                    "description": "Strategic narrative quality has been declining - review recent changes",
                    "implementation_guide": """
                    1. Review recent prompt changes
                    2. Ensure evidence pipeline is providing strategic insights
                    3. Check LLM model performance
                    4. Validate strategic sections are being generated
                    """,
                    "expected_impact": 1.5
                }
            },
            EvaluationDimension.ANALYTICAL_RIGOR: {
                "low_score": {
                    "title": "Improve Analytical Depth",
                    "description": "Add more quantitative analysis and evidence-based reasoning",
                    "implementation_guide": """
                    1. Increase evidence gathering scope
                    2. Add more quantitative metrics and calculations
                    3. Strengthen logical flow between claims and conclusions
                    4. Cross-reference all assertions with data
                    5. Include sensitivity analysis and scenario planning
                    """,
                    "related_files": [
                        "investing_agent/agents/sensitivity.py",
                        "investing_agent/agents/research_unified.py"
                    ],
                    "expected_impact": 1.8
                }
            },
            EvaluationDimension.INDUSTRY_CONTEXT: {
                "low_score": {
                    "title": "Expand Industry Analysis",
                    "description": "Industry context and competitive positioning need more depth",
                    "implementation_guide": """
                    1. Enable comparables analysis if disabled
                    2. Add peer comparison visualizations
                    3. Include industry trends in evidence gathering
                    4. Analyze competitive dynamics
                    5. Position company within industry landscape
                    """,
                    "related_files": [
                        "investing_agent/agents/comparables.py",
                        "investing_agent/agents/peer_selection.py",
                        "prompts/writer/industry_analysis_professional.md"
                    ],
                    "expected_impact": 1.5
                }
            },
            EvaluationDimension.PROFESSIONAL_PRESENTATION: {
                "low_score": {
                    "title": "Enhance Report Presentation",
                    "description": "Improve formatting, structure, and visual elements",
                    "implementation_guide": """
                    1. Add professional charts and tables
                    2. Improve section organization
                    3. Enhance executive summary formatting
                    4. Add visual separators and highlights
                    5. Ensure consistent styling throughout
                    """,
                    "related_files": [
                        "investing_agent/agents/visualization_professional.py",
                        "investing_agent/agents/table_generator.py",
                        "investing_agent/agents/report_assembler.py"
                    ],
                    "expected_impact": 1.2
                }
            },
            EvaluationDimension.CITATION_DISCIPLINE: {
                "low_score": {
                    "title": "Strengthen Citation Discipline",
                    "description": "Increase evidence citations and attribution",
                    "implementation_guide": """
                    1. Review writer validation rules
                    2. Ensure all claims have [ev:xxx] citations
                    3. Increase evidence gathering breadth
                    4. Validate citation density metrics
                    5. Enable strict citation enforcement in critic
                    """,
                    "related_files": [
                        "investing_agent/agents/writer_validation.py",
                        "investing_agent/agents/critic.py"
                    ],
                    "expected_impact": 2.5
                }
            }
        }
    
    def generate_recommendations(
        self,
        evaluation: EvaluationResult,
        history: Optional[EvaluationHistory] = None
    ) -> List[ImprovementRecommendation]:
        """Generate recommendations based on evaluation results.
        
        Args:
            evaluation: Current evaluation result
            history: Historical evaluations for trend analysis
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []
        
        # Analyze dimensional scores
        for score in evaluation.dimensional_scores:
            if score.score < 6.0:
                rec = self._create_dimension_recommendation(
                    score.dimension,
                    score.score,
                    "low_score",
                    priority=1 if score.score < 5.0 else 2
                )
                recommendations.append(rec)
        
        # Analyze trends if history available
        if history and len(history.evaluations) >= 3:
            dimensional_analysis = self._analyze_dimensional_trends(history)
            for dim, trend in dimensional_analysis.items():
                if trend == QualityTrend.DECLINING:
                    rec = self._create_dimension_recommendation(
                        dim,
                        0,  # Score not relevant for trend
                        "declining_trend",
                        priority=2
                    )
                    recommendations.append(rec)
        
        # Check hard metrics
        hard_recs = self._analyze_hard_metrics(evaluation.hard_metrics)
        recommendations.extend(hard_recs)
        
        # Check specific issues
        specific_recs = self._analyze_specific_issues(evaluation)
        recommendations.extend(specific_recs)
        
        # Sort by priority and expected impact
        recommendations.sort(key=lambda r: (r.priority, -r.expected_impact))
        
        # Return top recommendations
        return recommendations[:10]
    
    def _create_dimension_recommendation(
        self,
        dimension: EvaluationDimension,
        score: float,
        issue_type: str,
        priority: int
    ) -> ImprovementRecommendation:
        """Create recommendation for a dimension issue.
        
        Args:
            dimension: Evaluation dimension
            score: Current score
            issue_type: Type of issue (low_score, declining_trend)
            priority: Recommendation priority
            
        Returns:
            Improvement recommendation
        """
        template = self.recommendation_templates.get(dimension, {}).get(issue_type, {})
        
        return ImprovementRecommendation(
            recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
            category=dimension,
            priority=priority,
            title=template.get("title", f"Improve {dimension.value}"),
            description=template.get("description", f"Score: {score:.1f}/10"),
            expected_impact=template.get("expected_impact", 1.0),
            implementation_effort="medium",
            implementation_guide=template.get("implementation_guide"),
            related_files=template.get("related_files", []),
            status="pending"
        )
    
    def _analyze_dimensional_trends(
        self,
        history: EvaluationHistory
    ) -> Dict[EvaluationDimension, QualityTrend]:
        """Analyze trends for each dimension.
        
        Args:
            history: Evaluation history
            
        Returns:
            Trend by dimension
        """
        dimensional_trends = {}
        
        # Get last 5 evaluations
        recent_evals = history.evaluations[:5]
        
        for dimension in EvaluationDimension:
            scores = []
            for eval in recent_evals:
                dim_score = next((s.score for s in eval.dimensional_scores 
                                 if s.dimension == dimension), None)
                if dim_score is not None:
                    scores.append(dim_score)
            
            if len(scores) >= 3:
                # Check trend
                if scores[0] < scores[-1] - 0.5:
                    dimensional_trends[dimension] = QualityTrend.DECLINING
                elif scores[0] > scores[-1] + 0.5:
                    dimensional_trends[dimension] = QualityTrend.IMPROVING
                else:
                    dimensional_trends[dimension] = QualityTrend.STABLE
        
        return dimensional_trends
    
    def _analyze_hard_metrics(self, hard_metrics) -> List[ImprovementRecommendation]:
        """Analyze hard metrics and generate recommendations.
        
        Args:
            hard_metrics: Hard metrics from evaluation
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if hard_metrics.evidence_coverage < 0.80:
            rec = ImprovementRecommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                category=EvaluationDimension.CITATION_DISCIPLINE,
                priority=1,
                title="Increase Evidence Coverage",
                description=f"Evidence coverage is {hard_metrics.evidence_coverage:.0%}, target is ≥80%",
                expected_impact=2.0,
                implementation_effort="low",
                implementation_guide="""
                1. Review uncited claims in report
                2. Add evidence gathering for unsupported assertions
                3. Ensure writer adds [ev:xxx] citations
                4. Validate with critic agent
                """,
                related_files=["investing_agent/agents/writer_validation.py"],
                status="pending"
            )
            recommendations.append(rec)
        
        if hard_metrics.citation_density < 0.70:
            rec = ImprovementRecommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                category=EvaluationDimension.CITATION_DISCIPLINE,
                priority=2,
                title="Improve Citation Density",
                description=f"Citation density is {hard_metrics.citation_density:.2f}, target is ≥0.70",
                expected_impact=1.5,
                implementation_effort="low",
                implementation_guide="""
                1. Add more evidence citations per paragraph
                2. Break up long paragraphs
                3. Ensure each claim has supporting evidence
                """,
                status="pending"
            )
            recommendations.append(rec)
        
        if hard_metrics.contradiction_rate > 0.20:
            rec = ImprovementRecommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                category=EvaluationDimension.ANALYTICAL_RIGOR,
                priority=1,
                title="Resolve Contradictions",
                description=f"Contradiction rate is {hard_metrics.contradiction_rate:.0%}, target is ≤20%",
                expected_impact=1.8,
                implementation_effort="medium",
                implementation_guide="""
                1. Review conflicting statements
                2. Ensure consistent narrative throughout
                3. Validate evidence doesn't conflict
                4. Check critic validation rules
                """,
                related_files=["investing_agent/agents/critic.py"],
                status="pending"
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _analyze_specific_issues(self, evaluation: EvaluationResult) -> List[ImprovementRecommendation]:
        """Analyze specific issues in the evaluation.
        
        Args:
            evaluation: Evaluation result
            
        Returns:
            List of specific recommendations
        """
        recommendations = []
        
        # Check if failing quality gates
        if not evaluation.passes_quality_gates:
            if evaluation.overall_score < 6.0:
                rec = ImprovementRecommendation(
                    recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                    category=EvaluationDimension.STRATEGIC_NARRATIVE,
                    priority=1,
                    title="Address Quality Gate Failure",
                    description=f"Overall score {evaluation.overall_score:.1f} is below minimum 6.0",
                    expected_impact=3.0,
                    implementation_effort="high",
                    implementation_guide="""
                    1. Review all dimensional scores
                    2. Focus on lowest scoring dimensions first
                    3. Ensure all Priority 1-6 components are enabled
                    4. Validate evidence pipeline is working
                    5. Check prompt quality and LLM performance
                    """,
                    status="pending"
                )
                recommendations.append(rec)
        
        # Check vs benchmark
        if evaluation.score_vs_benchmark and evaluation.score_vs_benchmark < -2.0:
            rec = ImprovementRecommendation(
                recommendation_id=f"rec_{uuid.uuid4().hex[:8]}",
                category=EvaluationDimension.PROFESSIONAL_PRESENTATION,
                priority=2,
                title="Close Gap to Benchmark",
                description=f"Score is {abs(evaluation.score_vs_benchmark):.1f} points below BYD benchmark",
                expected_impact=2.5,
                implementation_effort="high",
                implementation_guide="""
                1. Review BYD report structure and style
                2. Match professional presentation standards
                3. Add all required artifacts (charts, tables)
                4. Enhance narrative depth and coherence
                """,
                status="pending"
            )
            recommendations.append(rec)
        
        return recommendations
    
    def track_recommendation_progress(
        self,
        recommendation_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Track progress on a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            status: New status (pending, in_progress, completed)
            notes: Optional notes
            
        Returns:
            Success status
        """
        # In a real implementation, this would update the database
        # For now, just return True
        return True
    
    def get_implementation_roadmap(
        self,
        ticker: str,
        max_recommendations: int = 5
    ) -> Dict[str, Any]:
        """Generate implementation roadmap for a ticker.
        
        Args:
            ticker: Company ticker
            max_recommendations: Maximum recommendations to include
            
        Returns:
            Implementation roadmap
        """
        history = self.storage.get_ticker_history(ticker)
        
        if not history.latest_evaluation:
            return {
                "ticker": ticker,
                "message": "No evaluation history available"
            }
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            history.latest_evaluation,
            history
        )
        
        # Group by priority
        priority_groups = {}
        for rec in recommendations[:max_recommendations]:
            priority = f"Priority {rec.priority}"
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append({
                "title": rec.title,
                "description": rec.description,
                "expected_impact": rec.expected_impact,
                "effort": rec.implementation_effort,
                "category": rec.category.value
            })
        
        # Calculate expected improvement
        total_impact = sum(r.expected_impact for r in recommendations[:max_recommendations])
        current_score = history.latest_evaluation.overall_score
        projected_score = min(10.0, current_score + total_impact)
        
        return {
            "ticker": ticker,
            "company": history.company,
            "current_score": current_score,
            "projected_score": projected_score,
            "expected_improvement": total_impact,
            "recommendations_by_priority": priority_groups,
            "total_recommendations": len(recommendations),
            "implementation_timeline": self._estimate_timeline(recommendations[:max_recommendations])
        }
    
    def _estimate_timeline(self, recommendations: List[ImprovementRecommendation]) -> Dict[str, List[str]]:
        """Estimate implementation timeline.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            Timeline by phase
        """
        timeline = {
            "Week 1": [],
            "Week 2-3": [],
            "Week 4+": []
        }
        
        for rec in recommendations:
            if rec.implementation_effort == "low" and rec.priority == 1:
                timeline["Week 1"].append(rec.title)
            elif rec.implementation_effort == "medium" or rec.priority == 2:
                timeline["Week 2-3"].append(rec.title)
            else:
                timeline["Week 4+"].append(rec.title)
        
        return timeline