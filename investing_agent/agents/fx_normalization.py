from __future__ import annotations

"""
FX Normalization for International Comparables

Implements currency conversion and purchasing power parity adjustments for 
cross-border comparable company analysis with regional cost of capital adjustments.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from investing_agent.schemas.comparables import PeerCompany, CompanyMultiples


@dataclass
class FXRate:
    """Foreign exchange rate data."""
    base_currency: str
    quote_currency: str
    rate: float
    date: str
    source: str = "market_data"
    is_ppp_adjusted: bool = False


@dataclass
class CountryRiskProfile:
    """Country-specific risk and economic data."""
    country_code: str
    country_name: str
    currency: str
    
    # Risk premiums (in decimal form)
    country_risk_premium: float = 0.0
    equity_risk_premium: float = 0.055  # Base ERP
    
    # Economic indicators
    inflation_rate: Optional[float] = None
    government_bond_yield: Optional[float] = None
    credit_rating: Optional[str] = None
    
    # PPP adjustments
    ppp_conversion_factor: float = 1.0
    cost_of_living_index: float = 100.0


class FXNormalizationEngine:
    """Engine for FX normalization and PPP adjustments."""
    
    def __init__(self, base_currency: str = "USD", valuation_date: Optional[str] = None):
        """Initialize FX normalization engine.
        
        Args:
            base_currency: Base currency for normalization (default: USD)
            valuation_date: Date for FX rates (default: current date)
        """
        self.base_currency = base_currency
        self.valuation_date = valuation_date or datetime.now().strftime("%Y-%m-%d")
        
        # Load default FX rates and country data
        self.fx_rates = self._load_default_fx_rates()
        self.country_profiles = self._load_country_profiles()
        
        print(f"💱 FX Normalization Engine initialized")
        print(f"   Base Currency: {base_currency}")
        print(f"   Valuation Date: {self.valuation_date}")
        print(f"   FX Rates: {len(self.fx_rates)} currency pairs")
        print(f"   Country Profiles: {len(self.country_profiles)} countries")
    
    def normalize_peer_companies(
        self, 
        peer_companies: List[PeerCompany],
        apply_ppp_adjustment: bool = True,
        apply_regional_adjustments: bool = True
    ) -> Tuple[List[PeerCompany], Dict[str, float]]:
        """Normalize peer companies to base currency with adjustments.
        
        Args:
            peer_companies: List of peer companies to normalize
            apply_ppp_adjustment: Whether to apply PPP adjustments
            apply_regional_adjustments: Whether to apply regional cost adjustments
            
        Returns:
            Tuple of (normalized peers, FX rates used)
        """
        normalized_peers = []
        fx_rates_used = {}
        
        print(f"💱 Normalizing {len(peer_companies)} peer companies to {self.base_currency}")
        
        for peer in peer_companies:
            if peer.currency == self.base_currency:
                # No conversion needed
                normalized_peer = peer.model_copy()
                normalized_peers.append(normalized_peer)
                continue
            
            # Get FX rate for conversion
            fx_rate = self._get_fx_rate(peer.currency, self.base_currency)
            if fx_rate is None:
                print(f"   ⚠️  No FX rate available for {peer.currency}, skipping {peer.ticker}")
                continue
            
            fx_rates_used[f"{peer.currency}/{self.base_currency}"] = fx_rate.rate
            
            # Apply currency conversion
            normalized_peer = self._convert_peer_currency(peer, fx_rate)
            
            # Apply PPP adjustments if requested
            if apply_ppp_adjustment:
                normalized_peer = self._apply_ppp_adjustment(normalized_peer)
            
            # Apply regional cost of capital adjustments if requested
            if apply_regional_adjustments:
                normalized_peer = self._apply_regional_adjustments(normalized_peer)
            
            normalized_peers.append(normalized_peer)
            
            print(f"   ✓ {peer.ticker} ({peer.currency}→{self.base_currency}): Rate {fx_rate.rate:.4f}")
        
        print(f"   📊 Normalized {len(normalized_peers)}/{len(peer_companies)} peers successfully")
        
        return normalized_peers, fx_rates_used
    
    def _get_fx_rate(self, from_currency: str, to_currency: str) -> Optional[FXRate]:
        """Get FX rate for currency conversion."""
        
        # Direct rate lookup
        direct_key = f"{from_currency}/{to_currency}"
        if direct_key in self.fx_rates:
            return self.fx_rates[direct_key]
        
        # Inverse rate lookup
        inverse_key = f"{to_currency}/{from_currency}"
        if inverse_key in self.fx_rates:
            inverse_rate = self.fx_rates[inverse_key]
            return FXRate(
                base_currency=from_currency,
                quote_currency=to_currency,
                rate=1.0 / inverse_rate.rate,
                date=inverse_rate.date,
                source=inverse_rate.source,
                is_ppp_adjusted=inverse_rate.is_ppp_adjusted
            )
        
        # Cross-rate calculation via USD
        if from_currency != "USD" and to_currency != "USD":
            usd_from_key = f"{from_currency}/USD"
            usd_to_key = f"USD/{to_currency}"
            
            if usd_from_key in self.fx_rates and usd_to_key in self.fx_rates:
                rate1 = self.fx_rates[usd_from_key].rate
                rate2 = self.fx_rates[usd_to_key].rate
                cross_rate = rate1 * rate2
                
                return FXRate(
                    base_currency=from_currency,
                    quote_currency=to_currency,
                    rate=cross_rate,
                    date=self.valuation_date,
                    source="cross_rate_calculation"
                )
        
        return None
    
    def _convert_peer_currency(self, peer: PeerCompany, fx_rate: FXRate) -> PeerCompany:
        """Convert peer company financials to base currency."""
        
        # Create a copy of the peer
        normalized_peer = peer.model_copy(deep=True)
        
        # Convert size metrics
        if peer.market_cap:
            normalized_peer.market_cap = peer.market_cap * fx_rate.rate
        
        if peer.enterprise_value:
            normalized_peer.enterprise_value = peer.enterprise_value * fx_rate.rate
        
        if peer.revenue_ttm:
            normalized_peer.revenue_ttm = peer.revenue_ttm * fx_rate.rate
        
        # Update currency
        normalized_peer.currency = self.base_currency
        
        # Note: Multiples (P/E, EV/EBITDA, etc.) don't need FX conversion as they are ratios
        # However, we may need to adjust for different accounting standards or market practices
        
        return normalized_peer
    
    def _apply_ppp_adjustment(self, peer: PeerCompany) -> PeerCompany:
        """Apply purchasing power parity adjustments."""
        
        country_profile = self.country_profiles.get(peer.country)
        if not country_profile or country_profile.ppp_conversion_factor == 1.0:
            return peer
        
        # Apply PPP adjustment to size metrics
        ppp_factor = country_profile.ppp_conversion_factor
        
        adjusted_peer = peer.model_copy(deep=True)
        
        if peer.market_cap:
            adjusted_peer.market_cap = peer.market_cap * ppp_factor
        
        if peer.enterprise_value:
            adjusted_peer.enterprise_value = peer.enterprise_value * ppp_factor
        
        if peer.revenue_ttm:
            adjusted_peer.revenue_ttm = peer.revenue_ttm * ppp_factor
        
        print(f"      PPP adjustment for {peer.country}: {ppp_factor:.3f}")
        
        return adjusted_peer
    
    def _apply_regional_adjustments(self, peer: PeerCompany) -> PeerCompany:
        """Apply regional cost of capital and market adjustments."""
        
        country_profile = self.country_profiles.get(peer.country)
        if not country_profile:
            return peer
        
        # For now, we don't adjust the multiples themselves but could apply
        # regional discount/premium factors based on:
        # - Different accounting standards
        # - Market liquidity differences
        # - Regulatory environment differences
        # - Market maturity factors
        
        # This is primarily for future enhancement
        # The country risk premium will be used in WACC calculations
        
        return peer
    
    def get_country_risk_premium(self, country: str) -> float:
        """Get country risk premium for WACC calculations."""
        country_profile = self.country_profiles.get(country)
        if country_profile:
            return country_profile.country_risk_premium
        
        # Default risk premium for unknown countries
        return 0.01  # 100bps default
    
    def validate_fx_normalization(
        self, 
        original_peers: List[PeerCompany],
        normalized_peers: List[PeerCompany],
        fx_rates_used: Dict[str, float]
    ) -> Dict[str, bool]:
        """Validate FX normalization results."""
        
        validation_results = {
            "peer_count_preserved": len(original_peers) >= len(normalized_peers),
            "all_currencies_normalized": True,
            "fx_rates_reasonable": True,
            "size_metrics_scaled": True
        }
        
        # Check all currencies normalized to base currency
        for peer in normalized_peers:
            if peer.currency != self.base_currency:
                validation_results["all_currencies_normalized"] = False
                break
        
        # Check FX rates are reasonable (between 0.001 and 1000)
        for pair, rate in fx_rates_used.items():
            if rate < 0.001 or rate > 1000:
                validation_results["fx_rates_reasonable"] = False
                print(f"   ⚠️  Unusual FX rate: {pair} = {rate}")
        
        # Check size metrics were properly scaled
        for original, normalized in zip(original_peers, normalized_peers):
            if (original.market_cap and normalized.market_cap and
                original.currency != normalized.currency):
                # Size should have changed due to FX conversion
                if abs(original.market_cap - normalized.market_cap) < 0.01 * original.market_cap:
                    validation_results["size_metrics_scaled"] = False
                    break
        
        return validation_results
    
    def _load_default_fx_rates(self) -> Dict[str, FXRate]:
        """Load default FX rates for major currencies."""
        
        # In production, this would fetch from market data APIs
        # For now, using representative rates as of early 2024
        
        fx_data = {
            "EUR/USD": 1.0850,
            "GBP/USD": 1.2650,
            "JPY/USD": 0.0067,  # 1 USD = ~149 JPY
            "CAD/USD": 0.7400,
            "AUD/USD": 0.6600,
            "CHF/USD": 1.0800,
            "SEK/USD": 0.0950,
            "NOK/USD": 0.0920,
            "DKK/USD": 0.1455,
            "CNY/USD": 0.1380,  # 1 USD = ~7.25 CNY
            "INR/USD": 0.0120,  # 1 USD = ~83 INR
            "BRL/USD": 0.2000,  # 1 USD = ~5 BRL
            "KRW/USD": 0.0007,  # 1 USD = ~1300 KRW
            "HKD/USD": 0.1280,  # 1 USD = ~7.8 HKD
            "SGD/USD": 0.7350,
            "MXN/USD": 0.0580,  # 1 USD = ~17 MXN
        }
        
        fx_rates = {}
        for pair, rate in fx_data.items():
            base, quote = pair.split("/")
            fx_rates[pair] = FXRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                date=self.valuation_date,
                source="default_rates"
            )
        
        return fx_rates
    
    def _load_country_profiles(self) -> Dict[str, CountryRiskProfile]:
        """Load country risk profiles and PPP data."""
        
        # In production, this would load from economic databases
        # Using representative data for major markets
        
        country_data = {
            "US": CountryRiskProfile(
                country_code="US",
                country_name="United States",
                currency="USD",
                country_risk_premium=0.0,
                equity_risk_premium=0.055,
                ppp_conversion_factor=1.0,
                cost_of_living_index=100.0,
                credit_rating="AAA"
            ),
            "EU": CountryRiskProfile(
                country_code="EU",
                country_name="European Union",
                currency="EUR", 
                country_risk_premium=0.005,  # 50bps
                equity_risk_premium=0.060,
                ppp_conversion_factor=0.95,
                cost_of_living_index=95.0,
                credit_rating="AA+"
            ),
            "GB": CountryRiskProfile(
                country_code="GB", 
                country_name="United Kingdom",
                currency="GBP",
                country_risk_premium=0.008,  # 80bps
                equity_risk_premium=0.063,
                ppp_conversion_factor=0.92,
                cost_of_living_index=92.0,
                credit_rating="AA"
            ),
            "JP": CountryRiskProfile(
                country_code="JP",
                country_name="Japan", 
                currency="JPY",
                country_risk_premium=0.003,  # 30bps
                equity_risk_premium=0.058,
                ppp_conversion_factor=1.15,
                cost_of_living_index=115.0,
                credit_rating="A+"
            ),
            "CA": CountryRiskProfile(
                country_code="CA",
                country_name="Canada",
                currency="CAD",
                country_risk_premium=0.004,  # 40bps
                equity_risk_premium=0.059,
                ppp_conversion_factor=0.98,
                cost_of_living_index=98.0,
                credit_rating="AAA"
            ),
            "DE": CountryRiskProfile(
                country_code="DE",
                country_name="Germany",
                currency="EUR",
                country_risk_premium=0.003,  # 30bps
                equity_risk_premium=0.058,
                ppp_conversion_factor=0.94,
                cost_of_living_index=94.0,
                credit_rating="AAA"
            ),
            "FR": CountryRiskProfile(
                country_code="FR",
                country_name="France", 
                currency="EUR",
                country_risk_premium=0.006,  # 60bps
                equity_risk_premium=0.061,
                ppp_conversion_factor=0.93,
                cost_of_living_index=93.0,
                credit_rating="AA"
            ),
            "CN": CountryRiskProfile(
                country_code="CN",
                country_name="China",
                currency="CNY",
                country_risk_premium=0.025,  # 250bps
                equity_risk_premium=0.080,
                ppp_conversion_factor=1.8,   # Higher PPP adjustment for China
                cost_of_living_index=180.0,
                credit_rating="A+"
            ),
            "IN": CountryRiskProfile(
                country_code="IN",
                country_name="India",
                currency="INR", 
                country_risk_premium=0.030,  # 300bps
                equity_risk_premium=0.085,
                ppp_conversion_factor=2.2,   # Higher PPP adjustment for India
                cost_of_living_index=220.0,
                credit_rating="BBB-"
            ),
        }
        
        return country_data
    
    def get_summary_report(
        self, 
        fx_rates_used: Dict[str, float],
        peer_count_by_currency: Dict[str, int]
    ) -> str:
        """Generate summary report of FX normalization."""
        
        report_lines = [
            f"FX Normalization Summary (Base: {self.base_currency})",
            "=" * 50,
            f"Valuation Date: {self.valuation_date}",
            f"Total Currency Pairs: {len(fx_rates_used)}",
            ""
        ]
        
        # FX rates used
        if fx_rates_used:
            report_lines.append("FX Rates Applied:")
            for pair, rate in sorted(fx_rates_used.items()):
                report_lines.append(f"  {pair}: {rate:.4f}")
            report_lines.append("")
        
        # Peer distribution by currency
        if peer_count_by_currency:
            report_lines.append("Peer Distribution by Currency:")
            for currency, count in sorted(peer_count_by_currency.items()):
                report_lines.append(f"  {currency}: {count} peers")
            report_lines.append("")
        
        # Available country risk premiums
        report_lines.append("Country Risk Premiums:")
        for country, profile in sorted(self.country_profiles.items()):
            crp_bps = profile.country_risk_premium * 10000
            report_lines.append(f"  {country}: {crp_bps:.0f}bps")
        
        return "\n".join(report_lines)


def normalize_international_peers(
    peer_companies: List[PeerCompany],
    base_currency: str = "USD",
    apply_ppp: bool = True
) -> Tuple[List[PeerCompany], Dict[str, float]]:
    """Convenience function for normalizing international peer companies.
    
    Args:
        peer_companies: List of peer companies to normalize
        base_currency: Base currency for normalization
        apply_ppp: Whether to apply PPP adjustments
        
    Returns:
        Tuple of (normalized peers, FX rates used)
    """
    engine = FXNormalizationEngine(base_currency=base_currency)
    return engine.normalize_peer_companies(
        peer_companies, 
        apply_ppp_adjustment=apply_ppp,
        apply_regional_adjustments=True
    )