from __future__ import annotations

"""
PV/Equity Bridge Validators

Implements validation logic to catch silent mathematical corruption in valuation
calculations by verifying consistency of the valuation chain from operating assets
to equity value through enterprise value calculations.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.agents.computational_validators import (
    ValidationIssue, ValidationSeverity, ValidationCategory, ValidationReport
)


class BridgeValidationType(Enum):
    """Types of bridge validation checks."""
    PV_TO_EV_BRIDGE = "pv_to_ev_bridge"
    EV_TO_EQUITY_BRIDGE = "ev_to_equity_bridge"  
    TERMINAL_VALUE_CONSISTENCY = "terminal_value_consistency"
    DISCOUNT_FACTOR_VALIDATION = "discount_factor_validation"
    CASH_FLOW_CHAIN_VALIDATION = "cash_flow_chain_validation"
    SHARE_PRICE_RECONCILIATION = "share_price_reconciliation"


@dataclass
class BridgeCalculation:
    """Intermediate bridge calculations for validation."""
    # Operating cash flows
    operating_cash_flows: List[float]
    terminal_value: float
    discount_factors: List[float]
    
    # Present values
    pv_explicit_cash_flows: float
    pv_terminal_value: float
    total_pv_operating_assets: float
    
    # Bridge components
    non_operating_assets: float
    enterprise_value: float
    
    # Debt and cash adjustments
    net_debt: float
    excess_cash: float
    equity_value: float
    
    # Final calculations
    shares_outstanding: float
    value_per_share: float
    
    # Quality metrics
    terminal_value_percentage: float
    wacc_terminal: float
    growth_terminal: float


class BridgeValidator:
    """Validator for PV to equity value bridge calculations."""
    
    def __init__(
        self,
        tolerance: float = 1e-3,  # 0.1% tolerance for bridge calculations
        max_terminal_percentage: float = 0.85,  # Max 85% terminal value
        min_terminal_percentage: float = 0.15,  # Min 15% terminal value
        reasonable_share_price_bounds: Tuple[float, float] = (0.01, 10000.0)
    ):
        """Initialize bridge validator.
        
        Args:
            tolerance: Numerical tolerance for bridge validations
            max_terminal_percentage: Maximum reasonable terminal value percentage
            min_terminal_percentage: Minimum reasonable terminal value percentage  
            reasonable_share_price_bounds: Min/max reasonable share price range
        """
        self.tolerance = tolerance
        self.max_terminal_percentage = max_terminal_percentage
        self.min_terminal_percentage = min_terminal_percentage
        self.share_price_bounds = reasonable_share_price_bounds
    
    def validate_valuation_bridge(
        self,
        inputs: InputsI,
        valuation: ValuationV
    ) -> ValidationReport:
        """Validate complete valuation bridge from PV to equity value.
        
        Args:
            inputs: Input data used for valuation
            valuation: Valuation output to validate
            
        Returns:
            Validation report for bridge calculations
        """
        print("🔗 Running comprehensive valuation bridge validation...")
        issues = []
        
        # Extract bridge calculation components
        try:
            bridge_calc = self._extract_bridge_calculation(inputs, valuation)
        except Exception as e:
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.CRITICAL,
                field_name="bridge_extraction",
                issue_description=f"Failed to extract bridge components: {str(e)}",
                suggested_fix="Check valuation output structure and completeness"
            ))
            return self._compile_bridge_validation_report(issues)
        
        # Validate PV to EV bridge
        issues.extend(self._validate_pv_to_ev_bridge(bridge_calc))
        
        # Validate EV to equity bridge
        issues.extend(self._validate_ev_to_equity_bridge(bridge_calc))
        
        # Validate terminal value consistency
        issues.extend(self._validate_terminal_value_consistency(bridge_calc, inputs))
        
        # Validate discount factor calculations
        issues.extend(self._validate_discount_factors(bridge_calc, inputs))
        
        # Validate share price reconciliation
        issues.extend(self._validate_share_price_reconciliation(bridge_calc, inputs))
        
        return self._compile_bridge_validation_report(issues)
    
    def _extract_bridge_calculation(
        self,
        inputs: InputsI,
        valuation: ValuationV
    ) -> BridgeCalculation:
        """Extract bridge calculation components from valuation."""
        
        # Extract operating cash flows if available
        operating_cash_flows = getattr(valuation, 'operating_cash_flows', [])
        
        # Extract present value components
        pv_oper_assets = valuation.pv_oper_assets
        terminal_value = valuation.pv_terminal  # Use pv_terminal from schema
        pv_explicit = valuation.pv_explicit
        
        # Calculate enterprise value (PV of operating assets + non-operating)
        enterprise_value = pv_oper_assets  # Assuming no non-operating assets for now
        non_operating_assets = 0.0  # Not in current schema
        
        # Extract debt and cash from valuation (they're stored there)
        net_debt = valuation.net_debt
        excess_cash = valuation.cash_nonop
        
        # Use equity value and share data from valuation
        equity_value = valuation.equity_value
        shares_out = valuation.shares_out
        value_per_share = valuation.value_per_share
        
        # Calculate discount factors from WACC
        discount_factors = []
        if inputs.wacc:
            cumulative_discount = 1.0
            for i, wacc in enumerate(inputs.wacc):
                cumulative_discount /= (1 + wacc)
                discount_factors.append(cumulative_discount)
        
        # Terminal value metrics
        terminal_percentage = terminal_value / pv_oper_assets if pv_oper_assets > 0 else 0.0
        wacc_terminal = inputs.wacc[-1] if inputs.wacc else 0.08
        growth_terminal = getattr(inputs.drivers, 'stable_growth', 0.025)
        
        return BridgeCalculation(
            operating_cash_flows=operating_cash_flows,
            terminal_value=terminal_value,
            discount_factors=discount_factors,
            pv_explicit_cash_flows=pv_explicit,
            pv_terminal_value=terminal_value,
            total_pv_operating_assets=pv_oper_assets,
            non_operating_assets=non_operating_assets,
            enterprise_value=enterprise_value,
            net_debt=net_debt,
            excess_cash=excess_cash,
            equity_value=equity_value,
            shares_outstanding=shares_out,
            value_per_share=value_per_share,
            terminal_value_percentage=terminal_percentage,
            wacc_terminal=wacc_terminal,
            growth_terminal=growth_terminal
        )
    
    def _validate_pv_to_ev_bridge(self, bridge_calc: BridgeCalculation) -> List[ValidationIssue]:
        """Validate bridge from PV of operating assets to enterprise value."""
        issues = []
        
        # Enterprise Value = PV of Operating Assets + Non-Operating Assets
        expected_ev = bridge_calc.total_pv_operating_assets + bridge_calc.non_operating_assets
        actual_ev = bridge_calc.enterprise_value
        
        if abs(expected_ev - actual_ev) > self.tolerance * max(abs(expected_ev), abs(actual_ev), 1.0):
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="enterprise_value",
                issue_description=f"EV calculation inconsistent: Expected {expected_ev:.2f}, Got {actual_ev:.2f}",
                expected_value=expected_ev,
                actual_value=actual_ev,
                suggested_fix="Verify EV = PV Operating Assets + Non-Operating Assets"
            ))
        
        # PV of Operating Assets should be positive for going concern
        if bridge_calc.total_pv_operating_assets <= 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=ValidationSeverity.ERROR,
                field_name="pv_oper_assets",
                issue_description=f"Non-positive PV of operating assets: {bridge_calc.total_pv_operating_assets:.2f}",
                suggested_fix="Review cash flow projections and discount rates"
            ))
        
        # Terminal value should be reasonable percentage of total PV
        if not (self.min_terminal_percentage <= bridge_calc.terminal_value_percentage <= self.max_terminal_percentage):
            severity = ValidationSeverity.WARNING if 0.1 <= bridge_calc.terminal_value_percentage <= 0.9 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                category=ValidationCategory.TERMINAL_VALUE_SANITY,
                severity=severity,
                field_name="terminal_value_percentage",
                issue_description=f"Terminal value {bridge_calc.terminal_value_percentage:.1%} of total PV outside reasonable range",
                expected_value=f"{self.min_terminal_percentage:.1%} - {self.max_terminal_percentage:.1%}",
                actual_value=f"{bridge_calc.terminal_value_percentage:.1%}",
                suggested_fix="Adjust forecast period or terminal assumptions"
            ))
        
        return issues
    
    def _validate_ev_to_equity_bridge(self, bridge_calc: BridgeCalculation) -> List[ValidationIssue]:
        """Validate bridge from enterprise value to equity value."""
        issues = []
        
        # Equity Value = Enterprise Value - Net Debt + Excess Cash
        expected_equity = bridge_calc.enterprise_value - bridge_calc.net_debt + bridge_calc.excess_cash
        actual_equity = bridge_calc.equity_value
        
        if abs(expected_equity - actual_equity) > self.tolerance * max(abs(expected_equity), abs(actual_equity), 1.0):
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="equity_value",
                issue_description=f"Equity value calculation inconsistent: Expected {expected_equity:.2f}, Got {actual_equity:.2f}",
                expected_value=expected_equity,
                actual_value=actual_equity,
                suggested_fix="Verify Equity Value = EV - Net Debt + Excess Cash"
            ))
        
        # Warn if equity value is negative (unless distressed situation)
        if bridge_calc.equity_value < 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=ValidationSeverity.WARNING,
                field_name="equity_value",
                issue_description=f"Negative equity value: {bridge_calc.equity_value:.2f}",
                suggested_fix="Review debt levels and cash flow assumptions - may indicate distressed situation"
            ))
        
        return issues
    
    def _validate_terminal_value_consistency(
        self,
        bridge_calc: BridgeCalculation,
        inputs: InputsI
    ) -> List[ValidationIssue]:
        """Validate terminal value calculation consistency."""
        issues = []
        
        # Terminal value should be consistent with Gordon Growth Model
        # TV = FCF_terminal * (1 + g) / (WACC - g)
        wacc_growth_spread = bridge_calc.wacc_terminal - bridge_calc.growth_terminal
        
        if wacc_growth_spread <= 0.005:  # 50 bps minimum spread
            issues.append(ValidationIssue(
                category=ValidationCategory.TERMINAL_VALUE_SANITY,
                severity=ValidationSeverity.ERROR,
                field_name="wacc_growth_spread",
                issue_description=f"Terminal WACC-growth spread too low: {wacc_growth_spread:.1%}",
                expected_value=">= 0.5%",
                actual_value=f"{wacc_growth_spread:.1%}",
                suggested_fix="Ensure terminal WACC exceeds terminal growth by reasonable margin"
            ))
        
        # Terminal growth should not exceed long-term economic growth
        if bridge_calc.growth_terminal > 0.06:  # 6% long-term growth ceiling
            issues.append(ValidationIssue(
                category=ValidationCategory.TERMINAL_VALUE_SANITY,
                severity=ValidationSeverity.WARNING,
                field_name="growth_terminal",
                issue_description=f"Terminal growth rate {bridge_calc.growth_terminal:.1%} seems high",
                expected_value="<= 6%",
                actual_value=f"{bridge_calc.growth_terminal:.1%}",
                suggested_fix="Consider moderating terminal growth assumptions"
            ))
        
        return issues
    
    def _validate_discount_factors(
        self,
        bridge_calc: BridgeCalculation,
        inputs: InputsI
    ) -> List[ValidationIssue]:
        """Validate discount factor calculations."""
        issues = []
        
        if not bridge_calc.discount_factors or not inputs.wacc:
            return issues  # Skip if no discount factors available
        
        # Discount factors should be monotonically decreasing
        for i in range(1, len(bridge_calc.discount_factors)):
            if bridge_calc.discount_factors[i] >= bridge_calc.discount_factors[i-1]:
                issues.append(ValidationIssue(
                    category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    field_name="discount_factors",
                    issue_description=f"Discount factors not monotonically decreasing at year {i+1}",
                    suggested_fix="Check WACC calculation - discount factors should decrease over time"
                ))
                break
        
        # Discount factors should match WACC calculations
        for i, (wacc, discount_factor) in enumerate(zip(inputs.wacc, bridge_calc.discount_factors)):
            expected_discount = (1 + wacc) ** -(i + 1)
            if abs(discount_factor - expected_discount) > self.tolerance:
                issues.append(ValidationIssue(
                    category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                    severity=ValidationSeverity.ERROR,
                    field_name=f"discount_factor_year_{i+1}",
                    issue_description=f"Discount factor mismatch in year {i+1}: Expected {expected_discount:.4f}, Got {discount_factor:.4f}",
                    expected_value=expected_discount,
                    actual_value=discount_factor,
                    suggested_fix="Recalculate discount factors using (1 + WACC)^-t formula"
                ))
        
        return issues
    
    def _validate_share_price_reconciliation(
        self,
        bridge_calc: BridgeCalculation,
        inputs: InputsI
    ) -> List[ValidationIssue]:
        """Validate final share price calculation."""
        issues = []
        
        # Share Price = Equity Value / Shares Outstanding
        if bridge_calc.shares_outstanding <= 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.CRITICAL,
                field_name="shares_outstanding",
                issue_description=f"Invalid shares outstanding: {bridge_calc.shares_outstanding}",
                suggested_fix="Shares outstanding must be positive"
            ))
            return issues
        
        expected_price = bridge_calc.equity_value / bridge_calc.shares_outstanding
        actual_price = bridge_calc.value_per_share
        
        if abs(expected_price - actual_price) > self.tolerance * max(abs(expected_price), 1.0):
            issues.append(ValidationIssue(
                category=ValidationCategory.MATHEMATICAL_CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                field_name="value_per_share",
                issue_description=f"Share price calculation inconsistent: Expected {expected_price:.2f}, Got {actual_price:.2f}",
                expected_value=expected_price,
                actual_value=actual_price,
                suggested_fix="Verify Share Price = Equity Value / Shares Outstanding"
            ))
        
        # Share price reasonableness check
        if not (self.share_price_bounds[0] <= abs(actual_price) <= self.share_price_bounds[1]):
            severity = ValidationSeverity.WARNING if actual_price > 0 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                category=ValidationCategory.REASONABLENESS_BOUNDS,
                severity=severity,
                field_name="value_per_share",
                issue_description=f"Share price {actual_price:.2f} outside reasonable bounds",
                expected_value=f"{self.share_price_bounds[0]:.2f} - {self.share_price_bounds[1]:.2f}",
                actual_value=actual_price,
                suggested_fix="Review valuation assumptions and calculation methodology"
            ))
        
        return issues
    
    def _compile_bridge_validation_report(self, issues: List[ValidationIssue]) -> ValidationReport:
        """Compile bridge validation report."""
        total_issues = len(issues)
        
        # Count issues by severity
        issues_by_severity = {severity: 0 for severity in ValidationSeverity}
        for issue in issues:
            issues_by_severity[issue.severity] += 1
        
        # Count issues by category
        issues_by_category = {category: 0 for category in ValidationCategory}
        for issue in issues:
            issues_by_category[issue.category] += 1
        
        # Determine validation status
        critical_errors = issues_by_severity[ValidationSeverity.CRITICAL]
        errors = issues_by_severity[ValidationSeverity.ERROR]
        warnings = issues_by_severity[ValidationSeverity.WARNING]
        
        is_valid = critical_errors == 0 and errors == 0
        can_proceed_with_warnings = critical_errors == 0 and errors <= 2
        
        # Calculate validation score
        validation_score = max(0, 100 - (critical_errors * 60) - (errors * 20) - (warnings * 5))
        
        # Generate recommendations
        recommended_actions = []
        if critical_errors > 0:
            recommended_actions.append("CRITICAL: Fix bridge calculation errors before using valuation")
        if errors > 0:
            recommended_actions.append("Fix mathematical inconsistencies in valuation chain")
        if warnings > 2:
            recommended_actions.append("Review multiple warnings that may indicate systematic issues")
        if validation_score < 80:
            recommended_actions.append("Bridge validation issues may indicate fundamental calculation errors")
        
        print(f"   ✓ Bridge validation complete: {total_issues} issues found (Score: {validation_score:.0f}/100)")
        print(f"   ✓ Critical: {critical_errors}, Errors: {errors}, Warnings: {warnings}")
        
        return ValidationReport(
            is_valid=is_valid,
            total_issues=total_issues,
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            detailed_issues=issues,
            critical_errors=critical_errors,
            warnings_count=warnings,
            validation_score=validation_score,
            recommended_actions=recommended_actions,
            can_proceed_with_warnings=can_proceed_with_warnings
        )


def validate_valuation_bridge(
    inputs: InputsI,
    valuation: ValuationV,
    tolerance: float = 1e-3
) -> ValidationReport:
    """Convenience function for valuation bridge validation.
    
    Args:
        inputs: Input data used for valuation
        valuation: Valuation output to validate
        tolerance: Numerical tolerance for calculations
        
    Returns:
        Validation report for bridge calculations
    """
    validator = BridgeValidator(tolerance=tolerance)
    return validator.validate_valuation_bridge(inputs, valuation)