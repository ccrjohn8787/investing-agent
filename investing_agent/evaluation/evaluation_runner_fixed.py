"""Fixed evaluation runner that properly detects report quality."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from investing_agent.schemas.evaluation_metrics import (
    EvaluationResult,
    EvaluationScore,
    HardMetrics,
    EvaluationConfig,
    EvaluationDimension,
)
from investing_agent.storage.metrics_storage import MetricsStorage


class FixedEvaluationRunner:
    """Fixed evaluation runner that properly assesses report quality."""
    
    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        storage: Optional[MetricsStorage] = None
    ):
        """Initialize evaluation runner."""
        self.config = config or EvaluationConfig()
        self.storage = storage or MetricsStorage()
    
    def evaluate_report(
        self,
        report_content: str,
        ticker: str,
        company: str,
        report_id: Optional[str] = None,
        report_timestamp: Optional[datetime] = None
    ) -> EvaluationResult:
        """Evaluate a report with proper quality detection."""
        
        # Generate IDs
        evaluation_id = f"eval_{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        report_id = report_id or f"report_{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        report_timestamp = report_timestamp or datetime.utcnow()
        
        # Analyze report structure
        report_analysis = self._analyze_report_structure(report_content)
        
        # Calculate hard metrics
        hard_metrics = self._calculate_hard_metrics(report_content, report_analysis)
        
        # Get dimensional scores based on actual content
        dimensional_scores = self._evaluate_dimensions_fixed(report_content, report_analysis)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(dimensional_scores, hard_metrics, report_analysis)
        
        # Create result
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            report_id=report_id,
            ticker=ticker,
            company=company,
            report_timestamp=report_timestamp,
            evaluation_timestamp=datetime.utcnow(),
            dimensional_scores=dimensional_scores,
            hard_metrics=hard_metrics,
            recommendations=recommendations,
            evaluator_model="fixed_evaluator",
            evaluation_config=self.config.model_dump()
        )
        
        # Save to storage
        if self.config.save_to_database:
            self.storage.save_evaluation(result)
        
        return result
    
    def _analyze_report_structure(self, report_content: str) -> Dict[str, Any]:
        """Analyze the structure and content of the report."""
        
        lines = report_content.split('\n')
        
        # Check for key sections
        has_executive_summary = any('executive summary' in line.lower() for line in lines)
        has_investment_thesis = any('investment' in line.lower() and 'thesis' in line.lower() for line in lines)
        has_industry_context = any('industry' in line.lower() or 'competitive' in line.lower() for line in lines)
        has_risk_analysis = any('risk' in line.lower() for line in lines)
        has_strategic_analysis = any('strategic' in line.lower() or 'strategy' in line.lower() for line in lines)
        
        # Count narrative content
        narrative_lines = []
        table_lines = 0
        header_lines = 0
        
        for line in lines:
            if line.strip():
                if line.startswith('#'):
                    header_lines += 1
                elif line.startswith('|'):
                    table_lines += 1
                elif len(line) > 50:  # Substantial text line
                    narrative_lines.append(line)
        
        # Detect if this is a numbers-only report
        total_content_lines = len([l for l in lines if l.strip()])
        narrative_ratio = len(narrative_lines) / max(total_content_lines, 1)
        
        # Check for BYD-style rich narrative
        has_rich_narrative = False
        for line in narrative_lines:
            # Look for descriptive, analytical language
            analytical_phrases = [
                'demonstrates', 'suggests', 'indicates', 'reflects', 'underscores',
                'positioning', 'strategic', 'competitive', 'market dynamics',
                'growth trajectory', 'operational efficiency', 'value proposition'
            ]
            if any(phrase in line.lower() for phrase in analytical_phrases):
                has_rich_narrative = True
                break
        
        return {
            'total_lines': len(lines),
            'narrative_lines': len(narrative_lines),
            'table_lines': table_lines,
            'header_lines': header_lines,
            'narrative_ratio': narrative_ratio,
            'has_executive_summary': has_executive_summary,
            'has_investment_thesis': has_investment_thesis,
            'has_industry_context': has_industry_context,
            'has_risk_analysis': has_risk_analysis,
            'has_strategic_analysis': has_strategic_analysis,
            'has_rich_narrative': has_rich_narrative,
            'is_numbers_only': narrative_ratio < 0.2 and not has_rich_narrative
        }
    
    def _calculate_hard_metrics(self, report_content: str, analysis: Dict) -> HardMetrics:
        """Calculate hard metrics with proper detection."""
        
        # Count citations
        evidence_citations = report_content.count('[ev:')
        computed_citations = report_content.count('[ref:computed:')
        total_citations = evidence_citations + computed_citations
        
        # For numbers-only reports, evidence coverage should be very low
        if analysis['is_numbers_only']:
            # Numbers-only reports have no qualitative claims needing evidence
            evidence_coverage = 0.0
            citation_density = 0.0
        else:
            # Calculate based on narrative content
            paragraphs = max(analysis['narrative_lines'] // 3, 1)  # Approx 3 lines per paragraph
            citation_density = total_citations / paragraphs
            
            # Evidence coverage: should have citations for claims
            expected_citations = max(analysis['narrative_lines'] // 5, 1)  # Expect 1 citation per 5 narrative lines
            evidence_coverage = min(1.0, total_citations / expected_citations)
        
        # Contradiction rate (simplified)
        contradiction_rate = 0.0
        
        # Numeric accuracy
        numeric_accuracy = 1.0  # Assume accurate unless proven otherwise
        
        return HardMetrics(
            evidence_coverage=evidence_coverage,
            citation_density=citation_density,
            contradiction_rate=contradiction_rate,
            fixture_stability=True,
            numeric_accuracy=numeric_accuracy
        )
    
    def _evaluate_dimensions_fixed(
        self,
        report_content: str,
        analysis: Dict
    ) -> List[EvaluationScore]:
        """Evaluate dimensions based on actual content analysis."""
        
        scores = []
        
        # Strategic Narrative
        if analysis['is_numbers_only']:
            strategic_score = 2.0  # Very low - no narrative
            strategic_details = "No strategic narrative found - numbers-only report"
        elif analysis['has_rich_narrative'] and analysis['has_strategic_analysis']:
            strategic_score = 8.0
            strategic_details = "Strong strategic narrative with analytical depth"
        elif analysis['has_strategic_analysis']:
            strategic_score = 6.0
            strategic_details = "Basic strategic analysis present"
        else:
            strategic_score = 3.0
            strategic_details = "Minimal strategic narrative"
        
        scores.append(EvaluationScore(
            dimension=EvaluationDimension.STRATEGIC_NARRATIVE,
            score=strategic_score,
            percentage=(strategic_score / 10.0) * 100,
            details=strategic_details
        ))
        
        # Analytical Rigor
        if analysis['is_numbers_only']:
            analytical_score = 4.0  # Has numbers but no analysis
            analytical_details = "Numbers present but lacks analytical narrative"
        elif analysis['table_lines'] > 20 and analysis['has_rich_narrative']:
            analytical_score = 8.0
            analytical_details = "Strong quantitative and qualitative analysis"
        else:
            analytical_score = 5.0
            analytical_details = "Basic analytical content"
        
        scores.append(EvaluationScore(
            dimension=EvaluationDimension.ANALYTICAL_RIGOR,
            score=analytical_score,
            percentage=(analytical_score / 10.0) * 100,
            details=analytical_details
        ))
        
        # Industry Context
        if analysis['has_industry_context']:
            industry_score = 7.0
            industry_details = "Industry context present"
        elif analysis['is_numbers_only']:
            industry_score = 1.0
            industry_details = "No industry context - numbers-only report"
        else:
            industry_score = 3.0
            industry_details = "Minimal industry context"
        
        scores.append(EvaluationScore(
            dimension=EvaluationDimension.INDUSTRY_CONTEXT,
            score=industry_score,
            percentage=(industry_score / 10.0) * 100,
            details=industry_details
        ))
        
        # Professional Presentation
        if analysis['is_numbers_only']:
            presentation_score = 3.0  # Tables only, no narrative flow
            presentation_details = "Tables only, lacks narrative structure"
        elif analysis['has_executive_summary'] and analysis['narrative_lines'] > 20:
            presentation_score = 8.0
            presentation_details = "Professional structure with good flow"
        else:
            presentation_score = 5.0
            presentation_details = "Basic presentation structure"
        
        scores.append(EvaluationScore(
            dimension=EvaluationDimension.PROFESSIONAL_PRESENTATION,
            score=presentation_score,
            percentage=(presentation_score / 10.0) * 100,
            details=presentation_details
        ))
        
        # Citation Discipline
        citation_score = min(5.0, 2.0 + (analysis.get('citation_density', 0) * 3))
        if analysis['is_numbers_only']:
            citation_score = 2.0  # Can't have good citations without narrative
            citation_details = "No narrative to cite evidence"
        else:
            citation_details = f"Citation density: {analysis.get('citation_density', 0):.2f}"
        
        scores.append(EvaluationScore(
            dimension=EvaluationDimension.CITATION_DISCIPLINE,
            score=citation_score,
            percentage=(citation_score / 10.0) * 100,
            details=citation_details
        ))
        
        return scores
    
    def _generate_recommendations(
        self,
        dimensional_scores: List[EvaluationScore],
        hard_metrics: HardMetrics,
        analysis: Dict
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        
        recommendations = []
        
        # Critical issue: numbers-only report
        if analysis['is_numbers_only']:
            recommendations.append(
                "CRITICAL: Add strategic narrative - current report is numbers-only"
            )
            recommendations.append(
                "CRITICAL: Add investment thesis with forward-looking analysis"
            )
            recommendations.append(
                "CRITICAL: Include industry context and competitive positioning"
            )
        
        # Check each dimension
        for score in dimensional_scores:
            if score.score < 5.0:
                if score.dimension == EvaluationDimension.STRATEGIC_NARRATIVE:
                    recommendations.append("Add comprehensive strategic narrative section")
                elif score.dimension == EvaluationDimension.INDUSTRY_CONTEXT:
                    recommendations.append("Include industry analysis and peer comparison")
                elif score.dimension == EvaluationDimension.ANALYTICAL_RIGOR:
                    recommendations.append("Enhance analytical depth with qualitative insights")
        
        # Check missing sections
        if not analysis['has_executive_summary']:
            recommendations.append("Add executive summary with key investment points")
        if not analysis['has_investment_thesis']:
            recommendations.append("Develop clear investment thesis section")
        if not analysis['has_risk_analysis']:
            recommendations.append("Include comprehensive risk analysis")
        
        return recommendations[:5]  # Top 5 recommendations