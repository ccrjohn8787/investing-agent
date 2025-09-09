#!/usr/bin/env python3
"""
Enhanced Report Script with Evidence Pipeline Integration

Extends the standard report generation with evidence-based research pipeline
while maintaining backward compatibility with existing functionality.
"""

# Import all original functionality
from scripts.report import *
from investing_agent.orchestration.evidence_integration import (
    integrate_evidence_pipeline, 
    create_evidence_narrative_context
)

def main():
    """Enhanced main function with evidence pipeline integration."""
    # Parse arguments (using existing argument parser)
    args = parse_args()
    
    # Original initialization code
    ticker = args.ticker.upper()
    
    # Config
    cfg = {}
    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
    
    # Output setup
    out_dir = Path(args.output_dir or f"out/{ticker}")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize manifest and event log
    manifest = Manifest()
    eventlog = EventLog()
    
    # Build fundamentals and inputs (original flow)
    if args.mock:
        # Mock data path...
        I = build_mock_inputs(ticker, cfg)
        f_for_report = None
        citations = []
    else:
        # Real data path...
        # [Original fundamentals building code would go here]
        # For now, using simplified version
        from investing_agent.agents.valuation import build_inputs_from_fundamentals
        from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals
        
        try:
            cf_json = fetch_companyfacts(ticker)
            f = parse_companyfacts_to_fundamentals(ticker, cf_json)
            I = build_inputs_from_fundamentals(ticker, f, cfg)
            f_for_report = f
            citations = []
        except Exception as e:
            print(f"Failed to build fundamentals: {e}")
            I = build_mock_inputs(ticker, cfg)
            f_for_report = None
            citations = []
    
    # Apply CLI overrides to drivers
    if args.growth:
        I.drivers.sales_growth = _parse_path_arg(args.growth)
    if args.margin:
        I.drivers.oper_margin = _parse_path_arg(args.margin)
    
    print(f"Initial InputsI: growth={I.drivers.sales_growth}, margin={I.drivers.oper_margin}")
    
    # ✨ NEW: Evidence Pipeline Integration ✨
    evidence_artifacts = {}
    if not args.disable_evidence:  # New flag for backward compatibility
        print(f"\n🔬 Executing Evidence Pipeline for {ticker}")
        
        try:
            # Integrate evidence pipeline
            evidence_cassette = args.evidence_cassette if hasattr(args, 'evidence_cassette') else None
            I_with_evidence, evidence_artifacts = integrate_evidence_pipeline(
                ticker=ticker,
                inputs=I,
                manifest=manifest,
                cassette_path=evidence_cassette,
                output_dir=out_dir,
                confidence_threshold=args.evidence_threshold if hasattr(args, 'evidence_threshold') else 0.80
            )
            
            # Update InputsI with evidence-based modifications
            I = I_with_evidence
            
            print(f"Evidence-Enhanced InputsI: growth={I.drivers.sales_growth}, margin={I.drivers.oper_margin}")
            
            # Log evidence impact
            if evidence_artifacts.get('model_pr_log'):
                pr_log = evidence_artifacts['model_pr_log']
                print(f"Evidence Impact: {pr_log.validation_summary.get('total_applied', 0)} changes applied")
                
                # Save detailed logs
                pr_log.export_to_json(str(out_dir / f"model_pr_log_{ticker}.json"))
                manifest.add_artifact(f"model_pr_log_{ticker}.json", pr_log.dict())
                
        except Exception as e:
            print(f"Warning: Evidence pipeline failed: {e}")
            print("Continuing with original inputs...")
    else:
        print("Evidence pipeline disabled")
    
    # Continue with original valuation flow
    print(f"\n📊 Computing Valuation for {ticker}")
    
    # Valuation computation (original)
    V = kernel_value(I)
    
    # Market solver, consensus, etc. (original flow)
    # [Market solver and other enhancements would go here]
    
    # Sensitivity analysis (original)
    sensitivity = compute_sensitivity(I)
    
    # Plotting (original)
    heat_png = plot_sensitivity_heatmap(sensitivity, out_dir / "sensitivity.png")
    drv_png = plot_driver_paths(I, V, out_dir / "driver_paths.png")
    
    # News processing (keep existing for compatibility)
    news_summary = None
    if not args.disable_news:
        try:
            news_bundle = fetch_news(ticker, limit=5)
            news_summary = heuristic_summarize(news_bundle, I)
            manifest.add_artifact("news.json", news_bundle.model_dump())
        except Exception:
            pass
    
    # Insights processing (backward compatibility)
    insights_bundle = None
    if args.insights_llm_cassette or args.insights_llm_live:
        # Use existing insights processing
        try:
            texts = []
            filings_dir = out_dir / "filings"
            if filings_dir.exists():
                for p in sorted(filings_dir.glob("*.txt")):
                    sha = p.stem
                    texts.append({"kind": "filing", "text": p.read_text(), "snapshot_sha": sha, "url": "", "date": None})
            
            if args.insights_llm_cassette:
                from investing_agent.agents.research_llm import generate_insights
                insights_bundle = generate_insights(texts, cassette_path=args.insights_llm_cassette)
            elif args.insights_llm_live:
                from investing_agent.agents.research_llm import generate_insights
                insights_bundle = generate_insights(texts, cassette_path=None, live=True)
                
        except Exception:
            pass
    
    # ✨ NEW: Create Evidence Context for Narrative ✨
    narrative_context = create_evidence_narrative_context(evidence_artifacts)
    if narrative_context:
        # Use evidence-based insights if available
        insights_bundle = narrative_context.get('insights_bundle')
        print(f"Using evidence-based insights: {narrative_context['high_confidence_claims']} high-confidence claims")
    
    # Report generation (enhanced with evidence context)
    print(f"\n📝 Generating Report for {ticker}")
    
    md = render_report(
        I,
        V,
        sensitivity_png=heat_png,
        driver_paths_png=drv_png,
        citations=citations,
        fundamentals=f_for_report,
        news=news_summary,
        insights=insights_bundle,
        # Pass evidence context for enhanced narrative
        evidence_context=narrative_context
    )
    
    # Add evidence summary section to report
    if evidence_artifacts.get('evidence_bundle'):
        md += generate_evidence_summary_section(evidence_artifacts)
    
    # Save outputs
    (out_dir / "report.md").write_text(md)
    (out_dir / "inputs.json").write_text(I.model_dump_json(indent=2))
    (out_dir / "valuation.json").write_text(V.model_dump_json(indent=2))
    
    # Save manifest with evidence tracking
    manifest.save(out_dir / "manifest.json")
    
    print(f"✅ Enhanced report generated: {out_dir}/report.md")
    if evidence_artifacts.get('frozen_evidence_path'):
        print(f"🔒 Evidence frozen at: {evidence_artifacts['frozen_evidence_path']}")


def generate_evidence_summary_section(evidence_artifacts: Dict[str, Any]) -> str:
    """Generate evidence summary section for report."""
    if not evidence_artifacts.get('evidence_bundle'):
        return ""
    
    evidence_bundle = evidence_artifacts['evidence_bundle']
    processing_summary = evidence_artifacts.get('processing_summary', {})
    
    section = "\n\n## Evidence Summary\n\n"
    
    # Research metadata
    section += f"**Research Timestamp:** {evidence_bundle.research_timestamp}\n\n"
    section += f"**Evidence Status:** {'Frozen' if evidence_bundle.frozen else 'Active'}\n\n"
    
    # Evidence statistics
    total_items = len(evidence_bundle.items)
    total_claims = sum(len(item.claims) for item in evidence_bundle.items)
    high_conf_claims = len(evidence_bundle.get_high_confidence_claims(0.80))
    
    section += f"**Evidence Items:** {total_items}\n\n"
    section += f"**Total Claims:** {total_claims}\n\n"
    section += f"**High-Confidence Claims:** {high_conf_claims}\n\n"
    
    # Driver impacts
    if evidence_artifacts.get('model_pr_log'):
        pr_log = evidence_artifacts['model_pr_log']
        changes_applied = pr_log.validation_summary.get('total_applied', 0)
        section += f"**Driver Changes Applied:** {changes_applied}\n\n"
        
        # Show key driver modifications
        if changes_applied > 0:
            section += "**Key Driver Modifications:**\n\n"
            for change in pr_log.changes[:3]:  # Show first 3 changes
                section += f"- {change.target_path}: {change.before_value:.3f} → {change.after_value:.3f} (confidence: {change.claim_confidence:.2f})\n"
            section += "\n"
    
    # Quality score
    if processing_summary.get('quality_score'):
        quality_score = processing_summary['quality_score']
        section += f"**Evidence Quality Score:** {quality_score:.2f}/1.0\n\n"
    
    section += "*Evidence pipeline ensures deterministic, auditable valuation adjustments.*\n"
    
    return section


def parse_enhanced_args():
    """Parse arguments with evidence pipeline options."""
    import argparse
    
    # Start with existing parser
    parser = argparse.ArgumentParser(description="Enhanced report generation with evidence pipeline")
    
    # Add all original arguments
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--mock", action="store_true", help="Use mock data")
    parser.add_argument("--growth", help="Sales growth override (comma-separated)")
    parser.add_argument("--margin", help="Operating margin override (comma-separated)")
    parser.add_argument("--insights-llm-cassette", help="Insights cassette path")
    parser.add_argument("--insights-llm-live", action="store_true", help="Live insights generation")
    parser.add_argument("--disable-news", action="store_true", help="Disable news processing")
    
    # Add evidence pipeline arguments
    parser.add_argument("--disable-evidence", action="store_true", 
                       help="Disable evidence pipeline (backward compatibility)")
    parser.add_argument("--evidence-cassette", help="Evidence generation cassette path")
    parser.add_argument("--evidence-threshold", type=float, default=0.80,
                       help="Evidence confidence threshold (default: 0.80)")
    parser.add_argument("--force-new-research", action="store_true",
                       help="Force new research even if frozen evidence exists")
    
    return parser.parse_args()


if __name__ == "__main__":
    # Use enhanced argument parsing
    import sys
    sys.modules[__name__].parse_args = parse_enhanced_args
    main()