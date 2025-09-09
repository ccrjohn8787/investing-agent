"""
Test Suite for WACC Calculation Module

Tests comprehensive WACC calculation including cost of debt estimation,
capital structure evolution, and validation components.
"""

import pytest
from investing_agent.agents.wacc_calculation import (
    WACCCalculator,
    CostOfDebtMethod,
    CapitalStructureMode,
    calculate_levered_wacc
)
from investing_agent.agents.beta_calculation import BetaStatistics, BetaCalculationMethod


class TestWACCCalculator:
    """Test WACC calculation functionality."""
    
    @pytest.fixture
    def mock_beta_stats(self):
        """Create mock beta statistics for testing."""
        return BetaStatistics(
            raw_levered_betas=[1.0, 1.2, 0.8],
            raw_unlevered_betas=[0.85, 1.0, 0.7],
            unlevered_median=0.85,
            unlevered_mean=0.85,
            unlevered_winsorized_mean=0.85,
            unlevered_std=0.15,
            sample_size=3,
            data_completeness=1.0,
            coefficient_of_variation=0.18,
            outliers_removed=0,
            selected_unlevered_beta=0.85,
            calculation_method=BetaCalculationMethod.MEDIAN,
            quality_score="good"
        )
    
    def test_comprehensive_wacc_calculation(self, mock_beta_stats):
        """Test complete WACC calculation."""
        calculator = WACCCalculator()
        
        wacc_calc, wacc_evolution, cost_components = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.3,
            risk_free_rate=0.04,
            target_market_cap=5000.0,
            target_tax_rate=0.25,
            country_risk_premium=0.01
        )
        
        # Verify WACC calculation structure
        assert isinstance(wacc_calc.wacc, float)
        assert 0.03 < wacc_calc.wacc < 0.20  # Reasonable WACC range
        assert wacc_calc.beta_source == "bottom_up"
        assert abs(wacc_calc.debt_to_total_capital + wacc_calc.equity_to_total_capital - 1.0) < 0.01
        
        # Verify cost components
        assert cost_components.beta_levered > cost_components.beta_unlevered
        assert cost_components.cost_of_equity > cost_components.risk_free_rate
        assert cost_components.cost_of_debt_aftertax < cost_components.cost_of_debt_pretax
        assert 0.5 < cost_components.confidence_score <= 1.0
        
        # Verify evolution
        assert len(wacc_evolution.wacc_values) == 10  # Default forecast years
        assert wacc_evolution.terminal_wacc > 0
    
    def test_cost_of_debt_methods(self, mock_beta_stats):
        """Test different cost of debt estimation methods."""
        calculator = WACCCalculator()
        
        methods = [
            CostOfDebtMethod.CREDIT_SPREAD,
            CostOfDebtMethod.RATING_BASED,
            CostOfDebtMethod.PEER_AVERAGE
        ]
        
        results = {}
        for method in methods:
            wacc_calc, _, cost_components = calculator.calculate_comprehensive_wacc(
                beta_stats=mock_beta_stats,
                target_debt_to_equity=0.4,
                risk_free_rate=0.04,
                cost_of_debt_method=method
            )
            results[method] = cost_components.cost_of_debt_pretax
            assert cost_components.estimation_method == method.value
        
        # All methods should produce reasonable results
        for method, cost in results.items():
            assert 0.02 < cost < 0.15  # Reasonable cost of debt range
    
    def test_leverage_to_credit_spread(self):
        """Test leverage to credit spread conversion."""
        calculator = WACCCalculator()
        
        # Test different leverage levels
        test_cases = [
            (0.1, None, "low leverage should have low spread"),
            (0.5, None, "moderate leverage should have moderate spread"),
            (1.0, None, "high leverage should have high spread"),
            (2.0, None, "very high leverage should have very high spread"),
            (0.3, 500, "small cap should have higher spread"),
            (0.3, 50000, "large cap should have lower spread")
        ]
        
        for debt_to_equity, market_cap, description in test_cases:
            spread = calculator._leverage_to_credit_spread(debt_to_equity, market_cap)
            assert 0.001 < spread < 0.12, f"Failed for {description}: spread={spread}"
            
            # Higher leverage should generally mean higher spreads
            if debt_to_equity > 1.0:
                assert spread > 0.03, f"High leverage should have spread >3%: {spread}"
    
    def test_size_premium_calculation(self):
        """Test size premium calculation."""
        calculator = WACCCalculator()
        
        # Test size premium tiers
        test_cases = [
            (100, 0.08),    # Micro cap
            (500, 0.04),    # Small cap
            (2000, 0.02),   # Mid cap
            (10000, 0.01),  # Large cap
            (100000, 0.0)   # Mega cap
        ]
        
        for market_cap, expected_min_premium in test_cases:
            premium = calculator._calculate_size_premium(market_cap)
            assert premium >= expected_min_premium * 0.8, f"Premium too low for ${market_cap}M market cap"
            assert premium <= 0.1, f"Premium too high: {premium}"
    
    def test_capital_structure_modes(self, mock_beta_stats):
        """Test different capital structure evolution modes."""
        calculator = WACCCalculator()
        
        modes = [
            CapitalStructureMode.STATIC,
            CapitalStructureMode.TARGET_CONVERGENCE,
            CapitalStructureMode.DYNAMIC_OPTIMAL
        ]
        
        for mode in modes:
            _, wacc_evolution, _ = calculator.calculate_comprehensive_wacc(
                beta_stats=mock_beta_stats,
                target_debt_to_equity=0.5,
                risk_free_rate=0.04,
                capital_structure_mode=mode,
                forecast_years=5
            )
            
            # All modes should produce valid evolution paths
            assert len(wacc_evolution.wacc_values) == 5
            assert len(wacc_evolution.debt_ratios) == 5
            assert all(wacc > 0 for wacc in wacc_evolution.wacc_values)
            assert wacc_evolution.terminal_wacc > 0
            
            # Static mode should have constant debt ratios
            if mode == CapitalStructureMode.STATIC:
                debt_ratios = wacc_evolution.debt_ratios
                assert all(abs(dr - debt_ratios[0]) < 0.01 for dr in debt_ratios)
    
    def test_wacc_validation(self, mock_beta_stats):
        """Test WACC validation logic."""
        calculator = WACCCalculator()
        
        wacc_calc, _, cost_components = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.3,
            risk_free_rate=0.04,
            target_tax_rate=0.25
        )
        
        validation = calculator.validate_wacc_calculation(wacc_calc, cost_components)
        
        # Should pass basic validation
        assert validation["wacc_reasonable"] == True
        assert validation["cost_of_equity_reasonable"] == True  
        assert validation["cost_of_debt_reasonable"] == True
        assert validation["capital_structure_reasonable"] == True
        assert validation["overall_assessment"] in ["valid", "questionable"]
        
        # Test with unreasonable values
        wacc_calc.wacc = 0.50  # 50% WACC is unreasonable
        validation_bad = calculator.validate_wacc_calculation(wacc_calc, cost_components)
        assert validation_bad["wacc_reasonable"] == False
        assert validation_bad["overall_assessment"] != "valid"
    
    def test_extreme_leverage_scenarios(self, mock_beta_stats):
        """Test WACC calculation with extreme leverage scenarios."""
        calculator = WACCCalculator()
        
        # Very low leverage
        wacc_calc_low, _, _ = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.05,  # 5% D/E
            risk_free_rate=0.04
        )
        
        assert wacc_calc_low.debt_to_total_capital < 0.1
        assert wacc_calc_low.cost_of_equity > wacc_calc_low.wacc  # Equity dominates
        
        # High leverage (but not extreme)
        wacc_calc_high, _, _ = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=1.5,  # 150% D/E
            risk_free_rate=0.04
        )
        
        assert wacc_calc_high.debt_to_total_capital > 0.5
        assert wacc_calc_high.cost_of_debt > wacc_calc_low.cost_of_debt  # Higher leverage -> higher cost of debt
    
    def test_international_scenarios(self, mock_beta_stats):
        """Test WACC calculation with international factors."""
        calculator = WACCCalculator()
        
        # Emerging market scenario
        wacc_calc_em, _, cost_components_em = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.4,
            risk_free_rate=0.08,  # Higher risk-free rate
            country_risk_premium=0.03,  # 300 bps country risk
            target_tax_rate=0.30  # Higher tax rate
        )
        
        # Should have higher cost of equity due to country risk
        assert wacc_calc_em.cost_of_equity > 0.10
        assert cost_components_em.country_risk_premium == 0.03
        
        # Developed market scenario
        wacc_calc_dm, _, cost_components_dm = calculator.calculate_comprehensive_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.4,
            risk_free_rate=0.02,  # Lower risk-free rate
            country_risk_premium=0.0,
            target_tax_rate=0.20  # Lower tax rate
        )
        
        # Should have lower overall cost of capital
        assert wacc_calc_em.wacc > wacc_calc_dm.wacc
        assert cost_components_dm.country_risk_premium == 0.0
    
    def test_confidence_assessment(self, mock_beta_stats):
        """Test confidence score assessment."""
        calculator = WACCCalculator()
        
        # High confidence scenario (large cap, excellent beta quality)
        mock_beta_stats.quality_score = "excellent"
        mock_beta_stats.sample_size = 10
        
        confidence_high = calculator._assess_wacc_confidence(mock_beta_stats, 25000)  # Large cap
        
        # Low confidence scenario (small cap, poor beta quality)  
        mock_beta_stats.quality_score = "poor"
        mock_beta_stats.sample_size = 2
        
        confidence_low = calculator._assess_wacc_confidence(mock_beta_stats, 200)  # Small cap
        
        assert confidence_high > confidence_low
        assert 0.3 <= confidence_low <= 1.0
        assert 0.3 <= confidence_high <= 1.0
    
    def test_convenience_function(self, mock_beta_stats):
        """Test convenience function."""
        wacc_calc, wacc_evolution, cost_components = calculate_levered_wacc(
            beta_stats=mock_beta_stats,
            target_debt_to_equity=0.4,
            risk_free_rate=0.045,
            target_market_cap=8000.0,
            target_tax_rate=0.24,
            country_risk_premium=0.005
        )
        
        # Should produce valid results
        assert isinstance(wacc_calc.wacc, float)
        assert 0.03 < wacc_calc.wacc < 0.20
        assert len(wacc_evolution.wacc_values) > 0
        assert cost_components.confidence_score > 0.3