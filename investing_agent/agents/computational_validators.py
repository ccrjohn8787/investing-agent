from __future__ import annotations

"""
Computational Validators

Implements comprehensive validation system for catching computational errors,
array alignment issues, and mathematical inconsistencies in valuation calculations.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.comparables import PeerAnalysis, WACCCalculation


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of validation checks."""
    ARRAY_ALIGNMENT = "array_alignment"
    MATHEMATICAL_CONSISTENCY = "mathematical_consistency"
    REASONABLENESS_BOUNDS = "reasonableness_bounds"
    DATA_COMPLETENESS = "data_completeness"
    TERMINAL_VALUE_SANITY = "terminal_value_sanity"
    WACC_CONSISTENCY = "wacc_consistency"
    PEER_ANALYSIS_QUALITY = "peer_analysis_quality"


@dataclass
class ValidationIssue:
    """Single validation issue."""
    category: ValidationCategory
    severity: ValidationSeverity
    field_name: str
    issue_description: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    is_valid: bool
    total_issues: int
    issues_by_severity: Dict[ValidationSeverity, int]
    issues_by_category: Dict[ValidationCategory, int]
    detailed_issues: List[ValidationIssue]
    
    # Summary statistics
    critical_errors: int
    warnings_count: int
    validation_score: float  # 0-100 score
    
    # Recommendations
    recommended_actions: List[str]
    can_proceed_with_warnings: bool


class ComputationalValidator:
    """Comprehensive validator for investment calculations."""
    
    def __init__(
        self,
        tolerance: float = 1e-6,
        reasonable_growth_bounds: Tuple[float, float] = (-0.5, 2.0),
        reasonable_margin_bounds: Tuple[float, float] = (-0.5, 1.0),
        reasonable_wacc_bounds: Tuple[float, float] = (0.01, 0.25),
        reasonable_terminal_multiple_bounds: Tuple[float, float] = (5.0, 50.0)
    ):
        """Initialize computational validator.
        
        Args:
            tolerance: Numerical tolerance for floating point comparisons
            reasonable_growth_bounds: Min/max reasonable growth rates
            reasonable_margin_bounds: Min/max reasonable operating margins
            reasonable_wacc_bounds: Min/max reasonable WACC values
            reasonable_terminal_multiple_bounds: Min/max EV/Sales terminal multiples
        """
        self.tolerance = tolerance
        self.growth_bounds = reasonable_growth_bounds
        self.margin_bounds = reasonable_margin_bounds
        self.wacc_bounds = reasonable_wacc_bounds
        self.terminal_multiple_bounds = reasonable_terminal_multiple_bounds
    
    def validate_inputs(self, inputs: InputsI) -> ValidationReport:
        """Validate input data structure comprehensively.
        
        Args:
            inputs: Input data structure to validate
            
        Returns:
            Validation report with all issues found
        """
        print("🔍 Running comprehensive input validation...")
        issues = []
        
        # Array alignment validation
        issues.extend(self._validate_array_alignment(inputs))
        
        # Mathematical consistency validation  
        issues.extend(self._validate_mathematical_consistency(inputs))
        
        # Reasonableness bounds validation
        issues.extend(self._validate_reasonableness_bounds(inputs))
        
        # Data completeness validation
        issues.extend(self._validate_data_completeness(inputs))
        
        # Terminal value sanity validation
        issues.extend(self._validate_terminal_value_sanity(inputs))
        
        return self._compile_validation_report(issues)
    
    def validate_valuation(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> ValidationReport:
        """Validate valuation outputs against inputs.
        
        Args:
            inputs: Input data used for valuation
            valuation: Valuation output to validate
            
        Returns:
            Validation report for valuation consistency
        """
        print("🔍 Running comprehensive valuation validation...")
        issues = []
        
        # Validate valuation mathematical consistency
        issues.extend(self._validate_valuation_math(inputs, valuation))
        
        # Validate present value calculations
        issues.extend(self._validate_present_value_calculations(inputs, valuation))
        
        # Validate terminal value calculations
        issues.extend(self._validate_terminal_value_calculations(inputs, valuation))
        
        # Validate WACC consistency
        issues.extend(self._validate_wacc_consistency(inputs, valuation))
        
        return self._compile_validation_report(issues)
    
    def validate_peer_analysis(self, peer_analysis: PeerAnalysis) -> ValidationReport:
        """Validate peer analysis quality and consistency.
        
        Args:
            peer_analysis: Peer analysis to validate
            
        Returns:
            Validation report for peer analysis
        """
        print("🔍 Running peer analysis validation...")
        issues = []
        
        # Validate peer selection quality
        issues.extend(self._validate_peer_selection_quality(peer_analysis))
        
        # Validate industry statistics
        issues.extend(self._validate_industry_statistics(peer_analysis))
        
        # Validate WACC calculation from peers
        issues.extend(self._validate_peer_wacc_calculation(peer_analysis))
        
        return self._compile_validation_report(issues)
    
    def _validate_array_alignment(self, inputs: InputsI) -> List[ValidationIssue]:
        """Validate that all driver arrays have consistent lengths."""
        issues = []
        
        # Get reference length from sales growth
        sales_growth_length = len(inputs.drivers.sales_growth)
        
        # Check all driver arrays
        array_fields = [
            ('oper_margin', inputs.drivers.oper_margin),
            ('sales_to_capital', inputs.sales_to_capital),
            ('wacc', inputs.wacc)
        ]
        
        for field_name, array_values in array_fields:
            if len(array_values) != sales_growth_length:
                issues.append(ValidationIssue(
                    category=ValidationCategory.ARRAY_ALIGNMENT,
                    severity=ValidationSeverity.CRITICAL,
                    field_name=field_name,
                    issue_description=f"Array length mismatch: {len(array_values)} vs sales_growth length {sales_growth_length}",
                    expected_value=sales_growth_length,
                    actual_value=len(array_values),
                    suggested_fix="Ensure all driver arrays have the same length as sales_growth array"
                ))
        
        # Check horizon consistency using built-in validation
        try:
            horizon = inputs.horizon()
        except ValueError as e:
            issues.append(ValidationIssue(
                category=ValidationCategory.ARRAY_ALIGNMENT,
                severity=ValidationSeverity.CRITICAL,
                field_name="horizon",
                issue_description=f"Path length mismatch in driver arrays: {str(e)}",
                suggested_fix="Ensure all driver arrays (sales_growth, oper_margin, sales_to_capital, wacc) have same length"
            ))
        
        return issues
    
    def _validate_mathematical_consistency(self, inputs: InputsI) -> List[ValidationIssue]:
        """Validate mathematical relationships between inputs."""
        issues = []
        
        # Check for NaN or infinite values
        numeric_fields = [
            ('sales_growth', inputs.drivers.sales_growth),
            ('oper_margin', inputs.drivers.oper_margin),
            ('sales_to_capital', inputs.sales_to_capital),
            ('wacc', inputs.wacc)
        ]
        
        for field_name, values in numeric_fields:
            arr = np.array(values)
            
            if np.any(np.isnan(arr)):
                issues.append(ValidationIssue(
                    category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                    severity=ValidationSeverity.CRITICAL,
                    field_name=field_name,
                    issue_description=f"Contains NaN values",
                    suggested_fix="Replace NaN values with appropriate defaults or interpolated values"
                ))
            
            if np.any(np.isinf(arr)):
                issues.append(ValidationIssue(
                    category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                    severity=ValidationSeverity.CRITICAL,
                    field_name=field_name,
                    issue_description=f"Contains infinite values",
                    suggested_fix="Replace infinite values with bounded realistic values"
                ))
        
        # Check for division by zero scenarios in sales-to-capital
        s2c_arr = np.array(inputs.sales_to_capital)
        zero_s2c = np.abs(s2c_arr) < self.tolerance
        if np.any(zero_s2c):
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="sales_to_capital",
                issue_description=f"Contains values too close to zero: {s2c_arr[zero_s2c]}",
                suggested_fix="Set minimum sales-to-capital ratio (e.g., 0.1) to avoid division by zero"
            ))
        
        # Check WACC positivity
        wacc_arr = np.array(inputs.wacc)
        if np.any(wacc_arr <= 0):
            negative_wacc = wacc_arr[wacc_arr <= 0]
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.CRITICAL,
                field_name="wacc",
                issue_description=f"Contains non-positive WACC values: {negative_wacc}",
                expected_value="> 0",
                actual_value=negative_wacc.tolist(),
                suggested_fix="WACC must be positive for valid DCF calculations"
            ))
        
        return issues
    
    def _validate_reasonableness_bounds(self, inputs: InputsI) -> List[ValidationIssue]:
        """Validate that inputs are within reasonable economic bounds."""
        issues = []
        
        # Validate growth rates
        growth_arr = np.array(inputs.drivers.sales_growth)
        out_of_bounds_growth = (growth_arr < self.growth_bounds[0]) | (growth_arr > self.growth_bounds[1])
        if np.any(out_of_bounds_growth):
            bad_growth = growth_arr[out_of_bounds_growth]
            for growth in bad_growth:
                severity = ValidationSeverity.ERROR if abs(growth) > 3.0 else ValidationSeverity.WARNING
                issues.append(ValidationIssue(
                    category=ValidationCategory.REASONABLENESS_BOUNDS,
                    severity=severity,
                    field_name="sales_growth",
                    issue_description=f"Sales growth {growth:.1%} outside reasonable bounds",
                    expected_value=f"{self.growth_bounds[0]:.1%} to {self.growth_bounds[1]:.1%}",
                    actual_value=f"{growth:.1%}",
                    suggested_fix="Review sales growth projections for reasonableness"
                ))
        
        # Validate operating margins
        margin_arr = np.array(inputs.drivers.oper_margin)
        out_of_bounds_margins = (margin_arr < self.margin_bounds[0]) | (margin_arr > self.margin_bounds[1])
        if np.any(out_of_bounds_margins):
            bad_margins = margin_arr[out_of_bounds_margins]
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=ValidationSeverity.WARNING,
                field_name="oper_margin",
                issue_description=f"Operating margins outside typical bounds: {bad_margins}",
                expected_value=f"{self.margin_bounds[0]:.1%} to {self.margin_bounds[1]:.1%}",
                actual_value=bad_margins.tolist(),
                suggested_fix="Review operating margin assumptions for business model consistency"
            ))
        
        # Validate WACC bounds
        wacc_arr = np.array(inputs.wacc)
        out_of_bounds_wacc = (wacc_arr < self.wacc_bounds[0]) | (wacc_arr > self.wacc_bounds[1])
        if np.any(out_of_bounds_wacc):
            bad_wacc = wacc_arr[out_of_bounds_wacc]
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=ValidationSeverity.ERROR,
                field_name="wacc",
                issue_description=f"WACC values outside reasonable bounds: {bad_wacc}",
                expected_value=f"{self.wacc_bounds[0]:.1%} to {self.wacc_bounds[1]:.1%}",
                actual_value=bad_wacc.tolist(),
                suggested_fix="Review cost of capital calculation methodology"
            ))
        
        return issues
    
    def _validate_data_completeness(self, inputs: InputsI) -> List[ValidationIssue]:
        """Validate completeness of required data fields."""
        issues = []
        
        # Check for missing critical fields
        required_fields = [
            ('sales_growth', inputs.drivers.sales_growth, "Sales growth projections"),
            ('oper_margin', inputs.drivers.oper_margin, "Operating margin projections"),
            ('wacc', inputs.wacc, "WACC assumptions")
        ]
        
        for field_name, field_value, description in required_fields:
            if not field_value or len(field_value) == 0:
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_COMPLETENESS,
                    severity=ValidationSeverity.CRITICAL,
                    field_name=field_name,
                    issue_description=f"{description} are missing or empty",
                    suggested_fix=f"Provide {description.lower()} for valuation calculation"
                ))
        
        # Check for sufficient forecast horizon
        try:
            horizon = inputs.horizon()
            if horizon < 3:
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    field_name="horizon",
                    issue_description=f"Very short forecast period: {horizon} years",
                    expected_value=">= 5 years",
                    actual_value=horizon,
                    suggested_fix="Consider extending forecast period for more reliable valuation"
                ))
        except ValueError:
            # Already caught in array alignment validation
            pass
        
        return issues
    
    def _validate_terminal_value_sanity(self, inputs: InputsI) -> List[ValidationIssue]:
        """Validate terminal value assumptions for sanity."""
        issues = []
        
        if not inputs.drivers.sales_growth or len(inputs.drivers.sales_growth) == 0:
            return issues  # Already caught in data completeness
        
        # Use terminal growth rate from inputs, or last growth rate as proxy
        try:
            # Check if there's a stable growth rate defined
            implied_terminal_growth = getattr(inputs.drivers, 'stable_growth', inputs.drivers.sales_growth[-1])
        except (IndexError, AttributeError):
            return issues
        
        # Terminal growth should be reasonable (typically <= long-term GDP growth)
        if implied_terminal_growth > 0.06:  # 6% terminal growth is quite high
            issues.append(ValidationIssue(
                    category=ValidationCategory.TERMINAL_VALUE_SANITY,
                    severity=ValidationSeverity.WARNING,
                    field_name="terminal_growth_implied",
                    issue_description=f"High implied terminal growth: {implied_terminal_growth:.1%}",
                    expected_value="<= 6%",
                    actual_value=f"{implied_terminal_growth:.1%}",
                    suggested_fix="Consider moderating final year growth for conservative terminal value"
                ))
            
            if implied_terminal_growth < -0.05:  # Negative terminal growth concerning
                issues.append(ValidationIssue(
                    category=ValidationCategory.TERMINAL_VALUE_SANITY,
                    severity=ValidationSeverity.ERROR,
                    field_name="terminal_growth_implied",
                    issue_description=f"Negative implied terminal growth: {implied_terminal_growth:.1%}",
                    actual_value=f"{implied_terminal_growth:.1%}",
                    suggested_fix="Terminal growth should typically be positive for going concern"
                ))
        
        # Check terminal WACC vs growth spread
        if inputs.wacc:
            terminal_wacc = inputs.wacc[-1]
            wacc_growth_spread = terminal_wacc - implied_terminal_growth
            if wacc_growth_spread < 0.01:  # Less than 100 bps spread is dangerous
                issues.append(ValidationIssue(
                    category=ValidationCategory.TERMINAL_VALUE_SANITY,
                    severity=ValidationSeverity.ERROR,
                    field_name="wacc_growth_spread",
                    issue_description=f"Terminal WACC-growth spread too low: {wacc_growth_spread:.1%}",
                    expected_value=">= 1.0%",
                    actual_value=f"{wacc_growth_spread:.1%}",
                    suggested_fix="Ensure WACC exceeds terminal growth by reasonable margin"
                ))
        
        return issues
    
    def _validate_valuation_math(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> List[ValidationIssue]:
        """Validate mathematical consistency between inputs and valuation outputs."""
        issues = []
        
        # Validate that enterprise value components exist
        if not hasattr(valuation, 'pv_oper_assets') or valuation.pv_oper_assets is None:
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.CRITICAL,
                field_name="pv_oper_assets",
                issue_description="Present value of operating assets is missing",
                suggested_fix="Ensure DCF calculation produces present value of operating assets"
            ))
        
        # Validate enterprise value calculation if components exist
        if (hasattr(valuation, 'pv_oper_assets') and valuation.pv_oper_assets is not None and
            hasattr(valuation, 'enterprise_value') and valuation.enterprise_value is not None):
            
            # EV should equal PV of operating assets plus non-operating assets
            expected_ev = valuation.pv_oper_assets
            if hasattr(valuation, 'non_operating_assets') and valuation.non_operating_assets:
                expected_ev += valuation.non_operating_assets
            
            if abs(valuation.enterprise_value - expected_ev) > self.tolerance:
                issues.append(ValidationIssue(
                    category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    field_name="enterprise_value",
                    issue_description="Enterprise value doesn't equal sum of components",
                    expected_value=expected_ev,
                    actual_value=valuation.enterprise_value,
                    suggested_fix="Check enterprise value calculation logic"
                ))
        
        return issues
    
    def _validate_present_value_calculations(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> List[ValidationIssue]:
        """Validate present value discount calculations."""
        issues = []
        
        # Check if we have enough data to validate PV calculations
        if (not inputs.wacc_y or len(inputs.wacc_y) == 0 or 
            not hasattr(valuation, 'pv_oper_assets') or valuation.pv_oper_assets is None):
            return issues
        
        # Validate that present values are positive (for profitable companies)
        if valuation.pv_oper_assets <= 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                field_name="pv_oper_assets",
                issue_description=f"Non-positive present value of operating assets: {valuation.pv_oper_assets}",
                suggested_fix="Review cash flow projections and terminal value assumptions"
            ))
        
        return issues
    
    def _validate_terminal_value_calculations(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> List[ValidationIssue]:
        """Validate terminal value calculation components."""
        issues = []
        
        # Check if terminal value is reasonable proportion of total value
        if (hasattr(valuation, 'terminal_value') and valuation.terminal_value is not None and
            hasattr(valuation, 'pv_oper_assets') and valuation.pv_oper_assets is not None):
            
            if valuation.pv_oper_assets > 0:
                terminal_proportion = valuation.terminal_value / valuation.pv_oper_assets
                
                if terminal_proportion > 0.9:  # Terminal value >90% suggests forecast too short
                    issues.append(ValidationIssue(
                        category=ValidationCategory.TERMINAL_VALUE_SANITY,
                        severity=ValidationSeverity.WARNING,
                        field_name="terminal_value_proportion",
                        issue_description=f"Terminal value {terminal_proportion:.1%} of total value is very high",
                        suggested_fix="Consider extending explicit forecast period"
                    ))
                
                if terminal_proportion < 0.1:  # Terminal value <10% might indicate errors
                    issues.append(ValidationIssue(
                        category=ValidationCategory.TERMINAL_VALUE_SANITY,
                        severity=ValidationSeverity.WARNING,
                        field_name="terminal_value_proportion",
                        issue_description=f"Terminal value {terminal_proportion:.1%} of total value is very low",
                        suggested_fix="Check terminal value calculation methodology"
                    ))
        
        return issues
    
    def _validate_wacc_consistency(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> List[ValidationIssue]:
        """Validate WACC consistency in calculations."""
        issues = []
        
        # Check WACC trend (should generally be stable or declining)
        if inputs.wacc_y and len(inputs.wacc_y) > 1:
            wacc_changes = [inputs.wacc_y[i] - inputs.wacc_y[i-1] 
                           for i in range(1, len(inputs.wacc_y))]
            
            large_increases = [change for change in wacc_changes if change > 0.02]  # >200 bps increase
            if large_increases:
                issues.append(ValidationIssue(
                    category=ValidationCategory.WACC_CONSISTENCY,
                    severity=ValidationSeverity.WARNING,
                    field_name="wacc_y",
                    issue_description=f"Large WACC increases detected: {large_increases}",
                    suggested_fix="Review assumptions causing WACC to increase significantly over time"
                ))
        
        return issues
    
    def _validate_peer_selection_quality(self, peer_analysis: PeerAnalysis) -> List[ValidationIssue]:
        """Validate quality of peer selection."""
        issues = []
        
        # Check minimum peer count
        peer_count = len(peer_analysis.peer_companies)
        if peer_count < 3:
            issues.append(ValidationIssue(
                category=ValidationCategory.PEER_ANALYSIS_QUALITY,
                severity=ValidationSeverity.ERROR,
                field_name="peer_companies",
                issue_description=f"Insufficient peer companies: {peer_count}",
                expected_value=">= 3",
                actual_value=peer_count,
                suggested_fix="Expand peer selection criteria to include more comparable companies"
            ))
        
        # Check data completeness across peers
        data_coverage = peer_analysis.data_coverage
        if data_coverage < 0.7:
            issues.append(ValidationIssue(
                category=ValidationCategory.PEER_ANALYSIS_QUALITY,
                severity=ValidationSeverity.WARNING,
                field_name="data_coverage",
                issue_description=f"Low data coverage across peers: {data_coverage:.1%}",
                expected_value=">= 70%",
                actual_value=f"{data_coverage:.1%}",
                suggested_fix="Consider data quality when interpreting peer analysis results"
            ))
        
        return issues
    
    def _validate_industry_statistics(self, peer_analysis: PeerAnalysis) -> List[ValidationIssue]:
        """Validate industry statistics quality."""
        issues = []
        
        stats = peer_analysis.industry_statistics
        
        # Check for reasonable EV/EBITDA multiples
        if stats.ev_ebitda_median and (stats.ev_ebitda_median < 5 or stats.ev_ebitda_median > 50):
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=ValidationSeverity.WARNING,
                field_name="ev_ebitda_median",
                issue_description=f"EV/EBITDA median {stats.ev_ebitda_median:.1f}x outside typical range",
                expected_value="5-50x",
                actual_value=f"{stats.ev_ebitda_median:.1f}x",
                suggested_fix="Review peer selection for industry appropriateness"
            ))
        
        return issues
    
    def _validate_peer_wacc_calculation(self, peer_analysis: PeerAnalysis) -> List[ValidationIssue]:
        """Validate WACC calculation derived from peer analysis."""
        issues = []
        
        wacc_calc = peer_analysis.wacc_calculation
        
        # Validate WACC components
        if wacc_calc.cost_of_equity <= wacc_calc.risk_free_rate:
            issues.append(ValidationIssue(
                category=ValidationCategory.WACC_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="cost_of_equity",
                issue_description="Cost of equity not higher than risk-free rate",
                expected_value=f">{wacc_calc.risk_free_rate:.1%}",
                actual_value=f"{wacc_calc.cost_of_equity:.1%}",
                suggested_fix="Check beta calculation and risk premium assumptions"
            ))
        
        # Validate capital structure
        total_weight = wacc_calc.debt_to_total_capital + wacc_calc.equity_to_total_capital
        if abs(total_weight - 1.0) > self.tolerance:
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="capital_structure_weights",
                issue_description=f"Capital structure weights don't sum to 1.0: {total_weight:.3f}",
                expected_value=1.0,
                actual_value=total_weight,
                suggested_fix="Ensure debt and equity weights sum to 100%"
            ))
        
        return issues
    
    def _compile_validation_report(self, issues: List[ValidationIssue]) -> ValidationReport:
        """Compile comprehensive validation report from issues."""
        total_issues = len(issues)
        
        # Count issues by severity
        issues_by_severity = {severity: 0 for severity in ValidationSeverity}
        for issue in issues:
            issues_by_severity[issue.severity] += 1
        
        # Count issues by category  
        issues_by_category = {category: 0 for category in ValidationCategory}
        for issue in issues:
            issues_by_category[issue.category] += 1
        
        # Determine overall validation status
        critical_errors = issues_by_severity[ValidationSeverity.CRITICAL]
        warnings_count = issues_by_severity[ValidationSeverity.WARNING] + issues_by_severity[ValidationSeverity.ERROR]
        
        is_valid = critical_errors == 0
        can_proceed_with_warnings = critical_errors == 0 and issues_by_severity[ValidationSeverity.ERROR] == 0
        
        # Calculate validation score (0-100)
        validation_score = max(0, 100 - (critical_errors * 50) - (issues_by_severity[ValidationSeverity.ERROR] * 15) - (issues_by_severity[ValidationSeverity.WARNING] * 5))
        
        # Generate recommendations
        recommended_actions = []
        if critical_errors > 0:
            recommended_actions.append("CRITICAL: Fix all critical errors before proceeding")
        if issues_by_severity[ValidationSeverity.ERROR] > 0:
            recommended_actions.append("Fix error-level issues for reliable results")
        if warnings_count > 5:
            recommended_actions.append("Review multiple warnings that may indicate systematic issues")
        if validation_score < 70:
            recommended_actions.append("Consider improving data quality before finalizing analysis")
        
        print(f"   ✓ Validation complete: {total_issues} issues found (Score: {validation_score:.0f}/100)")
        print(f"   ✓ Critical: {critical_errors}, Errors: {issues_by_severity[ValidationSeverity.ERROR]}, Warnings: {issues_by_severity[ValidationSeverity.WARNING]}")
        
        return ValidationReport(
            is_valid=is_valid,
            total_issues=total_issues,
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            detailed_issues=issues,
            critical_errors=critical_errors,
            warnings_count=warnings_count,
            validation_score=validation_score,
            recommended_actions=recommended_actions,
            can_proceed_with_warnings=can_proceed_with_warnings
        )


def validate_computation_chain(
    inputs: InputsI,
    valuation: Optional[ValuationV] = None,
    peer_analysis: Optional[PeerAnalysis] = None
) -> Dict[str, ValidationReport]:
    """Convenience function to validate entire computation chain.
    
    Args:
        inputs: Input data structure
        valuation: Optional valuation output
        peer_analysis: Optional peer analysis
        
    Returns:
        Dictionary of validation reports by component
    """
    validator = ComputationalValidator()
    
    reports = {
        'inputs': validator.validate_inputs(inputs)
    }
    
    if valuation is not None:
        reports['valuation'] = validator.validate_valuation(inputs, valuation)
    
    if peer_analysis is not None:
        reports['peer_analysis'] = validator.validate_peer_analysis(peer_analysis)
    
    return reports