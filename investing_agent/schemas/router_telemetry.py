"""Router telemetry schemas for comprehensive logging and monitoring."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class RouteType(str, Enum):
    """Valid routing destinations."""
    MARKET = "market"
    CONSENSUS = "consensus" 
    COMPARABLES = "comparables"
    SENSITIVITY = "sensitivity"
    NEWS = "news"
    END = "end"


class RouteDecision(BaseModel):
    """Single routing decision with full context."""
    
    iteration: int = Field(description="Current iteration number")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Input state
    current_value: float = Field(description="Current value per share")
    previous_value: Optional[float] = Field(description="Previous iteration value")
    value_delta_pct: Optional[float] = Field(description="Percentage change from previous value")
    
    # Context state
    unchanged_steps: int = Field(description="Number of steps with no value change")
    ran_sensitivity_recent: bool = Field(description="Whether sensitivity was run recently")
    have_consensus: bool = Field(description="Whether consensus data is available")
    have_comparables: bool = Field(description="Whether comparables data is available") 
    allow_news: bool = Field(description="Whether news processing is allowed")
    last_route: Optional[RouteType] = Field(description="Previous routing decision")
    
    # Decision output
    chosen_route: RouteType = Field(description="Selected route for this iteration")
    decision_reason: str = Field(description="Human-readable reason for the routing decision")
    instruction: Optional[str] = Field(description="Optional instruction passed to the selected agent")
    
    # Performance metrics
    convergence_metric: Optional[float] = Field(description="Convergence indicator (0=converged, 1=diverging)")
    stability_score: Optional[float] = Field(description="Stability indicator (0-1, higher is more stable)")
    
    # Additional context
    context_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Full context at decision time")


class RouterTelemetrySession(BaseModel):
    """Complete telemetry for a routing session."""
    
    session_id: str = Field(description="Unique identifier for this routing session")
    ticker: str = Field(description="Company ticker being analyzed")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="Session completion time")
    
    # Session configuration
    max_iterations: int = Field(description="Maximum iterations allowed")
    convergence_threshold: float = Field(default=0.005, description="Value change threshold for convergence")
    stability_threshold: int = Field(default=2, description="Unchanged steps threshold")
    
    # Decision sequence
    decisions: List[RouteDecision] = Field(default_factory=list, description="Chronological routing decisions")
    
    # Session outcomes
    final_route: Optional[RouteType] = Field(description="Final route before termination")
    termination_reason: Optional[str] = Field(description="Why the routing session ended")
    converged: Optional[bool] = Field(description="Whether the session reached convergence")
    total_iterations: Optional[int] = Field(description="Total iterations completed")
    
    # Performance summary
    value_trajectory: List[float] = Field(default_factory=list, description="Value per share over time")
    convergence_rate: Optional[float] = Field(description="Rate of convergence (iterations to stability)")
    efficiency_score: Optional[float] = Field(description="Efficiency metric (0-1, higher is better)")
    
    # Quality metrics
    route_diversity: Optional[float] = Field(description="Diversity of routes taken (0-1)")
    cycle_completion_rate: Optional[float] = Field(description="Percentage of expected cycles completed")
    stability_violations: int = Field(default=0, description="Number of stability violations")
    

class RouterMetrics(BaseModel):
    """Aggregated metrics across multiple routing sessions."""
    
    # Aggregate statistics
    total_sessions: int = Field(default=0)
    successful_convergences: int = Field(default=0)
    convergence_rate: float = Field(default=0.0, description="Success rate across all sessions")
    
    # Performance distributions
    avg_iterations_to_convergence: Optional[float] = Field(description="Average iterations for successful sessions")
    median_convergence_time: Optional[float] = Field(description="Median time to convergence (seconds)")
    
    # Route usage statistics
    route_usage_frequency: Dict[RouteType, int] = Field(default_factory=dict)
    route_success_rates: Dict[RouteType, float] = Field(default_factory=dict)
    
    # Quality indicators
    overall_efficiency: Optional[float] = Field(description="System-wide efficiency score")
    stability_score: Optional[float] = Field(description="Overall system stability")
    
    # Trends and patterns
    recent_performance_trend: Optional[str] = Field(description="Recent performance trend (improving/declining/stable)")
    common_failure_modes: List[str] = Field(default_factory=list)
    

class RouterConfig(BaseModel):
    """Configuration for router behavior and telemetry."""
    
    # Routing parameters
    max_iterations: int = Field(default=10, description="Maximum routing iterations")
    convergence_threshold: float = Field(default=0.005, description="Convergence threshold (5% default)")
    stability_window: int = Field(default=2, description="Unchanged steps before termination")
    
    # Feature flags
    enable_consensus: bool = Field(default=True)
    enable_comparables: bool = Field(default=True) 
    enable_news: bool = Field(default=False)
    enable_sensitivity: bool = Field(default=True)
    
    # Telemetry settings
    log_level: str = Field(default="INFO", description="Telemetry logging level")
    enable_detailed_logging: bool = Field(default=True)
    enable_performance_tracking: bool = Field(default=True)
    session_timeout_minutes: int = Field(default=30)
    
    # Validation settings
    enable_validation: bool = Field(default=True)
    validation_threshold: float = Field(default=0.10, description="Maximum acceptable value jump")
    enable_sanity_checks: bool = Field(default=True)