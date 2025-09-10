#!/usr/bin/env python3
"""Generate full professional investment report using all Priority 1-7 features."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Auto-load .env file
from investing_agent.config import load_env_file
env_loaded = load_env_file()
if env_loaded:
    print(f"✅ Loaded environment from: {env_loaded}")

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals

# Priority 1: Evidence Pipeline
try:
    from investing_agent.orchestration.evidence_integration import EvidenceIntegrationPipeline
except ImportError:
    EvidenceIntegrationPipeline = None
    
try:
    from investing_agent.agents.research_unified import UnifiedResearchAgent
except ImportError:
    UnifiedResearchAgent = None

# Priority 2: Professional Writer
try:
    from investing_agent.agents.writer_llm_gen import WriterLLMGen
    from investing_agent.agents.writer_llm_optimized import OptimizedLLMWriter
except ImportError:
    WriterLLMGen = None
    OptimizedLLMWriter = None
    
try:
    from investing_agent.agents.critic import Critic
except ImportError:
    Critic = None

# Priority 3: Comparables and WACC
try:
    from investing_agent.agents.comparables import apply as apply_comparables
except ImportError:
    apply_comparables = None
    
try:
    from investing_agent.agents.sensitivity import compute_sensitivity
except ImportError:
    compute_sensitivity = None

# Priority 6: Professional Presentation  
try:
    from investing_agent.agents.report_assembler import ProfessionalReportAssembler
except ImportError:
    ProfessionalReportAssembler = None
    
try:
    from investing_agent.agents.visualization_professional import ProfessionalVisualizer
except ImportError:
    ProfessionalVisualizer = None
    
try:
    from investing_agent.agents.table_generator import ProfessionalTableGenerator
except ImportError:
    ProfessionalTableGenerator = None

# Priority 7: Evaluation
try:
    from investing_agent.evaluation.evaluation_runner_fixed import FixedEvaluationRunner
except ImportError:
    FixedEvaluationRunner = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_full_professional_report(
    ticker: str,
    output_dir: Path,
    use_llm: bool = True,
    enable_evidence: bool = True,
    enable_comparables: bool = True,
    enable_sensitivity: bool = True,
    enable_evaluation: bool = True,
    llm_quality: str = "standard"  # "premium", "standard", or "budget"
) -> tuple[str, Path]:
    """Generate complete professional investment report.
    
    Args:
        ticker: Company ticker symbol
        output_dir: Output directory for report
        use_llm: Whether to use LLM for narrative generation
        enable_evidence: Whether to use evidence pipeline
        enable_comparables: Whether to include peer analysis
        enable_router: Whether to use enhanced router
        enable_evaluation: Whether to evaluate the report
        
    Returns:
        Tuple of (report_content, report_path)
    """
    
    logger.info(f"=== Generating Professional Report for {ticker} ===")
    
    # Step 1: Fetch fundamentals
    logger.info("Step 1: Fetching fundamentals from EDGAR...")
    try:
        cf, metadata = fetch_companyfacts(ticker)
        fundamentals = parse_companyfacts_to_fundamentals(cf, ticker, company=metadata.get('entityName'))
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals: {e}")
        logger.info("Using mock fundamentals for demonstration")
        fundamentals = create_mock_fundamentals(ticker)
    
    # Step 2: Build initial inputs
    logger.info("Step 2: Building valuation inputs...")
    inputs = build_inputs_from_fundamentals(fundamentals, horizon=10)
    
    # Step 3: Evidence Pipeline (Priority 1)
    evidence_bundle = None
    model_pr_log = None
    
    if enable_evidence and use_llm and EvidenceIntegrationPipeline:
        logger.info("Step 3: Running evidence pipeline...")
        try:
            evidence_pipeline = EvidenceIntegrationPipeline()
            inputs, evidence_bundle, model_pr_log = evidence_pipeline.enhance_with_evidence(
                inputs=inputs,
                ticker=ticker,
                force_new_research=False
            )
            logger.info(f"  ✓ Evidence gathered: {len(evidence_bundle.items) if evidence_bundle else 0} items")
            logger.info(f"  ✓ Driver adjustments: {len(model_pr_log.changes) if model_pr_log else 0} changes")
        except Exception as e:
            logger.warning(f"Evidence pipeline not available or failed: {e}")
    else:
        if not enable_evidence:
            logger.info("Step 3: Evidence pipeline disabled")
        elif not use_llm:
            logger.info("Step 3: Evidence pipeline skipped (LLM disabled)")
        else:
            logger.info("Step 3: Evidence pipeline not available")
    
    # Step 4: Sensitivity Analysis
    sensitivity = None
    if enable_sensitivity and compute_sensitivity:
        logger.info("Step 4: Computing sensitivity analysis...")
        try:
            sensitivity = compute_sensitivity(inputs)
            logger.info("  ✓ Sensitivity analysis complete")
        except Exception as e:
            logger.warning(f"Sensitivity analysis failed: {e}")
    else:
        logger.info("Step 4: Sensitivity analysis skipped")
    
    # Step 5: Comparables Analysis (Priority 3)
    peer_analysis = None
    
    if enable_comparables and apply_comparables:
        logger.info("Step 5: Running comparables analysis...")
        try:
            # Apply comparables adjustment
            inputs = apply_comparables(inputs)
            logger.info("  ✓ Comparables adjustment applied")
        except Exception as e:
            logger.warning(f"Comparables analysis failed: {e}")
    else:
        logger.info("Step 5: Comparables analysis skipped")
    
    # Step 6: WACC already calculated in build_inputs_from_fundamentals
    logger.info("Step 6: WACC calculation...")
    logger.info(f"  ✓ WACC path: {inputs.wacc[:5]}...") # Show first 5 values
    
    # Step 7: Run valuation
    logger.info("Step 7: Running valuation kernel...")
    valuation = kernel_value(inputs)
    logger.info(f"  ✓ Value per share: ${valuation.value_per_share:.2f}")
    
    # Step 8: Generate Professional Report (Priority 2, 4, 6)
    logger.info("Step 8: Generating professional report...")
    
    narrative_sections = {}
    if use_llm:
        # Use optimized writer for cost savings
        try:
            # Choose writer based on quality setting
            if llm_quality != "premium" and OptimizedLLMWriter:
                logger.info(f"  Using optimized writer ({llm_quality} mode)")
                writer = OptimizedLLMWriter(quality_mode=llm_quality)
            elif WriterLLMGen:
                logger.info(f"  Using premium writer (GPT-4)")
                writer = WriterLLMGen()
            else:
                raise ImportError("No LLM writer available")
            
            # Generate narrative sections with LLM
            narrative_sections = writer.generate_professional_narrative(
                inputs=inputs,
                valuation=valuation,
                evidence=evidence_bundle,
                sensitivity=sensitivity
            )
            
            # Run critic validation if available
            if Critic:
                try:
                    critic = Critic()
                    critic_result = critic.validate_report(narrative_sections)
                    if critic_result.get('issues'):
                        logger.warning(f"Critic found issues: {critic_result['issues']}")
                except Exception as e:
                    logger.warning(f"Critic validation failed: {e}")
            
            logger.info("  ✓ Professional narrative generated")
        except Exception as e:
            logger.error(f"LLM narrative generation failed: {e}")
            narrative_sections = {}
    
    # Generate professional tables and visualizations
    sensitivity_table = ""
    if ProfessionalTableGenerator and sensitivity:
        try:
            table_gen = ProfessionalTableGenerator()
            if hasattr(sensitivity, 'grid'):
                growth_labels = ["13%", "15%", "17%", "19%", "21%"]
                margin_labels = ["38%", "40%", "42%", "44%", "46%"]
                sensitivity_table = table_gen.create_sensitivity_table(
                    sensitivity.grid, growth_labels, margin_labels
                )
        except Exception as e:
            logger.warning(f"Table generation failed: {e}")
    
    # Assemble the report with professional formatting
    if ProfessionalReportAssembler:
        try:
            assembler = ProfessionalReportAssembler()
            report_content = assembler.create_professional_report(
                inputs=inputs,
                valuation=valuation,
                evidence=evidence_bundle,
                sensitivity_table=sensitivity_table,
                narrative_sections=narrative_sections
            )
        except Exception as e:
            logger.warning(f"Professional assembler failed: {e}, using basic format")
            report_content = create_basic_report(inputs, valuation, narrative_sections, sensitivity_table)
    else:
        report_content = create_basic_report(inputs, valuation, narrative_sections, sensitivity_table)
    
    # Step 9: Save report
    logger.info("Step 9: Saving report...")
    report_path = output_dir / f"{ticker}_professional_report.md"
    report_path.write_text(report_content)
    
    # Also save HTML version
    html_path = output_dir / f"{ticker}_professional_report.html"
    html_content = convert_to_html(report_content)
    html_path.write_text(html_content)
    
    logger.info(f"  ✓ Report saved: {report_path}")
    logger.info(f"  ✓ HTML saved: {html_path}")
    
    # Step 10: Evaluate report quality (Priority 7)
    if enable_evaluation and FixedEvaluationRunner:
        logger.info("Step 10: Evaluating report quality...")
        try:
            evaluator = FixedEvaluationRunner()
            eval_result = evaluator.evaluate_report(
                report_content=report_content,
                ticker=ticker,
                company=fundamentals.company
            )
            
            logger.info(f"  ✓ Overall Score: {eval_result.overall_score:.1f}/10")
            logger.info(f"  ✓ Quality Gates: {'PASS' if eval_result.passes_quality_gates else 'FAIL'}")
            
            for score in eval_result.dimensional_scores:
                status = "✓" if score.score >= 7.0 else "✗"
                logger.info(f"    {status} {score.dimension.value}: {score.score:.1f}/10")
            
            # Save evaluation
            eval_path = output_dir / f"{ticker}_evaluation.json"
            with eval_path.open("w") as f:
                json.dump(eval_result.model_dump(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
    
    # Step 11: Generate Interactive HTML Report
    try:
        from investing_agent.ui import InteractiveReportBuilder
        
        logger.info("Step 11: Generating interactive HTML report...")
        
        # Get evaluation result if it exists
        evaluation = None
        eval_path = output_dir / f"{ticker}_evaluation.json"
        if eval_path.exists():
            with eval_path.open() as f:
                eval_data = json.load(f)
                # Just pass the raw eval data - the builder will handle it
                evaluation = eval_data
        
        # Fetch current market price
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
        except Exception as e:
            logger.warning(f"Could not fetch market price: {e}")
        
        # Build interactive report
        builder = InteractiveReportBuilder()
        interactive_html = builder.build(
            inputs=inputs,
            valuation=valuation,
            narratives=narrative_sections if use_llm else None,
            evaluation=evaluation,
            evidence=None,  # Could add evidence if available
            current_price=current_price  # Pass actual market price
        )
        
        # Save interactive report
        interactive_path = output_dir / "interactive_report.html"
        builder.save_report(interactive_html, interactive_path, include_chart_js=True)
        
        logger.info(f"  ✓ Interactive report saved: {interactive_path}")
        logger.info(f"  ✓ Open in browser: file://{interactive_path.absolute()}")
        
    except Exception as e:
        logger.warning(f"Could not generate interactive report: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"REPORT GENERATION COMPLETE")
    logger.info(f"{'='*60}")
    
    return report_content, report_path


def create_mock_fundamentals(ticker: str) -> Fundamentals:
    """Create mock fundamentals for demonstration."""
    current_year = datetime.now().year
    
    return Fundamentals(
        company=f"{ticker} Corporation",
        ticker=ticker,
        currency="USD",
        revenue={
            current_year - 2: 100_000_000_000,
            current_year - 1: 120_000_000_000,
            current_year: 150_000_000_000
        },
        ebit={
            current_year - 2: 20_000_000_000,
            current_year - 1: 25_000_000_000,
            current_year: 35_000_000_000
        },
        shares_out=1_000_000_000,
        tax_rate=0.21,
        net_debt=10_000_000_000
    )


def create_basic_report(inputs, valuation, narrative_sections, sensitivity_table):
    """Create a basic report when professional assembler is not available."""
    from datetime import datetime
    
    report = f"""# Investment Report: {inputs.company} ({inputs.ticker})

*Generated: {datetime.now().strftime('%B %d, %Y')}*

## Executive Summary

{narrative_sections.get('executive_summary', 'Our valuation analysis indicates a fair value per share of ${:.2f}.'.format(valuation.value_per_share))}

## Valuation Summary

| Metric | Value |
|--------|-------|
| **Fair Value per Share** | ${valuation.value_per_share:.2f} |
| **PV Explicit** | ${valuation.pv_explicit / 1e9:.1f}B |
| **PV Terminal** | ${valuation.pv_terminal / 1e9:.1f}B |
| **Enterprise Value** | ${(valuation.pv_oper_assets + valuation.net_debt - valuation.cash_nonop) / 1e9:.1f}B |

## Financial Analysis

{narrative_sections.get('financial_analysis', '')}

## Valuation Model

### Key Assumptions
- **Revenue Growth**: {inputs.drivers.sales_growth[0]*100:.1f}% Year 1, declining to {inputs.drivers.stable_growth*100:.1f}% terminal
- **Operating Margin**: {inputs.drivers.oper_margin[0]*100:.1f}% current, {inputs.drivers.stable_margin*100:.1f}% terminal  
- **WACC**: {inputs.wacc[0]*100:.1f}% current
- **Terminal Growth**: {inputs.drivers.stable_growth*100:.1f}%

{sensitivity_table}

## Investment Thesis

{narrative_sections.get('investment_thesis', '')}

## Risk Analysis

{narrative_sections.get('risk_analysis', '')}

## Conclusion

{narrative_sections.get('conclusion', f'Based on our DCF analysis, we derive a fair value of ${valuation.value_per_share:.2f} per share for {inputs.company}.')}

---

*This report integrates fundamental analysis and forward-looking projections. All valuations are based on DCF methodology with assumptions clearly stated above.*
"""
    return report

def convert_to_html(markdown_content: str) -> str:
    """Convert markdown to HTML with styling."""
    try:
        import markdown
        html_body = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    except ImportError:
        # Fallback to basic conversion
        html_body = f"<pre>{markdown_content}</pre>"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Professional Investment Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #2563eb; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }}
        h2 {{ color: #1e40af; margin-top: 30px; }}
        h3 {{ color: #3730a3; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f3f4f6;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9fafb;
        }}
        .metric-box {{
            background: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
        }}
        .citation {{
            color: #6b7280;
            font-size: 0.9em;
        }}
        blockquote {{
            border-left: 4px solid #d1d5db;
            padding-left: 20px;
            margin: 20px 0;
            color: #4b5563;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""
    return html


def main():
    """Main entry point."""
    import os
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\n⚠️  Warning: OPENAI_API_KEY not set")
        print("   To enable LLM narratives, either:")
        print("   1. Create a .env file with OPENAI_API_KEY=sk-...")
        print("   2. Export OPENAI_API_KEY=sk-...")
        print("   Continuing with template-only generation...\n")
    
    parser = argparse.ArgumentParser(description="Generate Professional Investment Report")
    parser.add_argument("ticker", help="Company ticker symbol")
    parser.add_argument("--output-dir", default="out", help="Output directory")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM narrative generation")
    parser.add_argument("--no-evidence", action="store_true", help="Disable evidence pipeline")
    parser.add_argument("--no-comparables", action="store_true", help="Disable comparables")
    parser.add_argument("--no-sensitivity", action="store_true", help="Disable sensitivity analysis")
    parser.add_argument("--no-evaluation", action="store_true", help="Disable quality evaluation")
    parser.add_argument("--llm-quality", choices=["premium", "standard", "budget"], 
                       default="standard", 
                       help="LLM quality mode: standard (GPT-4o-mini, default), premium (GPT-4 - use only when explicitly requested), budget (GPT-3.5)")
    
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = Path(args.output_dir) / args.ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate report
    report_content, report_path = generate_full_professional_report(
        ticker=args.ticker,
        output_dir=output_dir,
        use_llm=not args.no_llm,
        enable_evidence=not args.no_evidence,
        enable_comparables=not args.no_comparables,
        enable_sensitivity=not args.no_sensitivity,
        enable_evaluation=not args.no_evaluation,
        llm_quality=args.llm_quality
    )
    
    print(f"\n✅ Professional report generated: {report_path}")
    print(f"📊 View HTML: file://{output_dir.absolute()}/{args.ticker}_professional_report.html")


if __name__ == "__main__":
    main()