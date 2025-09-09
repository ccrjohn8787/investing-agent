from __future__ import annotations

"""
Bottom-Up Beta Calculation

Implements systematic beta calculation from comparable companies including
unlevered beta calculation, peer aggregation, and re-levering for target companies.
"""

import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.comparables import PeerCompany, WACCCalculation, IndustryStatistics


class BetaCalculationMethod(Enum):
    """Methods for calculating beta from peer companies."""
    MEDIAN = "median"
    WINSORIZED_MEAN = "winsorized_mean"
    TRIMMED_MEAN = "trimmed_mean"
    SIMPLE_MEAN = "simple_mean"


@dataclass 
class BetaStatistics:
    """Statistical measures for beta calculation."""
    raw_levered_betas: List[float]
    raw_unlevered_betas: List[float]
    
    # Unlevered beta statistics
    unlevered_median: float
    unlevered_mean: float
    unlevered_winsorized_mean: float
    unlevered_std: float
    
    # Quality metrics
    sample_size: int
    data_completeness: float
    coefficient_of_variation: float
    outliers_removed: int
    
    # Selected beta for target
    selected_unlevered_beta: float
    calculation_method: BetaCalculationMethod
    quality_score: str


class BetaCalculator:
    """Calculator for bottom-up beta from comparable companies."""
    
    def __init__(
        self, 
        default_tax_rate: float = 0.25,
        outlier_sigma: float = 2.5,
        winsorization_percentiles: Tuple[float, float] = (0.1, 0.9),
        min_beta_threshold: float = 0.1,
        max_beta_threshold: float = 3.0
    ):
        """Initialize beta calculator.
        
        Args:
            default_tax_rate: Default tax rate for unlevering (25%)
            outlier_sigma: Sigma threshold for beta outlier detection
            winsorization_percentiles: Percentiles for winsorization
            min_beta_threshold: Minimum reasonable beta value
            max_beta_threshold: Maximum reasonable beta value
        """
        self.default_tax_rate = default_tax_rate
        self.outlier_sigma = outlier_sigma
        self.winsorization_percentiles = winsorization_percentiles
        self.min_beta_threshold = min_beta_threshold
        self.max_beta_threshold = max_beta_threshold
    
    def calculate_bottom_up_beta(
        self, 
        peer_companies: List[PeerCompany],
        calculation_method: BetaCalculationMethod = BetaCalculationMethod.MEDIAN
    ) -> BetaStatistics:
        """Calculate bottom-up unlevered beta from peer companies.
        
        Args:
            peer_companies: List of peer companies with beta data
            calculation_method: Method for selecting representative beta
            
        Returns:
            Beta statistics with selected unlevered beta
        """
        print(f"📊 Calculating bottom-up beta from {len(peer_companies)} peers")
        
        # Extract and validate beta data
        beta_data = self._extract_beta_data(peer_companies)
        
        if len(beta_data) < 2:
            raise ValueError(f"Insufficient beta data: only {len(beta_data)} valid betas found")
        
        # Unlever peer betas
        unlevered_betas = []
        for peer_data in beta_data:
            unlevered_beta = self._unlever_beta(
                peer_data['levered_beta'], 
                peer_data['debt_to_equity'], 
                peer_data['tax_rate']
            )
            unlevered_betas.append(unlevered_beta)
        
        # Calculate comprehensive statistics
        stats = self._calculate_beta_statistics(
            levered_betas=[data['levered_beta'] for data in beta_data],
            unlevered_betas=unlevered_betas,
            calculation_method=calculation_method
        )
        
        print(f"   ✓ Selected unlevered beta: {stats.selected_unlevered_beta:.3f} ({stats.calculation_method.value})")
        print(f"   ✓ Sample size: {stats.sample_size}, Quality: {stats.quality_score}")
        
        return stats
    
    def relever_beta(
        self, 
        unlevered_beta: float, 
        target_debt_to_equity: float,
        target_tax_rate: float
    ) -> float:
        """Re-lever unlevered beta for target company capital structure.
        
        Formula: Beta_levered = Beta_unlevered * [1 + (1 - Tax_rate) * (D/E)]
        
        Args:
            unlevered_beta: Industry unlevered beta
            target_debt_to_equity: Target company debt-to-equity ratio
            target_tax_rate: Target company tax rate
            
        Returns:
            Re-levered beta for target company
        """
        if unlevered_beta <= 0:
            raise ValueError(f"Unlevered beta must be positive, got {unlevered_beta}")
            
        if target_debt_to_equity < 0:
            raise ValueError(f"Debt-to-equity ratio cannot be negative, got {target_debt_to_equity}")
            
        if not (0 <= target_tax_rate <= 1):
            raise ValueError(f"Tax rate must be between 0 and 1, got {target_tax_rate}")
        
        levered_beta = unlevered_beta * (1 + (1 - target_tax_rate) * target_debt_to_equity)
        
        # Apply reasonableness bounds
        levered_beta = max(self.min_beta_threshold, min(levered_beta, self.max_beta_threshold))
        
        print(f"   📈 Re-levered beta: {unlevered_beta:.3f} → {levered_beta:.3f} (D/E: {target_debt_to_equity:.2f}, Tax: {target_tax_rate:.1%})")
        
        return levered_beta
    
    def _extract_beta_data(self, peer_companies: List[PeerCompany]) -> List[Dict]:
        """Extract and validate beta data from peer companies."""
        beta_data = []
        
        for peer in peer_companies:
            # Prefer levered beta, fallback to unlevered if needed
            levered_beta = peer.beta_levered
            
            if levered_beta is None or not self._is_reasonable_beta(levered_beta):
                continue
            
            # Extract financial data for unlevering
            debt_to_equity = self._calculate_debt_to_equity(peer)
            tax_rate = self._estimate_tax_rate(peer)
            
            beta_data.append({
                'ticker': peer.ticker,
                'levered_beta': levered_beta,
                'debt_to_equity': debt_to_equity,
                'tax_rate': tax_rate
            })
        
        print(f"   📊 Valid beta data from {len(beta_data)}/{len(peer_companies)} peers")
        return beta_data
    
    def _unlever_beta(
        self, 
        levered_beta: float, 
        debt_to_equity: float, 
        tax_rate: float
    ) -> float:
        """Unlever beta using Hamada equation.
        
        Formula: Beta_unlevered = Beta_levered / [1 + (1 - Tax_rate) * (D/E)]
        """
        if debt_to_equity < 0:
            debt_to_equity = 0.0  # Handle negative D/E as zero leverage
        
        denominator = 1 + (1 - tax_rate) * debt_to_equity
        
        if denominator <= 0:
            # Edge case: extremely high leverage or tax rate
            return levered_beta * 0.5  # Conservative adjustment
        
        unlevered_beta = levered_beta / denominator
        
        # Apply bounds to unlevered beta
        unlevered_beta = max(0.05, min(unlevered_beta, 2.0))  # Reasonable range for unlevered beta
        
        return unlevered_beta
    
    def _calculate_debt_to_equity(self, peer: PeerCompany) -> float:
        """Calculate or estimate debt-to-equity ratio for peer."""
        # If direct D/E available from multiples data
        if hasattr(peer.multiples, 'debt_to_equity') and peer.multiples.debt_to_equity is not None:
            return max(0.0, peer.multiples.debt_to_equity)
        
        # Estimate from enterprise value and market cap if available
        if peer.enterprise_value and peer.market_cap and peer.enterprise_value > peer.market_cap:
            net_debt = peer.enterprise_value - peer.market_cap
            debt_to_equity = net_debt / peer.market_cap if peer.market_cap > 0 else 0.0
            return max(0.0, debt_to_equity)
        
        # Industry default for missing data
        return 0.3  # Conservative industry average D/E ratio
    
    def _estimate_tax_rate(self, peer: PeerCompany) -> float:
        """Estimate tax rate for peer company."""
        # Country-specific tax rate estimates
        tax_rates = {
            'US': 0.25,    # US federal + state average
            'GB': 0.25,    # UK corporation tax
            'DE': 0.30,    # Germany corporate tax
            'FR': 0.28,    # France corporate tax
            'CA': 0.27,    # Canada combined rate
            'JP': 0.30,    # Japan corporate tax
            'CN': 0.25,    # China enterprise tax
            'IN': 0.30     # India corporate tax
        }
        
        return tax_rates.get(peer.country, self.default_tax_rate)
    
    def _is_reasonable_beta(self, beta: float) -> bool:
        """Check if beta value is within reasonable bounds."""
        return self.min_beta_threshold <= beta <= self.max_beta_threshold
    
    def _calculate_beta_statistics(
        self,
        levered_betas: List[float],
        unlevered_betas: List[float], 
        calculation_method: BetaCalculationMethod
    ) -> BetaStatistics:
        """Calculate comprehensive beta statistics."""
        # Remove outliers from unlevered betas
        mean_beta = statistics.mean(unlevered_betas)
        std_beta = statistics.stdev(unlevered_betas) if len(unlevered_betas) > 1 else 0.0
        
        # Outlier bounds (more conservative for beta)
        lower_bound = max(0.05, mean_beta - self.outlier_sigma * std_beta)
        upper_bound = min(2.0, mean_beta + self.outlier_sigma * std_beta)
        
        clean_betas = [b for b in unlevered_betas if lower_bound <= b <= upper_bound]
        outliers_removed = len(unlevered_betas) - len(clean_betas)
        
        if not clean_betas:
            clean_betas = unlevered_betas  # Keep all if outlier removal too aggressive
            outliers_removed = 0
        
        # Calculate robust statistics
        median_beta = statistics.median(clean_betas)
        mean_beta_clean = statistics.mean(clean_betas)
        std_beta_clean = statistics.stdev(clean_betas) if len(clean_betas) > 1 else 0.0
        
        # Winsorized mean
        winsorized_betas = self._winsorize_values(clean_betas)
        winsorized_mean = statistics.mean(winsorized_betas)
        
        # Select beta based on method
        selected_beta = self._select_beta(
            clean_betas, median_beta, mean_beta_clean, winsorized_mean, calculation_method
        )
        
        # Quality assessment
        data_completeness = len(unlevered_betas) / len(unlevered_betas)  # Would use total peers in production
        cv = std_beta_clean / mean_beta_clean if mean_beta_clean > 0 else 0.0
        quality_score = self._assess_beta_quality(len(clean_betas), cv, outliers_removed / len(unlevered_betas))
        
        return BetaStatistics(
            raw_levered_betas=levered_betas,
            raw_unlevered_betas=unlevered_betas,
            unlevered_median=median_beta,
            unlevered_mean=mean_beta_clean,
            unlevered_winsorized_mean=winsorized_mean,
            unlevered_std=std_beta_clean,
            sample_size=len(clean_betas),
            data_completeness=data_completeness,
            coefficient_of_variation=cv,
            outliers_removed=outliers_removed,
            selected_unlevered_beta=selected_beta,
            calculation_method=calculation_method,
            quality_score=quality_score
        )
    
    def _winsorize_values(self, values: List[float]) -> List[float]:
        """Apply winsorization to beta values."""
        if len(values) < 3:
            return values.copy()
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        lower_idx = int(n * self.winsorization_percentiles[0])
        upper_idx = int(n * self.winsorization_percentiles[1])
        
        lower_bound = sorted_vals[lower_idx] if lower_idx < n else sorted_vals[0]
        upper_bound = sorted_vals[upper_idx] if upper_idx < n else sorted_vals[-1]
        
        return [max(lower_bound, min(upper_bound, val)) for val in values]
    
    def _select_beta(
        self,
        clean_betas: List[float],
        median_beta: float,
        mean_beta: float,
        winsorized_mean: float,
        method: BetaCalculationMethod
    ) -> float:
        """Select representative beta based on calculation method."""
        if method == BetaCalculationMethod.MEDIAN:
            return median_beta
        elif method == BetaCalculationMethod.SIMPLE_MEAN:
            return mean_beta
        elif method == BetaCalculationMethod.WINSORIZED_MEAN:
            return winsorized_mean
        elif method == BetaCalculationMethod.TRIMMED_MEAN:
            # 20% trimmed mean
            sorted_betas = sorted(clean_betas)
            n = len(sorted_betas)
            trim_count = max(0, int(n * 0.1))  # Remove 10% from each end
            trimmed = sorted_betas[trim_count:n-trim_count] if trim_count > 0 else sorted_betas
            return statistics.mean(trimmed) if trimmed else mean_beta
        else:
            return median_beta  # Default fallback
    
    def _assess_beta_quality(
        self,
        sample_size: int,
        coefficient_of_variation: float,
        outlier_rate: float
    ) -> str:
        """Assess quality of beta calculation."""
        if sample_size >= 8 and coefficient_of_variation < 0.3 and outlier_rate < 0.15:
            return "excellent"
        elif sample_size >= 5 and coefficient_of_variation < 0.5 and outlier_rate < 0.25:
            return "good"
        elif sample_size >= 3 and coefficient_of_variation < 0.8 and outlier_rate < 0.35:
            return "fair"
        else:
            return "poor"
    
    def create_wacc_calculation_base(
        self,
        beta_stats: BetaStatistics,
        target_debt_to_equity: float,
        target_tax_rate: float,
        risk_free_rate: float,
        equity_risk_premium: float,
        country_risk_premium: float = 0.0
    ) -> Dict:
        """Create base WACC calculation data structure.
        
        Args:
            beta_stats: Beta statistics from peer analysis
            target_debt_to_equity: Target company D/E ratio
            target_tax_rate: Target company tax rate
            risk_free_rate: Risk-free rate (10Y Treasury)
            equity_risk_premium: Market equity risk premium
            country_risk_premium: Additional country risk premium
            
        Returns:
            Dictionary with WACC calculation components
        """
        # Re-lever beta for target company
        target_beta_levered = self.relever_beta(
            beta_stats.selected_unlevered_beta,
            target_debt_to_equity,
            target_tax_rate
        )
        
        # Calculate cost of equity using CAPM
        cost_of_equity = (risk_free_rate + 
                         target_beta_levered * equity_risk_premium + 
                         country_risk_premium)
        
        # Capital structure weights
        debt_weight = target_debt_to_equity / (1 + target_debt_to_equity)
        equity_weight = 1 / (1 + target_debt_to_equity)
        
        return {
            'bottom_up_beta_unlevered': beta_stats.selected_unlevered_beta,
            'bottom_up_beta_levered': target_beta_levered,
            'beta_source': 'bottom_up',
            'cost_of_equity': cost_of_equity,
            'risk_free_rate': risk_free_rate,
            'equity_risk_premium': equity_risk_premium,
            'country_risk_premium': country_risk_premium,
            'debt_to_total_capital': debt_weight,
            'equity_to_total_capital': equity_weight,
            'tax_rate': target_tax_rate,
            'beta_calculation_quality': beta_stats.quality_score,
            'beta_sample_size': beta_stats.sample_size
        }


def calculate_bottom_up_beta(
    peer_companies: List[PeerCompany],
    calculation_method: BetaCalculationMethod = BetaCalculationMethod.MEDIAN
) -> BetaStatistics:
    """Convenience function for bottom-up beta calculation.
    
    Args:
        peer_companies: List of peer companies with beta data
        calculation_method: Method for selecting representative beta
        
    Returns:
        Beta statistics with selected unlevered beta
    """
    calculator = BetaCalculator()
    return calculator.calculate_bottom_up_beta(peer_companies, calculation_method)