"""Enhanced deterministic router with comprehensive telemetry and stability detection."""

from __future__ import annotations

import uuid
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

from investing_agent.schemas.router_telemetry import (
    RouteType, 
    RouteDecision, 
    RouterTelemetrySession,
    RouterConfig,
    RouterMetrics
)
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


logger = logging.getLogger(__name__)


class EnhancedRouter:
    """Deterministic router with comprehensive telemetry and stability detection."""
    
    def __init__(self, config: Optional[RouterConfig] = None, session_id: Optional[str] = None):
        self.config = config or RouterConfig()
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.session: Optional[RouterTelemetrySession] = None
        self.iteration_count = 0
        self.start_time: Optional[datetime] = None
        
    def start_session(self, ticker: str) -> str:
        """Initialize a new routing session with telemetry."""
        self.session = RouterTelemetrySession(
            session_id=self.session_id,
            ticker=ticker,
            max_iterations=self.config.max_iterations,
            convergence_threshold=self.config.convergence_threshold,
            stability_threshold=self.config.stability_window
        )
        self.start_time = datetime.utcnow()
        self.iteration_count = 0
        
        logger.info(f"Started routing session {self.session_id} for {ticker}")
        return self.session_id
    
    def choose_next_route(self, inputs: InputsI, valuation: ValuationV, context: Dict) -> Tuple[RouteType, Optional[str]]:
        """Enhanced route selection with telemetry logging."""
        
        if not self.session:
            raise RuntimeError("Router session not started. Call start_session() first.")
        
        self.iteration_count += 1
        current_time = datetime.utcnow()
        
        # Extract current state
        current_value = float(getattr(valuation, "value_per_share", 0.0))
        previous_value = context.get("last_value")
        
        # Calculate value delta
        value_delta_pct = None
        if previous_value is not None and previous_value != 0:
            value_delta_pct = abs(current_value - previous_value) / abs(previous_value)
        
        # Update value trajectory
        self.session.value_trajectory.append(current_value)
        
        # Make routing decision using deterministic logic
        route, instruction, decision_reason = self._determine_route(inputs, valuation, context, value_delta_pct)
        
        # Calculate performance metrics
        convergence_metric = value_delta_pct if value_delta_pct else 1.0
        stability_score = self._calculate_stability_score(context)
        
        # Create decision record
        decision = RouteDecision(
            iteration=self.iteration_count,
            timestamp=current_time,
            current_value=current_value,
            previous_value=previous_value,
            value_delta_pct=value_delta_pct,
            unchanged_steps=context.get("unchanged_steps", 0),
            ran_sensitivity_recent=context.get("ran_sensitivity_recent", False),
            have_consensus=context.get("have_consensus", False),
            have_comparables=context.get("have_comparables", False),
            allow_news=context.get("allow_news", False),
            last_route=RouteType(context.get("last_route")) if context.get("last_route") else None,
            chosen_route=route,
            decision_reason=decision_reason,
            instruction=instruction,
            convergence_metric=convergence_metric,
            stability_score=stability_score,
            context_snapshot=context.copy()
        )
        
        # Add to session
        self.session.decisions.append(decision)
        
        # Log decision
        if self.config.enable_detailed_logging:
            logger.info(
                f"Iteration {self.iteration_count}: {route.value} "
                f"(value=${current_value:.2f}, delta={value_delta_pct:.3%} if value_delta_pct else 'N/A', "
                f"reason: {decision_reason})"
            )
        
        return route, instruction
    
    def _determine_route(self, inputs: InputsI, valuation: ValuationV, context: Dict, 
                        value_delta_pct: Optional[float]) -> Tuple[RouteType, Optional[str], str]:
        """Deterministic routing logic with detailed reasoning."""
        
        # Check iteration limits
        if self.iteration_count >= self.config.max_iterations:
            return RouteType.END, None, f"Maximum iterations ({self.config.max_iterations}) reached"
        
        # Check stability threshold
        unchanged_steps = context.get("unchanged_steps", 0)
        if unchanged_steps >= self.config.stability_window:
            return RouteType.END, None, f"Stability reached: {unchanged_steps} unchanged steps"
        
        # Check convergence
        if value_delta_pct is not None and value_delta_pct <= self.config.convergence_threshold:
            ran_sens = context.get("ran_sensitivity_recent", False)
            if not ran_sens and self.config.enable_sensitivity:
                return RouteType.SENSITIVITY, None, f"Near convergence (Δ={value_delta_pct:.3%}), running sensitivity analysis"
            else:
                return RouteType.END, None, f"Converged (Δ={value_delta_pct:.3%}, sensitivity complete)"
        
        # Build available cycle based on configuration and data availability
        cycle = [RouteType.MARKET]
        
        if self.config.enable_consensus and context.get("have_consensus", False):
            cycle.append(RouteType.CONSENSUS)
            
        if self.config.enable_comparables and context.get("have_comparables", False):
            cycle.append(RouteType.COMPARABLES)
            
        if self.config.enable_news and context.get("allow_news", False):
            cycle.append(RouteType.NEWS)
        
        # Determine next route in cycle
        last_route = context.get("last_route")
        next_route = self._next_in_cycle(last_route, cycle)
        
        cycle_info = f"cycle={[r.value for r in cycle]}"
        reason = f"Following routing cycle: {cycle_info}, last={last_route}, next={next_route.value}"
        
        return next_route, None, reason
    
    def _next_in_cycle(self, last_route: Optional[str], options: List[RouteType]) -> RouteType:
        """Get next route in the cycle."""
        if not options:
            return RouteType.END
            
        try:
            last_route_type = RouteType(last_route) if last_route else None
        except ValueError:
            last_route_type = None
            
        if last_route_type not in options:
            return options[0]
            
        idx = options.index(last_route_type)
        return options[(idx + 1) % len(options)]
    
    def _calculate_stability_score(self, context: Dict) -> float:
        """Calculate stability score based on recent behavior."""
        unchanged_steps = context.get("unchanged_steps", 0)
        max_unchanged = self.config.stability_window
        
        # Higher score for more stability
        stability_from_unchanged = min(unchanged_steps / max_unchanged, 1.0)
        
        # Factor in value trajectory stability
        if len(self.session.value_trajectory) >= 3:
            recent_values = self.session.value_trajectory[-3:]
            value_variance = sum((v - sum(recent_values) / len(recent_values)) ** 2 for v in recent_values)
            stability_from_variance = 1.0 / (1.0 + value_variance)  # Inverse relationship
        else:
            stability_from_variance = 0.5
        
        return (stability_from_unchanged + stability_from_variance) / 2.0
    
    def end_session(self, final_route: RouteType, termination_reason: str) -> RouterTelemetrySession:
        """Complete the routing session and calculate final metrics."""
        if not self.session:
            raise RuntimeError("No active session to end")
        
        # Set session end state
        self.session.end_time = datetime.utcnow()
        self.session.final_route = final_route
        self.session.termination_reason = termination_reason
        self.session.total_iterations = self.iteration_count
        self.session.converged = final_route == RouteType.END and "convergence" in termination_reason.lower()
        
        # Calculate summary metrics
        self._calculate_session_metrics()
        
        logger.info(
            f"Routing session {self.session_id} completed: "
            f"{self.iteration_count} iterations, "
            f"final_value=${self.session.value_trajectory[-1] if self.session.value_trajectory else 0:.2f}, "
            f"converged={self.session.converged}"
        )
        
        return self.session
    
    def _calculate_session_metrics(self):
        """Calculate comprehensive session metrics."""
        if not self.session:
            return
        
        # Calculate convergence rate
        if self.session.start_time and self.session.end_time:
            duration = (self.session.end_time - self.session.start_time).total_seconds()
            if duration > 0:
                self.session.convergence_rate = self.iteration_count / duration
        
        # Calculate efficiency score
        if self.iteration_count > 0:
            optimal_iterations = max(1, len(set(d.chosen_route for d in self.session.decisions)))
            self.session.efficiency_score = min(optimal_iterations / self.iteration_count, 1.0)
        
        # Calculate route diversity
        if self.session.decisions:
            unique_routes = len(set(d.chosen_route for d in self.session.decisions))
            total_routes = len(self.session.decisions)
            self.session.route_diversity = unique_routes / total_routes if total_routes > 0 else 0.0
        
        # Count stability violations
        self.session.stability_violations = sum(
            1 for d in self.session.decisions 
            if d.value_delta_pct and d.value_delta_pct > self.config.validation_threshold
        )
    
    def save_session_log(self, output_dir: Path):
        """Save detailed session telemetry to file."""
        if not self.session:
            return
        
        output_dir.mkdir(parents=True, exist_ok=True)
        log_file = output_dir / f"router_session_{self.session_id}.json"
        
        with log_file.open("w") as f:
            json.dump(self.session.model_dump(), f, indent=2, default=str)
        
        logger.info(f"Router session telemetry saved to {log_file}")


def create_enhanced_router(ticker: str, config: Optional[RouterConfig] = None) -> EnhancedRouter:
    """Factory function to create and initialize an enhanced router."""
    router = EnhancedRouter(config=config)
    router.start_session(ticker)
    return router


# Legacy compatibility functions
def choose_next(inputs: InputsI, valuation: ValuationV, context: Dict) -> Tuple[str, Optional[str]]:
    """Legacy compatibility wrapper for existing code."""
    # Create temporary router for single decision
    router = EnhancedRouter()
    router.start_session(getattr(inputs, 'ticker', 'TEMP'))
    
    route_type, instruction = router.choose_next_route(inputs, valuation, context)
    return route_type.value, instruction


def simulate_routes(have_consensus: bool, have_comparables: bool, allow_news: bool, steps: int = 5) -> List[str]:
    """Legacy compatibility function for tests."""
    config = RouterConfig(
        max_iterations=steps,
        enable_consensus=have_consensus,
        enable_comparables=have_comparables,
        enable_news=allow_news
    )
    
    router = EnhancedRouter(config=config)
    router.start_session("SIM")
    
    # Mock objects
    class MockInputs:
        ticker = "SIM"
    
    class MockValuation:
        value_per_share = 1.0
    
    inputs = MockInputs()
    valuation = MockValuation()
    
    routes = []
    context = {
        "iter": 0,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": True,  # avoid sensitivity by default
        "have_consensus": have_consensus,
        "have_comparables": have_comparables,
        "allow_news": allow_news,
        "last_route": None,
    }
    
    for i in range(steps):
        route_type, _ = router.choose_next_route(inputs, valuation, context)
        if route_type == RouteType.END:
            break
        routes.append(route_type.value)
        context["last_route"] = route_type.value
        context["iter"] = i + 1
    
    router.end_session(RouteType.END, "Simulation complete")
    return routes