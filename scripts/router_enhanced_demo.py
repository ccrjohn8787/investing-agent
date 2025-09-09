#!/usr/bin/env python3
"""Enhanced router demonstration with comprehensive telemetry and Priority 1-4 integration."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import argparse
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.agents.router_enhanced import EnhancedRouter, create_enhanced_router
from investing_agent.agents.stability_detector import StabilityDetector
from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.agents.plotting import plot_sensitivity_heatmap, plot_driver_paths
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.market import apply as apply_market
from investing_agent.agents.consensus import apply as apply_consensus
from investing_agent.agents.comparables import apply as apply_comparables
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.schemas.router_telemetry import RouterConfig, RouteType
import numpy as np


def create_demonstration_fundamentals(ticker: str = "DEMO") -> Fundamentals:
    """Create sample fundamentals for demonstration."""
    return Fundamentals(
        company=f"{ticker} Corp",
        ticker=ticker,
        currency="USD",
        revenue={2022: 1000, 2023: 1200},
        ebit={2022: 120, 2023: 156},
        shares_out=1000.0,
        tax_rate=0.21,
        net_debt=100.0,
        cash=50.0,
        capex={2022: -80, 2023: -96}
    )


def print_routing_summary(router: EnhancedRouter):
    """Print comprehensive routing summary."""
    if not router.session:
        return
    
    session = router.session
    
    print("\n" + "="*60)
    print("ROUTING SESSION SUMMARY")
    print("="*60)
    
    print(f"\nSession ID: {session.session_id}")
    print(f"Company: {session.ticker}")
    print(f"Total Iterations: {session.total_iterations}")
    print(f"Converged: {session.converged}")
    
    if session.value_trajectory:
        print(f"\nValue Trajectory:")
        print(f"  Initial: ${session.value_trajectory[0]:.2f}")
        print(f"  Final:   ${session.value_trajectory[-1]:.2f}")
        print(f"  Change:  {((session.value_trajectory[-1] / session.value_trajectory[0]) - 1) * 100:.2f}%")
    
    print(f"\nPerformance Metrics:")
    print(f"  Efficiency Score: {session.efficiency_score:.2%}" if session.efficiency_score else "  Efficiency Score: N/A")
    print(f"  Route Diversity:  {session.route_diversity:.2%}" if session.route_diversity else "  Route Diversity: N/A")
    print(f"  Stability Violations: {session.stability_violations}")
    
    # Route frequency analysis
    if session.decisions:
        route_counts = {}
        for decision in session.decisions:
            route = decision.chosen_route
            route_counts[route] = route_counts.get(route, 0) + 1
        
        print(f"\nRoute Frequency:")
        for route, count in sorted(route_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {route.value:12s}: {count:2d} times ({count/len(session.decisions)*100:.0f}%)")
    
    print(f"\nTermination:")
    print(f"  Final Route: {session.final_route.value if session.final_route else 'N/A'}")
    print(f"  Reason: {session.termination_reason}")


def print_stability_analysis(stability_metrics):
    """Print detailed stability analysis."""
    print("\n" + "="*60)
    print("STABILITY ANALYSIS")
    print("="*60)
    
    print(f"\nStability State: {stability_metrics.stability_state.value.upper()}")
    print(f"Confidence Score: {stability_metrics.confidence_score:.2%}")
    
    print(f"\nStatistical Measures:")
    print(f"  Value Variance: {stability_metrics.value_variance:.6f}")
    print(f"  Trend Direction: {stability_metrics.trend_direction}")
    print(f"  Noise Level: {stability_metrics.noise_level:.6f}")
    print(f"  Predictability: {stability_metrics.predictability_score:.2%}")
    
    if stability_metrics.oscillation_frequency:
        print(f"  Oscillation Frequency: {stability_metrics.oscillation_frequency:.2f}")
    
    if stability_metrics.convergence_rate is not None:
        print(f"\nConvergence:")
        print(f"  Rate: {stability_metrics.convergence_rate:.4f}")
        if stability_metrics.time_to_stability_est:
            print(f"  Est. Time to Stability: {stability_metrics.time_to_stability_est:.1f} iterations")
    
    print(f"\nAction:")
    print(f"  Should Stop: {stability_metrics.should_stop}")
    if stability_metrics.stop_reason:
        print(f"  Stop Reason: {stability_metrics.stop_reason}")
    print(f"  Suggested Action: {stability_metrics.suggested_action}")


def run_enhanced_routing_demo(ticker: str = "DEMO", max_iterations: int = 10, 
                             enable_evidence: bool = True, enable_comparables: bool = True,
                             verbose: bool = True):
    """Run enhanced routing demonstration with full telemetry."""
    
    # Create fundamentals and initial inputs
    fundamentals = create_demonstration_fundamentals(ticker)
    inputs = build_inputs_from_fundamentals(fundamentals, horizon=8)
    valuation = kernel_value(inputs)
    
    # Configure router
    config = RouterConfig(
        max_iterations=max_iterations,
        convergence_threshold=0.005,
        stability_window=2,
        enable_consensus=True,
        enable_comparables=enable_comparables,
        enable_news=enable_evidence,
        enable_sensitivity=True,
        enable_detailed_logging=verbose
    )
    
    # Create enhanced router
    router = create_enhanced_router(ticker, config)
    stability_detector = StabilityDetector()
    
    # Initialize context with Priority 1-4 components
    context = {
        "iter": 0,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": False,
        "have_consensus": True,
        "have_comparables": enable_comparables,
        "allow_news": enable_evidence,
        "last_route": None,
        
        # Priority 1: Evidence context
        "evidence_available": enable_evidence,
        "evidence_confidence": 0.85 if enable_evidence else 0.0,
        
        # Priority 3: Comparables context
        "peer_count": 8 if enable_comparables else 0,
        "comparables_quality": "high" if enable_comparables else "none",
        
        # Priority 4: Professional analysis context
        "analysis_sections_ready": {
            "industry_analysis": False,
            "competitive_positioning": False,
            "forward_strategy": False,
            "risk_analysis": False,
            "investment_thesis": False
        }
    }
    
    # Track figures for report
    figures = None
    routes_taken = []
    
    print(f"\nStarting Enhanced Routing for {ticker}")
    print(f"Configuration: max_iter={max_iterations}, convergence={config.convergence_threshold:.3%}")
    print(f"Features: Evidence={enable_evidence}, Comparables={enable_comparables}")
    print("-" * 60)
    
    # Main routing loop
    while True:
        route, instruction = router.choose_next_route(inputs, valuation, context)
        routes_taken.append(route)
        
        if verbose:
            print(f"\nIteration {router.iteration_count}: {route.value}")
            print(f"  Value: ${valuation.value_per_share:.2f}")
            if context.get("last_value"):
                delta = (valuation.value_per_share - context["last_value"]) / context["last_value"] * 100
                print(f"  Change: {delta:+.2f}%")
        
        if route == RouteType.END:
            break
        
        # Store previous value
        prev_value = valuation.value_per_share
        
        # Apply route transformation
        if route == RouteType.MARKET:
            inputs = apply_market(inputs)
            # Simulate analysis progress
            context["analysis_sections_ready"]["industry_analysis"] = True
            
        elif route == RouteType.CONSENSUS:
            inputs = apply_consensus(inputs)
            context["analysis_sections_ready"]["competitive_positioning"] = True
            
        elif route == RouteType.COMPARABLES:
            inputs = apply_comparables(inputs)
            context["analysis_sections_ready"]["forward_strategy"] = True
            
        elif route == RouteType.NEWS:
            # Simulate evidence integration
            if enable_evidence:
                # Apply small evidence-based adjustments
                inputs.drivers.sales_growth = [g * 1.02 for g in inputs.drivers.sales_growth]
                context["evidence_frozen"] = True
            context["analysis_sections_ready"]["risk_analysis"] = True
            
        elif route == RouteType.SENSITIVITY:
            sens = compute_sensitivity(inputs)
            heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {inputs.ticker}")
            g = np.array(inputs.drivers.sales_growth)
            m = np.array(inputs.drivers.oper_margin)
            w = np.array(inputs.wacc)
            drv_png = plot_driver_paths(len(g), g, m, w)
            figures = (heat_png, drv_png)
            context["ran_sensitivity_recent"] = True
            context["analysis_sections_ready"]["investment_thesis"] = True
        
        # Revalue after transformation
        valuation = kernel_value(inputs)
        
        # Update context
        context["iter"] = router.iteration_count
        context["last_route"] = route.value
        
        # Track unchanged steps
        if prev_value is not None and abs(prev_value - valuation.value_per_share) < 0.01:
            context["unchanged_steps"] = context.get("unchanged_steps", 0) + 1
        else:
            context["unchanged_steps"] = 0
        
        context["last_value"] = prev_value
        
        # Perform stability analysis
        if len(router.session.decisions) >= 3:
            stability_metrics = stability_detector.analyze_stability(router.session.decisions)
            
            if verbose and router.iteration_count % 3 == 0:  # Print every 3rd iteration
                print(f"  Stability: {stability_metrics.stability_state.value} "
                      f"(confidence={stability_metrics.confidence_score:.0%})")
            
            # Check for early termination based on stability
            if stability_metrics.should_stop and router.iteration_count >= 5:
                if verbose:
                    print(f"\nEarly termination suggested: {stability_metrics.stop_reason}")
                break
    
    # Complete session
    final_session = router.end_session(route, f"Routing completed after {router.iteration_count} iterations")
    
    # Print summaries
    print_routing_summary(router)
    
    # Final stability analysis
    if len(router.session.decisions) >= 3:
        final_stability = stability_detector.analyze_stability(router.session.decisions)
        print_stability_analysis(final_stability)
    
    # Generate output artifacts
    output_dir = Path("out") / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save telemetry
    router.save_session_log(output_dir)
    
    # Generate report
    heat_png, drv_png = figures if figures else (None, None)
    md_report = render_report(inputs, valuation, sensitivity_png=heat_png, 
                            driver_paths_png=drv_png, fundamentals=fundamentals)
    
    report_path = output_dir / f"{ticker}_enhanced_router_report.md"
    report_path.write_text(md_report)
    
    if heat_png:
        (output_dir / f"{ticker}_sensitivity.png").write_bytes(heat_png)
    if drv_png:
        (output_dir / f"{ticker}_drivers.png").write_bytes(drv_png)
    
    # Save routing analysis
    analysis_path = output_dir / f"{ticker}_routing_analysis.json"
    analysis_data = {
        "ticker": ticker,
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": config.model_dump(),
        "routes_taken": [r.value for r in routes_taken],
        "final_value": valuation.value_per_share,
        "converged": final_session.converged,
        "total_iterations": final_session.total_iterations,
        "efficiency_score": final_session.efficiency_score,
        "route_diversity": final_session.route_diversity
    }
    
    with analysis_path.open("w") as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n✅ Enhanced routing demo complete!")
    print(f"📁 Artifacts saved to: {output_dir}")
    print(f"   - Report: {report_path.name}")
    print(f"   - Telemetry: router_session_{router.session_id}.json")
    print(f"   - Analysis: {analysis_path.name}")
    
    return final_session


def main():
    """Main entry point for the demonstration."""
    parser = argparse.ArgumentParser(description="Enhanced Router Demonstration")
    parser.add_argument("ticker", nargs="?", default="DEMO", help="Company ticker (default: DEMO)")
    parser.add_argument("--max-iterations", type=int, default=10, help="Maximum routing iterations")
    parser.add_argument("--no-evidence", action="store_true", help="Disable evidence integration")
    parser.add_argument("--no-comparables", action="store_true", help="Disable comparables")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    run_enhanced_routing_demo(
        ticker=args.ticker,
        max_iterations=args.max_iterations,
        enable_evidence=not args.no_evidence,
        enable_comparables=not args.no_comparables,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()