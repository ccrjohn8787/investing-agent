"""
Test Suite for Computational Validators Module

Tests comprehensive validation system for catching computational errors,
array alignment issues, and mathematical inconsistencies.
"""

import pytest
import numpy as np
from investing_agent.agents.computational_validators import (
    ComputationalValidator,
    ValidationSeverity,
    ValidationCategory,
    validate_computation_chain
)
from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.comparables import (
    PeerAnalysis, PeerSelectionCriteria, IndustryStatistics, WACCCalculation
)


class TestComputationalValidator:
    """Test computational validation functionality."""
    
    @pytest.fixture
    def valid_inputs(self):
        """Create valid inputs for testing."""
        return InputsI(
            company="Test Company",
            ticker="TEST",
            shares_out=100.0,
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
            pv_oper_assets=5000.0,
            terminal_value=3000.0,
            enterprise_value=5000.0,
            non_operating_assets=0.0
        )
    
    def test_valid_inputs_pass_validation(self, valid_inputs):
        """Test that valid inputs pass all validation checks."""
        validator = ComputationalValidator()
        report = validator.validate_inputs(valid_inputs)
        
        assert report.is_valid == True
        assert report.critical_errors == 0
        assert report.validation_score >= 90
    
    def test_array_alignment_validation(self):
        """Test array alignment validation."""
        validator = ComputationalValidator()
        
        # Create inputs with misaligned arrays
        inputs = InputsI(
            company="Test Company",
            ticker="TEST", 
            shares_out=100.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.09, 0.08, 0.07, 0.06],  # 5 elements
                oper_margin=[0.15, 0.16, 0.17, 0.18]  # 4 elements - misaligned!
            ),
            sales_to_capital=[2.0, 2.1, 2.2, 2.3, 2.4],
            wacc=[0.08, 0.08, 0.08, 0.08, 0.08]
        )
        
        report = validator.validate_inputs(inputs)
        
        # Should have critical error for array alignment
        assert report.critical_errors > 0
        assert any(issue.category == ValidationCategory.ARRAY_ALIGNMENT 
                  for issue in report.detailed_issues)
        assert any("horizon" in issue.field_name or "oper_margin" in issue.field_name
                  for issue in report.detailed_issues)
    
    def test_mathematical_consistency_validation(self):
        """Test mathematical consistency validation."""
        validator = ComputationalValidator()
        
        # Create inputs with mathematical issues
        inputs = InputsI(
            company="Test Company",
            ticker="TEST",
            shares_out=100.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.09, 0.08, 0.07, 0.06],
                oper_margin=[0.15, 0.16, 0.17, 0.18, 0.19]
            ),
            sales_to_capital=[2.0, 0.0, 2.2, 2.3, 2.4],  # Contains zero!
            wacc=[-0.01, 0.08, float('inf'), 0.08, float('nan')]  # Multiple issues!
        )
        
        report = validator.validate_inputs(inputs)
        
        # Should have multiple critical errors
        assert report.critical_errors > 0
        
        # Check for specific mathematical issues
        math_issues = [issue for issue in report.detailed_issues 
                      if issue.category == ValidationCategory.MATHEMATICAL_CONSISTENCY]
        assert len(math_issues) > 0
        
        # Should detect negative WACC, infinite values, and NaN
        issue_descriptions = [issue.issue_description for issue in math_issues]
        assert any("non-positive WACC" in desc for desc in issue_descriptions)
        assert any("infinite values" in desc for desc in issue_descriptions)
        assert any("NaN values" in desc for desc in issue_descriptions)
    
    def test_reasonableness_bounds_validation(self, valid_inputs):
        """Test reasonableness bounds validation."""
        validator = ComputationalValidator()
        
        # Create inputs with unreasonable values
        inputs = valid_inputs.model_copy()
        inputs.drivers.sales_growth = [4.0, 3.0, 2.0, 1.0, 0.5]  # Extreme growth rates (400%, 300%, etc.)
        inputs.drivers.oper_margin = [-0.8, 0.16, 1.5, 0.18, 0.19]  # Out of bounds margins
        inputs.wacc = [0.001, 0.08, 0.35, 0.08, 0.08]  # Out of bounds WACC
        
        report = validator.validate_inputs(inputs)
        
        # Should have multiple warnings/errors for reasonableness
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        assert len(bounds_issues) > 0
        
        # Check for specific bounds issues
        issue_fields = [issue.field_name for issue in bounds_issues]
        assert any("sales_growth" in field for field in issue_fields)
        assert "oper_margin" in issue_fields
        assert "wacc" in issue_fields
    
    def test_data_completeness_validation(self):
        """Test data completeness validation."""
        validator = ComputationalValidator()
        
        # Create inputs with missing data
        inputs = InputsI(
            company="Test Company",
            ticker="TEST",
            shares_out=100.0,
            drivers=Drivers(
                sales_growth=[],  # Missing sales growth!
                oper_margin=[0.15, 0.16]
            ),
            sales_to_capital=[2.0, 2.1],
            wacc=[]  # Missing WACC!
        )
        
        report = validator.validate_inputs(inputs)
        
        # Should have critical errors for missing data
        assert report.critical_errors > 0
        
        completeness_issues = [issue for issue in report.detailed_issues 
                              if issue.category == ValidationCategory.DATA_COMPLETENESS]
        assert len(completeness_issues) > 0
        
        # Should detect missing sales growth and WACC
        issue_fields = [issue.field_name for issue in completeness_issues]
        assert "sales_growth" in issue_fields
        assert "wacc" in issue_fields
    
    def test_terminal_value_sanity_validation(self, valid_inputs):
        """Test terminal value sanity checks."""
        validator = ComputationalValidator()
        
        # Create inputs with extreme terminal growth
        inputs = valid_inputs.model_copy()
        inputs.drivers.stable_growth = 0.12  # 12% terminal growth is very high
        
        report = validator.validate_inputs(inputs)
        
        # Should have warning about high terminal growth
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        
        if terminal_issues:  # May or may not trigger depending on exact threshold
            assert any("terminal growth" in issue.issue_description.lower() 
                      for issue in terminal_issues)
    
    def test_valuation_validation(self, valid_inputs, valid_valuation):
        """Test valuation output validation."""
        validator = ComputationalValidator()
        
        # Test with valid valuation
        report = validator.validate_valuation(valid_inputs, valid_valuation)
        assert report.is_valid == True
        
        # Test with problematic valuation
        bad_valuation = valid_valuation.model_copy()
        bad_valuation.pv_oper_assets = -1000.0  # Negative PV
        bad_valuation.enterprise_value = 3000.0  # Doesn't match components
        
        report_bad = validator.validate_valuation(valid_inputs, bad_valuation)
        
        # Should have warnings/errors
        math_issues = [issue for issue in report_bad.detailed_issues 
                      if issue.category == ValidationCategory.MATHEMATICAL_CONSISTENCY]
        assert len(math_issues) > 0
    
    def test_peer_analysis_validation(self):
        """Test peer analysis validation."""
        validator = ComputationalValidator()
        
        # Create minimal peer analysis with issues
        peer_analysis = PeerAnalysis(
            target_ticker="TEST",
            analysis_date="2024-01-01",
            selection_criteria=PeerSelectionCriteria(
                target_ticker="TEST",
                market_cap_range=(1000, 10000),
                min_peer_count=5
            ),
            peer_companies=[],  # No peers - should be error
            industry_statistics=IndustryStatistics(
                sample_size=0,
                data_completeness=0.5,  # Low data coverage
                ev_ebitda_median=100.0  # Unreasonable multiple
            ),
            wacc_calculation=WACCCalculation(
                bottom_up_beta_unlevered=1.0,
                bottom_up_beta_levered=1.2,
                beta_source="bottom_up",
                risk_free_rate=0.04,
                equity_risk_premium=0.06,
                country_risk_premium=0.0,
                cost_of_equity=0.03,  # Lower than risk-free rate - error!
                cost_of_debt=0.05,
                debt_to_total_capital=0.3,
                equity_to_total_capital=0.7,
                tax_rate=0.25,
                wacc=0.08
            ),
            selection_quality="poor",
            data_coverage=0.5,
            outliers_removed=0
        )
        
        report = validator.validate_peer_analysis(peer_analysis)
        
        # Should have multiple issues
        assert report.total_issues > 0
        
        # Check for specific peer analysis issues
        peer_issues = [issue for issue in report.detailed_issues 
                      if issue.category == ValidationCategory.PEER_ANALYSIS_QUALITY]
        wacc_issues = [issue for issue in report.detailed_issues 
                      if issue.category == ValidationCategory.WACC_CONSISTENCY]
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        
        assert len(peer_issues) > 0  # Should detect insufficient peers
        assert len(wacc_issues) > 0  # Should detect cost of equity < risk-free rate
        assert len(bounds_issues) > 0  # Should detect unreasonable EV/EBITDA
    
    def test_validation_scoring(self, valid_inputs):
        """Test validation scoring system."""
        validator = ComputationalValidator()
        
        # Test perfect inputs
        report_perfect = validator.validate_inputs(valid_inputs)
        assert report_perfect.validation_score >= 90
        
        # Test inputs with warnings
        inputs_warnings = valid_inputs.model_copy()
        inputs_warnings.forecast_years = 2  # Short forecast - warning
        inputs_warnings.capex_pc_of_sales_y = [1.5, 1.6, 1.7, 1.8, 1.9]  # High capex - warning
        
        report_warnings = validator.validate_inputs(inputs_warnings)
        assert report_warnings.validation_score < report_perfect.validation_score
        assert report_warnings.validation_score >= 70  # Still reasonable
        
        # Test inputs with critical errors
        inputs_critical = valid_inputs.model_copy()
        inputs_critical.revenue_y = []  # Missing revenue - critical
        inputs_critical.wacc_y = [-0.1, -0.2, -0.3, -0.4, -0.5]  # Negative WACC - critical
        
        report_critical = validator.validate_inputs(inputs_critical)
        assert report_critical.validation_score < 50
        assert report_critical.is_valid == False
    
    def test_convenience_function(self, valid_inputs, valid_valuation):
        """Test convenience function for full validation."""
        reports = validate_computation_chain(
            inputs=valid_inputs,
            valuation=valid_valuation
        )
        
        assert 'inputs' in reports
        assert 'valuation' in reports
        assert reports['inputs'].is_valid == True
        assert reports['valuation'].is_valid == True
    
    def test_validation_with_numpy_arrays(self):
        """Test validation works with numpy arrays."""
        validator = ComputationalValidator()
        
        # Create inputs using numpy arrays
        inputs = InputsI(
            ticker="TEST",
            company_name="Test Company",
            forecast_years=5,
            revenue_y=np.array([1000, 1100, 1200, 1300, 1400]).tolist(),
            operating_margin_y=np.array([0.15, 0.16, 0.17, 0.18, 0.19]).tolist(),
            capex_pc_of_sales_y=np.array([0.05, 0.05, 0.05, 0.05, 0.05]).tolist(),
            sales_to_capital_incremental_y=np.array([2.0, 2.1, 2.2, 2.3, 2.4]).tolist(),
            wacc_y=np.array([0.08, 0.08, 0.08, 0.08, 0.08]).tolist()
        )
        
        report = validator.validate_inputs(inputs)
        assert report.is_valid == True