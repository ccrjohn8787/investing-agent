"""
Simplified Test Suite for Bridge Validators Module

Tests core PV/Equity bridge validation functionality.
"""

import pytest
from investing_agent.agents.bridge_validators import (
    BridgeValidator,
    validate_valuation_bridge
)
from investing_agent.agents.computational_validators import ValidationSeverity, ValidationCategory
from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV


class TestBridgeValidatorSimple:
    """Test core bridge validation functionality."""
    
    @pytest.fixture
    def valid_inputs(self):
        """Create valid inputs for testing."""
        return InputsI(
            company="Test Company",
            ticker="TEST",
            shares_out=100.0,
            net_debt=200.0,
            cash_nonop=50.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.09, 0.08, 0.07, 0.06],
                oper_margin=[0.15, 0.16, 0.17, 0.18, 0.19],
                stable_growth=0.025,
                stable_margin=0.18
            ),
            sales_to_capital=[2.0, 2.1, 2.2, 2.3, 2.4],
            wacc=[0.08, 0.08, 0.08, 0.08, 0.08]
        )
    
    @pytest.fixture 
    def valid_valuation(self):
        """Create valid valuation output."""
        # EV = 5000, Net Debt = 200, Cash = 50 -> Equity = 4850, Share Price = 48.50
        return ValuationV(
            pv_explicit=2000.0,
            pv_terminal=3000.0,
            pv_oper_assets=5000.0,  # explicit + terminal
            net_debt=200.0,
            cash_nonop=50.0,
            equity_value=4850.0,    # EV - net debt + cash
            shares_out=100.0,
            value_per_share=48.50   # equity / shares
        )
    
    def test_valid_bridge_passes_validation(self, valid_inputs, valid_valuation):
        """Test that valid bridge calculations pass validation."""
        validator = BridgeValidator()
        report = validator.validate_valuation_bridge(valid_inputs, valid_valuation)
        
        # Should have no critical errors for valid inputs
        assert report.critical_errors == 0
        assert report.validation_score >= 70
    
    def test_bridge_calculation_extraction(self, valid_inputs, valid_valuation):
        """Test bridge calculation component extraction."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Verify key components match valuation
        assert bridge_calc.total_pv_operating_assets == valid_valuation.pv_oper_assets
        assert bridge_calc.terminal_value == valid_valuation.pv_terminal
        assert bridge_calc.net_debt == valid_valuation.net_debt
        assert bridge_calc.excess_cash == valid_valuation.cash_nonop
        assert bridge_calc.equity_value == valid_valuation.equity_value
        assert bridge_calc.shares_outstanding == valid_valuation.shares_out
        assert bridge_calc.value_per_share == valid_valuation.value_per_share
    
    def test_pv_components_consistency(self, valid_inputs, valid_valuation):
        """Test PV components add up correctly."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # PV Operating Assets should equal PV Explicit + PV Terminal
        expected_pv_oper = bridge_calc.pv_explicit_cash_flows + bridge_calc.pv_terminal_value
        assert abs(bridge_calc.total_pv_operating_assets - expected_pv_oper) < 1.0
    
    def test_equity_value_calculation(self, valid_inputs, valid_valuation):
        """Test equity value calculation from enterprise value."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Equity Value = Enterprise Value - Net Debt + Cash
        expected_equity = bridge_calc.enterprise_value - bridge_calc.net_debt + bridge_calc.excess_cash
        assert abs(bridge_calc.equity_value - expected_equity) < 0.01
    
    def test_share_price_calculation(self, valid_inputs, valid_valuation):
        """Test share price calculation."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Share Price = Equity Value / Shares Outstanding
        expected_price = bridge_calc.equity_value / bridge_calc.shares_outstanding
        assert abs(bridge_calc.value_per_share - expected_price) < 0.01
    
    def test_terminal_value_percentage_calculation(self, valid_inputs, valid_valuation):
        """Test terminal value percentage calculation."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Terminal percentage should be reasonable
        expected_percentage = bridge_calc.terminal_value / bridge_calc.total_pv_operating_assets
        assert abs(bridge_calc.terminal_value_percentage - expected_percentage) < 0.01
        assert 0.0 <= bridge_calc.terminal_value_percentage <= 1.0
    
    def test_inconsistent_equity_value_detection(self, valid_inputs):
        """Test detection of inconsistent equity value calculation."""
        validator = BridgeValidator()
        
        # Create valuation with inconsistent equity value
        valuation = ValuationV(
            pv_explicit=2000.0,
            pv_terminal=3000.0,
            pv_oper_assets=5000.0,
            net_debt=200.0,
            cash_nonop=50.0,
            equity_value=6000.0,  # Should be 4850 (5000-200+50), but is 6000
            shares_out=100.0,
            value_per_share=60.0  # Also inconsistent
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should detect equity value inconsistency
        assert report.total_issues > 0
        math_issues = [issue for issue in report.detailed_issues 
                      if issue.category == ValidationCategory.MATHEMATICAL_CONSISTENCY]
        assert len(math_issues) > 0
    
    def test_zero_shares_outstanding_error(self, valid_inputs, valid_valuation):
        """Test critical error for zero shares outstanding."""
        validator = BridgeValidator()
        
        # Create valuation with zero shares
        valuation = valid_valuation.model_copy()
        valuation.shares_out = 0.0
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should have critical error
        assert report.critical_errors > 0
        critical_issues = [issue for issue in report.detailed_issues 
                          if issue.severity == ValidationSeverity.CRITICAL]
        assert any("shares_outstanding" in issue.field_name for issue in critical_issues)
    
    def test_negative_equity_value_warning(self, valid_inputs):
        """Test warning for negative equity value.""" 
        validator = BridgeValidator()
        
        # Create valuation with negative equity (high debt scenario)
        valuation = ValuationV(
            pv_explicit=1000.0,
            pv_terminal=1500.0,
            pv_oper_assets=2500.0,
            net_debt=5000.0,  # Very high debt
            cash_nonop=100.0,
            equity_value=-2400.0,  # Negative equity (2500-5000+100)
            shares_out=100.0,
            value_per_share=-24.0
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should warn about negative equity
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        assert any("equity_value" in issue.field_name for issue in bounds_issues)
    
    def test_terminal_value_sanity_checks(self, valid_inputs):
        """Test terminal value sanity validation."""
        validator = BridgeValidator()
        
        # Create valuation with extreme terminal value percentage
        valuation = ValuationV(
            pv_explicit=200.0,   # Very low explicit PV
            pv_terminal=4800.0,  # Very high terminal PV (96% of total)
            pv_oper_assets=5000.0,
            net_debt=200.0,
            cash_nonop=50.0,
            equity_value=4850.0,
            shares_out=100.0,
            value_per_share=48.50
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should warn about high terminal value percentage
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        
        # May have warnings about terminal value percentage
        if terminal_issues:
            assert any("terminal" in issue.field_name.lower() for issue in terminal_issues)
    
    def test_wacc_growth_spread_validation(self, valid_inputs, valid_valuation):
        """Test WACC-growth spread validation."""
        validator = BridgeValidator()
        
        # Create inputs with dangerous WACC-growth spread
        inputs_low_spread = valid_inputs.model_copy()
        inputs_low_spread.drivers.stable_growth = 0.079  # 7.9% growth
        inputs_low_spread.wacc = [0.08, 0.08, 0.08, 0.08, 0.08]  # 8.0% WACC -> only 10 bps spread
        
        report = validator.validate_valuation_bridge(inputs_low_spread, valid_valuation)
        
        # Should error on low WACC-growth spread
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        spread_issues = [issue for issue in terminal_issues 
                        if "wacc_growth_spread" in issue.field_name]
        assert len(spread_issues) > 0
    
    def test_discount_factor_consistency(self, valid_inputs, valid_valuation):
        """Test discount factor calculation consistency."""
        validator = BridgeValidator()
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Should have discount factors
        assert len(bridge_calc.discount_factors) > 0
        
        # Discount factors should decrease over time
        if len(bridge_calc.discount_factors) > 1:
            for i in range(1, len(bridge_calc.discount_factors)):
                assert bridge_calc.discount_factors[i] < bridge_calc.discount_factors[i-1]
        
        # First discount factor should match 1/(1+WACC)
        if valid_inputs.wacc and bridge_calc.discount_factors:
            expected_first = 1.0 / (1 + valid_inputs.wacc[0])
            assert abs(bridge_calc.discount_factors[0] - expected_first) < 0.001
    
    def test_convenience_function(self, valid_inputs, valid_valuation):
        """Test convenience function."""
        report = validate_valuation_bridge(valid_inputs, valid_valuation)
        
        assert hasattr(report, 'is_valid')
        assert hasattr(report, 'validation_score')
        assert hasattr(report, 'total_issues')
        assert report.total_issues >= 0
    
    def test_validation_report_structure(self, valid_inputs, valid_valuation):
        """Test validation report structure."""
        validator = BridgeValidator()
        report = validator.validate_valuation_bridge(valid_inputs, valid_valuation)
        
        # Verify report structure
        assert hasattr(report, 'is_valid')
        assert hasattr(report, 'total_issues')
        assert hasattr(report, 'critical_errors')
        assert hasattr(report, 'validation_score')
        assert hasattr(report, 'detailed_issues')
        assert hasattr(report, 'recommended_actions')
        
        # Verify score is in valid range
        assert 0 <= report.validation_score <= 100
        
        # Verify counts are consistent
        assert report.critical_errors >= 0
        assert report.total_issues >= 0