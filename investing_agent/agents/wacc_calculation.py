from __future__ import annotations

"""
Levered WACC Path Calculation

Implements comprehensive WACC calculation with dynamic capital structure,
cost of debt estimation, and integration with bottom-up beta methodology.
"""

import math
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.comparables import WACCCalculation, PeerCompany
from investing_agent.agents.beta_calculation import BetaStatistics


class CostOfDebtMethod(Enum):
    """Methods for estimating cost of debt."""
    CREDIT_SPREAD = "credit_spread"
    INTEREST_COVERAGE = "interest_coverage"
    RATING_BASED = "rating_based"
    PEER_AVERAGE = "peer_average"


class CapitalStructureMode(Enum):
    """Capital structure evolution modes."""
    STATIC = "static"           # Constant D/E ratio
    TARGET_CONVERGENCE = "target_convergence"  # Converge to target over time
    DYNAMIC_OPTIMAL = "dynamic_optimal"        # Optimize D/E based on conditions


@dataclass
class CostComponents:
    """Individual cost components for WACC calculation."""
    # Beta and equity cost
    beta_levered: float
    beta_unlevered: Optional[float]
    cost_of_equity: float
    
    # Debt cost components
    risk_free_rate: float
    credit_spread: float
    cost_of_debt_pretax: float
    cost_of_debt_aftertax: float
    
    # Risk premiums
    equity_risk_premium: float
    country_risk_premium: float
    size_premium: float
    
    # Capital structure
    debt_to_equity: float
    debt_weight: float
    equity_weight: float
    tax_rate: float
    
    # Quality indicators
    estimation_method: str
    confidence_score: float


@dataclass
class WACCEvolution:
    """WACC evolution over time periods."""
    years: List[int]
    wacc_values: List[float]
    debt_ratios: List[float]
    cost_of_equity_values: List[float]
    cost_of_debt_values: List[float]
    
    terminal_wacc: float
    terminal_debt_ratio: float


class WACCCalculator:
    """Advanced WACC calculator with levered methodology."""
    
    def __init__(
        self,
        default_tax_rate: float = 0.25,
        default_equity_risk_premium: float = 0.06,
        default_size_premium: float = 0.0,
        terminal_growth_rate: float = 0.025,
        cost_of_debt_floor: float = 0.015,
        cost_of_debt_ceiling: float = 0.15
    ):
        """Initialize WACC calculator.
        
        Args:
            default_tax_rate: Default corporate tax rate
            default_equity_risk_premium: Market equity risk premium
            default_size_premium: Small company premium
            terminal_growth_rate: Long-term growth assumption
            cost_of_debt_floor: Minimum cost of debt (investment grade)
            cost_of_debt_ceiling: Maximum cost of debt (distressed)
        """
        self.default_tax_rate = default_tax_rate
        self.default_equity_risk_premium = default_equity_risk_premium
        self.default_size_premium = default_size_premium
        self.terminal_growth_rate = terminal_growth_rate
        self.cost_of_debt_floor = cost_of_debt_floor
        self.cost_of_debt_ceiling = cost_of_debt_ceiling
    
    def calculate_comprehensive_wacc(
        self,
        beta_stats: BetaStatistics,
        target_debt_to_equity: float,
        risk_free_rate: float,
        target_market_cap: Optional[float] = None,
        target_tax_rate: Optional[float] = None,
        country_risk_premium: float = 0.0,
        cost_of_debt_method: CostOfDebtMethod = CostOfDebtMethod.CREDIT_SPREAD,
        capital_structure_mode: CapitalStructureMode = CapitalStructureMode.STATIC,
        forecast_years: int = 10
    ) -> Tuple[WACCCalculation, WACCEvolution, CostComponents]:
        """Calculate comprehensive WACC with evolution path.
        
        Args:
            beta_stats: Beta statistics from peer analysis
            target_debt_to_equity: Target company D/E ratio
            risk_free_rate: Risk-free rate (10Y Treasury)
            target_market_cap: Target company market cap for size premium
            target_tax_rate: Target company tax rate
            country_risk_premium: Country risk premium
            cost_of_debt_method: Method for estimating cost of debt
            capital_structure_mode: Capital structure evolution mode
            forecast_years: Number of forecast years
            
        Returns:
            Tuple of (WACC calculation, WACC evolution, cost components)
        """
        print(f"💰 Calculating comprehensive WACC (method: {cost_of_debt_method.value})")
        
        # Use defaults if not provided
        tax_rate = target_tax_rate or self.default_tax_rate
        equity_risk_premium = self.default_equity_risk_premium
        
        # Calculate size premium if market cap provided
        size_premium = self._calculate_size_premium(target_market_cap) if target_market_cap else 0.0
        
        # Re-lever beta for target capital structure
        from investing_agent.agents.beta_calculation import BetaCalculator
        beta_calc = BetaCalculator()
        
        target_beta_levered = beta_calc.relever_beta(
            beta_stats.selected_unlevered_beta,
            target_debt_to_equity,
            tax_rate
        )
        
        # Calculate cost of equity
        cost_of_equity = (risk_free_rate + 
                         target_beta_levered * equity_risk_premium + 
                         country_risk_premium + 
                         size_premium)
        
        # Estimate cost of debt
        cost_of_debt_pretax, credit_spread, debt_method = self._estimate_cost_of_debt(
            target_debt_to_equity, 
            risk_free_rate, 
            cost_of_debt_method,
            target_market_cap
        )
        
        cost_of_debt_aftertax = cost_of_debt_pretax * (1 - tax_rate)
        
        # Calculate capital structure weights
        debt_weight = target_debt_to_equity / (1 + target_debt_to_equity)
        equity_weight = 1 / (1 + target_debt_to_equity)
        
        # Base WACC calculation
        base_wacc = (equity_weight * cost_of_equity + 
                    debt_weight * cost_of_debt_aftertax)
        
        # Create cost components
        cost_components = CostComponents(
            beta_levered=target_beta_levered,
            beta_unlevered=beta_stats.selected_unlevered_beta,
            cost_of_equity=cost_of_equity,
            risk_free_rate=risk_free_rate,
            credit_spread=credit_spread,
            cost_of_debt_pretax=cost_of_debt_pretax,
            cost_of_debt_aftertax=cost_of_debt_aftertax,
            equity_risk_premium=equity_risk_premium,
            country_risk_premium=country_risk_premium,
            size_premium=size_premium,
            debt_to_equity=target_debt_to_equity,
            debt_weight=debt_weight,
            equity_weight=equity_weight,
            tax_rate=tax_rate,
            estimation_method=debt_method,
            confidence_score=self._assess_wacc_confidence(beta_stats, target_market_cap)
        )
        
        # Calculate WACC evolution
        wacc_evolution = self._calculate_wacc_evolution(
            cost_components, 
            capital_structure_mode, 
            forecast_years
        )
        
        # Create standard WACCCalculation object
        wacc_calculation = WACCCalculation(
            bottom_up_beta_unlevered=beta_stats.selected_unlevered_beta,
            bottom_up_beta_levered=target_beta_levered,
            beta_source="bottom_up",
            risk_free_rate=risk_free_rate,
            equity_risk_premium=equity_risk_premium,
            country_risk_premium=country_risk_premium,
            cost_of_equity=cost_of_equity,
            cost_of_debt=cost_of_debt_aftertax,
            credit_spread=credit_spread,
            debt_to_total_capital=debt_weight,
            equity_to_total_capital=equity_weight,
            tax_rate=tax_rate,
            wacc=base_wacc,
            wacc_terminal=wacc_evolution.terminal_wacc
        )
        
        print(f"   ✓ Base WACC: {base_wacc:.2%}")
        print(f"   ✓ Cost of Equity: {cost_of_equity:.2%}, Cost of Debt: {cost_of_debt_aftertax:.2%}")
        print(f"   ✓ Capital Structure: {debt_weight:.1%} debt, {equity_weight:.1%} equity")
        
        return wacc_calculation, wacc_evolution, cost_components
    
    def _estimate_cost_of_debt(
        self,
        debt_to_equity: float,
        risk_free_rate: float,
        method: CostOfDebtMethod,
        market_cap: Optional[float] = None
    ) -> Tuple[float, float, str]:
        """Estimate cost of debt using various methods.
        
        Returns:
            Tuple of (cost of debt, credit spread, method used)
        """
        if method == CostOfDebtMethod.CREDIT_SPREAD:
            # Estimate based on leverage and size
            credit_spread = self._leverage_to_credit_spread(debt_to_equity, market_cap)
            
        elif method == CostOfDebtMethod.RATING_BASED:
            # Estimate based on implied credit rating
            credit_rating = self._estimate_credit_rating(debt_to_equity, market_cap)
            credit_spread = self._rating_to_spread(credit_rating)
            
        elif method == CostOfDebtMethod.INTEREST_COVERAGE:
            # Estimate based on interest coverage (would need EBITDA data)
            # Default to credit spread method for now
            credit_spread = self._leverage_to_credit_spread(debt_to_equity, market_cap)
            
        else:  # PEER_AVERAGE
            # Use industry average spread
            credit_spread = 0.02  # 200 bps default
        
        cost_of_debt = risk_free_rate + credit_spread
        
        # Apply bounds
        cost_of_debt = max(self.cost_of_debt_floor, min(cost_of_debt, self.cost_of_debt_ceiling))
        actual_spread = cost_of_debt - risk_free_rate
        
        return cost_of_debt, actual_spread, method.value
    
    def _leverage_to_credit_spread(
        self, 
        debt_to_equity: float, 
        market_cap: Optional[float]
    ) -> float:
        """Convert leverage ratio to credit spread estimate."""
        # Base spread from leverage
        if debt_to_equity <= 0.2:
            base_spread = 0.005  # 50 bps (very low leverage)
        elif debt_to_equity <= 0.4:
            base_spread = 0.01   # 100 bps (moderate leverage)
        elif debt_to_equity <= 0.8:
            base_spread = 0.02   # 200 bps (high leverage)
        elif debt_to_equity <= 1.5:
            base_spread = 0.04   # 400 bps (very high leverage)
        else:
            base_spread = 0.08   # 800 bps (distressed)
        
        # Size adjustment (smaller companies pay higher spreads)
        size_adjustment = 0.0
        if market_cap:
            if market_cap < 500:      # Small cap ($500M)
                size_adjustment = 0.015   # +150 bps
            elif market_cap < 2000:   # Mid cap ($2B)
                size_adjustment = 0.01    # +100 bps
            elif market_cap < 10000:  # Large cap ($10B)
                size_adjustment = 0.005   # +50 bps
            # Mega cap gets no adjustment
        
        return base_spread + size_adjustment
    
    def _estimate_credit_rating(
        self, 
        debt_to_equity: float, 
        market_cap: Optional[float]
    ) -> str:
        """Estimate credit rating from financial metrics."""
        # Simple mapping from leverage to rating
        if debt_to_equity <= 0.2:
            base_rating = "AAA" if market_cap and market_cap > 50000 else "AA"
        elif debt_to_equity <= 0.4:
            base_rating = "A"
        elif debt_to_equity <= 0.8:
            base_rating = "BBB"
        elif debt_to_equity <= 1.5:
            base_rating = "BB"
        else:
            base_rating = "B"
        
        return base_rating
    
    def _rating_to_spread(self, rating: str) -> float:
        """Convert credit rating to spread estimate."""
        rating_spreads = {
            "AAA": 0.003,   # 30 bps
            "AA": 0.005,    # 50 bps
            "A": 0.01,      # 100 bps
            "BBB": 0.02,    # 200 bps
            "BB": 0.04,     # 400 bps
            "B": 0.08,      # 800 bps
            "CCC": 0.15     # 1500 bps
        }
        
        return rating_spreads.get(rating, 0.02)  # Default to BBB
    
    def _calculate_size_premium(self, market_cap: float) -> float:
        """Calculate size premium based on market capitalization."""
        # Size premiums in basis points (academic research based)
        if market_cap < 250:        # Micro cap
            return 0.08             # 800 bps
        elif market_cap < 1000:     # Small cap
            return 0.04             # 400 bps
        elif market_cap < 5000:     # Mid cap
            return 0.02             # 200 bps
        elif market_cap < 25000:    # Large cap
            return 0.01             # 100 bps
        else:                       # Mega cap
            return 0.0              # No premium
    
    def _calculate_wacc_evolution(
        self,
        cost_components: CostComponents,
        capital_structure_mode: CapitalStructureMode,
        forecast_years: int
    ) -> WACCEvolution:
        """Calculate WACC evolution over forecast period."""
        years = list(range(1, forecast_years + 1))
        wacc_values = []
        debt_ratios = []
        cost_of_equity_values = []
        cost_of_debt_values = []
        
        for year in years:
            if capital_structure_mode == CapitalStructureMode.STATIC:
                # Static capital structure
                year_debt_ratio = cost_components.debt_to_equity
                year_cost_of_equity = cost_components.cost_of_equity
                year_cost_of_debt = cost_components.cost_of_debt_aftertax
                
            elif capital_structure_mode == CapitalStructureMode.TARGET_CONVERGENCE:
                # Gradual convergence to optimal structure
                convergence_factor = min(1.0, year / (forecast_years * 0.6))  # Converge by 60% of forecast
                optimal_debt_ratio = self._estimate_optimal_debt_ratio(cost_components)
                
                year_debt_ratio = (cost_components.debt_to_equity * (1 - convergence_factor) + 
                                 optimal_debt_ratio * convergence_factor)
                
                # Recalculate levered beta and cost of equity
                from investing_agent.agents.beta_calculation import BetaCalculator
                beta_calc = BetaCalculator()
                year_beta_levered = beta_calc.relever_beta(
                    cost_components.beta_unlevered or 1.0,
                    year_debt_ratio,
                    cost_components.tax_rate
                )
                
                year_cost_of_equity = (cost_components.risk_free_rate + 
                                     year_beta_levered * cost_components.equity_risk_premium +
                                     cost_components.country_risk_premium +
                                     cost_components.size_premium)
                
                year_cost_of_debt = cost_components.cost_of_debt_aftertax
                
            else:  # DYNAMIC_OPTIMAL
                # Dynamic optimization (simplified)
                year_debt_ratio = cost_components.debt_to_equity
                year_cost_of_equity = cost_components.cost_of_equity
                year_cost_of_debt = cost_components.cost_of_debt_aftertax
            
            # Calculate year WACC
            year_debt_weight = year_debt_ratio / (1 + year_debt_ratio)
            year_equity_weight = 1 / (1 + year_debt_ratio)
            
            year_wacc = (year_equity_weight * year_cost_of_equity + 
                        year_debt_weight * year_cost_of_debt)
            
            wacc_values.append(year_wacc)
            debt_ratios.append(year_debt_ratio)
            cost_of_equity_values.append(year_cost_of_equity)
            cost_of_debt_values.append(year_cost_of_debt)
        
        # Terminal WACC (typically converges to stable level)
        terminal_debt_ratio = debt_ratios[-1] if debt_ratios else cost_components.debt_to_equity
        terminal_wacc = wacc_values[-1] if wacc_values else cost_components.cost_of_equity * 0.9  # Conservative estimate
        
        return WACCEvolution(
            years=years,
            wacc_values=wacc_values,
            debt_ratios=debt_ratios,
            cost_of_equity_values=cost_of_equity_values,
            cost_of_debt_values=cost_of_debt_values,
            terminal_wacc=terminal_wacc,
            terminal_debt_ratio=terminal_debt_ratio
        )
    
    def _estimate_optimal_debt_ratio(self, cost_components: CostComponents) -> float:
        """Estimate optimal debt ratio for target convergence."""
        # Simplified trade-off theory: balance tax benefits vs distress costs
        # Optimal ratio typically ranges from 20-50% depending on:
        # - Industry (stable cash flows support more debt)
        # - Size (larger companies can support more debt)
        # - Profitability (higher margins support more debt)
        
        base_optimal = 0.35  # 35% baseline optimal debt ratio
        
        # Adjust for company characteristics
        # Higher beta suggests more volatile cash flows -> lower optimal debt
        if cost_components.beta_levered > 1.2:
            base_optimal *= 0.8
        elif cost_components.beta_levered < 0.8:
            base_optimal *= 1.2
        
        # Size premium suggests smaller company -> lower optimal debt
        if cost_components.size_premium > 0.02:
            base_optimal *= 0.7
        
        return max(0.1, min(0.6, base_optimal))  # Bound between 10% and 60%
    
    def _assess_wacc_confidence(
        self, 
        beta_stats: BetaStatistics, 
        market_cap: Optional[float]
    ) -> float:
        """Assess confidence in WACC calculation."""
        confidence = 0.8  # Base confidence
        
        # Beta quality impact
        if beta_stats.quality_score == "excellent":
            confidence += 0.1
        elif beta_stats.quality_score == "poor":
            confidence -= 0.2
        
        # Sample size impact
        if beta_stats.sample_size >= 8:
            confidence += 0.05
        elif beta_stats.sample_size < 4:
            confidence -= 0.1
        
        # Market cap impact (larger companies have more reliable data)
        if market_cap:
            if market_cap > 10000:      # Large cap
                confidence += 0.05
            elif market_cap < 500:      # Small cap
                confidence -= 0.1
        
        return max(0.3, min(1.0, confidence))
    
    def validate_wacc_calculation(
        self, 
        wacc_calculation: WACCCalculation,
        cost_components: CostComponents
    ) -> Dict[str, Union[bool, str, float]]:
        """Validate WACC calculation for reasonableness."""
        validation_results = {
            "wacc_reasonable": True,
            "cost_of_equity_reasonable": True,
            "cost_of_debt_reasonable": True,
            "capital_structure_reasonable": True,
            "overall_assessment": "valid",
            "warnings": []
        }
        
        warnings = []
        
        # WACC bounds check (typical range 4-20%)
        if wacc_calculation.wacc < 0.03 or wacc_calculation.wacc > 0.25:
            validation_results["wacc_reasonable"] = False
            warnings.append(f"WACC {wacc_calculation.wacc:.1%} outside typical range (3-25%)")
        
        # Cost of equity bounds (typical range 6-20%)
        if wacc_calculation.cost_of_equity < 0.04 or wacc_calculation.cost_of_equity > 0.25:
            validation_results["cost_of_equity_reasonable"] = False
            warnings.append(f"Cost of equity {wacc_calculation.cost_of_equity:.1%} outside typical range (4-25%)")
        
        # Cost of debt bounds (after-tax, typical range 1-12%)
        if wacc_calculation.cost_of_debt < 0.005 or wacc_calculation.cost_of_debt > 0.15:
            validation_results["cost_of_debt_reasonable"] = False
            warnings.append(f"Cost of debt {wacc_calculation.cost_of_debt:.1%} outside typical range (0.5-15%)")
        
        # Capital structure reasonableness
        if wacc_calculation.debt_to_total_capital > 0.8:
            validation_results["capital_structure_reasonable"] = False
            warnings.append(f"Debt ratio {wacc_calculation.debt_to_total_capital:.1%} extremely high")
        
        # Cost of equity should typically be higher than risk-free rate
        if wacc_calculation.cost_of_equity <= wacc_calculation.risk_free_rate:
            warnings.append("Cost of equity not higher than risk-free rate")
        
        # After-tax cost of debt should be lower than cost of equity
        if wacc_calculation.cost_of_debt >= wacc_calculation.cost_of_equity:
            warnings.append("Cost of debt higher than cost of equity (unusual)")
        
        validation_results["warnings"] = warnings
        
        if not all([validation_results["wacc_reasonable"], 
                   validation_results["cost_of_equity_reasonable"],
                   validation_results["cost_of_debt_reasonable"],
                   validation_results["capital_structure_reasonable"]]):
            validation_results["overall_assessment"] = "questionable"
        
        if len(warnings) >= 3:
            validation_results["overall_assessment"] = "poor"
        
        return validation_results


def calculate_levered_wacc(
    beta_stats: BetaStatistics,
    target_debt_to_equity: float,
    risk_free_rate: float,
    target_market_cap: Optional[float] = None,
    target_tax_rate: Optional[float] = None,
    country_risk_premium: float = 0.0
) -> Tuple[WACCCalculation, WACCEvolution, CostComponents]:
    """Convenience function for levered WACC calculation.
    
    Args:
        beta_stats: Beta statistics from peer analysis
        target_debt_to_equity: Target D/E ratio
        risk_free_rate: Risk-free rate
        target_market_cap: Target market cap for size premium
        target_tax_rate: Target tax rate
        country_risk_premium: Country risk premium
        
    Returns:
        Tuple of (WACC calculation, WACC evolution, cost components)
    """
    calculator = WACCCalculator()
    return calculator.calculate_comprehensive_wacc(
        beta_stats=beta_stats,
        target_debt_to_equity=target_debt_to_equity,
        risk_free_rate=risk_free_rate,
        target_market_cap=target_market_cap,
        target_tax_rate=target_tax_rate,
        country_risk_premium=country_risk_premium
    )