"""Automated evaluation runner for report quality assessment."""

from __future__ import annotations

import uuid
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import json

from investing_agent.schemas.evaluation_metrics import (
    EvaluationResult,
    EvaluationScore,
    HardMetrics,
    EvaluationConfig,
    EvaluationBatch,
    EvaluationDimension,
    EvaluationSummary,
)
from investing_agent.storage.metrics_storage import MetricsStorage
from investing_agent.llm.enhanced_provider import LLMProvider


class EvaluationRunner:
    """Runner for automated report quality evaluation."""
    
    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        storage: Optional[MetricsStorage] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        """Initialize evaluation runner.
        
        Args:
            config: Evaluation configuration
            storage: Metrics storage instance
            llm_provider: LLM provider for evaluation
        """
        self.config = config or EvaluationConfig()
        self.storage = storage or MetricsStorage()
        self.llm_provider = llm_provider or LLMProvider()
    
    def evaluate_report(
        self,
        report_content: str,
        ticker: str,
        company: str,
        report_id: Optional[str] = None,
        report_timestamp: Optional[datetime] = None
    ) -> EvaluationResult:
        """Evaluate a single report.
        
        Args:
            report_content: Markdown report content
            ticker: Company ticker
            company: Company name
            report_id: Report identifier
            report_timestamp: When report was generated
            
        Returns:
            Evaluation result
        """
        # Generate IDs and timestamps
        evaluation_id = f"eval_{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        report_id = report_id or f"report_{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        report_timestamp = report_timestamp or datetime.utcnow()
        
        # Calculate hard metrics
        hard_metrics = self._calculate_hard_metrics(report_content)
        
        # Get dimensional scores from LLM
        dimensional_scores = self._evaluate_dimensions(report_content, ticker, company)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(dimensional_scores, hard_metrics)
        
        # Create evaluation result
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
            evaluator_model=self.config.evaluator_model,
            evaluation_config=self.config.model_dump()
        )
        
        # Save to storage
        if self.config.save_to_database:
            self.storage.save_evaluation(result)
        
        return result
    
    def evaluate_batch(
        self,
        reports: List[Tuple[str, str, str]],  # [(content, ticker, company), ...]
        batch_id: Optional[str] = None
    ) -> EvaluationBatch:
        """Evaluate multiple reports in batch.
        
        Args:
            reports: List of (content, ticker, company) tuples
            batch_id: Batch identifier
            
        Returns:
            Batch evaluation results
        """
        batch_id = batch_id or f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        batch_timestamp = datetime.utcnow()
        start_time = time.time()
        
        evaluations = []
        total_cost = 0.0
        
        for content, ticker, company in reports:
            try:
                result = self.evaluate_report(content, ticker, company)
                evaluations.append(result)
                # Track cost if available
                # total_cost += self.llm_provider.get_last_cost()
            except Exception as e:
                print(f"Error evaluating {ticker}: {e}")
                continue
        
        processing_time = time.time() - start_time
        
        # Create batch result
        batch = EvaluationBatch(
            batch_id=batch_id,
            batch_timestamp=batch_timestamp,
            config=self.config,
            evaluations=evaluations,
            summary=EvaluationSummary(),  # Will be populated in post_init
            processing_time_seconds=processing_time,
            total_cost_usd=total_cost
        )
        
        # Save batch
        if self.config.save_to_database:
            self.storage.save_batch(batch)
        
        return batch
    
    def _calculate_hard_metrics(self, report_content: str) -> HardMetrics:
        """Calculate hard metrics from report content.
        
        Args:
            report_content: Markdown report content
            
        Returns:
            Hard metrics
        """
        lines = report_content.split('\n')
        paragraphs = [p for p in report_content.split('\n\n') if p.strip()]
        
        # Count evidence citations
        evidence_citations = report_content.count('[ev:')
        computed_citations = report_content.count('[ref:computed:')
        total_citations = evidence_citations + computed_citations
        
        # Count qualitative claims (approximation)
        qualitative_claims = 0
        for paragraph in paragraphs:
            # Skip code blocks and tables
            if paragraph.startswith('```') or paragraph.startswith('|'):
                continue
            # Count sentences with assertions
            sentences = paragraph.split('. ')
            for sentence in sentences:
                if any(word in sentence.lower() for word in [
                    'will', 'should', 'expect', 'likely', 'believe', 
                    'suggest', 'indicate', 'show', 'demonstrate'
                ]):
                    qualitative_claims += 1
        
        # Calculate coverage
        evidence_coverage = min(1.0, total_citations / max(qualitative_claims, 1))
        
        # Calculate citation density
        citation_density = total_citations / max(len(paragraphs), 1)
        
        # Check for contradictions (simplified)
        contradiction_rate = self._check_contradictions(report_content)
        
        # Fixture stability (always true for now)
        fixture_stability = True
        
        # Numeric accuracy (simplified check)
        numeric_accuracy = self._check_numeric_accuracy(report_content)
        
        return HardMetrics(
            evidence_coverage=evidence_coverage,
            citation_density=citation_density,
            contradiction_rate=contradiction_rate,
            fixture_stability=fixture_stability,
            numeric_accuracy=numeric_accuracy
        )
    
    def _check_contradictions(self, report_content: str) -> float:
        """Check for contradictory statements in report.
        
        Args:
            report_content: Report content
            
        Returns:
            Contradiction rate (0-1)
        """
        # Simplified contradiction detection
        contradictions = 0
        total_claims = 0
        
        # Look for opposing statements
        opposing_pairs = [
            ('increasing', 'decreasing'),
            ('growth', 'decline'),
            ('positive', 'negative'),
            ('bullish', 'bearish'),
            ('strong', 'weak'),
        ]
        
        paragraphs = [p for p in report_content.split('\n\n') if p.strip()]
        
        for i, para1 in enumerate(paragraphs):
            for para2 in paragraphs[i+1:]:
                for pos, neg in opposing_pairs:
                    if pos in para1.lower() and neg in para2.lower():
                        # Check if talking about same metric
                        if any(metric in para1.lower() and metric in para2.lower() 
                               for metric in ['revenue', 'margin', 'growth', 'profit']):
                            contradictions += 1
                total_claims += 1
        
        return min(1.0, contradictions / max(total_claims, 1))
    
    def _check_numeric_accuracy(self, report_content: str) -> float:
        """Check numeric accuracy in report.
        
        Args:
            report_content: Report content
            
        Returns:
            Numeric accuracy score (0-1)
        """
        # Simplified numeric validation
        # In real implementation, would cross-check with valuation data
        import re
        
        # Find all percentages
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', report_content)
        
        # Check if percentages are reasonable (0-100% for most metrics)
        unreasonable = sum(1 for p in percentages if float(p) > 100 or float(p) < -50)
        
        if not percentages:
            return 1.0
        
        return max(0, 1.0 - (unreasonable / len(percentages)))
    
    def _evaluate_dimensions(
        self,
        report_content: str,
        ticker: str,
        company: str
    ) -> List[EvaluationScore]:
        """Evaluate report across quality dimensions using LLM.
        
        Args:
            report_content: Report content
            ticker: Company ticker
            company: Company name
            
        Returns:
            List of dimensional scores
        """
        scores = []
        
        # Evaluate each dimension
        for dimension in EvaluationDimension:
            score, details = self._evaluate_single_dimension(
                report_content, ticker, company, dimension
            )
            
            scores.append(EvaluationScore(
                dimension=dimension,
                score=score,
                percentage=(score / 10.0) * 100,
                details=details
            ))
        
        return scores
    
    def _evaluate_single_dimension(
        self,
        report_content: str,
        ticker: str,
        company: str,
        dimension: EvaluationDimension
    ) -> Tuple[float, str]:
        """Evaluate a single dimension.
        
        Args:
            report_content: Report content
            ticker: Company ticker
            company: Company name
            dimension: Dimension to evaluate
            
        Returns:
            Score and details
        """
        # Create evaluation prompt
        prompt = self._create_dimension_prompt(dimension, report_content, ticker, company)
        
        try:
            # Get LLM evaluation
            response = self.llm_provider.call(
                model_name=self.config.evaluator_model,
                messages=[{"role": "user", "content": prompt}],
                params={
                    "temperature": self.config.temperature,
                    "max_tokens": 1000
                }
            )
            
            # Parse response
            response_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_dimension_response(response_text, dimension)
        except Exception as e:
            print(f"Error evaluating {dimension}: {e}")
            # Return default score on error
            return 5.0, f"Evaluation error: {str(e)}"
    
    def _create_dimension_prompt(
        self,
        dimension: EvaluationDimension,
        report_content: str,
        ticker: str,
        company: str
    ) -> str:
        """Create evaluation prompt for a dimension.
        
        Args:
            dimension: Dimension to evaluate
            report_content: Report content
            ticker: Company ticker
            company: Company name
            
        Returns:
            Evaluation prompt
        """
        dimension_prompts = {
            EvaluationDimension.STRATEGIC_NARRATIVE: """
                Evaluate the strategic narrative quality of this investment report.
                Score from 0-10 based on:
                - Clarity and coherence of investment thesis
                - Connection between business strategy and valuation
                - Forward-looking perspective and strategic insights
                - Storytelling quality and narrative flow
                """,
            EvaluationDimension.ANALYTICAL_RIGOR: """
                Evaluate the analytical rigor of this investment report.
                Score from 0-10 based on:
                - Depth of financial analysis
                - Quality of evidence and data support
                - Logical reasoning and methodology
                - Quantitative backing for qualitative claims
                """,
            EvaluationDimension.INDUSTRY_CONTEXT: """
                Evaluate the industry context in this investment report.
                Score from 0-10 based on:
                - Understanding of competitive landscape
                - Industry trends and dynamics coverage
                - Peer comparison quality
                - Market positioning analysis
                """,
            EvaluationDimension.PROFESSIONAL_PRESENTATION: """
                Evaluate the professional presentation of this investment report.
                Score from 0-10 based on:
                - Report structure and organization
                - Visual elements and formatting
                - Clarity and readability
                - Professional tone and language
                """,
            EvaluationDimension.CITATION_DISCIPLINE: """
                Evaluate the citation discipline in this investment report.
                Score from 0-10 based on:
                - Presence of evidence citations [ev:xxx]
                - Proper attribution of claims
                - Traceability of assertions
                - No unsupported statements
                """
        }
        
        base_prompt = dimension_prompts.get(dimension, "Evaluate this report.")
        
        return f"""
        {base_prompt}
        
        Company: {company} ({ticker})
        
        Report Content (first 5000 chars):
        {report_content[:5000]}
        
        Provide your evaluation in the following format:
        SCORE: [0-10 numeric score]
        DETAILS: [2-3 sentences explaining the score]
        """
    
    def _parse_dimension_response(
        self,
        response: str,
        dimension: EvaluationDimension
    ) -> Tuple[float, str]:
        """Parse LLM response for dimension evaluation.
        
        Args:
            response: LLM response
            dimension: Dimension being evaluated
            
        Returns:
            Score and details
        """
        lines = response.strip().split('\n')
        score = 5.0  # Default
        details = f"Evaluated {dimension.value}"
        
        for line in lines:
            if line.startswith('SCORE:'):
                try:
                    score_str = line.replace('SCORE:', '').strip()
                    score = float(score_str.split()[0])
                    score = max(0, min(10, score))  # Clamp to 0-10
                except:
                    pass
            elif line.startswith('DETAILS:'):
                details = line.replace('DETAILS:', '').strip()
        
        return score, details
    
    def _generate_recommendations(
        self,
        dimensional_scores: List[EvaluationScore],
        hard_metrics: HardMetrics
    ) -> List[str]:
        """Generate improvement recommendations.
        
        Args:
            dimensional_scores: Dimensional evaluation scores
            hard_metrics: Hard metric values
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check dimensional scores
        for score in dimensional_scores:
            if score.score < 6.0:
                if score.dimension == EvaluationDimension.STRATEGIC_NARRATIVE:
                    recommendations.append(
                        "Strengthen strategic narrative with clearer investment thesis and better storytelling"
                    )
                elif score.dimension == EvaluationDimension.ANALYTICAL_RIGOR:
                    recommendations.append(
                        "Enhance analytical depth with more quantitative analysis and evidence"
                    )
                elif score.dimension == EvaluationDimension.INDUSTRY_CONTEXT:
                    recommendations.append(
                        "Add more industry analysis and competitive positioning context"
                    )
                elif score.dimension == EvaluationDimension.PROFESSIONAL_PRESENTATION:
                    recommendations.append(
                        "Improve report structure and formatting for better readability"
                    )
                elif score.dimension == EvaluationDimension.CITATION_DISCIPLINE:
                    recommendations.append(
                        "Add more evidence citations [ev:xxx] to support claims"
                    )
        
        # Check hard metrics
        if hard_metrics.evidence_coverage < 0.80:
            recommendations.append(
                f"Increase evidence coverage (currently {hard_metrics.evidence_coverage:.0%}) - aim for ≥80%"
            )
        
        if hard_metrics.citation_density < 0.70:
            recommendations.append(
                f"Increase citation density (currently {hard_metrics.citation_density:.2f}) - aim for ≥0.70 per paragraph"
            )
        
        if hard_metrics.contradiction_rate > 0.20:
            recommendations.append(
                f"Reduce contradictory statements (currently {hard_metrics.contradiction_rate:.0%}) - aim for ≤20%"
            )
        
        # Prioritize top 5 recommendations
        return recommendations[:5]
    
    def run_continuous_evaluation(
        self,
        report_directory: Path,
        interval_seconds: int = 3600
    ):
        """Run continuous evaluation on reports in directory.
        
        Args:
            report_directory: Directory containing reports
            interval_seconds: Evaluation interval
        """
        import time
        
        while True:
            try:
                # Find new reports
                reports = list(report_directory.glob("*_report.md"))
                
                batch_reports = []
                for report_path in reports:
                    # Extract ticker from filename
                    ticker = report_path.stem.split('_')[0]
                    
                    # Check if already evaluated recently
                    history = self.storage.get_ticker_history(ticker, limit=1)
                    if history.latest_evaluation:
                        # Skip if evaluated in last interval
                        time_since = datetime.utcnow() - history.latest_evaluation.evaluation_timestamp
                        if time_since.total_seconds() < interval_seconds:
                            continue
                    
                    # Add to batch
                    content = report_path.read_text()
                    batch_reports.append((content, ticker, ticker))
                
                if batch_reports:
                    print(f"Evaluating {len(batch_reports)} reports...")
                    batch = self.evaluate_batch(batch_reports)
                    print(f"Evaluation complete. Average score: {batch.summary.average_score:.1f}")
                
                # Sleep before next run
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("Continuous evaluation stopped.")
                break
            except Exception as e:
                print(f"Error in continuous evaluation: {e}")
                time.sleep(60)  # Wait before retry