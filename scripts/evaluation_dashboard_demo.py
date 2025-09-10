#!/usr/bin/env python3
"""Demonstration of evaluation dashboard and continuous improvement system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.evaluation.dashboard import EvaluationDashboard
from investing_agent.schemas.evaluation_metrics import EvaluationConfig
from investing_agent.storage.metrics_storage import MetricsStorage


def main():
    """Main function for evaluation dashboard demo."""
    
    parser = argparse.ArgumentParser(description="Evaluation Dashboard Demo")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "evaluate", "trends", "recommendations", "export"],
        default="dashboard",
        help="Operation mode"
    )
    parser.add_argument(
        "--ticker",
        help="Company ticker for analysis"
    )
    parser.add_argument(
        "--report-dir",
        default="out",
        help="Directory containing reports"
    )
    parser.add_argument(
        "--output-dir",
        default="out/evaluation",
        help="Output directory for results"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch evaluation"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    report_dir = Path(args.report_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize dashboard
    config = EvaluationConfig(
        min_quality_score=6.0,
        target_quality_score=8.0,
        excellence_threshold=9.0,
        enable_recommendations=True,
        enable_trend_analysis=True,
        generate_detailed_report=True
    )
    
    storage = MetricsStorage(db_path=output_dir / "metrics.db")
    dashboard = EvaluationDashboard(storage=storage, config=config)
    
    print("\n" + "="*60)
    print("EVALUATION DASHBOARD DEMONSTRATION")
    print("="*60)
    
    if args.mode == "dashboard":
        # Generate HTML dashboard
        print("\n📊 Generating evaluation dashboard...")
        
        html_path = output_dir / "dashboard.html"
        html = dashboard.generate_dashboard_html(output_path=html_path)
        
        print(f"✅ Dashboard saved to: {html_path}")
        print(f"   Open in browser: file://{html_path.absolute()}")
        
        # Generate summary
        summary = storage.generate_summary()
        print(f"\n📈 Summary Statistics:")
        print(f"   Total Evaluations: {summary.total_evaluations}")
        print(f"   Average Score: {summary.average_score:.1f}/10")
        print(f"   Passing Rate: {summary.passing_rate:.0f}%")
        print(f"   Highest Score: {summary.highest_score:.1f}/10")
        
        if summary.top_performers:
            print(f"\n🏆 Top Performers:")
            for ticker in summary.top_performers[:3]:
                print(f"   - {ticker}")
        
        if summary.needs_attention:
            print(f"\n⚠️ Needs Attention:")
            for ticker in summary.needs_attention[:3]:
                print(f"   - {ticker}")
    
    elif args.mode == "evaluate":
        # Run evaluation on reports
        if args.batch:
            print("\n🔄 Running batch evaluation...")
            
            results = dashboard.run_batch_evaluation(report_dir)
            
            if "error" not in results:
                print(f"✅ Evaluated {results['total_evaluated']} reports")
                print(f"   Average Score: {results['average_score']:.1f}/10")
                print(f"   Passing Rate: {results['passing_rate']:.0f}%")
                
                # Save results
                results_path = output_dir / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with results_path.open("w") as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"   Results saved to: {results_path}")
            else:
                print(f"❌ Error: {results['error']}")
        
        elif args.ticker:
            print(f"\n🔍 Evaluating report for {args.ticker}...")
            
            # Try both naming conventions
            report_path = report_dir / f"{args.ticker}_report.md"
            if not report_path.exists():
                report_path = report_dir / args.ticker / "report.md"
            if not report_path.exists():
                print(f"❌ Report not found: {report_path}")
                return
            
            content = report_path.read_text()
            result = dashboard.runner.evaluate_report(
                content, args.ticker, args.ticker
            )
            
            print(f"✅ Evaluation complete:")
            print(f"   Overall Score: {result.overall_score:.1f}/10")
            print(f"   Quality Gates: {'✓ Passing' if result.passes_quality_gates else '✗ Failing'}")
            
            print(f"\n📊 Dimensional Scores:")
            for score in result.dimensional_scores:
                status = "✓" if score.score >= 6.0 else "✗"
                print(f"   {status} {score.dimension.value}: {score.score:.1f}/10")
            
            print(f"\n📋 Hard Metrics:")
            print(f"   Evidence Coverage: {result.hard_metrics.evidence_coverage:.0%}")
            print(f"   Citation Density: {result.hard_metrics.citation_density:.2f}")
            print(f"   Contradiction Rate: {result.hard_metrics.contradiction_rate:.0%}")
            
            if result.recommendations:
                print(f"\n💡 Top Recommendations:")
                for rec in result.recommendations[:3]:
                    print(f"   - {rec}")
        else:
            print("❌ Please specify --ticker or --batch")
    
    elif args.mode == "trends":
        # Analyze trends
        if not args.ticker:
            print("❌ Please specify --ticker for trend analysis")
            return
        
        print(f"\n📈 Analyzing trends for {args.ticker}...")
        
        trends = dashboard.trend_analyzer.analyze_ticker_trends(args.ticker)
        
        if "message" in trends:
            print(f"ℹ️ {trends['message']}")
        else:
            print(f"✅ Trend Analysis:")
            print(f"   Overall Trend: {trends['trend'].value.replace('_', ' ').title()}")
            print(f"   Latest Score: {trends['latest_score']:.1f}/10")
            print(f"   Historical Average: {trends['historical_average']:.1f}/10")
            print(f"   Improvement: {trends['improvement_percentage']:+.1f}%")
            print(f"   Total Evaluations: {trends['total_evaluations']}")
            
            # Generate visualization
            chart_path = output_dir / f"{args.ticker}_trends.png"
            dashboard.trend_analyzer.create_trend_visualization(
                args.ticker, output_path=chart_path
            )
            print(f"\n📊 Trend chart saved to: {chart_path}")
        
        # Identify patterns
        patterns = dashboard.trend_analyzer.identify_patterns(args.ticker)
        if patterns.get("patterns"):
            print(f"\n🔍 Patterns Identified:")
            for pattern in patterns["patterns"]:
                print(f"   - {pattern.replace('_', ' ').title()}")
    
    elif args.mode == "recommendations":
        # Generate recommendations
        if not args.ticker:
            print("❌ Please specify --ticker for recommendations")
            return
        
        print(f"\n💡 Generating recommendations for {args.ticker}...")
        
        roadmap = dashboard.recommendation_engine.get_implementation_roadmap(args.ticker)
        
        if "message" in roadmap:
            print(f"ℹ️ {roadmap['message']}")
        else:
            print(f"✅ Implementation Roadmap:")
            print(f"   Current Score: {roadmap['current_score']:.1f}/10")
            print(f"   Projected Score: {roadmap['projected_score']:.1f}/10")
            print(f"   Expected Improvement: +{roadmap['expected_improvement']:.1f} points")
            
            print(f"\n📋 Recommendations by Priority:")
            for priority, recs in roadmap["recommendations_by_priority"].items():
                print(f"\n   {priority}:")
                for rec in recs:
                    print(f"   • {rec['title']}")
                    print(f"     {rec['description']}")
                    print(f"     Impact: +{rec['expected_impact']:.1f} | Effort: {rec['effort']}")
            
            print(f"\n📅 Implementation Timeline:")
            for phase, items in roadmap["implementation_timeline"].items():
                if items:
                    print(f"   {phase}:")
                    for item in items:
                        print(f"   • {item}")
            
            # Save roadmap
            roadmap_path = output_dir / f"{args.ticker}_roadmap.json"
            with roadmap_path.open("w") as f:
                json.dump(roadmap, f, indent=2)
            print(f"\n💾 Roadmap saved to: {roadmap_path}")
    
    elif args.mode == "export":
        # Export all metrics
        print("\n💾 Exporting evaluation metrics...")
        
        export_path = output_dir / f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        success = dashboard.export_metrics(export_path)
        
        if success:
            print(f"✅ Metrics exported to: {export_path}")
            
            # Show export summary
            with export_path.open() as f:
                data = json.load(f)
                print(f"   Total Evaluations: {data['total_evaluations']}")
        else:
            print("❌ Export failed")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    
    print("\n📚 Next Steps:")
    print("1. Run evaluations regularly to track progress")
    print("2. Review recommendations and implement improvements")
    print("3. Monitor trends to ensure quality is improving")
    print("4. Use the dashboard to identify patterns and issues")
    print("5. Export metrics for detailed analysis")
    
    print("\n🎯 Quality Targets:")
    print("• Minimum Score: 6.0/10 (quality gate)")
    print("• Target Score: 8.0/10 (professional quality)")
    print("• Excellence: 9.0/10 (BYD benchmark)")
    
    print("\n✨ Priority 7 Features:")
    print("• Automated evaluation with LLM judge")
    print("• Metrics storage and tracking over time")
    print("• Trend analysis and pattern detection")
    print("• Actionable improvement recommendations")
    print("• Interactive HTML dashboard")
    print("• Continuous improvement roadmaps")


if __name__ == "__main__":
    main()