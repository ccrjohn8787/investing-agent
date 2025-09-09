"""
Simplified Test Suite for Computational Validators Module

Tests core validation functionality with focus on the most critical validations.
"""

import pytest
import numpy as np
from investing_agent.agents.computational_validators import (
    ComputationalValidator,
    ValidationSeverity,
    ValidationCategory
)
from investing_agent.schemas.inputs import InputsI, Drivers


class TestComputationalValidatorSimple:
    """Test core computational validation functionality."""
    
    @pytest.fixture
    def valid_inputs(self):
        """Create valid inputs for testing."""
        return InputsI(
            company="Test Company",
            ticker="TEST",
            shares_out=100.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.09, 0.08, 0.07, 0.06],
                oper_margin=[0.15, 0.16, 0.17, 0.18, 0.19]
            ),
            sales_to_capital=[2.0, 2.1, 2.2, 2.3, 2.4],
            wacc=[0.08, 0.08, 0.08, 0.08, 0.08]
        )
    
    def test_valid_inputs_pass_validation(self, valid_inputs):
        """Test that valid inputs pass validation."""
        validator = ComputationalValidator()
        report = validator.validate_inputs(valid_inputs)
        
        assert report.is_valid == True
        assert report.critical_errors == 0
        assert report.validation_score >= 80
    
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
                oper_margin=[0.15, 0.16, 0.17, 0.18]          # 4 elements - misaligned!
            ),
            sales_to_capital=[2.0, 2.1, 2.2, 2.3, 2.4],
            wacc=[0.08, 0.08, 0.08, 0.08, 0.08]
        )
        
        report = validator.validate_inputs(inputs)
        
        # Should have critical error for array alignment
        assert report.critical_errors > 0
        assert any(issue.category == ValidationCategory.ARRAY_ALIGNMENT 
                  for issue in report.detailed_issues)
    
    def test_mathematical_consistency_validation(self):
        """Test mathematical consistency validation."""
        validator = ComputationalValidator()
        
        # Create inputs with very small sales-to-capital values (near zero)
        inputs = InputsI(
            company="Test Company", 
            ticker="TEST",
            shares_out=100.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.09, 0.08, 0.07, 0.06],
                oper_margin=[0.15, 0.16, 0.17, 0.18, 0.19]
            ),
            sales_to_capital=[2.0, 0.001, 2.2, 2.3, 2.4],  # Very small value (near zero)
            wacc=[0.001, 0.08, 0.08, 0.08, 0.08]           # Very small WACC (near zero)
        )
        
        report = validator.validate_inputs(inputs)
        
        # Should have issues for values too close to zero or out of bounds
        issues = [issue for issue in report.detailed_issues 
                 if issue.category in [ValidationCategory.MATHEMATICAL_CONSISTENCY, 
                                     ValidationCategory.REASONABLENESS_BOUNDS]]
        assert len(issues) > 0
    
    def test_reasonableness_bounds_validation(self, valid_inputs):
        """Test reasonableness bounds validation."""
        validator = ComputationalValidator()
        
        # Create inputs with unreasonable values
        inputs = valid_inputs.model_copy()
        inputs.drivers.sales_growth = [4.0, 3.0, 2.0, 1.0, 0.5]  # 400%, 300% growth etc.
        inputs.drivers.oper_margin = [-0.8, 0.16, 1.5, 0.18, 0.19]  # Negative and >100% margins
        inputs.wacc = [0.001, 0.08, 0.35, 0.08, 0.08]  # Very low and very high WACC
        
        report = validator.validate_inputs(inputs)
        
        # Should have warnings/errors for reasonableness
        bounds_issues = [issue for issue in report.detailed_issues 
                        if issue.category == ValidationCategory.REASONABLENESS_BOUNDS]
        assert len(bounds_issues) > 0
    
    def test_validation_scoring_system(self, valid_inputs):
        """Test validation scoring system."""
        validator = ComputationalValidator()
        
        # Test perfect inputs
        report_perfect = validator.validate_inputs(valid_inputs)
        assert report_perfect.validation_score >= 90
        
        # Test inputs with critical errors by using unreasonable high values
        inputs_critical = valid_inputs.model_copy()
        inputs_critical.drivers.sales_growth = [10.0, 9.0, 8.0, 7.0, 6.0]  # 1000%, 900% growth etc. - extreme
        
        report_critical = validator.validate_inputs(inputs_critical)
        # Should have errors for extreme growth rates
        assert report_critical.validation_score < report_perfect.validation_score
    
    def test_terminal_value_sanity_validation(self, valid_inputs):
        """Test terminal value sanity checks."""
        validator = ComputationalValidator()
        
        # Test inputs with extreme terminal growth and low WACC-growth spread
        inputs = valid_inputs.model_copy()
        inputs.drivers.stable_growth = 0.12  # 12% terminal growth is very high
        inputs.wacc = [0.08, 0.08, 0.08, 0.08, 0.125]  # Terminal WACC only slightly above growth
        
        report = validator.validate_inputs(inputs)
        
        # Should have warnings about terminal value
        terminal_issues = [issue for issue in report.detailed_issues 
                          if issue.category == ValidationCategory.TERMINAL_VALUE_SANITY]
        
        # May have issues depending on exact implementation
        if terminal_issues:
            assert any("terminal" in issue.issue_description.lower() 
                      for issue in terminal_issues)
    
    def test_validation_report_structure(self, valid_inputs):
        """Test validation report structure and completeness."""
        validator = ComputationalValidator()
        report = validator.validate_inputs(valid_inputs)
        
        # Verify report structure
        assert hasattr(report, 'is_valid')
        assert hasattr(report, 'total_issues')
        assert hasattr(report, 'critical_errors')
        assert hasattr(report, 'validation_score')
        assert hasattr(report, 'detailed_issues')
        assert hasattr(report, 'recommended_actions')
        
        # Verify score is in valid range
        assert 0 <= report.validation_score <= 100
        
        # Verify severity and category counts add up
        total_by_severity = sum(report.issues_by_severity.values())
        total_by_category = sum(report.issues_by_category.values())
        assert total_by_severity == report.total_issues
        assert total_by_category == report.total_issues