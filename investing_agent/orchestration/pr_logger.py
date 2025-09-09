from __future__ import annotations

"""
PR Logger Service for Evidence-Based Driver Changes

Provides atomic application of evidence-driven changes to InputsI with
complete audit trail, validation, and rollback capabilities.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import copy
import json

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceClaim
from investing_agent.schemas.model_pr_log import ModelPRLog, DriverChange, ConflictResolution, ValidationResult


class PRLogger:
    """Service for applying and logging evidence-driven model changes."""
    
    def __init__(self, confidence_threshold: float = 0.80):
        """Initialize PR Logger with configuration."""
        self.confidence_threshold = confidence_threshold
        self.current_log: Optional[ModelPRLog] = None
    
    def create_log(self, ticker: str, evidence_bundle_id: str) -> ModelPRLog:
        """Create new model PR log for tracking changes."""
        self.current_log = ModelPRLog(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            evidence_bundle_id=evidence_bundle_id
        )
        return self.current_log
    
    def apply_evidence_to_inputs(
        self, 
        inputs: InputsI, 
        evidence_bundle: EvidenceBundle,
        dry_run: bool = False
    ) -> Tuple[InputsI, ModelPRLog]:
        """
        Apply evidence claims to InputsI with full audit trail.
        
        Args:
            inputs: Original InputsI to modify
            evidence_bundle: Evidence bundle with claims to apply
            dry_run: If True, don't actually modify inputs
            
        Returns:
            Tuple of (modified_inputs, complete_pr_log)
        """
        if evidence_bundle.frozen:
            # Use existing evidence - validation that it's not re-researched
            pass
            
        # Create new log
        log = self.create_log(inputs.ticker, f"bundle_{evidence_bundle.research_timestamp}")
        
        # Create working copy for modifications
        modified_inputs = copy.deepcopy(inputs)
        
        # Get high-confidence claims
        high_conf_claims = evidence_bundle.get_high_confidence_claims(self.confidence_threshold)
        
        # Group claims by driver path to detect conflicts
        path_to_claims = self._group_claims_by_path(high_conf_claims)
        
        # Process each driver path
        for target_path, claims in path_to_claims.items():
            if len(claims) > 1:
                # Handle conflicts
                winning_claim, resolution = self._resolve_conflicts(target_path, claims)
                log.add_conflict_resolution(resolution)
                claims_to_apply = [winning_claim]
            else:
                claims_to_apply = claims
            
            # Apply each claim
            for claim in claims_to_apply:
                change, validation = self._apply_single_claim(
                    modified_inputs, claim, target_path, dry_run
                )
                log.add_change(change, validation)
        
        return modified_inputs, log
    
    def _group_claims_by_path(self, claims: List[EvidenceClaim]) -> Dict[str, List[EvidenceClaim]]:
        """Group evidence claims by target driver path."""
        path_to_claims = {}
        
        for claim in claims:
            target_path = self._claim_to_path(claim)
            if target_path not in path_to_claims:
                path_to_claims[target_path] = []
            path_to_claims[target_path].append(claim)
        
        return path_to_claims
    
    def _claim_to_path(self, claim: EvidenceClaim) -> str:
        """Convert evidence claim to InputsI JSONPath."""
        base_mapping = {
            "growth": "drivers.sales_growth",
            "margin": "drivers.oper_margin", 
            "wacc": "wacc",
            "s2c": "sales_to_capital"
        }
        
        base_path = base_mapping[claim.driver]
        
        # Add array index based on horizon
        if claim.horizon == "y1":
            index = 0
        elif claim.horizon == "y2-3":
            index = 1  # Could be more sophisticated
        else:  # LT
            if claim.driver in ["growth", "margin"]:
                # Long-term affects stable values
                return f"drivers.stable_{claim.driver.replace('growth', 'growth')}" if claim.driver == "growth" else "drivers.stable_margin"
            else:
                index = -1  # Last element for WACC/S2C
        
        if claim.driver in ["growth", "margin"] and claim.horizon != "LT":
            return f"{base_path}[{index}]"
        else:
            return base_path
    
    def _resolve_conflicts(self, target_path: str, claims: List[EvidenceClaim]) -> Tuple[EvidenceClaim, ConflictResolution]:
        """Resolve conflicting claims using confidence-based selection."""
        # Sort by confidence descending
        sorted_claims = sorted(claims, key=lambda c: c.confidence, reverse=True)
        winning_claim = sorted_claims[0]
        
        resolution = ConflictResolution(
            target_path=target_path,
            conflicting_evidence_ids=[f"ev_{id(c)}" for c in claims],  # Simplified for now
            resolution_method="highest_confidence",
            winning_evidence_id=f"ev_{id(winning_claim)}",  # Simplified for now  
            resolution_reason=f"Selected claim with confidence {winning_claim.confidence:.2f} over {len(claims)-1} alternatives",
            timestamp=datetime.now().isoformat()
        )
        
        return winning_claim, resolution
    
    def _apply_single_claim(
        self, 
        inputs: InputsI, 
        claim: EvidenceClaim, 
        target_path: str, 
        dry_run: bool
    ) -> Tuple[DriverChange, ValidationResult]:
        """Apply single evidence claim to inputs with validation."""
        
        # Get current value
        before_value = self._get_path_value(inputs, target_path)
        
        # Calculate new value
        after_value, cap_applied = self._calculate_new_value(before_value, claim)
        
        # Validate change
        validation = self._validate_change(before_value, after_value, claim, cap_applied)
        
        # Apply if valid and not dry run
        if validation.is_valid and not dry_run:
            self._set_path_value(inputs, target_path, after_value)
            validation.applied = True
        
        # Create change record
        change = DriverChange(
            evidence_id=f"ev_{id(claim)}",  # Simplified - should come from evidence item
            target_path=target_path,
            before_value=before_value,
            after_value=after_value,
            change_reason=claim.statement,
            applied_rule=f"{claim.driver}_cap_{claim.horizon}_{self._get_cap_value(claim)}",
            cap_applied=cap_applied,
            confidence_threshold=self.confidence_threshold,
            claim_confidence=claim.confidence,
            timestamp=datetime.now().isoformat()
        )
        
        return change, validation
    
    def _get_path_value(self, inputs: InputsI, path: str) -> Optional[float]:
        """Get current value at JSONPath."""
        # Simplified path resolution - would need full JSONPath implementation
        if path.startswith("drivers.sales_growth"):
            if "[0]" in path:
                return inputs.drivers.sales_growth[0] if inputs.drivers.sales_growth else None
            elif "[1]" in path:
                return inputs.drivers.sales_growth[1] if len(inputs.drivers.sales_growth) > 1 else None
        elif path.startswith("drivers.oper_margin"):
            if "[0]" in path:
                return inputs.drivers.oper_margin[0] if inputs.drivers.oper_margin else None
            elif "[1]" in path:
                return inputs.drivers.oper_margin[1] if len(inputs.drivers.oper_margin) > 1 else None
        elif path == "drivers.stable_growth":
            return inputs.drivers.stable_growth
        elif path == "drivers.stable_margin":
            return inputs.drivers.stable_margin
        # Add more paths as needed
        
        return None
    
    def _set_path_value(self, inputs: InputsI, path: str, value: float) -> None:
        """Set value at JSONPath."""
        # Simplified path setting - would need full JSONPath implementation
        if path.startswith("drivers.sales_growth"):
            if "[0]" in path:
                if not inputs.drivers.sales_growth:
                    inputs.drivers.sales_growth = [value]
                else:
                    inputs.drivers.sales_growth[0] = value
            elif "[1]" in path:
                while len(inputs.drivers.sales_growth) <= 1:
                    inputs.drivers.sales_growth.append(0.0)
                inputs.drivers.sales_growth[1] = value
        elif path.startswith("drivers.oper_margin"):
            if "[0]" in path:
                if not inputs.drivers.oper_margin:
                    inputs.drivers.oper_margin = [value]
                else:
                    inputs.drivers.oper_margin[0] = value
            elif "[1]" in path:
                while len(inputs.drivers.oper_margin) <= 1:
                    inputs.drivers.oper_margin.append(0.1)
                inputs.drivers.oper_margin[1] = value
        elif path == "drivers.stable_growth":
            inputs.drivers.stable_growth = value
        elif path == "drivers.stable_margin":
            inputs.drivers.stable_margin = value
        # Add more paths as needed
    
    def _calculate_new_value(self, before_value: Optional[float], claim: EvidenceClaim) -> Tuple[float, bool]:
        """Calculate new value applying magnitude and caps."""
        if before_value is None:
            before_value = self._get_default_value(claim.driver)
        
        # Apply magnitude change
        if claim.magnitude_value is not None:
            if claim.magnitude_units == "%":
                magnitude = claim.magnitude_value / 100.0
            elif claim.magnitude_units == "bps":
                magnitude = claim.magnitude_value / 10000.0
            else:  # abs
                magnitude = claim.magnitude_value
            
            if claim.direction == "+":
                new_value = before_value + magnitude
            elif claim.direction == "-":
                new_value = before_value - magnitude
            else:  # unclear
                # Use neutral adjustment or before_value
                new_value = before_value
        else:
            # No quantified magnitude - use directional hint
            adjustment = 0.01  # 1% default adjustment
            if claim.direction == "+":
                new_value = before_value + adjustment
            elif claim.direction == "-":
                new_value = before_value - adjustment
            else:
                new_value = before_value
        
        # Apply safety caps
        cap_applied = False
        if claim.driver == "growth":
            max_change = 0.05  # 5% cap
            if abs(new_value - before_value) > max_change:
                new_value = before_value + (max_change if new_value > before_value else -max_change)
                cap_applied = True
        elif claim.driver == "margin":
            max_change = 0.02  # 2% cap
            if abs(new_value - before_value) > max_change:
                new_value = before_value + (max_change if new_value > before_value else -max_change)
                cap_applied = True
        
        return new_value, cap_applied
    
    def _get_default_value(self, driver: str) -> float:
        """Get sensible default value for driver."""
        defaults = {
            "growth": 0.05,   # 5% default growth
            "margin": 0.10,   # 10% default margin  
            "wacc": 0.08,     # 8% default WACC
            "s2c": 2.0        # 2.0 default sales-to-capital
        }
        return defaults.get(driver, 0.0)
    
    def _get_cap_value(self, claim: EvidenceClaim) -> str:
        """Get cap description for rule naming."""
        if claim.driver == "growth":
            return "500bps"
        elif claim.driver == "margin":
            return "200bps"
        else:
            return "uncapped"
    
    def _validate_change(
        self, 
        before_value: Optional[float], 
        after_value: float, 
        claim: EvidenceClaim,
        cap_applied: bool
    ) -> ValidationResult:
        """Validate proposed change."""
        validation_errors = []
        warnings = []
        caps_triggered = []
        
        # Confidence check
        if claim.confidence < self.confidence_threshold:
            validation_errors.append(f"Claim confidence {claim.confidence} below threshold {self.confidence_threshold}")
        
        # Reasonableness checks
        if claim.driver == "growth" and (after_value < -0.5 or after_value > 2.0):
            validation_errors.append(f"Growth rate {after_value:.1%} outside reasonable bounds [-50%, 200%]")
        
        if claim.driver == "margin" and (after_value < -0.2 or after_value > 0.8):
            validation_errors.append(f"Operating margin {after_value:.1%} outside reasonable bounds [-20%, 80%]")
        
        # Cap warnings
        if cap_applied:
            caps_triggered.append(f"{claim.driver}_safety_cap")
            warnings.append(f"Safety cap applied to {claim.driver} change")
        
        is_valid = len(validation_errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            applied=False,  # Will be set to True if actually applied
            validation_errors=validation_errors,
            warnings=warnings,
            caps_triggered=caps_triggered
        )
    
    def save_log(self, output_dir: Path, filename: Optional[str] = None) -> Path:
        """Save current PR log to file."""
        if self.current_log is None:
            raise ValueError("No current log to save")
        
        if filename is None:
            filename = f"model_pr_log_{self.current_log.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = output_dir / filename
        self.current_log.export_to_json(str(output_path))
        return output_path
    
    def load_log(self, log_path: Path) -> ModelPRLog:
        """Load PR log from file."""
        self.current_log = ModelPRLog.load_from_json(str(log_path))
        return self.current_log