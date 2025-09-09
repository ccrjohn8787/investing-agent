"""
Test Suite for Beta Calculation Module

Tests bottom-up beta calculation from peer companies including
unlevered beta calculation, peer aggregation, and re-levering.
"""

import pytest
from investing_agent.agents.beta_calculation import (
    BetaCalculator, 
    BetaCalculationMethod,
    calculate_bottom_up_beta
)
from investing_agent.schemas.comparables import PeerCompany, CompanyMultiples


class TestBetaCalculator:
    """Test beta calculation functionality."""
    
    def test_bottom_up_beta_calculation(self):
        """Test basic bottom-up beta calculation from peers."""
        calculator = BetaCalculator()
        
        # Create test peer companies
        peers = [
            PeerCompany(
                ticker="PEER1",
                company_name="Peer Company 1", 
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.2,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ),
            PeerCompany(
                ticker="PEER2",
                company_name="Peer Company 2",
                sic_code="3571", 
                market_cap=8000.0,
                enterprise_value=9500.0,
                beta_levered=1.5,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ),
            PeerCompany(
                ticker="PEER3",
                company_name="Peer Company 3",
                sic_code="3571",
                market_cap=3000.0,
                enterprise_value=3600.0,
                beta_levered=0.8,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match", 
                country="US"
            )
        ]
        
        # Calculate beta statistics
        stats = calculator.calculate_bottom_up_beta(peers)
        
        # Verify results
        assert stats.sample_size == 3
        assert 0.5 < stats.selected_unlevered_beta < 1.5
        assert stats.calculation_method == BetaCalculationMethod.MEDIAN
        assert len(stats.raw_levered_betas) == 3
        assert len(stats.raw_unlevered_betas) == 3
        assert stats.quality_score in ["excellent", "good", "fair", "poor"]
    
    def test_beta_relevering(self):
        """Test beta re-levering for target company."""
        calculator = BetaCalculator()
        
        unlevered_beta = 1.0
        debt_to_equity = 0.5  # 50% D/E ratio
        tax_rate = 0.25       # 25% tax rate
        
        levered_beta = calculator.relever_beta(unlevered_beta, debt_to_equity, tax_rate)
        
        # Expected: 1.0 * [1 + (1-0.25) * 0.5] = 1.375
        expected = 1.0 * (1 + (1 - 0.25) * 0.5)
        assert abs(levered_beta - expected) < 0.01
        
    def test_outlier_handling(self):
        """Test outlier detection and removal in beta calculation."""
        calculator = BetaCalculator(outlier_sigma=2.0)
        
        # Include one outlier beta
        peers = [
            PeerCompany(
                ticker=f"PEER{i}",
                company_name=f"Peer Company {i}",
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.0 + i * 0.1 if i < 4 else 5.0,  # Last peer is outlier
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ) for i in range(5)
        ]
        
        stats = calculator.calculate_bottom_up_beta(peers)
        
        # The outlier beta (5.0) should be filtered out during validation
        # so it won't appear in the final calculation
        assert stats.sample_size == 4  # Should have 4 valid betas (excluding the 5.0 outlier)
        assert stats.selected_unlevered_beta < 1.5  # Result should be reasonable
    
    def test_different_calculation_methods(self):
        """Test different beta calculation methods."""
        calculator = BetaCalculator()
        
        peers = [
            PeerCompany(
                ticker=f"PEER{i}",
                company_name=f"Peer Company {i}",
                sic_code="3571",
                market_cap=5000.0 + i * 1000,  # Varying market caps
                enterprise_value=6000.0 + i * 2000,  # Varying enterprise values (affects D/E)
                beta_levered=0.8 + i * 0.2,  # Range from 0.8 to 1.6
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ) for i in range(5)
        ]
        
        # Test different methods
        methods = [
            BetaCalculationMethod.MEDIAN,
            BetaCalculationMethod.SIMPLE_MEAN,
            BetaCalculationMethod.WINSORIZED_MEAN,
            BetaCalculationMethod.TRIMMED_MEAN
        ]
        
        results = {}
        for method in methods:
            stats = calculator.calculate_bottom_up_beta(peers, method)
            results[method] = stats.selected_unlevered_beta
            assert stats.calculation_method == method
        
        # Results should be reasonable (may be similar for small datasets)
        assert all(0.3 < beta < 1.5 for beta in results.values())
        # Verify at least some methods were used
        assert len(results) == 4
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient beta data."""
        calculator = BetaCalculator()
        
        # Only one peer with valid beta
        peers = [
            PeerCompany(
                ticker="PEER1",
                company_name="Peer Company 1",
                sic_code="3571",
                market_cap=5000.0,
                beta_levered=1.2,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            )
        ]
        
        # Should raise error for insufficient data
        with pytest.raises(ValueError, match="Insufficient beta data"):
            calculator.calculate_bottom_up_beta(peers)
    
    def test_international_peers_tax_rates(self):
        """Test handling of international peers with different tax rates."""
        calculator = BetaCalculator()
        
        peers = [
            PeerCompany(
                ticker="US_PEER",
                company_name="US Company",
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.2,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ),
            PeerCompany(
                ticker="DE_PEER", 
                company_name="German Company",
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.1,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="DE"  # Higher tax rate
            ),
            PeerCompany(
                ticker="GB_PEER",
                company_name="UK Company", 
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.3,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="GB"
            )
        ]
        
        stats = calculator.calculate_bottom_up_beta(peers)
        
        # Should handle different tax rates appropriately
        assert stats.sample_size == 3
        assert 0.5 < stats.selected_unlevered_beta < 1.5
    
    def test_wacc_calculation_base(self):
        """Test WACC calculation base structure creation."""
        calculator = BetaCalculator()
        
        # Create mock beta statistics
        peers = [
            PeerCompany(
                ticker="PEER1",
                company_name="Peer Company 1",
                sic_code="3571", 
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.2,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ),
            PeerCompany(
                ticker="PEER2",
                company_name="Peer Company 2",
                sic_code="3571",
                market_cap=8000.0,
                enterprise_value=9500.0, 
                beta_levered=1.0,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            )
        ]
        
        # Add a third peer to meet minimum requirement
        peers.append(
            PeerCompany(
                ticker="PEER3",
                company_name="Peer Company 3",
                sic_code="3571",
                market_cap=7000.0,
                enterprise_value=8500.0,
                beta_levered=1.1,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            )
        )
        
        beta_stats = calculator.calculate_bottom_up_beta(peers)
        
        # Create WACC base
        wacc_base = calculator.create_wacc_calculation_base(
            beta_stats=beta_stats,
            target_debt_to_equity=0.3,
            target_tax_rate=0.25,
            risk_free_rate=0.04,
            equity_risk_premium=0.06,
            country_risk_premium=0.01
        )
        
        # Verify structure
        required_keys = [
            'bottom_up_beta_unlevered', 'bottom_up_beta_levered', 'beta_source',
            'cost_of_equity', 'risk_free_rate', 'equity_risk_premium', 
            'debt_to_total_capital', 'equity_to_total_capital', 'tax_rate'
        ]
        
        for key in required_keys:
            assert key in wacc_base
        
        # Verify calculations
        assert wacc_base['beta_source'] == 'bottom_up'
        assert 0.05 < wacc_base['cost_of_equity'] < 0.15  # Reasonable cost of equity
        assert abs(wacc_base['debt_to_total_capital'] + wacc_base['equity_to_total_capital'] - 1.0) < 0.01
    
    def test_convenience_function(self):
        """Test convenience function for beta calculation."""
        peers = [
            PeerCompany(
                ticker="PEER1",
                company_name="Peer Company 1",
                sic_code="3571",
                market_cap=5000.0,
                enterprise_value=6000.0,
                beta_levered=1.2,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            ),
            PeerCompany(
                ticker="PEER2",
                company_name="Peer Company 2", 
                sic_code="3571",
                market_cap=8000.0,
                enterprise_value=9500.0,
                beta_levered=0.9,
                multiples=CompanyMultiples(data_quality="good"),
                selection_reason="Industry match",
                country="US"
            )
        ]
        
        stats = calculate_bottom_up_beta(peers, BetaCalculationMethod.WINSORIZED_MEAN)
        
        assert stats.sample_size == 2
        assert stats.calculation_method == BetaCalculationMethod.WINSORIZED_MEAN
        assert 0.3 < stats.selected_unlevered_beta < 1.5