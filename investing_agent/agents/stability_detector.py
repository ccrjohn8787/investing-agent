"""Advanced stability detection and convergence analysis for router optimization."""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.router_telemetry import RouteDecision


class StabilityState(str, Enum):
    """Router stability states."""
    CONVERGING = "converging"      # Values are approaching stability
    STABLE = "stable"              # System has reached stable state
    OSCILLATING = "oscillating"    # Values are oscillating around equilibrium
    DIVERGING = "diverging"        # Values are moving away from stability
    CHAOTIC = "chaotic"           # No discernible pattern


@dataclass
class StabilityMetrics:
    """Comprehensive stability analysis metrics."""
    
    # Core stability indicators  
    stability_state: StabilityState
    confidence_score: float  # 0-1, higher means more confident in stability assessment
    convergence_rate: Optional[float]  # How fast the system is converging (if applicable)
    
    # Statistical measures
    value_variance: float  # Variance in recent values
    trend_direction: str  # "increasing", "decreasing", "stable", "mixed"
    oscillation_frequency: Optional[float]  # Frequency of oscillations (if detected)
    
    # Performance indicators
    time_to_stability_est: Optional[float]  # Estimated iterations until stability
    stability_window_size: int  # Number of recent values used for analysis
    last_significant_change: Optional[int]  # Iterations since last significant change
    
    # Quality measures
    noise_level: float  # Amount of noise in the signal
    predictability_score: float  # How predictable the next values are
    
    # Actionable insights
    should_stop: bool  # Whether router should terminate
    stop_reason: Optional[str]  # Human-readable reason for stopping
    suggested_action: Optional[str]  # Suggestion for next steps


class StabilityDetector:
    """Advanced stability detection system for router optimization."""
    
    def __init__(self, 
                 convergence_threshold: float = 0.005,
                 stability_window: int = 5,
                 min_observations: int = 3,
                 noise_threshold: float = 0.001):
        self.convergence_threshold = convergence_threshold
        self.stability_window = stability_window
        self.min_observations = min_observations
        self.noise_threshold = noise_threshold
        
    def analyze_stability(self, decisions: List[RouteDecision]) -> StabilityMetrics:
        """Perform comprehensive stability analysis on routing decisions."""
        
        if len(decisions) < self.min_observations:
            return StabilityMetrics(
                stability_state=StabilityState.CONVERGING,
                confidence_score=0.0,
                convergence_rate=None,
                value_variance=0.0,
                trend_direction="insufficient_data",
                oscillation_frequency=None,
                time_to_stability_est=None,
                stability_window_size=len(decisions),
                last_significant_change=None,
                noise_level=0.0,
                predictability_score=0.0,
                should_stop=False,
                stop_reason=None,
                suggested_action="continue_monitoring"
            )
        
        # Extract value trajectory
        values = [d.current_value for d in decisions if d.current_value is not None]
        if not values:
            return self._insufficient_data_metrics(len(decisions))
        
        # Use sliding window for recent analysis
        window_size = min(self.stability_window, len(values))
        recent_values = values[-window_size:]
        
        # Calculate core metrics
        value_variance = np.var(recent_values) if len(recent_values) > 1 else 0.0
        trend_direction = self._analyze_trend(recent_values)
        stability_state = self._determine_stability_state(values, recent_values)
        
        # Calculate convergence metrics
        convergence_rate = self._calculate_convergence_rate(values)
        oscillation_freq = self._detect_oscillations(recent_values)
        
        # Assess quality and predictability
        noise_level = self._calculate_noise_level(recent_values)
        predictability_score = self._calculate_predictability(recent_values)
        
        # Determine stopping conditions
        should_stop, stop_reason = self._should_stop_routing(
            stability_state, value_variance, recent_values, decisions
        )
        
        # Estimate time to stability
        time_to_stability = self._estimate_time_to_stability(
            stability_state, convergence_rate, value_variance
        )
        
        # Find last significant change
        last_sig_change = self._find_last_significant_change(values)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            len(values), value_variance, predictability_score, noise_level
        )
        
        # Generate actionable suggestion
        suggested_action = self._suggest_action(stability_state, should_stop, confidence_score)
        
        return StabilityMetrics(
            stability_state=stability_state,
            confidence_score=confidence_score,
            convergence_rate=convergence_rate,
            value_variance=value_variance,
            trend_direction=trend_direction,
            oscillation_frequency=oscillation_freq,
            time_to_stability_est=time_to_stability,
            stability_window_size=window_size,
            last_significant_change=last_sig_change,
            noise_level=noise_level,
            predictability_score=predictability_score,
            should_stop=should_stop,
            stop_reason=stop_reason,
            suggested_action=suggested_action
        )
    
    def _insufficient_data_metrics(self, observations: int) -> StabilityMetrics:
        """Return metrics for insufficient data scenario."""
        return StabilityMetrics(
            stability_state=StabilityState.CONVERGING,
            confidence_score=0.0,
            convergence_rate=None,
            value_variance=0.0,
            trend_direction="insufficient_data",
            oscillation_frequency=None,
            time_to_stability_est=None,
            stability_window_size=observations,
            last_significant_change=None,
            noise_level=0.0,
            predictability_score=0.0,
            should_stop=False,
            stop_reason=None,
            suggested_action="continue_monitoring"
        )
    
    def _analyze_trend(self, values: List[float]) -> str:
        """Analyze the trend direction in recent values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Calculate linear regression slope
        n = len(values)
        x = np.arange(n)
        slope = np.corrcoef(x, values)[0, 1] * np.std(values) / np.std(x)
        
        if abs(slope) < self.noise_threshold:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _determine_stability_state(self, all_values: List[float], recent_values: List[float]) -> StabilityState:
        """Determine the current stability state."""
        if len(recent_values) < 2:
            return StabilityState.CONVERGING
        
        # Calculate recent variance and overall variance
        recent_var = np.var(recent_values)
        
        # Check for stability (low variance)
        if recent_var < self.convergence_threshold ** 2:
            return StabilityState.STABLE
        
        # Check for oscillations
        if self._is_oscillating(recent_values):
            return StabilityState.OSCILLATING
        
        # Check for divergence (increasing variance over time)
        if len(all_values) >= self.stability_window * 2:
            early_var = np.var(all_values[:self.stability_window])
            if recent_var > early_var * 2:
                return StabilityState.DIVERGING
        
        # Check for chaotic behavior (high unpredictability)
        if self._calculate_predictability(recent_values) < 0.3:
            return StabilityState.CHAOTIC
        
        return StabilityState.CONVERGING
    
    def _calculate_convergence_rate(self, values: List[float]) -> Optional[float]:
        """Calculate the rate of convergence."""
        if len(values) < 3:
            return None
        
        # Calculate rate of variance decrease
        mid_point = len(values) // 2
        early_values = values[:mid_point]
        recent_values = values[mid_point:]
        
        if len(early_values) < 2 or len(recent_values) < 2:
            return None
        
        early_var = np.var(early_values)
        recent_var = np.var(recent_values)
        
        if early_var == 0:
            return None
        
        # Rate of variance reduction (positive means converging)
        return (early_var - recent_var) / early_var
    
    def _detect_oscillations(self, values: List[float]) -> Optional[float]:
        """Detect oscillating behavior and return frequency."""
        if len(values) < 4:
            return None
        
        # Simple peak detection
        peaks = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] > values[i+1]:
                peaks.append(i)
            elif values[i] < values[i-1] and values[i] < values[i+1]:
                peaks.append(i)
        
        if len(peaks) < 2:
            return None
        
        # Calculate average distance between peaks
        avg_distance = np.mean(np.diff(peaks))
        return 1.0 / avg_distance if avg_distance > 0 else None
    
    def _is_oscillating(self, values: List[float]) -> bool:
        """Simple oscillation detection."""
        if len(values) < 4:
            return False
        
        # Check for alternating increases/decreases
        directions = []
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                directions.append(1)
            elif values[i] < values[i-1]:
                directions.append(-1)
            else:
                directions.append(0)
        
        if len(directions) < 3:
            return False
        
        # Count direction changes
        changes = sum(1 for i in range(1, len(directions)) 
                     if directions[i] != 0 and directions[i-1] != 0 and directions[i] != directions[i-1])
        
        # High frequency of direction changes suggests oscillation
        return changes >= len(directions) * 0.5
    
    def _calculate_noise_level(self, values: List[float]) -> float:
        """Calculate the noise level in the signal."""
        if len(values) < 3:
            return 0.0
        
        # Calculate variance of first differences (measure of noise)
        diffs = [values[i] - values[i-1] for i in range(1, len(values))]
        return np.var(diffs)
    
    def _calculate_predictability(self, values: List[float]) -> float:
        """Calculate how predictable the next value is."""
        if len(values) < 3:
            return 0.0
        
        # Simple linear regression R²
        n = len(values)
        x = np.arange(n)
        
        # Calculate correlation coefficient
        correlation = np.corrcoef(x, values)[0, 1]
        return correlation ** 2 if not np.isnan(correlation) else 0.0
    
    def _should_stop_routing(self, stability_state: StabilityState, variance: float, 
                            recent_values: List[float], decisions: List[RouteDecision]) -> Tuple[bool, Optional[str]]:
        """Determine if routing should stop based on comprehensive analysis."""
        
        # Stop if stable
        if stability_state == StabilityState.STABLE:
            return True, f"System reached stable state (variance={variance:.6f})"
        
        # Stop if oscillating with low amplitude
        if stability_state == StabilityState.OSCILLATING and variance < (self.convergence_threshold ** 2) * 2:
            return True, f"Low-amplitude oscillation detected (variance={variance:.6f})"
        
        # Stop if no significant change for extended period
        unchanged_count = 0
        for i in range(len(decisions) - 1, max(-1, len(decisions) - self.stability_window - 1), -1):
            if i < len(decisions) and decisions[i].unchanged_steps > 0:
                unchanged_count = max(unchanged_count, decisions[i].unchanged_steps)
        
        if unchanged_count >= self.stability_window:
            return True, f"No significant change for {unchanged_count} steps"
        
        # Stop if diverging dangerously
        if stability_state == StabilityState.DIVERGING and variance > 1.0:
            return True, f"System diverging dangerously (variance={variance:.6f})"
        
        return False, None
    
    def _estimate_time_to_stability(self, stability_state: StabilityState, 
                                   convergence_rate: Optional[float], variance: float) -> Optional[float]:
        """Estimate iterations until stability."""
        if stability_state == StabilityState.STABLE:
            return 0.0
        
        if stability_state in [StabilityState.DIVERGING, StabilityState.CHAOTIC]:
            return None  # Cannot estimate for unstable systems
        
        if convergence_rate is None or convergence_rate <= 0:
            return None
        
        # Simple extrapolation based on variance reduction rate
        target_variance = self.convergence_threshold ** 2
        if variance <= target_variance:
            return 1.0
        
        # Estimate based on exponential decay
        return max(1.0, np.log(target_variance / variance) / np.log(1 - convergence_rate))
    
    def _find_last_significant_change(self, values: List[float]) -> Optional[int]:
        """Find iterations since last significant change."""
        if len(values) < 2:
            return None
        
        for i in range(len(values) - 1, 0, -1):
            if abs(values[i] - values[i-1]) / values[i-1] > self.convergence_threshold:
                return len(values) - i
        
        return len(values) - 1  # All changes were insignificant
    
    def _calculate_confidence_score(self, n_observations: int, variance: float, 
                                   predictability: float, noise_level: float) -> float:
        """Calculate confidence in stability assessment."""
        # Base confidence on number of observations
        obs_confidence = min(n_observations / (self.stability_window * 2), 1.0)
        
        # Adjust for predictability (higher is better)
        pred_confidence = predictability
        
        # Adjust for noise (lower is better)
        noise_confidence = 1.0 / (1.0 + noise_level * 100)
        
        # Weighted average
        return (obs_confidence * 0.4 + pred_confidence * 0.4 + noise_confidence * 0.2)
    
    def _suggest_action(self, stability_state: StabilityState, should_stop: bool, confidence: float) -> str:
        """Suggest next action based on stability analysis."""
        if should_stop:
            return "terminate_routing"
        
        if confidence < 0.3:
            return "continue_monitoring_low_confidence"
        
        if stability_state == StabilityState.STABLE:
            return "terminate_routing"
        elif stability_state == StabilityState.CONVERGING:
            return "continue_routing_converging"
        elif stability_state == StabilityState.OSCILLATING:
            return "consider_early_termination_oscillating"
        elif stability_state == StabilityState.DIVERGING:
            return "investigate_divergence_causes"
        else:  # CHAOTIC
            return "reset_or_investigate_chaos"