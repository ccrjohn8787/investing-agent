#!/usr/bin/env python3
"""Mock demonstration of evaluation dashboard (no LLM required)."""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.evaluation.dashboard import EvaluationDashboard
from investing_agent.schemas.evaluation_metrics import (
    EvaluationConfig,
    EvaluationResult,
    EvaluationScore,
    HardMetrics,
    EvaluationDimension,
)
from investing_agent.storage.metrics_storage import MetricsStorage


def create_mock_evaluation(ticker: str, company: str, report_content: str) -> EvaluationResult:
    """Create mock evaluation result for demonstration."""
    
    # Calculate mock hard metrics based on report content
    evidence_count = report_content.count('[ev:')
    ref_count = report_content.count('[ref:computed:')
    total_citations = evidence_count + ref_count
    paragraphs = len([p for p in report_content.split('\n\n') if p.strip()])
    
    hard_metrics = HardMetrics(
        evidence_coverage=min(1.0, total_citations / max(paragraphs * 2, 1)),
        citation_density=total_citations / max(paragraphs, 1),
        contradiction_rate=random.uniform(0.05, 0.15),
        fixture_stability=True,
        numeric_accuracy=random.uniform(0.90, 0.98)
    )
    
    # Generate mock dimensional scores
    dimensional_scores = []
    
    # Base scores influenced by report characteristics
    base_scores = {
        EvaluationDimension.STRATEGIC_NARRATIVE: 6.5 + random.uniform(0, 2),
        EvaluationDimension.ANALYTICAL_RIGOR: 7.0 + random.uniform(0, 1.5),
        EvaluationDimension.INDUSTRY_CONTEXT: 6.0 + random.uniform(0, 2),
        EvaluationDimension.PROFESSIONAL_PRESENTATION: 7.5 + random.uniform(0, 1),
        EvaluationDimension.CITATION_DISCIPLINE: min(9.0, 5.0 + (total_citations / 10))
    }
    
    for dimension, base_score in base_scores.items():
        score = min(10.0, base_score)
        dimensional_scores.append(EvaluationScore(
            dimension=dimension,
            score=score,
            percentage=(score / 10.0) * 100,
            details=f"Mock evaluation score for {dimension.value}"
        ))
    
    # Generate recommendations based on scores
    recommendations = []
    for score_obj in dimensional_scores:
        if score_obj.score < 7.0:
            recommendations.append(f"Improve {score_obj.dimension.value.replace('_', ' ')}")
    
    if hard_metrics.evidence_coverage < 0.80:
        recommendations.append("Increase evidence coverage to support claims")
    if hard_metrics.citation_density < 0.70:
        recommendations.append("Add more citations throughout the report")
    
    # Create evaluation result
    return EvaluationResult(
        evaluation_id=f"eval_{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        report_id=f"report_{ticker}_{datetime.utcnow().strftime('%Y%m%d')}",
        ticker=ticker,
        company=company,
        report_timestamp=datetime.utcnow(),
        evaluation_timestamp=datetime.utcnow(),
        dimensional_scores=dimensional_scores,
        hard_metrics=hard_metrics,
        recommendations=recommendations[:5],
        evaluator_model="mock",
        evaluation_config={"mock": True}
    )


def generate_historical_data(storage: MetricsStorage, ticker: str, company: str):
    """Generate historical evaluation data for trend demonstration."""
    
    print(f"📊 Generating historical data for {ticker}...")
    
    # Generate 10 historical evaluations
    for i in range(10):
        # Create evaluation with improving trend
        eval_time = datetime.utcnow() - timedelta(days=10-i)
        base_score = 5.5 + (i * 0.3)  # Improving trend
        
        dimensional_scores = []
        for dimension in EvaluationDimension:
            score = min(10.0, base_score + random.uniform(-0.5, 0.5))
            dimensional_scores.append(EvaluationScore(
                dimension=dimension,
                score=score,
                percentage=(score / 10.0) * 100,
                details=f"Historical score {i+1}"
            ))
        
        eval_result = EvaluationResult(
            evaluation_id=f"eval_{ticker}_hist_{i:03d}",
            report_id=f"report_{ticker}_hist_{i:03d}",
            ticker=ticker,
            company=company,
            report_timestamp=eval_time,
            evaluation_timestamp=eval_time,
            dimensional_scores=dimensional_scores,
            hard_metrics=HardMetrics(
                evidence_coverage=0.70 + (i * 0.02),
                citation_density=0.60 + (i * 0.03),
                contradiction_rate=max(0.05, 0.25 - (i * 0.02)),
                fixture_stability=True,
                numeric_accuracy=0.90 + (i * 0.01)
            ),
            recommendations=[],
            evaluator_model="mock",
            evaluation_config={"mock": True}
        )
        
        storage.save_evaluation(eval_result)


def main():
    """Main demo function."""
    
    print("\n" + "="*60)
    print("EVALUATION DASHBOARD MOCK DEMONSTRATION")
    print("="*60)
    print("(Using mock data - no LLM API required)")
    
    # Setup
    output_dir = Path("out/evaluation_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    storage = MetricsStorage(db_path=output_dir / "mock_metrics.db")
    dashboard = EvaluationDashboard(storage=storage)
    
    # Available reports
    reports = [
        ("META", "Meta Platforms Inc"),
        ("BYD", "BYD Company Limited"),
        ("UBER", "Uber Technologies Inc"),
        ("NVDA", "NVIDIA Corporation"),
    ]
    
    print("\n📋 Processing Reports:")
    
    # Process each report
    for ticker, company in reports:
        report_path = Path("out") / ticker / "report.md"
        if not report_path.exists():
            print(f"  ⚠️ {ticker}: Report not found")
            continue
        
        # Read report
        report_content = report_path.read_text()
        
        # Generate historical data
        generate_historical_data(storage, ticker, company)
        
        # Create current evaluation
        eval_result = create_mock_evaluation(ticker, company, report_content)
        storage.save_evaluation(eval_result)
        
        print(f"  ✓ {ticker}: Score {eval_result.overall_score:.1f}/10 - {'PASS' if eval_result.passes_quality_gates else 'FAIL'}")
    
    # Generate dashboard
    print("\n📊 Generating Dashboard...")
    
    html_path = output_dir / "dashboard.html"
    dashboard.generate_dashboard_html(output_path=html_path)
    print(f"  ✓ HTML Dashboard: {html_path}")
    
    # Generate summary
    summary = storage.generate_summary()
    print(f"\n📈 Overall Statistics:")
    print(f"  • Total Evaluations: {summary.total_evaluations}")
    print(f"  • Average Score: {summary.average_score:.1f}/10")
    print(f"  • Passing Rate: {summary.passing_rate:.0f}%")
    print(f"  • Highest Score: {summary.highest_score:.1f}/10")
    
    # Generate trend analysis for META
    print(f"\n📉 Trend Analysis (META):")
    trends = dashboard.trend_analyzer.analyze_ticker_trends("META")
    if "trend" in trends:
        print(f"  • Trend: {trends['trend'].value.replace('_', ' ').title()}")
        print(f"  • Latest Score: {trends['latest_score']:.1f}/10")
        print(f"  • Improvement: {trends['improvement_percentage']:+.1f}%")
    
    # Generate visualization
    chart_path = output_dir / "META_trends.png"
    dashboard.trend_analyzer.create_trend_visualization("META", output_path=chart_path)
    print(f"  ✓ Trend Chart: {chart_path}")
    
    # Generate comparison chart
    comparison_path = output_dir / "comparison.png"
    dashboard.trend_analyzer.generate_comparison_chart(
        [t for t, _ in reports], 
        output_path=comparison_path
    )
    print(f"  ✓ Comparison Chart: {comparison_path}")
    
    # Generate recommendations for META
    print(f"\n💡 Recommendations (META):")
    roadmap = dashboard.recommendation_engine.get_implementation_roadmap("META")
    if "recommendations_by_priority" in roadmap:
        for priority, recs in list(roadmap["recommendations_by_priority"].items())[:2]:
            print(f"  {priority}:")
            for rec in recs[:2]:
                print(f"    • {rec['title']}")
    
    # Export metrics
    export_path = output_dir / "metrics_export.json"
    dashboard.export_metrics(export_path)
    print(f"\n💾 Metrics Export: {export_path}")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    
    print(f"\n🎯 View Results:")
    print(f"  • Dashboard: file://{html_path.absolute()}")
    print(f"  • Trends: {chart_path.name}")
    print(f"  • Comparison: {comparison_path.name}")
    print(f"  • Export: {export_path.name}")
    
    print(f"\n✨ Key Features Demonstrated:")
    print(f"  ✓ Automated quality evaluation")
    print(f"  ✓ Historical trend tracking")
    print(f"  ✓ Multi-dimensional scoring")
    print(f"  ✓ Improvement recommendations")
    print(f"  ✓ Interactive HTML dashboard")
    print(f"  ✓ Professional visualizations")


if __name__ == "__main__":
    main()