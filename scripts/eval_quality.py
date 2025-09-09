#!/usr/bin/env python3
"""
Report Quality Evaluation Script

Evaluates investment reports using the LLM-based quality judge system.
Supports both individual report evaluation and batch processing.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from investing_agent.evals.report_quality_judge import ReportQualityJudge
from investing_agent.schemas.report_evaluation import ReportQualityResult


def evaluate_report(ticker: str, skip_generation: bool = False) -> ReportQualityResult:
    """Evaluate a single report for the given ticker."""
    
    report_path = Path(f"out/{ticker}/report.md")
    
    # Check if report exists
    if not report_path.exists():
        if skip_generation:
            raise FileNotFoundError(f"Report not found: {report_path}")
        else:
            print(f"Report not found for {ticker}. Please generate report first with: make report CT={ticker}")
            sys.exit(1)
    
    # Initialize judge and evaluate
    judge = ReportQualityJudge()
    
    # For now, use cassette-based evaluation (CI mode)
    # In future, this could switch to live LLM evaluation
    cassette_path = f"evals/report_quality/cassettes/current_{ticker.lower()}_baseline.json"
    
    try:
        # Read report content
        report_content = report_path.read_text()
        
        # Evaluate using judge
        result = judge.evaluate_report(
            report_content=report_content,
            cassette_path=cassette_path if Path(cassette_path).exists() else None
        )
        return result
        
    except Exception as e:
        print(f"Error evaluating {ticker}: {str(e)}")
        sys.exit(1)


def format_evaluation_results(result: ReportQualityResult) -> Dict[str, Any]:
    """Format evaluation results for display."""
    
    output = {
        "overall_score": result.overall_score,
        "grade": get_quality_grade(result.overall_score),
        "dimensions": {},
        "recommendations": result.recommendations,
        "comparative_analysis": result.comparative_analysis
    }
    
    for dim in result.dimensions:
        output["dimensions"][dim.name] = {
            "score": dim.score,
            "reasoning": dim.reasoning,
            "improvements": dim.improvement_suggestions
        }
    
    return output


def get_quality_grade(score: float) -> str:
    """Convert numerical score to quality grade."""
    if score >= 9.0:
        return "A+ (Exceptional - BYD Benchmark Level)"
    elif score >= 7.0:
        return "B+ (Good - Professional Quality)"
    elif score >= 5.0:
        return "C+ (Acceptable - Basic Professional)"
    elif score >= 3.0:
        return "D+ (Poor - META Baseline Level)"
    else:
        return "F (Inadequate)"


def print_evaluation_summary(ticker: str, result: ReportQualityResult):
    """Print a formatted evaluation summary to console."""
    
    print(f"\n{'='*60}")
    print(f"REPORT QUALITY EVALUATION: {ticker}")
    print(f"{'='*60}")
    
    print(f"\n🎯 OVERALL SCORE: {result.overall_score:.1f}/10")
    print(f"📊 GRADE: {get_quality_grade(result.overall_score)}")
    
    print(f"\n📋 DIMENSIONAL BREAKDOWN:")
    print("-" * 40)
    
    for dim in result.dimensions:
        print(f"{dim.name:25}: {dim.score:4.1f}/10")
        print(f"{'Reasoning':25}: {dim.reasoning[:100]}...")
        if dim.improvement_suggestions:
            print(f"{'Top Improvement':25}: {dim.improvement_suggestions[0]}")
        print()
    
    if result.recommendations:
        print(f"\n💡 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(result.recommendations[:3], 1):
            print(f"   {i}. {rec}")
    
    if result.comparative_analysis:
        print(f"\n🔍 COMPARATIVE ANALYSIS:")
        print(f"   {result.comparative_analysis}")
    
    print(f"\n{'='*60}")


def save_evaluation_results(ticker: str, result: ReportQualityResult):
    """Save evaluation results to JSON file."""
    
    output_dir = Path(f"out/{ticker}")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "quality_evaluation.json"
    
    # Convert to serializable format
    output_data = {
        "ticker": ticker,
        "overall_score": result.overall_score,
        "grade": get_quality_grade(result.overall_score),
        "dimensions": [
            {
                "name": dim.name,
                "score": dim.score,
                "reasoning": dim.reasoning,
                "evidence": dim.evidence,
                "improvement_suggestions": dim.improvement_suggestions
            }
            for dim in result.dimensions
        ],
        "recommendations": result.recommendations,
        "comparative_analysis": result.comparative_analysis,
        "metadata": result.metadata
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate investment report quality")
    parser.add_argument("--ticker", required=True, help="Stock ticker to evaluate")
    parser.add_argument("--skip-generation", action="store_true", 
                       help="Skip report generation, evaluate existing report only")
    parser.add_argument("--output-format", choices=["console", "json", "both"], 
                       default="both", help="Output format")
    parser.add_argument("--save-results", action="store_true", default=True,
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    try:
        # Evaluate the report
        result = evaluate_report(args.ticker, args.skip_generation)
        
        # Display results based on format preference
        if args.output_format in ["console", "both"]:
            print_evaluation_summary(args.ticker, result)
        
        if args.output_format in ["json", "both"]:
            formatted_results = format_evaluation_results(result)
            if args.output_format == "json":
                print(json.dumps(formatted_results, indent=2))
        
        # Save results if requested
        if args.save_results:
            save_evaluation_results(args.ticker, result)
            
        # Exit with appropriate code based on score
        if result.overall_score >= 6.0:
            sys.exit(0)  # Success
        else:
            print(f"\n⚠️  Report quality below acceptable threshold (6.0): {result.overall_score:.1f}")
            sys.exit(1)  # Quality gate failure
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()