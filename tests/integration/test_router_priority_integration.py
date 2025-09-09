"""Integration tests connecting enhanced router with Priority 1-4 components."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
import json

from investing_agent.agents.router_enhanced import EnhancedRouter, create_enhanced_router
from investing_agent.agents.stability_detector import StabilityDetector
from investing_agent.schemas.router_telemetry import RouterConfig, RouteType
from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.comparables import PeerAnalysis


class TestRouterEvidenceIntegration:
    """Test router integration with Priority 1 Evidence Pipeline."""
    
    def test_router_with_evidence_context(self):
        """Test router decision-making with evidence pipeline context."""
        config = RouterConfig(enable_news=True)  # Enable news for evidence processing
        router = EnhancedRouter(config=config)
        router.start_session("EVID")
        
        # Mock inputs with evidence-enhanced context
        inputs = self._create_mock_inputs_with_evidence()
        valuation = self._create_mock_valuation()
        
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,
            "allow_news": True,  # Evidence processing enabled
            "evidence_available": True,
            "evidence_confidence": 0.85,
            "evidence_freshness": "recent",
            "last_route": None,
        }
        
        # Router should handle evidence context appropriately
        route, instruction = router.choose_next_route(inputs, valuation, context)
        
        # Verify evidence context is captured in telemetry
        decision = router.session.decisions[-1]
        assert "evidence_available" in decision.context_snapshot
        assert decision.context_snapshot["evidence_available"] == True
        assert decision.context_snapshot["evidence_confidence"] == 0.85
        
    def test_router_evidence_convergence(self):
        """Test router convergence behavior with evidence-driven changes."""
        router = create_enhanced_router("EVID_CONV")
        
        inputs = self._create_mock_inputs_with_evidence()
        
        # Simulate evidence-driven value changes
        evidence_values = [100.0, 102.5, 104.0, 104.2, 104.25]  # Converging after evidence
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,
            "allow_news": True,
            "evidence_frozen": False,
            "last_route": None,
        }
        
        routes = []
        for i, value in enumerate(evidence_values):
            valuation = self._create_mock_valuation(value)
            context["last_value"] = evidence_values[i-1] if i > 0 else None
            
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            
            if route == RouteType.END:
                break
                
            context["last_route"] = route.value
            context["iter"] = i + 1
            
            # Simulate evidence freezing after first iteration
            if i == 0:
                context["evidence_frozen"] = True
        
        # Should converge due to evidence stabilization
        assert RouteType.END in routes or RouteType.SENSITIVITY in routes
        
        # Verify session captured evidence integration
        session = router.end_session(routes[-1], "Evidence convergence test")
        assert any("evidence" in d.context_snapshot for d in session.decisions if d.context_snapshot)
    
    def _create_mock_inputs_with_evidence(self) -> InputsI:
        """Create mock inputs with evidence integration markers."""
        return InputsI(
            ticker="EVID",
            company="Evidence Corp",
            currency="USD",
            drivers=Drivers(
                sales_growth=[0.15, 0.12, 0.10],  # Evidence-adjusted growth
                oper_margin=[0.25, 0.26, 0.27],  # Evidence-enhanced margins
                tax_rate=0.21
            ),
            wacc=[0.08, 0.085, 0.09],
            horizon=3,
            revenue_base=1000.0,
            shares_outstanding=100.0,
            net_debt=50.0,
            evidence_integration_metadata={
                "evidence_count": 5,
                "evidence_confidence_avg": 0.85,
                "driver_adjustments": {"growth": 0.02, "margin": 0.01}
            }
        )
    
    def _create_mock_valuation(self, value_per_share: float = 104.0) -> ValuationV:
        """Create mock valuation with realistic structure."""
        return ValuationV(
            ticker="EVID",
            value_per_share=value_per_share,
            enterprise_value=value_per_share * 100 + 50,  # shares * price + net_debt
            revenue_projection=[1000.0, 1150.0, 1288.0],
            ebitda_projection=[250.0, 299.0, 347.8],
            present_value_sum=value_per_share * 100,
            terminal_value=value_per_share * 60,
            total_pv=value_per_share * 100
        )


class TestRouterComparablesIntegration:
    """Test router integration with Priority 3 Comparables system."""
    
    def test_router_with_comparables_data(self):
        """Test router decision-making with comparables context."""
        router = create_enhanced_router("COMP")
        
        inputs = self._create_mock_inputs_with_comparables()
        valuation = self._create_mock_valuation_comp()
        
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,  # Comparables data available
            "comparables_quality": "high",
            "peer_count": 8,
            "multiples_available": ["ev_ebitda", "ev_sales", "pe_forward"],
            "last_route": None,
        }
        
        # Router should prioritize comparables route when available
        route, instruction = router.choose_next_route(inputs, valuation, context)
        
        # With market first, then comparables should be in cycle
        expected_routes = [RouteType.MARKET, RouteType.CONSENSUS, RouteType.COMPARABLES]
        
        # Run through cycle to verify comparables integration
        routes = [route]
        for i in range(3):
            context["last_route"] = route.value
            context["iter"] = i + 1
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            if route == RouteType.END:
                break
        
        # Should include comparables in routing cycle
        assert RouteType.COMPARABLES in routes or any("comparables" in r.value for r in routes if isinstance(r, RouteType))
        
    def test_router_wacc_convergence_integration(self):
        """Test router behavior with WACC calculation convergence."""
        config = RouterConfig(convergence_threshold=0.003)  # Tight convergence for WACC
        router = EnhancedRouter(config=config)
        router.start_session("WACC")
        
        inputs = self._create_mock_inputs_with_comparables()
        
        # Simulate WACC convergence pattern
        wacc_values = [0.085, 0.0845, 0.0843, 0.0842, 0.08425]  # WACC stabilizing
        share_values = [95.0, 96.2, 96.5, 96.58, 96.6]  # Corresponding share price
        
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,
            "wacc_calculation_method": "bottom_up_beta",
            "peer_beta_quality": "good",
            "last_route": None,
        }
        
        routes = []
        for i, (wacc, share_val) in enumerate(zip(wacc_values, share_values)):
            valuation = self._create_mock_valuation_comp(share_val)
            context["last_value"] = share_values[i-1] if i > 0 else None
            context["current_wacc"] = wacc
            
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            
            if route == RouteType.END:
                break
                
            context["last_route"] = route.value
            context["iter"] = i + 1
        
        # Should achieve convergence due to WACC stabilization
        final_session = router.end_session(routes[-1], "WACC convergence")
        assert final_session.converged == True or RouteType.SENSITIVITY in routes
        
    def _create_mock_inputs_with_comparables(self) -> InputsI:
        """Create mock inputs with comparables integration."""
        return InputsI(
            ticker="COMP",
            company="Comparables Corp",
            currency="USD",
            drivers=Drivers(
                sales_growth=[0.12, 0.10, 0.08],
                oper_margin=[0.22, 0.23, 0.24],
                tax_rate=0.21
            ),
            wacc=[0.085, 0.087, 0.089],  # WACC from bottom-up calculation
            horizon=3,
            revenue_base=2000.0,
            shares_outstanding=200.0,
            net_debt=100.0,
            comparables_metadata={
                "peer_count": 8,
                "industry_median_ev_ebitda": 15.2,
                "peer_selection_quality": "high",
                "wacc_method": "bottom_up_beta"
            }
        )
    
    def _create_mock_valuation_comp(self, value_per_share: float = 96.0) -> ValuationV:
        """Create mock valuation for comparables testing."""
        return ValuationV(
            ticker="COMP",
            value_per_share=value_per_share,
            enterprise_value=value_per_share * 200 + 100,
            revenue_projection=[2000.0, 2240.0, 2464.0],
            ebitda_projection=[440.0, 515.2, 591.4],
            present_value_sum=value_per_share * 200,
            terminal_value=value_per_share * 120,
            total_pv=value_per_share * 200,
            comparable_multiples={
                "ev_ebitda_peer_median": 15.2,
                "current_ev_ebitda": 14.8,
                "ev_sales_peer_median": 4.2
            }
        )


class TestRouterPromptIntegration:
    """Test router integration with Priority 4 Prompt Engineering."""
    
    def test_router_with_professional_analysis_context(self):
        """Test router with professional analysis generation context."""
        config = RouterConfig(enable_detailed_logging=True)
        router = EnhancedRouter(config=config)
        router.start_session("PROMPT")
        
        inputs = self._create_mock_inputs_analysis()
        valuation = self._create_mock_valuation_analysis()
        
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,
            "allow_news": False,
            "analysis_sections_ready": {
                "industry_analysis": True,
                "competitive_positioning": True,
                "forward_strategy": False,
                "risk_analysis": False,
                "investment_thesis": False
            },
            "professional_analysis_quality": "high",
            "last_route": None,
        }
        
        # Router should capture professional analysis context
        route, instruction = router.choose_next_route(inputs, valuation, context)
        
        decision = router.session.decisions[-1]
        assert "analysis_sections_ready" in decision.context_snapshot
        assert "professional_analysis_quality" in decision.context_snapshot
        
        # Verify professional context influences routing
        assert decision.decision_reason is not None
        assert len(decision.decision_reason) > 10  # Should have detailed reasoning
        
    def test_router_analysis_completion_convergence(self):
        """Test router convergence when all analysis sections are complete."""
        router = create_enhanced_router("ANALYSIS")
        
        inputs = self._create_mock_inputs_analysis()
        
        context = {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            "have_consensus": True,
            "have_comparables": True,
            "allow_news": False,
            "last_route": None,
        }
        
        # Simulate progressive analysis completion
        analysis_stages = [
            {"industry_analysis": True, "competitive_positioning": False},
            {"industry_analysis": True, "competitive_positioning": True, "forward_strategy": True},
            {"industry_analysis": True, "competitive_positioning": True, "forward_strategy": True, 
             "risk_analysis": True, "investment_thesis": True}
        ]
        
        values = [100.0, 101.2, 101.25]  # Minor changes as analysis completes
        routes = []
        
        for i, (analysis_state, value) in enumerate(zip(analysis_stages, values)):
            valuation = self._create_mock_valuation_analysis(value)
            context.update({
                "last_value": values[i-1] if i > 0 else None,
                "analysis_sections_ready": analysis_state,
                "analysis_completion_pct": len([v for v in analysis_state.values() if v]) / len(analysis_state)
            })
            
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            
            if route == RouteType.END:
                break
                
            context["last_route"] = route.value
            context["iter"] = i + 1
        
        # Should show impact of analysis completion on routing decisions
        session = router.end_session(routes[-1] if routes else RouteType.END, "Analysis completion test")
        
        # Verify analysis context was captured throughout
        analysis_decisions = [d for d in session.decisions if "analysis_sections_ready" in d.context_snapshot]
        assert len(analysis_decisions) > 0
        
    def _create_mock_inputs_analysis(self) -> InputsI:
        """Create mock inputs for analysis testing."""
        return InputsI(
            ticker="ANALYSIS",
            company="Analysis Corp", 
            currency="USD",
            drivers=Drivers(
                sales_growth=[0.14, 0.11, 0.09],
                oper_margin=[0.21, 0.22, 0.23],
                tax_rate=0.21
            ),
            wacc=[0.082, 0.084, 0.086],
            horizon=3,
            revenue_base=1500.0,
            shares_outstanding=150.0,
            net_debt=75.0,
            professional_analysis_metadata={
                "prompt_version": "v2.1",
                "analysis_quality_target": "professional",
                "strategic_frameworks": ["porter_five_forces", "value_chain", "competitive_moats"]
            }
        )
    
    def _create_mock_valuation_analysis(self, value_per_share: float = 101.0) -> ValuationV:
        """Create mock valuation for analysis testing."""
        return ValuationV(
            ticker="ANALYSIS",
            value_per_share=value_per_share,
            enterprise_value=value_per_share * 150 + 75,
            revenue_projection=[1500.0, 1710.0, 1863.0],
            ebitda_projection=[315.0, 376.2, 428.5],
            present_value_sum=value_per_share * 150,
            terminal_value=value_per_share * 90,
            total_pv=value_per_share * 150
        )


class TestRouterFullIntegration:
    """End-to-end integration tests with all Priority 1-4 components."""
    
    def test_full_system_routing_simulation(self):
        """Test complete system routing with all priority components."""
        config = RouterConfig(
            max_iterations=15,
            convergence_threshold=0.004,
            stability_window=3,
            enable_consensus=True,
            enable_comparables=True,
            enable_news=True,
            enable_sensitivity=True,
            enable_detailed_logging=True
        )
        
        router = EnhancedRouter(config=config)
        router.start_session("FULL_SIM")
        
        # Create comprehensive context
        context = self._create_full_system_context()
        inputs = self._create_comprehensive_inputs()
        
        # Simulate realistic value progression
        value_progression = [
            98.0,   # Initial estimate
            101.5,  # Evidence adjustment
            103.2,  # Comparables adjustment
            102.8,  # Consensus integration
            103.1,  # Market adjustment
            103.05, # Convergence beginning
            103.08, # Fine-tuning
            103.085 # Near stability
        ]
        
        routes = []
        stability_detector = StabilityDetector()
        
        for i, value in enumerate(value_progression):
            valuation = self._create_comprehensive_valuation(value)
            context["last_value"] = value_progression[i-1] if i > 0 else None
            context["iter"] = i
            
            # Update context with progressive completions
            context.update(self._get_progressive_context(i))
            
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            
            # Check stability
            if len(router.session.decisions) >= 3:
                stability_metrics = stability_detector.analyze_stability(router.session.decisions)
                context["stability_state"] = stability_metrics.stability_state.value
                context["stability_confidence"] = stability_metrics.confidence_score
            
            if route == RouteType.END:
                break
                
            context["last_route"] = route.value
        
        # Complete session and verify comprehensive integration
        final_session = router.end_session(routes[-1], "Full system simulation")
        
        # Verify all priority components were integrated
        assert final_session.total_iterations >= 3
        assert len(final_session.value_trajectory) >= 3
        assert final_session.efficiency_score is not None
        
        # Check that context captured all priority components
        final_decision = final_session.decisions[-1]
        priority_markers = [
            "evidence_available",      # Priority 1
            "have_comparables",        # Priority 3
            "analysis_sections_ready", # Priority 4
        ]
        
        captured_priorities = sum(1 for marker in priority_markers 
                                if marker in final_decision.context_snapshot)
        assert captured_priorities >= 2  # Should capture most priority components
        
    def test_router_telemetry_persistence(self):
        """Test telemetry persistence and loading."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            
            # Run routing session
            router = create_enhanced_router("PERSIST")
            
            inputs = self._create_comprehensive_inputs()
            valuation = self._create_comprehensive_valuation()
            context = self._create_full_system_context()
            
            # Make a few routing decisions
            for i in range(3):
                route, instruction = router.choose_next_route(inputs, valuation, context)
                context["last_route"] = route.value
                context["iter"] = i + 1
                if route == RouteType.END:
                    break
            
            # Save session
            router.save_session_log(output_dir)
            
            # Verify file was created and contains expected data
            log_files = list(output_dir.glob("router_session_*.json"))
            assert len(log_files) == 1
            
            with log_files[0].open() as f:
                session_data = json.load(f)
            
            assert session_data["ticker"] == "PERSIST"
            assert "decisions" in session_data
            assert len(session_data["decisions"]) >= 1
            assert "value_trajectory" in session_data
    
    def _create_full_system_context(self) -> Dict[str, Any]:
        """Create comprehensive context with all priority components."""
        return {
            "iter": 0,
            "last_value": None,
            "unchanged_steps": 0,
            "ran_sensitivity_recent": False,
            
            # Priority 1: Evidence Pipeline
            "have_evidence": True,
            "evidence_frozen": False,
            "evidence_confidence": 0.87,
            "evidence_count": 12,
            
            # Priority 2: Writer/Critic (implicit in professional analysis)
            "writer_validation_passed": True,
            "citation_density": 0.75,
            
            # Priority 3: Comparables + WACC
            "have_consensus": True,
            "have_comparables": True,
            "peer_count": 9,
            "wacc_method": "bottom_up_beta",
            "comparables_quality": "high",
            
            # Priority 4: Professional Analysis
            "analysis_sections_ready": {
                "industry_analysis": False,
                "competitive_positioning": False,
                "forward_strategy": False,
                "risk_analysis": False,
                "investment_thesis": False
            },
            
            # Routing state
            "allow_news": True,
            "last_route": None,
        }
    
    def _get_progressive_context(self, iteration: int) -> Dict[str, Any]:
        """Get progressively updated context for different iterations."""
        updates = {}
        
        if iteration >= 1:
            updates["evidence_frozen"] = True
        
        if iteration >= 2:
            updates["analysis_sections_ready"] = {
                "industry_analysis": True,
                "competitive_positioning": False,
                "forward_strategy": False,
                "risk_analysis": False,
                "investment_thesis": False
            }
        
        if iteration >= 4:
            updates["analysis_sections_ready"]["competitive_positioning"] = True
            updates["analysis_sections_ready"]["forward_strategy"] = True
        
        if iteration >= 6:
            updates["analysis_sections_ready"]["risk_analysis"] = True
            updates["analysis_sections_ready"]["investment_thesis"] = True
            updates["ran_sensitivity_recent"] = True
        
        return updates
    
    def _create_comprehensive_inputs(self) -> InputsI:
        """Create comprehensive inputs with all priority integrations."""
        return InputsI(
            ticker="FULL_SIM",
            company="Comprehensive Corp",
            currency="USD",
            drivers=Drivers(
                sales_growth=[0.13, 0.105, 0.085],
                oper_margin=[0.235, 0.245, 0.255],
                tax_rate=0.21
            ),
            wacc=[0.081, 0.083, 0.085],
            horizon=3,
            revenue_base=3000.0,
            shares_outstanding=300.0,
            net_debt=150.0,
            
            # All priority metadata
            evidence_integration_metadata={
                "evidence_count": 12,
                "evidence_confidence_avg": 0.87,
                "driver_adjustments": {"growth": 0.015, "margin": 0.008}
            },
            comparables_metadata={
                "peer_count": 9,
                "industry_median_ev_ebitda": 16.8,
                "peer_selection_quality": "high",
                "wacc_method": "bottom_up_beta"
            },
            professional_analysis_metadata={
                "prompt_version": "v2.1",
                "analysis_quality_target": "professional",
                "strategic_frameworks": ["porter_five_forces", "value_chain", "competitive_moats"]
            }
        )
    
    def _create_comprehensive_valuation(self, value_per_share: float = 103.0) -> ValuationV:
        """Create comprehensive valuation for full integration testing."""
        return ValuationV(
            ticker="FULL_SIM",
            value_per_share=value_per_share,
            enterprise_value=value_per_share * 300 + 150,
            revenue_projection=[3000.0, 3390.0, 3680.0],
            ebitda_projection=[705.0, 830.6, 939.2],
            present_value_sum=value_per_share * 300,
            terminal_value=value_per_share * 180,
            total_pv=value_per_share * 300,
            comparable_multiples={
                "ev_ebitda_peer_median": 16.8,
                "current_ev_ebitda": 15.9,
                "ev_sales_peer_median": 4.8
            },
            evidence_impact_summary={
                "growth_adjustment": 0.015,
                "margin_adjustment": 0.008,
                "confidence_weighted_impact": 0.87
            }
        )


if __name__ == "__main__":
    pytest.main([__file__])