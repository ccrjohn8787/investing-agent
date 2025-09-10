#!/usr/bin/env python3
"""Safe report generator with cost awareness and user confirmation."""

import sys
import os
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.config import load_env_file

# Load environment
load_env_file()

def estimate_cost(quality_mode: str, num_reports: int = 1) -> float:
    """Estimate cost for report generation."""
    costs = {
        "premium": 0.15,    # GPT-4
        "standard": 0.0008,  # GPT-4o-mini (DEFAULT)
        "budget": 0.003      # GPT-3.5-turbo
    }
    return costs.get(quality_mode, costs["standard"]) * num_reports

def confirm_generation(tickers: List[str], quality_mode: str = "standard") -> bool:
    """Ask user for confirmation before generating reports."""
    
    num_reports = len(tickers)
    total_cost = estimate_cost(quality_mode, num_reports)
    
    print("="*60)
    print("REPORT GENERATION CONFIRMATION")
    print("="*60)
    print()
    print(f"📊 Reports to Generate: {num_reports}")
    print(f"📝 Tickers: {', '.join(tickers)}")
    print(f"🤖 Model Mode: {quality_mode}")
    
    if quality_mode == "premium":
        print(f"   ⚠️  Using GPT-4 (expensive!)")
    elif quality_mode == "standard":
        print(f"   ✅ Using GPT-4o-mini (cost-efficient)")
    else:
        print(f"   💰 Using GPT-3.5-turbo (budget)")
    
    print(f"💵 Estimated Cost: ${total_cost:.4f}")
    print()
    
    # Warnings for high costs
    if total_cost > 1.0:
        print("⚠️  WARNING: This will cost more than $1.00!")
    if quality_mode == "premium" and num_reports > 5:
        print("⚠️  WARNING: Generating many reports with GPT-4 is expensive!")
    
    response = input("Do you want to proceed? (y/n): ").lower()
    return response == 'y'

def safe_generate_report(ticker: str, quality_mode: str = "standard", force: bool = False):
    """Generate a report with safety checks."""
    
    if not force and not confirm_generation([ticker], quality_mode):
        print("Generation cancelled.")
        return
    
    # Import here to avoid loading without confirmation
    from scripts.generate_full_report import generate_full_professional_report
    
    output_dir = Path("out") / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🚀 Generating report for {ticker}...")
    
    try:
        report_content, report_path = generate_full_professional_report(
            ticker=ticker,
            output_dir=output_dir,
            use_llm=True,
            llm_quality=quality_mode
        )
        
        print(f"✅ Report generated: {report_path}")
        
        # Show actual cost if tracked
        if os.getenv("LLM_COST_TRACKING") == "true":
            actual_cost = estimate_cost(quality_mode)
            print(f"💵 Actual cost: ~${actual_cost:.4f}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

def main():
    """Main entry point with safety checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Safe Report Generator with Cost Awareness")
    parser.add_argument("tickers", nargs="+", help="One or more ticker symbols")
    parser.add_argument("--quality", choices=["premium", "standard", "budget"],
                       default="standard",
                       help="Model quality (default: standard/GPT-4o-mini)")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # Safety check for premium mode
    if args.quality == "premium" and not args.force:
        print("⚠️  Premium mode uses GPT-4 which costs $0.15 per report!")
        print("   Use --quality standard for GPT-4o-mini (200x cheaper)")
        print()
    
    # Batch limit check
    if len(args.tickers) > 3 and not args.force:
        print(f"⚠️  You're trying to generate {len(args.tickers)} reports.")
        print("   This is above the safety limit of 3 reports.")
        if not confirm_generation(args.tickers, args.quality):
            print("Generation cancelled.")
            return
    
    # Generate each report
    for ticker in args.tickers:
        safe_generate_report(ticker, args.quality, args.force)

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        print("   Please set it in your .env file")
        sys.exit(1)
    
    main()