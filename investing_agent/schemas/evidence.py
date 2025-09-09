from __future__ import annotations

"""
Evidence Schema Foundation for Research-Once Pipeline

Defines structured evidence collection with confidence scoring, driver mapping,
and provenance tracking for deterministic valuation adjustments.
"""

from datetime import datetime
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class SnapshotReference(BaseModel):
    """Reference to source content snapshot with integrity verification."""
    url: str = Field(..., description="Source URL where content was retrieved")
    retrieved_at: str = Field(..., description="ISO timestamp of retrieval")
    content_sha256: str = Field(..., description="SHA256 hash of content for integrity")
    license_info: Optional[str] = Field(None, description="Content licensing information")
    
    @field_validator('retrieved_at')
    @classmethod
    def validate_timestamp(cls, v):
        # Ensure valid ISO format
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('timestamp must be valid ISO format')
        return v
    
    @field_validator('content_sha256')
    @classmethod
    def validate_sha256(cls, v):
        if not v or len(v) != 64:
            raise ValueError('content_sha256 must be 64-character hex string')
        return v


class EvidenceClaim(BaseModel):
    """Individual claim extracted from source with driver impact mapping."""
    driver: Literal["growth", "margin", "wacc", "s2c"] = Field(
        ..., description="Valuation driver affected by this claim"
    )
    statement: str = Field(..., description="Natural language statement of the claim")
    direction: Literal["+", "-", "unclear"] = Field(
        ..., description="Direction of impact on valuation driver"
    )
    magnitude_units: Literal["%", "bps", "abs"] = Field(
        ..., description="Units for magnitude measurement"
    )
    magnitude_value: Optional[float] = Field(
        None, description="Quantified impact magnitude if available"
    )
    horizon: Literal["y1", "y2-3", "LT"] = Field(
        ..., description="Time horizon for impact (Year 1, Years 2-3, Long Term)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this claim (0.0-1.0)"
    )
    quote: str = Field(..., description="Direct quote from source supporting claim")
    page_ref: Optional[int] = Field(None, description="Page reference in source document")
    line_range: Optional[List[int]] = Field(
        None, description="Line range [start, end] in source document"
    )
    
    @field_validator('line_range')
    @classmethod
    def validate_line_range(cls, v):
        if v is not None:
            if len(v) != 2 or v[0] > v[1] or any(x < 0 for x in v):
                raise ValueError('line_range must be [start, end] with start <= end and both >= 0')
        return v
    
    @model_validator(mode='after')
    def validate_magnitude_bounds(self):
        """Apply safety caps for magnitude changes."""
        if self.magnitude_value is None:
            return self
            
        if self.driver == 'growth' and self.magnitude_units in ['%', 'bps']:
            # Growth changes ≤500bps (5%) per evidence item
            max_val = 5.0 if self.magnitude_units == '%' else 500.0
            if abs(self.magnitude_value) > max_val:
                raise ValueError(f'growth magnitude exceeds {max_val}{self.magnitude_units} cap')
                
        elif self.driver == 'margin' and self.magnitude_units in ['%', 'bps']:
            # Margin changes ≤200bps (2%) per evidence item  
            max_val = 2.0 if self.magnitude_units == '%' else 200.0
            if abs(self.magnitude_value) > max_val:
                raise ValueError(f'margin magnitude exceeds {max_val}{self.magnitude_units} cap')
                
        return self


class EvidenceItem(BaseModel):
    """Single evidence item with metadata and extracted claims."""
    id: str = Field(..., description="Unique evidence identifier (e.g., 'ev_ab12cd34')")
    source_url: str = Field(..., description="Original source URL")
    snapshot_id: str = Field(..., description="Snapshot reference ID")
    date: Optional[str] = Field(None, description="Publication/filing date (YYYY-MM-DD)")
    source_type: Literal["10K", "10Q", "8K", "PR", "transcript", "news"] = Field(
        ..., description="Type of source document"
    )
    title: str = Field(..., description="Document title or headline")
    claims: List[EvidenceClaim] = Field(
        default_factory=list, description="Extracted claims from this evidence"
    )
    
    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v):
        if not v.startswith('ev_') or len(v) < 6:
            raise ValueError('evidence id must start with "ev_" and be at least 6 characters')
        return v
    
    @field_validator('snapshot_id')  
    @classmethod
    def validate_snapshot_id(cls, v):
        if not v.startswith('snap_') or len(v) < 8:
            raise ValueError('snapshot_id must start with "snap_" and be at least 8 characters')
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('date must be in YYYY-MM-DD format')
        return v


class EvidenceBundle(BaseModel):
    """Complete evidence collection from research pass with metadata."""
    research_timestamp: str = Field(..., description="ISO timestamp of research execution")
    ticker: str = Field(..., description="Stock ticker symbol")
    frozen: bool = Field(default=False, description="Whether evidence is frozen (immutable)")
    freeze_timestamp: Optional[str] = Field(None, description="ISO timestamp of freeze action")
    content_hash: Optional[str] = Field(None, description="Hash of bundle for integrity checking")
    items: List[EvidenceItem] = Field(
        default_factory=list, description="Evidence items collected during research"
    )
    
    @field_validator('research_timestamp', 'freeze_timestamp')
    @classmethod
    def validate_timestamps(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('timestamp must be valid ISO format')
        return v
    
    @model_validator(mode='after')
    def validate_freeze_state(self):
        if self.frozen and self.freeze_timestamp is None:
            raise ValueError('freeze_timestamp required when frozen=True')
        if not self.frozen and self.freeze_timestamp is not None:
            raise ValueError('freeze_timestamp not allowed when frozen=False')
            
        return self
    
    def freeze(self) -> None:
        """Mark evidence bundle as frozen (immutable)."""
        if self.frozen:
            raise ValueError('Evidence bundle is already frozen')
            
        self.frozen = True
        self.freeze_timestamp = datetime.now().isoformat()
        
        # Generate content hash for integrity verification
        import hashlib
        import json
        content = {
            'ticker': self.ticker,
            'research_timestamp': self.research_timestamp,
            'items': [item.dict() for item in self.items]
        }
        self.content_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
    
    def get_high_confidence_claims(self, threshold: float = 0.80) -> List[EvidenceClaim]:
        """Extract claims above confidence threshold for driver application."""
        claims = []
        for item in self.items:
            for claim in item.claims:
                if claim.confidence >= threshold:
                    claims.append(claim)
        return claims
    
    def get_claims_by_driver(self, driver: str) -> List[EvidenceClaim]:
        """Get all claims affecting specific driver."""
        claims = []
        for item in self.items:
            for claim in item.claims:
                if claim.driver == driver:
                    claims.append(claim)
        return claims
    
    def validate_integrity(self) -> bool:
        """Verify content hash matches current content."""
        if not self.content_hash:
            return False
            
        import hashlib
        import json
        content = {
            'ticker': self.ticker,
            'research_timestamp': self.research_timestamp,
            'items': [item.dict() for item in self.items]
        }
        expected_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        
        return expected_hash == self.content_hash


class EvidenceValidationResult(BaseModel):
    """Result of evidence validation with issues and recommendations."""
    is_valid: bool = Field(..., description="Whether evidence passes validation")
    total_claims: int = Field(..., description="Total number of claims processed")
    high_confidence_claims: int = Field(..., description="Claims above confidence threshold")
    issues: List[str] = Field(default_factory=list, description="Validation issues found")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    
    coverage_metrics: dict = Field(
        default_factory=dict, description="Evidence coverage analysis"
    )


def validate_evidence_bundle(bundle: EvidenceBundle, confidence_threshold: float = 0.80) -> EvidenceValidationResult:
    """Comprehensive validation of evidence bundle quality and coverage."""
    issues = []
    recommendations = []
    
    total_claims = sum(len(item.claims) for item in bundle.items)
    high_confidence_claims = len(bundle.get_high_confidence_claims(confidence_threshold))
    
    # Coverage analysis
    drivers_covered = set()
    source_types = set()
    
    for item in bundle.items:
        source_types.add(item.source_type)
        for claim in item.claims:
            if claim.confidence >= confidence_threshold:
                drivers_covered.add(claim.driver)
    
    # Validation checks
    if total_claims == 0:
        issues.append("No claims extracted from evidence")
    
    if high_confidence_claims / max(total_claims, 1) < 0.5:
        issues.append(f"Low confidence ratio: {high_confidence_claims}/{total_claims}")
        recommendations.append("Review evidence quality and extraction methods")
    
    if len(drivers_covered) < 2:
        issues.append(f"Limited driver coverage: {list(drivers_covered)}")
        recommendations.append("Seek evidence for additional valuation drivers")
    
    if bundle.frozen and not bundle.validate_integrity():
        issues.append("Frozen evidence bundle failed integrity verification")
    
    coverage_metrics = {
        "drivers_covered": list(drivers_covered),
        "source_types": list(source_types),
        "confidence_ratio": high_confidence_claims / max(total_claims, 1),
        "claims_per_item": total_claims / max(len(bundle.items), 1)
    }
    
    return EvidenceValidationResult(
        is_valid=len(issues) == 0,
        total_claims=total_claims,
        high_confidence_claims=high_confidence_claims,
        issues=issues,
        recommendations=recommendations,
        coverage_metrics=coverage_metrics
    )