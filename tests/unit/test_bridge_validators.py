"""
Test Suite for Bridge Validators Module

Tests PV/Equity bridge validation to catch mathematical corruption
in valuation calculations.
"""

import pytest
from investing_agent.agents.bridge_validators import (
    BridgeValidator,
    BridgeValidationType,
    validate_valuation_bridge
)
from investing_agent.agents.computational_validators import ValidationSeverity, ValidationCategory
from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV


class TestBridgeValidator:
    """Test bridge validation functionality."""
    
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
        return ValuationV(
            pv_explicit=2000.0,
            pv_terminal=3000.0,
            pv_oper_assets=5000.0,
            net_debt=200.0,
            cash_nonop=50.0,
            equity_value=4850.0,
            shares_out=100.0,
            value_per_share=48.50
        )
    
    def test_valid_bridge_passes_validation(self, valid_inputs, valid_valuation):
        """Test that valid bridge calculations pass validation."""
        validator = BridgeValidator()
        report = validator.validate_valuation_bridge(valid_inputs, valid_valuation)
        
        # Should have minimal issues
        assert report.critical_errors == 0
        assert report.validation_score >= 70  # Should be reasonably good score
    
    def test_pv_to_ev_bridge_validation(self, valid_inputs):
        """Test PV to EV bridge validation."""
        validator = BridgeValidator()
        
        # Create valuation with inconsistent values
        valuation = ValuationV(
            pv_explicit=2000.0,
            pv_terminal=3000.0,
            pv_oper_assets=5000.0,
            net_debt=200.0,
            cash_nonop=50.0,
            equity_value=5000.0,  # Inconsistent with PV calculation
            shares_out=100.0,
            value_per_share=50.0
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should detect EV calculation error
        assert report.total_issues > 0
        math_issues = [issue for issue in report.detailed_issues 
                      if issue.category == ValidationCategory.MATHEMATICAL_CONSISTENCY]
        assert len(math_issues) > 0
        
        # Should specifically detect enterprise value inconsistency
        assert any("enterprise_value" in issue.field_name for issue in math_issues)
    
    def test_ev_to_equity_bridge_validation(self, valid_inputs):
        """Test EV to equity bridge validation."""
        validator = BridgeValidator()
        
        # Create valuation that should result in specific equity value
        # EV = 5000, Net Debt = 200, Cash = 50 -> Equity = 5000 - 200 + 50 = 4850
        valuation = ValuationV(
            pv_oper_assets=5000.0,
            terminal_value=3000.0,
            enterprise_value=5000.0,
            non_operating_assets=0.0
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Extract bridge calculation to verify equity value calculation
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valuation)
        expected_equity = 5000.0 - 200.0 + 50.0  # EV - Net Debt + Cash
        assert abs(bridge_calc.equity_value - expected_equity) < 0.01
    
    def test_terminal_value_percentage_validation(self, valid_inputs):
        """Test terminal value percentage validation."""
        validator = BridgeValidator()
        
        # Create valuation with excessive terminal value percentage
        valuation = ValuationV(
            pv_oper_assets=5000.0,
            terminal_value=4800.0,  # 96% of total PV - too high
            enterprise_value=5000.0,
            non_operating_assets=0.0
        )
        
        report = validator.validate_valuation_bridge(valid_inputs, valuation)
        
        # Should warn about high terminal value percentage
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        assert len(terminal_issues) > 0
        assert any("terminal_value_percentage" in issue.field_name for issue in terminal_issues)
    
    def test_share_price_calculation_validation(self, valid_inputs, valid_valuation):
        """Test share price calculation validation."""
        validator = BridgeValidator()
        
        # Test with zero shares (should be critical error)
        inputs_zero_shares = valid_inputs.model_copy()
        inputs_zero_shares.shares_out = 0.0
        
        report = validator.validate_valuation_bridge(inputs_zero_shares, valid_valuation)
        
        # Should have critical error for zero shares
        assert report.critical_errors > 0
        critical_issues = [issue for issue in report.detailed_issues 
                          if issue.severity == ValidationSeverity.CRITICAL]
        assert any("shares_outstanding" in issue.field_name for issue in critical_issues)
    
    def test_negative_equity_value_warning(self, valid_inputs):
        """Test warning for negative equity value."""
        validator = BridgeValidator()
        
        # Create scenario with high debt leading to negative equity
        inputs_high_debt = valid_inputs.model_copy()
        inputs_high_debt.net_debt = 10000.0  # Very high debt
        
        valuation = ValuationV(
            pv_oper_assets=5000.0,
            terminal_value=3000.0,
            enterprise_value=5000.0,
            non_operating_assets=0.0
        )
        
        report = validator.validate_valuation_bridge(inputs_high_debt, valuation)
        
        # Should warn about negative equity value
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        assert any("equity_value" in issue.field_name and "negative" in issue.issue_description.lower() 
                  for issue in bounds_issues)
    
    def test_wacc_growth_spread_validation(self, valid_inputs, valid_valuation):
        """Test WACC-growth spread validation."""
        validator = BridgeValidator()
        
        # Create inputs with WACC very close to terminal growth (dangerous)
        inputs_low_spread = valid_inputs.model_copy()
        inputs_low_spread.drivers.stable_growth = 0.079  # 7.9% growth
        inputs_low_spread.wacc = [0.08, 0.08, 0.08, 0.08, 0.081]  # 8.1% terminal WACC -> 20 bps spread
        
        report = validator.validate_valuation_bridge(inputs_low_spread, valid_valuation)
        
        # Should error on low WACC-growth spread
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        assert any("wacc_growth_spread" in issue.field_name for issue in terminal_issues)
    
    def test_discount_factor_validation(self, valid_inputs, valid_valuation):
        """Test discount factor validation."""
        validator = BridgeValidator()
        
        # Extract bridge calculation to check discount factors
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Should have discount factors that decrease over time
        if len(bridge_calc.discount_factors) > 1:
            for i in range(1, len(bridge_calc.discount_factors)):
                assert bridge_calc.discount_factors[i] < bridge_calc.discount_factors[i-1]
        
        # Discount factors should match WACC calculations
        for i, (wacc, discount_factor) in enumerate(zip(valid_inputs.wacc, bridge_calc.discount_factors)):
            expected_discount = (1 + wacc) ** -(i + 1)
            assert abs(discount_factor - expected_discount) < 0.001
    
    def test_unreasonable_share_price_bounds(self, valid_inputs):
        """Test unreasonable share price detection."""
        validator = BridgeValidator()
        
        # Create scenario leading to extremely high share price
        inputs_few_shares = valid_inputs.model_copy()
        inputs_few_shares.shares_out = 0.1  # Very few shares
        
        valuation = ValuationV(
            pv_oper_assets=50000.0,  # High value
            terminal_value=30000.0,
            enterprise_value=50000.0,
            non_operating_assets=0.0
        )
        
        report = validator.validate_valuation_bridge(inputs_few_shares, valuation)
        
        # Should warn about unreasonable share price
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        assert any("value_per_share" in issue.field_name for issue in bounds_issues)
    
    def test_bridge_validation_scoring(self, valid_inputs, valid_valuation):
        """Test bridge validation scoring system."""
        validator = BridgeValidator()
        
        # Test clean validation
        report_clean = validator.validate_valuation_bridge(valid_inputs, valid_valuation)
        
        # Test with multiple issues
        valuation_issues = ValuationV(
            pv_oper_assets=5000.0,
            terminal_value=4800.0,    # High terminal percentage
            enterprise_value=6000.0,  # EV inconsistency
            non_operating_assets=0.0
        )
        
        report_issues = validator.validate_valuation_bridge(valid_inputs, valuation_issues)
        
        # Score should be lower for problematic valuation
        assert report_issues.validation_score < report_clean.validation_score
        assert report_issues.total_issues > report_clean.total_issues
    
    def test_convenience_function(self, valid_inputs, valid_valuation):
        """Test convenience function."""
        report = validate_valuation_bridge(valid_inputs, valid_valuation, tolerance=1e-4)
        
        assert hasattr(report, 'is_valid')
        assert hasattr(report, 'validation_score')
        assert report.total_issues >= 0
    
    def test_bridge_calculation_extraction(self, valid_inputs, valid_valuation):
        """Test bridge calculation component extraction."""
        validator = BridgeValidator()
        
        bridge_calc = validator._extract_bridge_calculation(valid_inputs, valid_valuation)
        
        # Verify key components are extracted
        assert bridge_calc.total_pv_operating_assets == valid_valuation.pv_oper_assets
        assert bridge_calc.terminal_value == valid_valuation.terminal_value
        assert bridge_calc.enterprise_value == valid_valuation.enterprise_value
        assert bridge_calc.net_debt == valid_inputs.net_debt
        assert bridge_calc.excess_cash == valid_inputs.cash_nonop
        assert bridge_calc.shares_outstanding == valid_inputs.shares_out
        
        # Verify calculated components
        expected_equity = valid_valuation.enterprise_value - valid_inputs.net_debt + valid_inputs.cash_nonop
        assert abs(bridge_calc.equity_value - expected_equity) < 0.01
        
        expected_share_price = bridge_calc.equity_value / valid_inputs.shares_out
        assert abs(bridge_calc.value_per_share - expected_share_price) < 0.01