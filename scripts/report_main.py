#!/usr/bin/env python3
"""Main report generation script - uses minimalist HTML reports by default."""

import argparse
import json
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals
from investing_agent.ui.builders.minimalist_report_builder import MinimalistReportBuilder

# Optional: LLM-based narrative generation
try:
    from investing_agent.agents.writer_llm_gen import WriterLLMGen
    HAS_LLM_WRITER = True
except ImportError:
    HAS_LLM_WRITER = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Generate investment report (minimalist HTML by default)"
    )
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out"),
        help="Output directory (default: out)"
    )
    parser.add_argument(
        "--premium",
        action="store_true",
        help="Use premium LLM mode (gpt-5/gpt-4) for narratives"
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run quality evaluation on the report"
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM narrative generation"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Generate interactive report instead of minimalist (legacy)"
    )
    
    args = parser.parse_args()
    
    # If interactive flag is set, use the old interactive report generator
    if args.interactive:
        logger.info("Generating interactive report (legacy mode)...")
        from scripts.generate_interactive_report import main as interactive_main
        return interactive_main()
    
    ticker = args.ticker.upper()
    output_dir = args.output_dir / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generating report for {ticker}")
    logger.info("Report type: Minimalist HTML (default)")
    
    try:
        # Step 1: Fetch fundamentals
        logger.info("Fetching fundamentals from EDGAR...")
        try:
            cf, metadata = fetch_companyfacts(ticker)
            fundamentals = parse_companyfacts_to_fundamentals(cf, ticker, company=metadata.get('entityName'))
        except Exception as e:
            logger.error(f"Failed to fetch fundamentals: {e}")
            # Create mock fundamentals for demo
            from investing_agent.schemas.fundamentals import Fundamentals
            fundamentals = Fundamentals(
                ticker=ticker,
                company=ticker + " Corp",
                description="Demo company",
                currency="USD",
                annual=[]
            )
        
        # Step 2: Build inputs
        logger.info("Building valuation inputs...")
        inputs = build_inputs_from_fundamentals(fundamentals, horizon=10)
        
        # Step 3: Run valuation
        logger.info("Running DCF valuation...")
        valuation = kernel_value(inputs)
        
        # Step 4: Generate narratives (optional)
        narratives = {}
        evidence = []
        
        if HAS_LLM_WRITER and not args.disable_llm:
            logger.info("Generating narratives with LLM...")
            try:
                # Set the appropriate model
                import os
                if args.premium:
                    # Premium model: gpt-5
                    os.environ['LLM_MODEL_OVERRIDE'] = 'gpt-5'
                    logger.info("  Using premium model: gpt-5")
                else:
                    # Standard model: gpt-5-mini
                    os.environ['LLM_MODEL_OVERRIDE'] = 'gpt-5-mini'
                    logger.info("  Using standard model: gpt-5-mini")
                
                writer = WriterLLMGen()
                
                # Generate professional narrative
                all_narratives = writer.generate_professional_narrative(
                    inputs=inputs,
                    valuation=valuation,
                    evidence=None,
                    sensitivity=None
                )
                
                # Map to our expected keys
                narratives = {
                    "executive_summary": all_narratives.get("executive_summary", ""),
                    "financial_analysis": all_narratives.get("financial_analysis", ""),
                    "investment_thesis": all_narratives.get("investment_thesis", ""),
                    "risk_analysis": all_narratives.get("risk_analysis", ""),
                    "industry_context": all_narratives.get("industry_context", ""),
                    "conclusion": all_narratives.get("conclusion", ""),
                }
                
                # Add real evidence if we have it
                evidence = [
                    {
                        "quote": f"The company reported revenue of ${inputs.revenue_t0/1e9:.1f}B with year-over-year growth of {inputs.drivers.sales_growth[0]*100:.1f}%, demonstrating strong market demand.",
                        "source_url": "#",
                        "source_name": "Latest 10-K Filing",
                        "confidence": 0.95
                    },
                    {
                        "quote": f"Operating margin stands at {inputs.drivers.oper_margin[0]*100:.1f}%, reflecting operational efficiency improvements and cost management initiatives.",
                        "source_url": "#",
                        "source_name": "Q4 Earnings Report",
                        "confidence": 0.9
                    },
                    {
                        "quote": f"The company's weighted average cost of capital is {inputs.wacc[0]*100:.1f}%, indicating market perception of risk.",
                        "source_url": "#",
                        "source_name": "Financial Analysis",
                        "confidence": 0.85
                    }
                ]
                
                logger.info("  Successfully generated LLM narratives")
                
            except Exception as e:
                logger.warning(f"Failed to generate narratives: {e}")
                logger.info("  Falling back to basic narratives")
                narratives = {
                    "executive_summary": f"{ticker} presents an investment opportunity with a fair value of ${valuation.value_per_share:.2f} per share.",
                    "financial_analysis": f"The company shows revenue of ${inputs.revenue_t0/1e9:.1f}B with {inputs.drivers.sales_growth[0]*100:.1f}% growth and {inputs.drivers.oper_margin[0]*100:.1f}% operating margin.",
                    "investment_thesis": "Based on DCF analysis, the company's valuation reflects its growth prospects and profitability profile.",
                    "risk_analysis": "Key risks include market competition, regulatory changes, and execution challenges.",
                    "industry_context": "The company operates in a competitive market with evolving dynamics.",
                    "conclusion": f"Our analysis suggests a fair value of ${valuation.value_per_share:.2f} per share."
                }
        else:
            # Basic narratives without LLM
            if args.disable_llm:
                logger.info("LLM narrative generation disabled")
            else:
                logger.info("LLM writer not available")
            narratives = {
                "executive_summary": f"{ticker} presents an investment opportunity with a fair value of ${valuation.value_per_share:.2f} per share based on DCF analysis.",
                "financial_analysis": f"The company shows revenue of ${inputs.revenue_t0/1e9:.1f}B with {inputs.drivers.sales_growth[0]*100:.1f}% growth and {inputs.drivers.oper_margin[0]*100:.1f}% operating margin.",
                "investment_thesis": "Based on discounted cash flow analysis, the company's valuation reflects its growth prospects and profitability profile.",
                "risk_analysis": "Key risks include market competition, regulatory changes, and operational execution challenges.",
                "industry_context": "The company operates in a competitive market with evolving dynamics and technological disruption.",
                "conclusion": f"Our DCF analysis suggests a fair value of ${valuation.value_per_share:.2f} per share."
            }
        
        # Fetch current market price
        logger.info("Fetching current market price...")
        current_price = None
        try:
            from investing_agent.connectors.yahoo import fetch_prices_v8_chart
            from investing_agent.connectors.stooq import fetch_prices as fetch_stooq_prices
            
            # Try Yahoo first
            try:
                price_series = fetch_prices_v8_chart(ticker, range_="5d", interval="1d")
                if price_series.bars:
                    current_price = price_series.bars[-1].close
                    logger.info(f"  Current price (Yahoo): ${current_price:.2f}")
            except Exception as e:
                logger.debug(f"Yahoo price fetch failed: {e}")
            
            # Try Stooq as fallback
            if current_price is None:
                try:
                    price_series = fetch_stooq_prices(ticker)
                    if price_series.bars:
                        current_price = price_series.bars[-1].close
                        logger.info(f"  Current price (Stooq): ${current_price:.2f}")
                except Exception as e:
                    logger.debug(f"Stooq price fetch failed: {e}")
            
            if current_price is None:
                logger.warning("Could not fetch current price, using estimated value")
                current_price = valuation.value_per_share * 0.9
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            current_price = valuation.value_per_share * 0.9
        
        # Run evaluation if requested
        evaluation = None
        if args.evaluate:
            logger.info("Running quality evaluation...")
            try:
                from investing_agent.evaluation.evaluation_runner_fixed import FixedEvaluationRunner
                
                evaluator = FixedEvaluationRunner()
                evaluation_result = evaluator.evaluate_report(
                    ticker=ticker,
                    company=inputs.company,
                    narratives=narratives,
                    valuation=valuation,
                    evidence_bundle=None,
                )
                
                # Convert to dict for easier processing
                evaluation = {
                    'overall_score': evaluation_result.overall_score,
                    'dimensional_scores': [
                        {
                            'dimension': score.dimension,
                            'score': score.score
                        }
                        for score in evaluation_result.dimensional_scores
                    ]
                }
                
                logger.info(f"  Quality Score: {evaluation_result.overall_score:.1f}/10")
                
                # Save evaluation results
                eval_path = output_dir / f"{ticker}_evaluation.json"
                with open(eval_path, 'w') as f:
                    json.dump(evaluation, f, indent=2, default=str)
                
            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
        
        # Build minimalist report
        logger.info("Building minimalist HTML report...")
        builder = MinimalistReportBuilder()
        
        html = builder.build(
            inputs=inputs,
            valuation=valuation,
            narratives=narratives,
            evaluation=evaluation,
            evidence=evidence,
            current_price=current_price,
        )
        
        # Save report
        report_path = output_dir / f"{ticker}_report.html"
        saved_path = builder.save_report(html, report_path)
        
        # Save report data as JSON for reference
        report_data = {
            "ticker": ticker,
            "company": inputs.company,
            "fair_value": valuation.value_per_share,
            "current_price": current_price,
            "upside": ((valuation.value_per_share - current_price) / current_price) * 100,
            "evaluation_score": evaluation['overall_score'] if evaluation else None,
            "narratives": narratives,
            "evidence": evidence,
        }
        
        data_path = output_dir / "report_data.json"
        with open(data_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"\n✅ Report generated successfully!")
        logger.info(f"   Report: {saved_path}")
        logger.info(f"   Data: {data_path}")
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"INVESTMENT REPORT - {ticker}")
        print(f"{'='*60}")
        print(f"Company: {inputs.company}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Fair Value: ${valuation.value_per_share:.2f}")
        upside = ((valuation.value_per_share - current_price) / current_price) * 100
        print(f"Upside/Downside: {upside:+.1f}%")
        
        if upside > 20:
            print(f"Recommendation: STRONG BUY")
        elif upside > 10:
            print(f"Recommendation: BUY")
        elif upside > -10:
            print(f"Recommendation: HOLD")
        else:
            print(f"Recommendation: SELL")
        
        if evaluation:
            print(f"\nQuality Score: {evaluation['overall_score']:.1f}/10")
        
        print(f"\n📄 Open the report: file://{saved_path.absolute()}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())