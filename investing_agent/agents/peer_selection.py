from __future__ import annotations

"""
Automatic Peer Selection Agent

Implements deterministic peer selection algorithm using SIC codes, market cap,
and geographic filtering to identify comparable companies for valuation analysis.
"""

import re
import statistics
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

from investing_agent.schemas.comparables import (
    PeerSelectionCriteria, PeerCompany, CompanyMultiples, PeerAnalysis,
    IndustryStatistics
)


@dataclass
class CompanyScreeningData:
    """Raw company data for screening and selection."""
    ticker: str
    company_name: str
    sic_code: str
    country: str = "US"
    currency: str = "USD"
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    revenue_ttm: Optional[float] = None
    beta_levered: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_sales: Optional[float] = None
    debt_to_equity: Optional[float] = None
    is_penny_stock: bool = False
    is_recent_bankruptcy: bool = False
    data_quality: str = "good"


class PeerSelectionEngine:
    """Engine for automatic peer company selection."""
    
    def __init__(self, company_database: Optional[List[CompanyScreeningData]] = None):
        """Initialize peer selection engine.
        
        Args:
            company_database: Optional database of companies. If None, uses built-in data.
        """
        self.company_database = company_database or self._load_default_database()
    
    def select_peers(
        self, 
        target_ticker: str,
        target_sic_code: str,
        target_market_cap: Optional[float] = None,
        min_peers: int = 5,
        max_peers: int = 15,
        geographic_focus: str = "Global"
    ) -> PeerAnalysis:
        """Select peer companies using multi-stage filtering algorithm.
        
        Args:
            target_ticker: Target company ticker
            target_sic_code: Target company SIC code (4-digit preferred)
            target_market_cap: Target company market cap for size filtering
            min_peers: Minimum number of peers required
            max_peers: Maximum number of peers to select
            geographic_focus: Geographic focus ("US", "Global", "Region")
            
        Returns:
            Complete peer analysis with selected companies and statistics
        """
        print(f"🔍 Starting peer selection for {target_ticker}")
        
        # Step 1: Create selection criteria
        criteria = self._create_selection_criteria(
            target_ticker, target_sic_code, target_market_cap,
            min_peers, max_peers, geographic_focus
        )
        
        # Step 2: Multi-stage filtering
        candidate_pool = self._filter_candidate_pool(target_ticker, criteria)
        print(f"   📊 Initial candidate pool: {len(candidate_pool)} companies")
        
        # Step 3: SIC code matching (progressive relaxation)
        sic_matched = self._sic_code_matching(candidate_pool, target_sic_code, min_peers)
        print(f"   🎯 SIC-matched candidates: {len(sic_matched)} companies")
        
        # Step 4: Market cap filtering
        size_filtered = self._market_cap_filtering(sic_matched, target_market_cap, criteria)
        print(f"   📏 Size-filtered candidates: {len(size_filtered)} companies")
        
        # Step 5: Geographic filtering
        geo_filtered = self._geographic_filtering(size_filtered, geographic_focus)
        print(f"   🌍 Geographic-filtered candidates: {len(geo_filtered)} companies")
        
        # Step 6: Quality and exclusion filtering
        quality_filtered = self._quality_filtering(geo_filtered)
        print(f"   ✨ Quality-filtered candidates: {len(quality_filtered)} companies")
        
        # Step 7: Final selection and ranking
        selected_peers = self._final_peer_selection(
            quality_filtered, target_ticker, target_market_cap, min_peers, max_peers
        )
        print(f"   🏆 Final peer selection: {len(selected_peers)} companies")
        
        # Step 8: Calculate industry statistics
        industry_stats = self._calculate_industry_statistics(selected_peers)
        
        # Step 9: Create peer analysis
        peer_analysis = PeerAnalysis(
            target_ticker=target_ticker,
            analysis_date="2024-01-15",  # In production, use actual date
            selection_criteria=criteria,
            peer_companies=selected_peers,
            industry_statistics=industry_stats,
            wacc_calculation=self._placeholder_wacc_calculation(),  # Will be implemented in Task 5
            selection_quality=self._assess_selection_quality(selected_peers),
            data_coverage=self._calculate_data_coverage(selected_peers),
            outliers_removed=0  # Will be implemented with winsorization
        )
        
        return peer_analysis
    
    def _create_selection_criteria(
        self, 
        target_ticker: str, 
        target_sic_code: str,
        target_market_cap: Optional[float],
        min_peers: int,
        max_peers: int, 
        geographic_focus: str
    ) -> PeerSelectionCriteria:
        """Create comprehensive selection criteria."""
        
        # Determine market cap range
        if target_market_cap:
            market_cap_range = (
                target_market_cap * 0.5,  # 0.5x to 2x range
                target_market_cap * 2.0
            )
        else:
            market_cap_range = (100.0, 1000000.0)  # $100M to $1T range
        
        # Build SIC code hierarchy
        sic_codes = self._build_sic_hierarchy(target_sic_code)
        
        return PeerSelectionCriteria(
            target_ticker=target_ticker,
            target_market_cap=target_market_cap,
            sic_codes=sic_codes,
            market_cap_range=market_cap_range,
            geographic_focus=geographic_focus,
            min_peer_count=min_peers,
            max_peer_count=max_peers,
            exclusions=["penny_stocks", "recent_bankruptcies", "extreme_outliers"]
        )
    
    def _build_sic_hierarchy(self, target_sic_code: str) -> List[str]:
        """Build SIC code hierarchy for progressive matching."""
        sic_codes = []
        
        if len(target_sic_code) >= 4:
            sic_codes.append(target_sic_code[:4])  # 4-digit exact match
        if len(target_sic_code) >= 3:
            sic_codes.append(target_sic_code[:3])  # 3-digit industry group
        if len(target_sic_code) >= 2:
            sic_codes.append(target_sic_code[:2])  # 2-digit major group
            
        return sic_codes
    
    def _filter_candidate_pool(
        self, 
        target_ticker: str, 
        criteria: PeerSelectionCriteria
    ) -> List[CompanyScreeningData]:
        """Filter initial candidate pool excluding target and basic criteria."""
        candidates = []
        
        for company in self.company_database:
            # Exclude target company
            if company.ticker == target_ticker:
                continue
                
            # Basic exclusions
            if company.is_penny_stock or company.is_recent_bankruptcy:
                continue
                
            # Data quality requirements
            if company.data_quality not in ["good", "excellent"]:
                continue
                
            candidates.append(company)
        
        return candidates
    
    def _sic_code_matching(
        self, 
        candidates: List[CompanyScreeningData], 
        target_sic_code: str,
        min_peers: int
    ) -> List[CompanyScreeningData]:
        """Apply SIC code matching with progressive relaxation."""
        sic_hierarchy = self._build_sic_hierarchy(target_sic_code)
        
        for sic_level in sic_hierarchy:
            matches = [c for c in candidates if c.sic_code.startswith(sic_level)]
            
            if len(matches) >= min_peers:
                print(f"      Using {len(sic_level)}-digit SIC matching: {sic_level}")
                return matches
        
        # If no SIC level provides enough matches, return best available
        print(f"      Warning: Insufficient SIC matches, using all candidates")
        return candidates
    
    def _market_cap_filtering(
        self, 
        candidates: List[CompanyScreeningData],
        target_market_cap: Optional[float],
        criteria: PeerSelectionCriteria
    ) -> List[CompanyScreeningData]:
        """Filter candidates by market capitalization range."""
        if not target_market_cap:
            return candidates
            
        min_cap, max_cap = criteria.market_cap_range
        
        size_filtered = []
        for candidate in candidates:
            if candidate.market_cap is None:
                continue
                
            if min_cap <= candidate.market_cap <= max_cap:
                size_filtered.append(candidate)
        
        # If size filtering is too restrictive, relax constraints
        if len(size_filtered) < criteria.min_peer_count:
            print(f"      Size filter too restrictive, expanding range")
            # Expand to 0.2x - 5x range
            expanded_min = target_market_cap * 0.2
            expanded_max = target_market_cap * 5.0
            
            size_filtered = [
                c for c in candidates 
                if c.market_cap and expanded_min <= c.market_cap <= expanded_max
            ]
        
        return size_filtered
    
    def _geographic_filtering(
        self, 
        candidates: List[CompanyScreeningData],
        geographic_focus: str
    ) -> List[CompanyScreeningData]:
        """Apply geographic filtering based on focus."""
        if geographic_focus == "Global":
            return candidates
        elif geographic_focus == "US":
            return [c for c in candidates if c.country == "US"]
        else:
            # For other regions, return all (would implement region mapping in production)
            return candidates
    
    def _quality_filtering(
        self, 
        candidates: List[CompanyScreeningData]
    ) -> List[CompanyScreeningData]:
        """Apply quality filtering and outlier detection."""
        quality_filtered = []
        
        # Collect market caps for outlier detection
        market_caps = [c.market_cap for c in candidates if c.market_cap]
        
        if len(market_caps) > 3:
            # Calculate 3-sigma bounds for market cap outlier detection
            mean_cap = statistics.mean(market_caps)
            std_cap = statistics.stdev(market_caps) if len(market_caps) > 1 else 0
            
            outlier_threshold = 3.0
            lower_bound = mean_cap - outlier_threshold * std_cap
            upper_bound = mean_cap + outlier_threshold * std_cap
            
            for candidate in candidates:
                if candidate.market_cap is None:
                    quality_filtered.append(candidate)
                elif lower_bound <= candidate.market_cap <= upper_bound:
                    quality_filtered.append(candidate)
                # Else: exclude as outlier
        else:
            quality_filtered = candidates
        
        return quality_filtered
    
    def _final_peer_selection(
        self,
        candidates: List[CompanyScreeningData],
        target_ticker: str,
        target_market_cap: Optional[float],
        min_peers: int,
        max_peers: int
    ) -> List[PeerCompany]:
        """Final peer selection and ranking."""
        
        # Calculate similarity scores
        scored_candidates = []
        for candidate in candidates:
            similarity = self._calculate_similarity_score(candidate, target_market_cap)
            scored_candidates.append((candidate, similarity))
        
        # Sort by similarity score (descending)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select top peers within limits
        selected_count = min(len(scored_candidates), max_peers)
        selected_count = max(selected_count, min_peers if len(scored_candidates) >= min_peers else len(scored_candidates))
        
        selected_peers = []
        for i in range(selected_count):
            candidate, similarity = scored_candidates[i]
            
            peer = PeerCompany(
                ticker=candidate.ticker,
                company_name=candidate.company_name,
                sic_code=candidate.sic_code,
                country=candidate.country,
                currency=candidate.currency,
                market_cap=candidate.market_cap,
                enterprise_value=candidate.enterprise_value,
                revenue_ttm=candidate.revenue_ttm,
                beta_levered=candidate.beta_levered,
                multiples=CompanyMultiples(
                    pe_ratio=candidate.pe_ratio,
                    ev_ebitda=candidate.ev_ebitda,
                    ev_sales=candidate.ev_sales,
                    debt_to_equity=candidate.debt_to_equity,
                    data_quality=candidate.data_quality
                ),
                selection_reason=f"SIC {candidate.sic_code}, similar size, quality data",
                similarity_score=similarity
            )
            
            selected_peers.append(peer)
        
        return selected_peers
    
    def _calculate_similarity_score(
        self, 
        candidate: CompanyScreeningData, 
        target_market_cap: Optional[float]
    ) -> float:
        """Calculate similarity score for candidate ranking."""
        score = 0.0
        
        # Size similarity (40% weight)
        if target_market_cap and candidate.market_cap:
            size_ratio = min(target_market_cap, candidate.market_cap) / max(target_market_cap, candidate.market_cap)
            score += 0.4 * size_ratio
        else:
            score += 0.2  # Partial credit if size data missing
        
        # Data quality (30% weight)
        quality_scores = {"excellent": 1.0, "good": 0.8, "fair": 0.5, "poor": 0.2}
        score += 0.3 * quality_scores.get(candidate.data_quality, 0.5)
        
        # Data completeness (20% weight)
        completeness = sum([
            1 if candidate.market_cap is not None else 0,
            1 if candidate.revenue_ttm is not None else 0,
            1 if candidate.beta_levered is not None else 0,
            1 if candidate.pe_ratio is not None else 0,
            1 if candidate.ev_ebitda is not None else 0
        ]) / 5.0
        score += 0.2 * completeness
        
        # Geographic preference (10% weight)
        if candidate.country == "US":
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_industry_statistics(
        self, 
        peers: List[PeerCompany]
    ) -> IndustryStatistics:
        """Calculate industry-level statistics using winsorized multiples."""
        
        # Use winsorized multiples calculation for robust statistics
        from investing_agent.agents.multiples_calculation import calculate_winsorized_multiples
        
        print(f"   📊 Calculating winsorized industry statistics...")
        multiple_stats, industry_stats = calculate_winsorized_multiples(peers)
        
        # Add beta statistics (placeholder - will be enhanced in Task 4)
        beta_values = [p.beta_levered for p in peers if p.beta_levered]
        if beta_values:
            # Convert to unlevered betas (simplified calculation)
            unlevered_betas = [b * 0.7 for b in beta_values]  # Rough approximation
            industry_stats.beta_unlevered_median = statistics.median(unlevered_betas)
            industry_stats.beta_unlevered_mean = statistics.mean(unlevered_betas)
            industry_stats.beta_unlevered_std = statistics.stdev(unlevered_betas) if len(unlevered_betas) > 1 else 0
        
        return industry_stats
    
    def _assess_selection_quality(self, peers: List[PeerCompany]) -> str:
        """Assess overall quality of peer selection."""
        if len(peers) >= 8:
            return "excellent"
        elif len(peers) >= 5:
            return "good"
        elif len(peers) >= 3:
            return "acceptable"
        else:
            return "poor"
    
    def _calculate_data_coverage(self, peers: List[PeerCompany]) -> float:
        """Calculate data completeness across peer group."""
        if not peers:
            return 0.0
        
        total_fields = 0
        complete_fields = 0
        
        for peer in peers:
            fields_to_check = [
                peer.market_cap,
                peer.enterprise_value,
                peer.revenue_ttm,
                peer.beta_levered,
                peer.multiples.pe_ratio,
                peer.multiples.ev_ebitda,
                peer.multiples.ev_sales
            ]
            
            total_fields += len(fields_to_check)
            complete_fields += sum(1 for field in fields_to_check if field is not None)
        
        return complete_fields / total_fields if total_fields > 0 else 0.0
    
    def _placeholder_wacc_calculation(self):
        """Placeholder WACC calculation - will be implemented in Task 5."""
        from investing_agent.schemas.comparables import WACCCalculation
        
        return WACCCalculation(
            bottom_up_beta_unlevered=1.0,
            bottom_up_beta_levered=1.2,
            beta_source="bottom_up",
            risk_free_rate=0.035,
            equity_risk_premium=0.055,
            cost_of_equity=0.101,
            cost_of_debt=0.045,
            debt_to_total_capital=0.3,
            equity_to_total_capital=0.7,
            tax_rate=0.25,
            wacc=0.084
        )
    
    def _load_default_database(self) -> List[CompanyScreeningData]:
        """Load default company database for peer selection."""
        # In production, this would load from external data sources
        # For now, return sample data for testing
        
        return [
            CompanyScreeningData(
                ticker="AAPL",
                company_name="Apple Inc",
                sic_code="3571",
                market_cap=3000000,
                enterprise_value=3000000,
                revenue_ttm=365000,
                beta_levered=1.2,
                pe_ratio=25.0,
                ev_ebitda=20.0,
                ev_sales=8.2,
                debt_to_equity=0.3
            ),
            CompanyScreeningData(
                ticker="MSFT", 
                company_name="Microsoft Corp",
                sic_code="7372",
                market_cap=2800000,
                enterprise_value=2750000,
                revenue_ttm=211000,
                beta_levered=0.9,
                pe_ratio=28.0,
                ev_ebitda=22.0,
                ev_sales=13.0,
                debt_to_equity=0.25
            ),
            CompanyScreeningData(
                ticker="GOOGL",
                company_name="Alphabet Inc",
                sic_code="7372",
                market_cap=1600000,
                enterprise_value=1550000,
                revenue_ttm=282000,
                beta_levered=1.1,
                pe_ratio=22.0,
                ev_ebitda=15.5,
                ev_sales=5.5,
                debt_to_equity=0.1
            ),
            CompanyScreeningData(
                ticker="META",
                company_name="Meta Platforms Inc",
                sic_code="7372",
                market_cap=900000,
                enterprise_value=850000,
                revenue_ttm=134000,
                beta_levered=1.3,
                pe_ratio=24.0,
                ev_ebitda=16.0,
                ev_sales=6.3,
                debt_to_equity=0.05
            ),
            CompanyScreeningData(
                ticker="ORCL",
                company_name="Oracle Corp",
                sic_code="7372", 
                market_cap=320000,
                enterprise_value=350000,
                revenue_ttm=50000,
                beta_levered=1.0,
                pe_ratio=18.0,
                ev_ebitda=12.0,
                ev_sales=7.0,
                debt_to_equity=0.4
            ),
            CompanyScreeningData(
                ticker="CRM",
                company_name="Salesforce Inc",
                sic_code="7372",
                market_cap=220000,
                enterprise_value=240000,
                revenue_ttm=31000,
                beta_levered=1.4,
                pe_ratio=50.0,
                ev_ebitda=35.0,
                ev_sales=7.7,
                debt_to_equity=0.1
            ),
            CompanyScreeningData(
                ticker="ADBE",
                company_name="Adobe Inc",
                sic_code="7372",
                market_cap=210000,
                enterprise_value=205000,
                revenue_ttm=19400,
                beta_levered=1.1,
                pe_ratio=32.0,
                ev_ebitda=25.0,
                ev_sales=10.6,
                debt_to_equity=0.15
            ),
            # Add some different industry companies
            CompanyScreeningData(
                ticker="JPM",
                company_name="JPMorgan Chase & Co",
                sic_code="6021",
                market_cap=450000,
                enterprise_value=450000,
                revenue_ttm=128000,
                beta_levered=1.1,
                pe_ratio=12.0,
                ev_ebitda=None,  # Banks don't use EBITDA
                ev_sales=None,
                debt_to_equity=1.5
            ),
            CompanyScreeningData(
                ticker="JNJ",
                company_name="Johnson & Johnson",
                sic_code="2834",
                market_cap=450000,
                enterprise_value=470000,
                revenue_ttm=94000,
                beta_levered=0.7,
                pe_ratio=15.0,
                ev_ebitda=12.0,
                ev_sales=5.0,
                debt_to_equity=0.2
            )
        ]


def select_peers_for_company(
    target_ticker: str,
    target_sic_code: str,
    target_market_cap: Optional[float] = None,
    min_peers: int = 5,
    max_peers: int = 12
) -> PeerAnalysis:
    """Convenience function for peer selection.
    
    Args:
        target_ticker: Target company ticker
        target_sic_code: Target company SIC code
        target_market_cap: Target company market cap
        min_peers: Minimum peers required
        max_peers: Maximum peers to select
        
    Returns:
        Complete peer analysis
    """
    engine = PeerSelectionEngine()
    return engine.select_peers(
        target_ticker=target_ticker,
        target_sic_code=target_sic_code,
        target_market_cap=target_market_cap,
        min_peers=min_peers,
        max_peers=max_peers
    )