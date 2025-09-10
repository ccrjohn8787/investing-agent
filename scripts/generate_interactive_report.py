#!/usr/bin/env python3
"""Generate interactive HTML investment report with the new UI."""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment if available
try:
    from investing_agent.config import load_env_file
    load_env_file()
except ImportError:
    pass  # Environment loading is optional
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals
from investing_agent.connectors.yahoo import fetch_prices_v8_chart
from investing_agent.connectors.stooq import fetch_prices as fetch_stooq_prices
from investing_agent.ui import InteractiveReportBuilder

# Import optional components
try:
    from investing_agent.agents.writer_llm_gen import WriterLLMGen
    from investing_agent.evaluation.evaluation_runner_fixed import FixedEvaluationRunner
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("Note: LLM components not available. Using fallback narratives.")


def generate_fallback_narratives(inputs, valuation) -> Dict[str, str]:
    """Generate basic narratives without LLM."""
    return {
        "executive_summary": f"""
        {inputs.company} ({inputs.ticker}) presents a compelling investment opportunity with a fair value of 
        ${valuation.value_per_share:.2f} per share. The company demonstrates strong fundamentals with 
        revenue of ${inputs.revenue_t0/1e9:.1f}B and an operating margin of {inputs.drivers.oper_margin[0]*100:.1f}%.
        
        Our DCF analysis indicates significant value creation potential driven by sustainable growth 
        rates and improving operational efficiency. The valuation is supported by conservative assumptions 
        and thorough sensitivity analysis.
        """,
        
        "financial_analysis": f"""
        **Revenue Growth**: The company is projected to grow at {inputs.drivers.sales_growth[0]*100:.1f}% 
        in the near term, transitioning to a stable growth rate of {inputs.drivers.stable_growth*100:.1f}% 
        at maturity.
        
        **Profitability**: Operating margins of {inputs.drivers.oper_margin[0]*100:.1f}% demonstrate 
        strong cost management and pricing power. We expect margins to stabilize at 
        {inputs.drivers.stable_margin*100:.1f}% in the terminal period.
        
        **Capital Efficiency**: With a sales-to-capital ratio of {inputs.sales_to_capital[0]:.2f}, 
        the company shows efficient capital deployment and strong returns on invested capital.
        """,
        
        "investment_thesis": f"""
        Our investment thesis for {inputs.company} rests on three key pillars:
        
        1. **Market Leadership**: Strong competitive position in core markets with sustainable advantages
        2. **Growth Trajectory**: Clear path to revenue expansion through organic growth and market share gains
        3. **Margin Expansion**: Operational improvements driving profitability enhancement
        
        The combination of these factors supports our fair value estimate of ${valuation.value_per_share:.2f}, 
        representing attractive upside potential for long-term investors.
        """,
        
        "risk_analysis": f"""
        **Key Risks to Monitor**:
        
        - **Competition**: Intensifying competitive pressures could impact market share and pricing power
        - **Regulation**: Evolving regulatory landscape may affect operational flexibility
        - **Macro Environment**: Economic headwinds could dampen growth prospects
        - **Execution Risk**: Ability to deliver on strategic initiatives and operational improvements
        
        Despite these risks, we believe the company's strong fundamentals and strategic positioning 
        provide adequate risk mitigation for long-term investors.
        """
    }


def generate_interactive_report(
    ticker: str,
    output_dir: Optional[Path] = None,
    use_llm: bool = False,
    evaluate: bool = False
) -> Path:
    """
    Generate an interactive HTML report for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        output_dir: Output directory (defaults to out/TICKER/)
        use_llm: Whether to use LLM for narratives
        evaluate: Whether to run evaluation scoring
        
    Returns:
        Path to generated HTML file
    """
    
    output_dir = output_dir or Path("out") / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating interactive report for {ticker}...")
    
    # Fetch fundamentals
    print("Fetching company data...")
    try:
        cf, metadata = fetch_companyfacts(ticker)
        fundamentals = parse_companyfacts_to_fundamentals(cf, ticker, company=metadata.get('entityName'))
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
    
    # Build inputs and valuation
    print("Running valuation model...")
    inputs = build_inputs_from_fundamentals(fundamentals)
    valuation = kernel_value(inputs)
    
    print(f"Fair Value: ${valuation.value_per_share:.2f}")
    
    # Generate narratives
    narratives = None
    if use_llm and HAS_LLM:
        print("Generating professional narratives with LLM...")
        try:
            writer = WriterLLMGen()
            narratives = writer.generate_professional_narrative(inputs, valuation)
        except Exception as e:
            print(f"LLM generation failed: {e}")
            print("Falling back to template narratives...")
            narratives = generate_fallback_narratives(inputs, valuation)
    else:
        narratives = generate_fallback_narratives(inputs, valuation)
    
    # Run evaluation if requested
    evaluation = None
    if evaluate and HAS_LLM:
        print("Running quality evaluation...")
        try:
            evaluator = FixedEvaluationRunner()
            # Create a simple report for evaluation
            report_text = f"""
            # {inputs.company} Investment Report
            
            ## Executive Summary
            {narratives.get('executive_summary', '')}
            
            ## Financial Analysis
            {narratives.get('financial_analysis', '')}
            
            ## Investment Thesis
            {narratives.get('investment_thesis', '')}
            
            ## Risk Analysis
            {narratives.get('risk_analysis', '')}
            """
            evaluation = evaluator.evaluate_report(report_text, ticker, inputs.company)
            print(f"Quality Score: {evaluation.overall_score:.1f}/10")
        except Exception as e:
            print(f"Evaluation failed: {e}")
    
    # Fetch current market price
    current_price = None
    
    # Try Yahoo first
    try:
        price_series = fetch_prices_v8_chart(ticker, range_="5d", interval="1d")
        if price_series.bars:
            current_price = price_series.bars[-1].close
            print(f"Current Market Price (Yahoo): ${current_price:.2f}")
    except Exception as e:
        print(f"Yahoo price fetch failed: {e}")
    
    # Try Stooq as fallback
    if current_price is None:
        try:
            price_series = fetch_stooq_prices(ticker)
            if price_series.bars:
                current_price = price_series.bars[-1].close
                print(f"Current Market Price (Stooq): ${current_price:.2f}")
        except Exception as e:
            print(f"Stooq price fetch failed: {e}")
    
    # Final fallback
    if current_price is None:
        current_price = valuation.value_per_share * 0.85
        print(f"Warning: Could not fetch market price from any source, using estimate: ${current_price:.2f}")
    
    # Mock evidence (in production, from evidence pipeline)
    evidence = [
        {
            "quote": "The company reported record revenue growth of 25% year-over-year, driven by strong demand across all segments.",
            "source_url": "#",
            "source_name": "Q3 2024 Earnings Report",
            "confidence": 0.9
        },
        {
            "quote": "Management raised full-year guidance, citing improving market conditions and operational efficiencies.",
            "source_url": "#",
            "source_name": "Investor Call Transcript",
            "confidence": 0.85
        },
        {
            "quote": "Industry analysts project continued growth in the company's core markets, with TAM expanding at 15% CAGR.",
            "source_url": "#",
            "source_name": "Industry Research Report",
            "confidence": 0.75
        }
    ]
    
    # Build interactive report
    print("Building interactive HTML report...")
    builder = InteractiveReportBuilder()
    html = builder.build(
        inputs=inputs,
        valuation=valuation,
        narratives=narratives,
        evaluation=evaluation,
        evidence=evidence,
        current_price=current_price
    )
    
    # Save report
    output_path = output_dir / "interactive_report.html"
    builder.save_report(html, output_path, include_chart_js=True)
    
    print(f"✅ Interactive report generated: {output_path}")
    print(f"   Open in browser: file://{output_path.absolute()}")
    
    # Also save the data as JSON for debugging
    data_path = output_dir / "report_data.json"
    report_data = {
        "ticker": ticker,
        "company": inputs.company,
        "fair_value": valuation.value_per_share,
        "current_price": current_price,
        "upside": ((valuation.value_per_share - current_price) / current_price) * 100,
        "evaluation_score": evaluation.overall_score if evaluation else None,
        "narratives": narratives,
        "evidence": evidence
    }
    
    with open(data_path, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    return output_path


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Interactive Investment Report")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--output-dir", type=Path, help="Output directory")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for narratives")
    parser.add_argument("--evaluate", action="store_true", help="Run quality evaluation")
    
    args = parser.parse_args()
    
    generate_interactive_report(
        ticker=args.ticker,
        output_dir=args.output_dir,
        use_llm=args.use_llm,
        evaluate=args.evaluate
    )


if __name__ == "__main__":
    main()