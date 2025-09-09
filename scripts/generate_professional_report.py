#!/usr/bin/env python3
"""Generate professional investment report with all Priority 6 enhancements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.agents.report_assembler import create_professional_report
from investing_agent.agents.sensitivity import compute_sensitivity

# Import Priority 1-5 components if available
try:
    from investing_agent.orchestration.evidence_integration import EvidenceIntegrationPipeline
except ImportError:
    EvidenceIntegrationPipeline = None

try:
    from investing_agent.agents.comparables import apply as apply_comparables
    from investing_agent.agents.peer_selection import PeerSelector
except ImportError:
    apply_comparables = None
    PeerSelector = None


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_fundamentals(ticker: str = "DEMO") -> Fundamentals:
    """Create sample fundamentals for demonstration."""
    
    current_year = datetime.now().year
    
    return Fundamentals(
        company=f"{ticker} Corporation",
        ticker=ticker,
        currency="USD",
        revenue={
            current_year - 2: 2500.0,
            current_year - 1: 2800.0,
            current_year: 3100.0
        },
        ebit={
            current_year - 2: 375.0,
            current_year - 1: 448.0,
            current_year: 527.0
        },
        ebitda={
            current_year - 2: 425.0,
            current_year - 1: 504.0,
            current_year: 589.0
        },
        net_income={
            current_year - 2: 300.0,
            current_year - 1: 358.0,
            current_year: 422.0
        },
        shares_out=500.0,
        shares_out_diluted=510.0,
        total_assets={
            current_year - 2: 5000.0,
            current_year - 1: 5500.0,
            current_year: 6000.0
        },
        total_debt={
            current_year - 2: 1000.0,
            current_year - 1: 1100.0,
            current_year: 1200.0
        },
        cash={
            current_year - 2: 500.0,
            current_year - 1: 600.0,
            current_year: 700.0
        },
        net_debt=500.0,
        tax_rate=0.21,
        capex={
            current_year - 2: -250.0,
            current_year - 1: -280.0,
            current_year: -310.0
        }
    )


def load_real_fundamentals(ticker: str) -> Fundamentals:
    """Load real fundamentals from EDGAR if available."""
    try:
        from investing_agent.connectors.edgar import fetch_fundamentals
        logger.info(f"Fetching fundamentals for {ticker} from EDGAR...")
        return fetch_fundamentals(ticker)
    except Exception as e:
        logger.warning(f"Could not fetch real fundamentals: {e}")
        logger.info("Using sample fundamentals instead")
        return create_sample_fundamentals(ticker)


def generate_mock_evidence_bundle(ticker: str) -> dict:
    """Generate mock evidence bundle for demonstration."""
    
    from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
    
    bundle = EvidenceBundle(
        research_timestamp=datetime.utcnow().isoformat(),
        ticker=ticker,
        items=[
            EvidenceItem(
                id="ev_mgmt_guidance",
                source_url="https://example.com/earnings-call",
                snapshot_id="snap_001",
                date=datetime.now().strftime("%Y-%m-%d"),
                source_type="transcript",
                title=f"{ticker} Q4 Earnings Call Transcript",
                claims=[
                    EvidenceClaim(
                        driver="growth",
                        statement="Management guides for 12-15% revenue growth in FY2024",
                        direction="+",
                        magnitude_units="%",
                        magnitude_value=13.5,
                        horizon="y1",
                        confidence=0.90,
                        quote="We expect revenue growth of 12-15% driven by new product launches"
                    ),
                    EvidenceClaim(
                        driver="margin",
                        statement="Operating margin expansion of 200bps expected",
                        direction="+",
                        magnitude_units="bps",
                        magnitude_value=200,
                        horizon="y1-3",
                        confidence=0.85,
                        quote="We see clear path to 200bps margin improvement through operational efficiency"
                    )
                ]
            ),
            EvidenceItem(
                id="ev_industry_report",
                source_url="https://example.com/industry-analysis",
                snapshot_id="snap_002",
                date=datetime.now().strftime("%Y-%m-%d"),
                source_type="research",
                title="Industry Growth Outlook 2024",
                claims=[
                    EvidenceClaim(
                        driver="growth",
                        statement="Industry expected to grow at 10% CAGR through 2028",
                        direction="+",
                        magnitude_units="%",
                        magnitude_value=10.0,
                        horizon="LT",
                        confidence=0.75,
                        quote="The global market is projected to expand at 10% annually"
                    )
                ]
            )
        ]
    )
    
    return bundle


def generate_mock_peer_analysis(ticker: str) -> dict:
    """Generate mock peer analysis for demonstration."""
    
    from investing_agent.schemas.comparables import PeerAnalysis, PeerCompany
    
    return PeerAnalysis(
        peer_companies=[
            PeerCompany(
                ticker="COMP1",
                company_name="Competitor One Inc",
                market_cap=35000.0,
                multiples={
                    "ev_ebitda": 16.5,
                    "ev_sales": 3.2,
                    "pe_forward": 22.0,
                    "price_book": 4.5
                }
            ),
            PeerCompany(
                ticker="COMP2",
                company_name="Competitor Two Corp",
                market_cap=28000.0,
                multiples={
                    "ev_ebitda": 14.8,
                    "ev_sales": 2.8,
                    "pe_forward": 19.5,
                    "price_book": 3.8
                }
            ),
            PeerCompany(
                ticker="COMP3",
                company_name="Competitor Three Ltd",
                market_cap=31000.0,
                multiples={
                    "ev_ebitda": 15.2,
                    "ev_sales": 3.0,
                    "pe_forward": 20.5,
                    "price_book": 4.1
                }
            ),
            PeerCompany(
                ticker=ticker,
                company_name=f"{ticker} Corporation",
                market_cap=30000.0,
                multiples={
                    "ev_ebitda": 15.0,
                    "ev_sales": 2.9,
                    "pe_forward": 20.0,
                    "price_book": 4.0
                }
            )
        ],
        industry_medians={
            "ev_ebitda": 15.1,
            "ev_sales": 3.0,
            "pe_forward": 20.5,
            "price_book": 4.05
        }
    )


def generate_mock_model_pr_log(ticker: str) -> dict:
    """Generate mock Model-PR log for demonstration."""
    
    from investing_agent.schemas.model_pr_log import ModelPRLog, ModelPRChange
    
    return ModelPRLog(
        ticker=ticker,
        timestamp=datetime.utcnow().isoformat(),
        changes=[
            ModelPRChange(
                evidence_id="ev_mgmt_guidance",
                target_path="drivers.sales_growth[0]",
                before_value=0.08,
                after_value=0.135,
                change_reason="Management guidance for FY2024",
                applied_rule="growth_cap_y1_500bps",
                cap_applied=False,
                confidence_threshold=0.90
            ),
            ModelPRChange(
                evidence_id="ev_mgmt_guidance",
                target_path="drivers.oper_margin[1]",
                before_value=0.17,
                after_value=0.19,
                change_reason="Operational efficiency initiatives",
                applied_rule="margin_cap_200bps",
                cap_applied=True,
                confidence_threshold=0.85
            ),
            ModelPRChange(
                evidence_id="ev_industry_report",
                target_path="drivers.sales_growth[2]",
                before_value=0.06,
                after_value=0.08,
                change_reason="Industry growth trends",
                applied_rule="growth_cap_y3_300bps",
                cap_applied=False,
                confidence_threshold=0.75
            )
        ]
    )


def main():
    """Main function to generate professional report."""
    
    parser = argparse.ArgumentParser(description="Generate Professional Investment Report")
    parser.add_argument("ticker", nargs="?", default="DEMO", help="Company ticker symbol")
    parser.add_argument("--real-data", action="store_true", help="Use real fundamentals from EDGAR")
    parser.add_argument("--output-dir", default="out", help="Output directory for report")
    parser.add_argument("--include-evidence", action="store_true", help="Include mock evidence data")
    parser.add_argument("--include-peers", action="store_true", help="Include mock peer analysis")
    parser.add_argument("--include-model-pr", action="store_true", help="Include mock Model-PR log")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown", help="Output format")
    
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = Path(args.output_dir) / args.ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generating professional report for {args.ticker}")
    
    # Load fundamentals
    if args.real_data:
        fundamentals = load_real_fundamentals(args.ticker)
    else:
        fundamentals = create_sample_fundamentals(args.ticker)
    
    # Build inputs and valuation
    logger.info("Building valuation inputs...")
    inputs = build_inputs_from_fundamentals(fundamentals, horizon=10)
    
    logger.info("Computing valuation...")
    valuation = kernel_value(inputs)
    
    # Generate optional components
    evidence = None
    peer_analysis = None
    model_pr_log = None
    
    if args.include_evidence:
        logger.info("Generating mock evidence bundle...")
        evidence = generate_mock_evidence_bundle(args.ticker)
    
    if args.include_peers:
        logger.info("Generating mock peer analysis...")
        peer_analysis = generate_mock_peer_analysis(args.ticker)
    
    if args.include_model_pr:
        logger.info("Generating mock Model-PR log...")
        model_pr_log = generate_mock_model_pr_log(args.ticker)
    
    # Generate professional report
    logger.info("Assembling professional report...")
    report = create_professional_report(
        inputs=inputs,
        valuation=valuation,
        evidence=evidence,
        peer_analysis=peer_analysis,
        model_pr_log=model_pr_log
    )
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{args.ticker}_professional_report_{timestamp}.md"
    report_path = output_dir / report_filename
    
    logger.info(f"Saving report to {report_path}")
    report_path.write_text(report)
    
    # Save metadata
    metadata = {
        "ticker": args.ticker,
        "timestamp": timestamp,
        "valuation": {
            "value_per_share": valuation.value_per_share,
            "enterprise_value": valuation.enterprise_value,
            "terminal_value": valuation.terminal_value
        },
        "inputs": {
            "revenue_base": inputs.revenue_base,
            "wacc": inputs.wacc,
            "horizon": inputs.horizon
        },
        "components": {
            "evidence_included": args.include_evidence,
            "peers_included": args.include_peers,
            "model_pr_included": args.include_model_pr
        }
    }
    
    metadata_path = output_dir / f"{args.ticker}_report_metadata_{timestamp}.json"
    with metadata_path.open("w") as f:
        json.dump(metadata, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("PROFESSIONAL REPORT GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Company: {fundamentals.company} ({args.ticker})")
    print(f"Valuation: ${valuation.value_per_share:.2f} per share")
    print(f"Enterprise Value: ${valuation.enterprise_value:,.0f}M")
    print(f"\nReport saved to: {report_path}")
    print(f"Metadata saved to: {metadata_path}")
    print(f"\nReport includes:")
    print(f"  ✓ Professional visualization components")
    print(f"  ✓ Sophisticated table formatting")
    print(f"  ✓ Dynamic section generation")
    print(f"  ✓ Comprehensive financial analysis")
    if args.include_evidence:
        print(f"  ✓ Evidence-based adjustments")
    if args.include_peers:
        print(f"  ✓ Peer comparison analysis")
    if args.include_model_pr:
        print(f"  ✓ Model-PR audit trail")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()