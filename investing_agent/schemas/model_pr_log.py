from __future__ import annotations

"""
Model-PR Log System for Evidence-Based Driver Changes

Provides complete auditability of valuation driver modifications with
provenance tracking from evidence claims to final InputsI values.
"""

from datetime import datetime
from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator
import json


class DriverChange(BaseModel):
    """Individual driver modification with complete provenance."""
    evidence_id: str = Field(..., description="Evidence item ID that triggered this change")
    target_path: str = Field(..., description="JSONPath to modified field (e.g., 'drivers.sales_growth[0]')")
    before_value: Union[float, int, None] = Field(..., description="Original value before change")
    after_value: Union[float, int] = Field(..., description="New value after change applied")
    change_reason: str = Field(..., description="Human-readable reason for change")
    applied_rule: str = Field(..., description="Rule/policy that governed the change")
    cap_applied: bool = Field(default=False, description="Whether safety cap was applied")
    confidence_threshold: float = Field(..., description="Minimum confidence required for change")
    claim_confidence: float = Field(..., description="Actual confidence of evidence claim")
    timestamp: str = Field(..., description="ISO timestamp of change application")
    
    @field_validator('evidence_id')
    @classmethod
    def validate_evidence_id(cls, v):
        if not v.startswith('ev_'):
            raise ValueError('evidence_id must start with "ev_"')
        return v
    
    @field_validator('target_path')
    @classmethod
    def validate_target_path(cls, v):
        # Basic validation of JSONPath format
        valid_prefixes = ['drivers.', 'sales_to_capital', 'wacc', 'macro.', 'tax_rate']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f'target_path must start with one of: {valid_prefixes}')
        return v
    
    @field_validator('confidence_threshold', 'claim_confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence values must be between 0.0 and 1.0')
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('timestamp must be valid ISO format')
        return v
    
    @property
    def change_magnitude(self) -> float:
        """Calculate absolute change magnitude."""
        if self.before_value is None:
            return abs(self.after_value) if self.after_value is not None else 0.0
        return abs(self.after_value - self.before_value)
    
    @property
    def change_direction(self) -> str:
        """Determine direction of change."""
        if self.before_value is None:
            return "new" if self.after_value != 0 else "zero"
        if self.after_value > self.before_value:
            return "increase"
        elif self.after_value < self.before_value:
            return "decrease"
        else:
            return "unchanged"


class ConflictResolution(BaseModel):
    """Record of how conflicting evidence claims were resolved."""
    target_path: str = Field(..., description="Driver path where conflict occurred")
    conflicting_evidence_ids: List[str] = Field(..., description="Evidence IDs in conflict")
    resolution_method: str = Field(..., description="Method used to resolve conflict")
    winning_evidence_id: str = Field(..., description="Evidence ID that was applied")
    resolution_reason: str = Field(..., description="Explanation of resolution choice")
    timestamp: str = Field(..., description="ISO timestamp of resolution")
    
    @field_validator('conflicting_evidence_ids')
    @classmethod
    def validate_evidence_ids(cls, v):
        if len(v) < 2:
            raise ValueError('conflict requires at least 2 evidence IDs')
        for eid in v:
            if not eid.startswith('ev_'):
                raise ValueError('all evidence IDs must start with "ev_"')
        return v


class ValidationResult(BaseModel):
    """Result of change validation before application."""
    is_valid: bool = Field(..., description="Whether change passed all validation checks")
    applied: bool = Field(default=False, description="Whether change was actually applied")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking warnings")
    caps_triggered: List[str] = Field(default_factory=list, description="Safety caps that were triggered")


class ModelPRLog(BaseModel):
    """Complete log of all model changes with full audit trail."""
    ticker: str = Field(..., description="Stock ticker symbol")
    timestamp: str = Field(..., description="ISO timestamp of log creation")
    evidence_bundle_id: str = Field(..., description="Associated evidence bundle identifier")
    changes: List[DriverChange] = Field(default_factory=list, description="All driver changes applied")
    conflicts_resolved: List[ConflictResolution] = Field(
        default_factory=list, description="Conflicts encountered and resolved"
    )
    validation_summary: dict = Field(default_factory=dict, description="Overall validation summary")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('timestamp must be valid ISO format')
        return v
    
    def add_change(self, change: DriverChange, validation: ValidationResult) -> None:
        """Add validated change to log."""
        if validation.applied:
            self.changes.append(change)
        
        # Update validation summary
        self.validation_summary.setdefault('total_attempted', 0)
        self.validation_summary.setdefault('total_applied', 0)
        self.validation_summary.setdefault('total_rejected', 0)
        
        self.validation_summary['total_attempted'] += 1
        if validation.applied:
            self.validation_summary['total_applied'] += 1
        else:
            self.validation_summary['total_rejected'] += 1
    
    def add_conflict_resolution(self, conflict: ConflictResolution) -> None:
        """Add conflict resolution to log."""
        self.conflicts_resolved.append(conflict)
    
    def get_changes_by_driver(self, driver_path: str) -> List[DriverChange]:
        """Get all changes affecting specific driver."""
        return [change for change in self.changes if change.target_path.startswith(driver_path)]
    
    def get_changes_by_evidence(self, evidence_id: str) -> List[DriverChange]:
        """Get all changes from specific evidence item."""
        return [change for change in self.changes if change.evidence_id == evidence_id]
    
    def calculate_total_impact(self, driver_path: str) -> dict:
        """Calculate cumulative impact on specific driver."""
        changes = self.get_changes_by_driver(driver_path)
        if not changes:
            return {"total_changes": 0, "net_impact": 0.0}
        
        # Sort by timestamp to get chronological order
        sorted_changes = sorted(changes, key=lambda x: x.timestamp)
        
        initial_value = sorted_changes[0].before_value
        final_value = sorted_changes[-1].after_value
        
        net_impact = (final_value - initial_value) if initial_value is not None else final_value
        
        return {
            "total_changes": len(changes),
            "initial_value": initial_value,
            "final_value": final_value,
            "net_impact": net_impact,
            "change_sequence": [
                {
                    "evidence_id": change.evidence_id,
                    "from": change.before_value,
                    "to": change.after_value,
                    "confidence": change.claim_confidence
                }
                for change in sorted_changes
            ]
        }
    
    def generate_audit_report(self) -> dict:
        """Generate comprehensive audit report."""
        # Driver impact analysis
        driver_impacts = {}
        all_paths = set(change.target_path for change in self.changes)
        for path in all_paths:
            driver_impacts[path] = self.calculate_total_impact(path)
        
        # Evidence utilization analysis
        evidence_usage = {}
        for change in self.changes:
            eid = change.evidence_id
            if eid not in evidence_usage:
                evidence_usage[eid] = {
                    "changes_applied": 0,
                    "avg_confidence": 0.0,
                    "paths_affected": set()
                }
            
            evidence_usage[eid]["changes_applied"] += 1
            evidence_usage[eid]["paths_affected"].add(change.target_path)
        
        # Calculate average confidence per evidence item
        for eid, usage in evidence_usage.items():
            changes = self.get_changes_by_evidence(eid)
            usage["avg_confidence"] = sum(c.claim_confidence for c in changes) / len(changes)
            usage["paths_affected"] = list(usage["paths_affected"])
        
        # High-level statistics
        stats = {
            "total_changes": len(self.changes),
            "unique_evidence_items": len(evidence_usage),
            "unique_drivers_affected": len(all_paths),
            "conflicts_resolved": len(self.conflicts_resolved),
            "avg_claim_confidence": sum(c.claim_confidence for c in self.changes) / len(self.changes) if self.changes else 0.0,
            "caps_applied": sum(1 for c in self.changes if c.cap_applied)
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "ticker": self.ticker,
            "statistics": stats,
            "driver_impacts": driver_impacts,
            "evidence_utilization": evidence_usage,
            "validation_summary": self.validation_summary,
            "conflicts_resolved": [c.dict() for c in self.conflicts_resolved]
        }
    
    def export_to_json(self, filepath: str) -> None:
        """Export complete log to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.dict(), f, indent=2, default=str)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> "ModelPRLog":
        """Load log from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)