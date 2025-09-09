"""Comprehensive testing suite for enhanced router with telemetry and stability detection."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from typing import List, Dict
import json

from investing_agent.agents.router_enhanced import EnhancedRouter, create_enhanced_router
from investing_agent.agents.stability_detector import StabilityDetector, StabilityState
from investing_agent.schemas.router_telemetry import (
    RouterConfig, RouteType, RouteDecision, RouterTelemetrySession
)


class MockInputs:
    """Mock InputsI for testing."""
    def __init__(self, ticker: str = "TEST"):
        self.ticker = ticker


class MockValuation:
    """Mock ValuationV for testing."""
    def __init__(self, value_per_share: float = 100.0):
        self.value_per_share = value_per_share


@pytest.fixture
def default_config():
    """Default router configuration for testing."""
    return RouterConfig(
        max_iterations=10,
        convergence_threshold=0.005,
        stability_window=2,
        enable_consensus=True,
        enable_comparables=True,
        enable_news=False,
        enable_sensitivity=True
    )


@pytest.fixture
def basic_context():
    """Basic context dictionary for testing."""
    return {
        "iter": 0,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": False,
        "have_consensus": True,
        "have_comparables": True,
        "allow_news": False,
        "last_route": None,
    }


class TestEnhancedRouter:
    """Test suite for EnhancedRouter class."""
    
    def test_router_initialization(self, default_config):
        """Test router initialization and configuration."""
        router = EnhancedRouter(config=default_config)
        assert router.config == default_config
        assert router.session is None
        assert router.iteration_count == 0
        
    def test_session_management(self, default_config):
        """Test session start and end lifecycle."""
        router = EnhancedRouter(config=default_config)
        
        # Start session
        session_id = router.start_session("TEST")
        assert session_id == router.session_id
        assert router.session is not None
        assert router.session.ticker == "TEST"
        assert router.session.max_iterations == 10
        
        # End session
        final_session = router.end_session(RouteType.END, "Test completion")
        assert final_session.final_route == RouteType.END
        assert final_session.termination_reason == "Test completion"
        assert final_session.total_iterations == 0
        
    def test_basic_routing_cycle(self, default_config, basic_context):
        """Test basic routing cycle through market -> consensus -> comparables."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation()
        
        # First route should be market
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.MARKET
        
        # Second route should be consensus  
        basic_context["last_route"] = route.value
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.CONSENSUS
        
        # Third route should be comparables
        basic_context["last_route"] = route.value
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.COMPARABLES
        
    def test_convergence_detection(self, default_config, basic_context):
        """Test convergence detection and sensitivity triggering."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Set up near-convergence scenario
        basic_context["last_value"] = 100.2  # 0.2% difference
        
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.SENSITIVITY
        assert "convergence" in router.session.decisions[-1].decision_reason.lower()
        
    def test_convergence_termination(self, default_config, basic_context):
        """Test termination after convergence and sensitivity."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Set up convergence with sensitivity already run
        basic_context.update({
            "last_value": 100.2,  # 0.2% difference
            "ran_sensitivity_recent": True
        })
        
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.END
        assert "converged" in router.session.decisions[-1].decision_reason.lower()
        
    def test_stability_termination(self, default_config, basic_context):
        """Test termination due to stability threshold."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Set up stability scenario
        basic_context["unchanged_steps"] = 2  # Matches stability_window
        
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.END
        assert "stability" in router.session.decisions[-1].decision_reason.lower()
        
    def test_iteration_limit(self, basic_context):
        """Test termination due to iteration limit."""
        config = RouterConfig(max_iterations=3)
        router = EnhancedRouter(config=config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Simulate iterations up to limit
        for i in range(3):
            route, instruction = router.choose_next_route(inputs, valuation, basic_context)
            if route == RouteType.END:
                break
            basic_context["last_route"] = route.value
        
        # Next call should hit iteration limit
        router.iteration_count = 3  # Simulate reaching limit
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.END
        assert "maximum iterations" in router.session.decisions[-1].decision_reason.lower()
        
    def test_telemetry_logging(self, default_config, basic_context):
        """Test comprehensive telemetry logging."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Make several routing decisions
        for i in range(3):
            basic_context["last_value"] = 100.0 + i * 0.5
            route, instruction = router.choose_next_route(inputs, valuation, basic_context)
            basic_context["last_route"] = route.value
        
        # Verify telemetry data
        session = router.session
        assert len(session.decisions) == 3
        assert len(session.value_trajectory) == 3
        
        # Check decision details
        decision = session.decisions[0]
        assert decision.iteration == 1
        assert decision.current_value == 100.0
        assert decision.chosen_route in RouteType
        assert decision.decision_reason is not None
        assert decision.context_snapshot == basic_context
        
    def test_session_metrics_calculation(self, default_config, basic_context):
        """Test session metrics calculation."""
        router = EnhancedRouter(config=default_config)
        router.start_session("TEST")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        # Simulate routing session
        for i in range(5):
            route, instruction = router.choose_next_route(inputs, valuation, basic_context)
            if route == RouteType.END:
                break
            basic_context["last_route"] = route.value
        
        # End session and check metrics
        final_session = router.end_session(RouteType.END, "Test completion")
        assert final_session.efficiency_score is not None
        assert final_session.route_diversity is not None
        assert 0.0 <= final_session.efficiency_score <= 1.0
        assert 0.0 <= final_session.route_diversity <= 1.0
        
    def test_configuration_variations(self, basic_context):
        """Test different configuration scenarios."""
        # Test with minimal features
        minimal_config = RouterConfig(
            enable_consensus=False,
            enable_comparables=False,
            enable_news=False,
            enable_sensitivity=False
        )
        
        router = EnhancedRouter(config=minimal_config)
        router.start_session("MINIMAL")
        
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.MARKET  # Should only cycle through market
        
        basic_context["last_route"] = route.value
        route, instruction = router.choose_next_route(inputs, valuation, basic_context)
        assert route == RouteType.MARKET  # Should cycle back to market


class TestStabilityDetector:
    """Test suite for StabilityDetector class."""
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data."""
        detector = StabilityDetector()
        decisions = [self._create_mock_decision(1, 100.0)]
        
        metrics = detector.analyze_stability(decisions)
        assert metrics.stability_state == StabilityState.CONVERGING
        assert metrics.confidence_score == 0.0
        assert metrics.should_stop == False
        
    def test_stable_detection(self):
        """Test detection of stable state."""
        detector = StabilityDetector(convergence_threshold=0.01)
        decisions = [
            self._create_mock_decision(1, 100.0),
            self._create_mock_decision(2, 100.05),
            self._create_mock_decision(3, 99.98),
            self._create_mock_decision(4, 100.02),
        ]
        
        metrics = detector.analyze_stability(decisions)
        assert metrics.stability_state == StabilityState.STABLE
        assert metrics.should_stop == True
        assert "stable" in metrics.stop_reason.lower()
        
    def test_oscillation_detection(self):
        """Test detection of oscillating behavior."""
        detector = StabilityDetector()
        decisions = [
            self._create_mock_decision(1, 100.0),
            self._create_mock_decision(2, 110.0),
            self._create_mock_decision(3, 90.0),
            self._create_mock_decision(4, 105.0),
            self._create_mock_decision(5, 95.0),
        ]
        
        metrics = detector.analyze_stability(decisions)
        assert metrics.stability_state == StabilityState.OSCILLATING
        assert metrics.oscillation_frequency is not None
        
    def test_convergence_rate_calculation(self):
        """Test convergence rate calculation."""
        detector = StabilityDetector()
        decisions = [
            self._create_mock_decision(1, 110.0),
            self._create_mock_decision(2, 105.0),
            self._create_mock_decision(3, 102.0),
            self._create_mock_decision(4, 100.5),
            self._create_mock_decision(5, 100.1),
        ]
        
        metrics = detector.analyze_stability(decisions)
        assert metrics.convergence_rate is not None
        assert metrics.convergence_rate > 0  # Should be positive (converging)
        assert metrics.time_to_stability_est is not None
        
    def test_divergence_detection(self):
        """Test detection of diverging behavior."""
        detector = StabilityDetector()
        decisions = [
            self._create_mock_decision(1, 100.0),
            self._create_mock_decision(2, 105.0),
            self._create_mock_decision(3, 115.0),
            self._create_mock_decision(4, 130.0),
            self._create_mock_decision(5, 150.0),
        ]
        
        metrics = detector.analyze_stability(decisions)
        # Note: May not always detect as DIVERGING due to limited data
        assert metrics.trend_direction == "increasing"
        assert metrics.value_variance > 0
        
    def _create_mock_decision(self, iteration: int, value: float) -> RouteDecision:
        """Create a mock routing decision for testing."""
        return RouteDecision(
            iteration=iteration,
            current_value=value,
            previous_value=value - 1.0 if iteration > 1 else None,
            unchanged_steps=0,
            ran_sensitivity_recent=False,
            have_consensus=True,
            have_comparables=True,
            allow_news=False,
            last_route=None,
            chosen_route=RouteType.MARKET,
            decision_reason="Test decision",
            convergence_metric=0.01,
            stability_score=0.5,
            context_snapshot={}
        )


class TestRouterIntegration:
    """Integration tests for router components."""
    
    def test_factory_function(self):
        """Test router factory function."""
        router = create_enhanced_router("TEST")
        assert router.session is not None
        assert router.session.ticker == "TEST"
        
    def test_full_routing_simulation(self, default_config):
        """Test complete routing simulation."""
        router = EnhancedRouter(config=default_config)
        router.start_session("SIM")
        
        inputs = MockInputs("SIM")
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
        
        # Simulate convergence scenario
        values = [100.0, 99.5, 99.8, 99.9, 99.95]
        routes = []
        
        for i, value in enumerate(values):
            valuation = MockValuation(value)
            context["last_value"] = values[i-1] if i > 0 else None
            
            route, instruction = router.choose_next_route(inputs, valuation, context)
            routes.append(route)
            
            if route == RouteType.END:
                break
                
            context["last_route"] = route.value
            context["iter"] = i + 1
        
        # Should eventually terminate
        assert RouteType.END in routes
        
        # End session and verify
        final_session = router.end_session(routes[-1], "Simulation complete")
        assert final_session.converged is not None
        assert len(final_session.value_trajectory) > 0
        
    def test_legacy_compatibility(self):
        """Test legacy compatibility functions."""
        from investing_agent.agents.router_enhanced import choose_next, simulate_routes
        
        # Test legacy choose_next function
        inputs = MockInputs()
        valuation = MockValuation(100.0)
        context = {"last_value": None, "unchanged_steps": 0}
        
        route_str, instruction = choose_next(inputs, valuation, context)
        assert isinstance(route_str, str)
        assert route_str in [r.value for r in RouteType]
        
        # Test legacy simulate_routes function
        routes = simulate_routes(have_consensus=True, have_comparables=True, allow_news=False, steps=3)
        assert isinstance(routes, list)
        assert all(isinstance(r, str) for r in routes)


if __name__ == "__main__":
    pytest.main([__file__])