from __future__ import annotations

"""
Winsorized Multiple Calculations

Implements robust statistical methods for calculating industry multiples with
outlier handling, winsorization, and comprehensive statistical analysis.
"""

import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.comparables import PeerCompany, IndustryStatistics


class MultipleType(Enum):
    """Types of financial multiples supported."""
    PE_RATIO = "pe_ratio"
    PE_FORWARD = "pe_forward" 
    EV_EBITDA = "ev_ebitda"
    EV_SALES = "ev_sales"
    PRICE_TO_BOOK = "price_to_book"
    PEG_RATIO = "peg_ratio"
    EV_EBIT = "ev_ebit"
    PRICE_TO_SALES = "price_to_sales"


@dataclass
class MultipleStatistics:
    """Statistical measures for a financial multiple."""
    multiple_type: MultipleType
    raw_values: List[float]
    
    # Basic statistics
    count: int
    mean: float
    median: float
    std_dev: float
    
    # Robust statistics
    trimmed_mean: float  # 10% trimmed mean
    winsorized_mean: float
    winsorized_std: float
    
    # Percentiles
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    
    # Outlier information
    outliers_removed: int
    outlier_threshold_lower: float
    outlier_threshold_upper: float
    
    # Quality metrics
    data_completeness: float  # Fraction of peers with valid data
    coefficient_of_variation: float  # std_dev / mean
    quality_score: str  # excellent, good, fair, poor


class MultiplesCalculator:
    """Calculator for winsorized and robust multiple statistics."""
    
    def __init__(
        self, 
        winsorization_percentiles: Tuple[float, float] = (0.05, 0.95),
        trim_percentage: float = 0.10,
        outlier_sigma: float = 3.0
    ):
        """Initialize multiples calculator.
        
        Args:
            winsorization_percentiles: Percentiles for winsorization (lower, upper)
            trim_percentage: Percentage to trim from each end for trimmed mean
            outlier_sigma: Sigma threshold for outlier detection
        """
        self.winsorization_percentiles = winsorization_percentiles
        self.trim_percentage = trim_percentage
        self.outlier_sigma = outlier_sigma
    
    def calculate_industry_multiples(
        self, 
        peer_companies: List[PeerCompany],
        multiple_types: Optional[List[MultipleType]] = None
    ) -> Dict[MultipleType, MultipleStatistics]:
        """Calculate comprehensive multiple statistics for peer group.
        
        Args:
            peer_companies: List of peer companies
            multiple_types: Specific multiples to calculate (all if None)
            
        Returns:
            Dictionary mapping multiple types to their statistics
        """
        if multiple_types is None:
            multiple_types = [
                MultipleType.PE_RATIO,
                MultipleType.PE_FORWARD,
                MultipleType.EV_EBITDA,
                MultipleType.EV_SALES,
                MultipleType.PRICE_TO_BOOK,
                MultipleType.PEG_RATIO
            ]
        
        results = {}
        
        print(f"📊 Calculating winsorized multiples for {len(peer_companies)} peers")
        
        for multiple_type in multiple_types:
            # Extract values for this multiple
            raw_values = self._extract_multiple_values(peer_companies, multiple_type)
            
            if len(raw_values) < 2:
                print(f"   ⚠️  Insufficient data for {multiple_type.value}: {len(raw_values)} values")
                continue
            
            # Calculate comprehensive statistics
            stats = self._calculate_multiple_statistics(multiple_type, raw_values)
            results[multiple_type] = stats
            
            print(f"   ✓ {multiple_type.value}: {stats.median:.1f} median, {stats.winsorized_mean:.1f} winsorized mean")
        
        return results
    
    def _extract_multiple_values(
        self, 
        peer_companies: List[PeerCompany], 
        multiple_type: MultipleType
    ) -> List[float]:
        """Extract values for specific multiple type from peer companies."""
        values = []
        
        for peer in peer_companies:
            value = None
            
            if multiple_type == MultipleType.PE_RATIO:
                value = peer.multiples.pe_ratio
            elif multiple_type == MultipleType.PE_FORWARD:
                value = peer.multiples.pe_forward
            elif multiple_type == MultipleType.EV_EBITDA:
                value = peer.multiples.ev_ebitda
            elif multiple_type == MultipleType.EV_SALES:
                value = peer.multiples.ev_sales
            elif multiple_type == MultipleType.PRICE_TO_BOOK:
                value = peer.multiples.price_to_book
            elif multiple_type == MultipleType.PEG_RATIO:
                value = peer.multiples.peg_ratio
            
            # Apply basic filters
            if value is not None and self._is_reasonable_multiple(multiple_type, value):
                values.append(value)
        
        return values
    
    def _is_reasonable_multiple(self, multiple_type: MultipleType, value: float) -> bool:
        """Apply basic reasonableness filters to multiples."""
        if value <= 0:
            return False
        
        # Type-specific upper bounds to filter obvious errors
        upper_bounds = {
            MultipleType.PE_RATIO: 1000.0,
            MultipleType.PE_FORWARD: 1000.0,
            MultipleType.EV_EBITDA: 500.0,
            MultipleType.EV_SALES: 100.0,
            MultipleType.PRICE_TO_BOOK: 100.0,
            MultipleType.PEG_RATIO: 50.0
        }
        
        max_value = upper_bounds.get(multiple_type, 1000.0)
        return value <= max_value
    
    def _calculate_multiple_statistics(
        self, 
        multiple_type: MultipleType, 
        raw_values: List[float]
    ) -> MultipleStatistics:
        """Calculate comprehensive statistics for a multiple."""
        
        # Sort values for percentile calculations
        sorted_values = sorted(raw_values)
        n = len(sorted_values)
        
        # Basic statistics
        mean_val = statistics.mean(sorted_values)
        median_val = statistics.median(sorted_values)
        std_val = statistics.stdev(sorted_values) if n > 1 else 0.0
        
        # Percentiles
        percentiles = self._calculate_percentiles(sorted_values)
        
        # Outlier detection and removal
        outlier_lower = mean_val - self.outlier_sigma * std_val
        outlier_upper = mean_val + self.outlier_sigma * std_val
        
        # For multiples, we typically only remove upper outliers
        outlier_lower = max(outlier_lower, 0.0)  # Don't remove low positive multiples
        
        clean_values = [v for v in sorted_values if outlier_lower <= v <= outlier_upper]
        outliers_removed = len(sorted_values) - len(clean_values)
        
        # Winsorized statistics
        winsorized_values = self._winsorize_values(clean_values)
        winsorized_mean = statistics.mean(winsorized_values)
        winsorized_std = statistics.stdev(winsorized_values) if len(winsorized_values) > 1 else 0.0
        
        # Trimmed mean (remove top and bottom percentiles)
        trimmed_values = self._trim_values(clean_values)
        trimmed_mean = statistics.mean(trimmed_values) if trimmed_values else mean_val
        
        # Quality assessment
        data_completeness = len(raw_values) / len(raw_values)  # Would compare to total peers in production
        cv = std_val / mean_val if mean_val > 0 else float('inf')
        quality_score = self._assess_data_quality(n, cv, outliers_removed / n if n > 0 else 0)
        
        return MultipleStatistics(
            multiple_type=multiple_type,
            raw_values=raw_values,
            count=len(clean_values),
            mean=statistics.mean(clean_values) if clean_values else mean_val,
            median=statistics.median(clean_values) if clean_values else median_val,
            std_dev=statistics.stdev(clean_values) if len(clean_values) > 1 else std_val,
            trimmed_mean=trimmed_mean,
            winsorized_mean=winsorized_mean,
            winsorized_std=winsorized_std,
            percentile_5=percentiles['p5'],
            percentile_25=percentiles['p25'],
            percentile_75=percentiles['p75'],
            percentile_95=percentiles['p95'],
            outliers_removed=outliers_removed,
            outlier_threshold_lower=outlier_lower,
            outlier_threshold_upper=outlier_upper,
            data_completeness=data_completeness,
            coefficient_of_variation=cv,
            quality_score=quality_score
        )
    
    def _calculate_percentiles(self, sorted_values: List[float]) -> Dict[str, float]:
        """Calculate percentiles from sorted values."""
        n = len(sorted_values)
        
        if n == 0:
            return {'p5': 0, 'p25': 0, 'p75': 0, 'p95': 0}
        
        def percentile(data: List[float], p: float) -> float:
            """Calculate percentile using linear interpolation."""
            if len(data) == 1:
                return data[0]
            
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            
            if f == len(data) - 1:
                return data[f]
            
            return data[f] * (1 - c) + data[f + 1] * c
        
        return {
            'p5': percentile(sorted_values, 0.05),
            'p25': percentile(sorted_values, 0.25),
            'p75': percentile(sorted_values, 0.75),
            'p95': percentile(sorted_values, 0.95)
        }
    
    def _winsorize_values(self, values: List[float]) -> List[float]:
        """Apply winsorization to values."""
        if len(values) < 3:
            return values.copy()
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        # Calculate winsorization bounds
        lower_idx = int(n * self.winsorization_percentiles[0])
        upper_idx = int(n * self.winsorization_percentiles[1])
        
        lower_bound = sorted_vals[lower_idx] if lower_idx < n else sorted_vals[0]
        upper_bound = sorted_vals[upper_idx] if upper_idx < n else sorted_vals[-1]
        
        # Winsorize values
        winsorized = []
        for val in values:
            if val < lower_bound:
                winsorized.append(lower_bound)
            elif val > upper_bound:
                winsorized.append(upper_bound)
            else:
                winsorized.append(val)
        
        return winsorized
    
    def _trim_values(self, values: List[float]) -> List[float]:
        """Apply trimming to values (remove top and bottom percentages)."""
        if len(values) < 4:
            return values.copy()
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        # Calculate trim indices
        trim_count = int(n * self.trim_percentage)
        
        if trim_count >= n // 2:
            trim_count = max(0, n // 2 - 1)
        
        return sorted_vals[trim_count:n-trim_count] if trim_count > 0 else sorted_vals
    
    def _assess_data_quality(
        self, 
        sample_size: int, 
        coefficient_of_variation: float,
        outlier_rate: float
    ) -> str:
        """Assess overall data quality for multiple."""
        
        if sample_size >= 8 and coefficient_of_variation < 0.5 and outlier_rate < 0.2:
            return "excellent"
        elif sample_size >= 5 and coefficient_of_variation < 1.0 and outlier_rate < 0.3:
            return "good"
        elif sample_size >= 3 and coefficient_of_variation < 2.0 and outlier_rate < 0.4:
            return "fair"
        else:
            return "poor"
    
    def create_enhanced_industry_statistics(
        self, 
        multiple_stats: Dict[MultipleType, MultipleStatistics]
    ) -> IndustryStatistics:
        """Create enhanced industry statistics from multiple calculations."""
        
        # Extract key statistics
        ev_ebitda_stats = multiple_stats.get(MultipleType.EV_EBITDA)
        ev_sales_stats = multiple_stats.get(MultipleType.EV_SALES)
        pe_forward_stats = multiple_stats.get(MultipleType.PE_FORWARD)
        
        # Calculate overall data completeness
        total_data_points = sum(len(stats.raw_values) for stats in multiple_stats.values())
        expected_data_points = len(multiple_stats) * max(
            len(stats.raw_values) for stats in multiple_stats.values()
        ) if multiple_stats else 1
        
        data_completeness = total_data_points / expected_data_points
        
        # Create enhanced statistics
        industry_stats = IndustryStatistics(
            sample_size=max(stats.count for stats in multiple_stats.values()) if multiple_stats else 0,
            data_completeness=data_completeness,
            winsorized_at=self.winsorization_percentiles
        )
        
        # Populate EV/EBITDA statistics
        if ev_ebitda_stats:
            industry_stats.ev_ebitda_median = ev_ebitda_stats.median
            industry_stats.ev_ebitda_mean = ev_ebitda_stats.winsorized_mean  # Use winsorized mean
            industry_stats.ev_ebitda_std = ev_ebitda_stats.winsorized_std
        
        # Populate EV/Sales statistics
        if ev_sales_stats:
            industry_stats.ev_sales_median = ev_sales_stats.median
            industry_stats.ev_sales_mean = ev_sales_stats.winsorized_mean
        
        # Populate Forward P/E statistics
        if pe_forward_stats:
            industry_stats.pe_forward_median = pe_forward_stats.median
            industry_stats.pe_forward_mean = pe_forward_stats.winsorized_mean
        
        return industry_stats
    
    def validate_target_multiples(
        self, 
        target_multiples: Dict[str, float],
        industry_stats: Dict[MultipleType, MultipleStatistics],
        tolerance_multiple: float = 5.0
    ) -> Dict[str, bool]:
        """Validate target company multiples against peer statistics.
        
        Args:
            target_multiples: Target company multiples
            industry_stats: Industry statistics from peer analysis
            tolerance_multiple: Multiple of median for reasonableness check
            
        Returns:
            Dictionary of validation results
        """
        validation_results = {}
        
        multiple_mapping = {
            'pe_ratio': MultipleType.PE_RATIO,
            'pe_forward': MultipleType.PE_FORWARD,
            'ev_ebitda': MultipleType.EV_EBITDA,
            'ev_sales': MultipleType.EV_SALES,
            'price_to_book': MultipleType.PRICE_TO_BOOK
        }
        
        for target_key, target_value in target_multiples.items():
            if target_key not in multiple_mapping:
                continue
                
            multiple_type = multiple_mapping[target_key]
            
            if multiple_type not in industry_stats:
                validation_results[target_key] = False  # No peer data to validate against
                continue
            
            peer_stats = industry_stats[multiple_type]
            
            # Check if target multiple is within reasonable range of peers
            # Use percentile-based validation for robustness
            lower_bound = peer_stats.percentile_5
            upper_bound = min(
                peer_stats.percentile_95,
                peer_stats.median * tolerance_multiple
            )
            
            is_reasonable = lower_bound <= target_value <= upper_bound
            validation_results[target_key] = is_reasonable
            
            if not is_reasonable:
                print(f"   ⚠️  {target_key}: {target_value:.1f} outside peer range [{lower_bound:.1f}, {upper_bound:.1f}]")
        
        return validation_results


def calculate_winsorized_multiples(
    peer_companies: List[PeerCompany],
    winsorization_percentiles: Tuple[float, float] = (0.05, 0.95)
) -> Tuple[Dict[MultipleType, MultipleStatistics], IndustryStatistics]:
    """Convenience function for calculating winsorized multiples.
    
    Args:
        peer_companies: List of peer companies
        winsorization_percentiles: Percentiles for winsorization
        
    Returns:
        Tuple of (multiple statistics, enhanced industry statistics)
    """
    calculator = MultiplesCalculator(winsorization_percentiles=winsorization_percentiles)
    
    multiple_stats = calculator.calculate_industry_multiples(peer_companies)
    industry_stats = calculator.create_enhanced_industry_statistics(multiple_stats)
    
    return multiple_stats, industry_stats