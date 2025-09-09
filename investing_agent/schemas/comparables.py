from __future__ import annotations

"""
Comparables and Peer Analysis Schema

Defines structured data models for peer selection, comparable company analysis,
and bottom-up WACC calculation with comprehensive validation and quality controls.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Literal, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class PeerSelectionCriteria(BaseModel):
    """Criteria used for automatic peer selection."""
    target_ticker: str = Field(..., description="Target company ticker")
    target_market_cap: Optional[float] = Field(None, description="Target company market cap")
    sic_codes: List[str] = Field(default_factory=list, description="SIC codes for industry matching")
    market_cap_range: Tuple[float, float] = Field(..., description="Market cap range (min, max)")
    geographic_focus: str = Field(default="Global", description="Geographic focus for peer selection")
    min_peer_count: int = Field(default=5, description="Minimum number of peers required")
    max_peer_count: int = Field(default=15, description="Maximum number of peers to select")
    exclusions: List[str] = Field(default_factory=list, description="Exclusion criteria applied")
    
    @field_validator('sic_codes')
    @classmethod
    def validate_sic_codes(cls, v):
        """Validate SIC code formats."""
        for sic in v:
            if not isinstance(sic, str) or not sic.isdigit() or len(sic) not in [2, 3, 4]:
                raise ValueError(f"Invalid SIC code format: {sic}")
        return v


class CompanyMultiples(BaseModel):
    """Financial multiples for a single company."""
    # Valuation multiples
    pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
    pe_forward: Optional[float] = Field(None, description="Forward P/E ratio")
    ev_ebitda: Optional[float] = Field(None, description="EV/EBITDA multiple")
    ev_sales: Optional[float] = Field(None, description="EV/Sales multiple")
    price_to_book: Optional[float] = Field(None, description="Price-to-Book ratio")
    peg_ratio: Optional[float] = Field(None, description="PEG ratio")
    
    # Additional metrics
    roe: Optional[float] = Field(None, description="Return on Equity")
    roic: Optional[float] = Field(None, description="Return on Invested Capital")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-Equity ratio")
    
    # Data quality flags
    data_quality: str = Field(default="good", description="Data quality assessment")
    data_date: Optional[str] = Field(None, description="Date of data (YYYY-MM-DD)")
    
    @field_validator('pe_ratio', 'pe_forward', 'ev_ebitda', 'ev_sales', 'price_to_book')
    @classmethod
    def validate_positive_multiples(cls, v):
        """Ensure multiples are positive when present."""
        if v is not None and v <= 0:
            raise ValueError("Multiples must be positive")
        return v


class PeerCompany(BaseModel):
    """Single peer company with all relevant data."""
    ticker: str = Field(..., description="Company ticker symbol")
    company_name: str = Field(..., description="Company name")
    sic_code: str = Field(..., description="Primary SIC code")
    country: str = Field(default="US", description="Company domicile country")
    currency: str = Field(default="USD", description="Reporting currency")
    
    # Size metrics
    market_cap: Optional[float] = Field(None, description="Market capitalization in USD")
    enterprise_value: Optional[float] = Field(None, description="Enterprise value in USD")
    revenue_ttm: Optional[float] = Field(None, description="Trailing twelve months revenue")
    
    # Beta and risk metrics
    beta_levered: Optional[float] = Field(None, description="Levered beta")
    beta_unlevered: Optional[float] = Field(None, description="Unlevered beta")
    
    # Financial multiples
    multiples: CompanyMultiples = Field(..., description="Company financial multiples")
    
    # Selection metadata
    selection_reason: str = Field(..., description="Reason for peer selection")
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity to target (0-1)")
    
    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Validate ticker format."""
        if not v or len(v) < 1 or len(v) > 10:
            raise ValueError("Ticker must be 1-10 characters")
        return v.upper()


class IndustryStatistics(BaseModel):
    """Industry-level statistics calculated from peer group."""
    # Multiple statistics
    ev_ebitda_median: Optional[float] = Field(None, description="Industry median EV/EBITDA")
    ev_ebitda_mean: Optional[float] = Field(None, description="Industry mean EV/EBITDA")
    ev_ebitda_std: Optional[float] = Field(None, description="Industry standard deviation EV/EBITDA")
    
    ev_sales_median: Optional[float] = Field(None, description="Industry median EV/Sales")
    ev_sales_mean: Optional[float] = Field(None, description="Industry mean EV/Sales")
    
    pe_forward_median: Optional[float] = Field(None, description="Industry median forward P/E")
    pe_forward_mean: Optional[float] = Field(None, description="Industry mean forward P/E")
    
    # Beta statistics
    beta_unlevered_median: Optional[float] = Field(None, description="Industry median unlevered beta")
    beta_unlevered_mean: Optional[float] = Field(None, description="Industry mean unlevered beta")
    beta_unlevered_std: Optional[float] = Field(None, description="Industry standard deviation unlevered beta")
    
    # Quality metrics
    sample_size: int = Field(..., description="Number of companies in statistics")
    data_completeness: float = Field(..., ge=0.0, le=1.0, description="Fraction of complete data points")
    
    # Winsorization details
    winsorized_at: Tuple[float, float] = Field(default=(0.05, 0.95), description="Winsorization percentiles")


class WACCCalculation(BaseModel):
    """Complete WACC calculation with bottom-up beta."""
    # Beta calculation
    target_beta_levered: Optional[float] = Field(None, description="Target company levered beta")
    target_beta_unlevered: Optional[float] = Field(None, description="Target company unlevered beta")
    bottom_up_beta_unlevered: float = Field(..., description="Industry median unlevered beta")
    bottom_up_beta_levered: float = Field(..., description="Re-levered beta for target")
    beta_source: str = Field(default="bottom_up", description="Beta source used (bottom_up, regression, hybrid)")
    
    # Cost components
    risk_free_rate: float = Field(..., description="Risk-free rate used")
    equity_risk_premium: float = Field(..., description="Equity risk premium")
    country_risk_premium: float = Field(default=0.0, description="Country risk premium")
    cost_of_equity: float = Field(..., description="Cost of equity calculated")
    
    cost_of_debt: float = Field(..., description="After-tax cost of debt")
    credit_spread: Optional[float] = Field(None, description="Credit spread over risk-free rate")
    
    # Capital structure
    debt_to_total_capital: float = Field(..., ge=0.0, le=1.0, description="Debt weight in capital structure")
    equity_to_total_capital: float = Field(..., ge=0.0, le=1.0, description="Equity weight in capital structure")
    tax_rate: float = Field(..., ge=0.0, le=1.0, description="Tax rate for debt tax shield")
    
    # Final WACC
    wacc: float = Field(..., description="Weighted average cost of capital")
    wacc_terminal: Optional[float] = Field(None, description="Terminal period WACC if different")
    
    @model_validator(mode='after')
    def validate_capital_structure(self):
        """Ensure capital structure weights sum to 1."""
        total_weight = self.debt_to_total_capital + self.equity_to_total_capital
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Capital structure weights must sum to 1.0, got {total_weight}")
        return self


class PeerAnalysis(BaseModel):
    """Complete peer analysis results."""
    target_ticker: str = Field(..., description="Target company ticker")
    analysis_date: str = Field(..., description="Analysis date (YYYY-MM-DD)")
    
    # Selection process
    selection_criteria: PeerSelectionCriteria = Field(..., description="Criteria used for peer selection")
    peer_companies: List[PeerCompany] = Field(..., description="Selected peer companies")
    
    # Industry statistics
    industry_statistics: IndustryStatistics = Field(..., description="Industry-level statistics")
    
    # WACC calculation
    wacc_calculation: WACCCalculation = Field(..., description="Bottom-up WACC calculation")
    
    # Quality metrics
    selection_quality: str = Field(..., description="Quality assessment of peer selection")
    data_coverage: float = Field(..., ge=0.0, le=1.0, description="Data completeness across peers")
    outliers_removed: int = Field(default=0, description="Number of outliers removed")
    
    # FX normalization details
    fx_normalization: Dict[str, float] = Field(default_factory=dict, description="FX rates used for normalization")
    
    @field_validator('peer_companies')
    @classmethod
    def validate_minimum_peers(cls, v):
        """Ensure minimum peer count."""
        if len(v) < 3:
            raise ValueError("At least 3 peer companies required for valid analysis")
        return v
    
    @field_validator('analysis_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class ComparablesValidation(BaseModel):
    """Validation results for comparables analysis."""
    target_ticker: str = Field(..., description="Target company ticker")
    validation_date: str = Field(..., description="Validation date")
    
    # Validation results
    peer_selection_valid: bool = Field(..., description="Peer selection meets criteria")
    multiples_reasonable: bool = Field(..., description="Target multiples vs peers reasonable")
    wacc_reasonable: bool = Field(..., description="WACC calculation reasonable")
    data_quality_adequate: bool = Field(..., description="Data quality adequate")
    
    # Specific checks
    validation_checks: Dict[str, bool] = Field(default_factory=dict, description="Detailed validation results")
    validation_warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    validation_errors: List[str] = Field(default_factory=list, description="Critical errors")
    
    # Overall assessment
    overall_quality: Literal["excellent", "good", "acceptable", "poor"] = Field(..., description="Overall quality rating")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in analysis (0-1)")
    
    @field_validator('validation_checks')
    @classmethod
    def validate_required_checks(cls, v):
        """Ensure key validation checks are present."""
        required_checks = [
            "peer_count_adequate",
            "multiples_within_range", 
            "beta_reasonable",
            "wacc_within_bounds",
            "data_coverage_sufficient"
        ]
        
        for check in required_checks:
            if check not in v:
                v[check] = False
        
        return v