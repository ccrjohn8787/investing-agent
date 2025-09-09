# Evidence Pipeline Guide

This guide provides comprehensive documentation for the Evidence-Based Research Pipeline, a key component of the DBOT Quality Gap implementation that transforms investment reports from numbers-only to professional story-to-numbers analysis.

## Overview

The Evidence Pipeline implements a "research-once-then-freeze" architecture that ensures deterministic, auditable, and reproducible investment analysis by:

1. **Single Research Pass**: Comprehensive evidence gathering during initial execution
2. **Evidence Freezing**: Immutable evidence bundles prevent value drift across runs
3. **Complete Audit Trail**: Full provenance chain from source URLs to final valuation impact
4. **Safety Validation**: Confidence thresholds and caps prevent poor evidence from affecting results

## Architecture Components

### Core Schemas (`investing_agent/schemas/`)

#### Evidence Schema (`evidence.py`)
- **EvidenceBundle**: Container for all evidence items with research timestamp and freeze status
- **EvidenceItem**: Individual source with claims (10K, earnings call, news article, etc.)
- **EvidenceClaim**: Specific statement with driver impact, confidence, and magnitude
- **SnapshotReference**: Source content capture with integrity verification

#### Model-PR Log Schema (`model_pr_log.py`)
- **ModelPRLog**: Complete change tracking system
- **DriverChange**: Individual driver modification with full provenance
- **ConflictResolution**: Handling of competing evidence claims

### Orchestration Layer (`investing_agent/orchestration/`)

#### Evidence Integration (`evidence_integration.py`)
- **EvidenceIntegrationManager**: Main coordination class
- **integrate_evidence_pipeline()**: Convenience function for pipeline execution
- **create_evidence_narrative_context()**: Context creation for writer agents

#### Evidence Processing (`evidence_processor.py`)
- **EvidenceProcessor**: Core evidence ingestion engine
- **ingest_evidence()**: Apply evidence to InputsI with validation
- **validate_evidence_bundle_quality()**: Quality metrics and coverage analysis

#### Evidence Freezing (`evidence_freezer.py`)
- **EvidenceFreezer**: Immutability mechanism
- **freeze_evidence_bundle()**: Create immutable evidence with content hash
- **verify_freeze_integrity()**: Validate frozen evidence integrity

#### PR Logging (`pr_logger.py`)
- **PRLogger**: Atomic change application service
- **apply_evidence_to_inputs()**: Evidence→driver change mapping with validation
- **generate_audit_report()**: Complete audit trail generation

#### Snapshot Management (`snapshot_manager.py`)
- **SnapshotManager**: Provenance tracking system
- **create_snapshot()**: Capture source content with integrity verification
- **create_provenance_chain()**: Complete source→valuation tracking

### Research Agent (`investing_agent/agents/`)

#### Unified Research Agent (`research_unified.py`)
- **ResearchUnified**: Single comprehensive research agent
- **execute_research_pass()**: 3-phase evidence generation
- **generate_evidence_bundle()**: Evidence extraction with confidence scoring

## Usage Patterns

### Basic Evidence-Enhanced Report Generation

```bash
# Generate report with evidence pipeline (default settings)
python scripts/report_with_evidence.py META

# Disable evidence pipeline for backward compatibility
python scripts/report_with_evidence.py META --disable-evidence

# Set custom confidence threshold (default: 0.80)
python scripts/report_with_evidence.py META --evidence-threshold 0.85

# Force new research (override frozen evidence)
python scripts/report_with_evidence.py META --force-new-research
```

### Deterministic Testing with Cassettes

```bash
# Use evidence cassette for reproducible testing
python scripts/report_with_evidence.py META --evidence-cassette evals/evidence_pipeline/cassettes/meta_evidence.json

# Record new evidence cassette
python scripts/report_with_evidence.py META --evidence-cassette-out out/META/evidence_cassette.json
```

### Integration Testing

```bash
# Run comprehensive integration tests
python -m pytest evals/evidence_pipeline/test_evidence_integration.py -v

# Run driver accuracy validation tests  
python -m pytest evals/evidence_pipeline/test_driver_accuracy.py -v

# Run full evidence evaluation framework
python evals/evidence_pipeline/test_evidence_integration.py
```

## Evidence Processing Flow

### 1. Research Phase (3-Phase Processing)

**Phase 1: Headline Analysis**
- Filter sources for valuation relevance
- Exit early for non-material content
- Focus on earnings calls, filings, guidance updates

**Phase 2: Materiality Assessment**
- Assess potential driver impact
- Determine confidence levels
- Identify key claims for full extraction

**Phase 3: Full Extraction**
- Extract specific claims with quantitative impact
- Assign confidence scores (0.0-1.0)
- Map claims to driver categories (growth, margin, wacc, s2c)

### 2. Evidence Ingestion

**Validation Phase**
- Quality metrics calculation (coverage, confidence distribution)
- Safety validation (confidence thresholds, magnitude caps)
- Conflict detection between competing claims

**Application Phase**
- Map evidence claims to specific driver changes
- Apply safety caps: growth ≤500bps, margin ≤200bps per evidence item
- Filter by confidence threshold (default ≥0.80)
- Resolve conflicts using highest confidence claims

**Logging Phase**
- Complete Model-PR log generation
- Audit trail creation with provenance chain
- Change validation and integrity checking

### 3. Evidence Freezing

**Freezing Process**
- Content hash generation for immutability
- Timestamp recording for tracking
- Integration with manifest system

**Verification**
- Integrity checking of frozen evidence
- Hash validation on subsequent runs
- Error detection for corrupted evidence

## Data Structures

### Evidence Bundle Format

```json
{
  "evidence_bundle": {
    "research_timestamp": "2025-01-27T10:00:00Z",
    "ticker": "META",
    "frozen": true,
    "freeze_timestamp": "2025-01-27T10:05:00Z",
    "content_hash": "sha256:abc123...",
    "items": [
      {
        "id": "ev_meta_q4_2024",
        "source_url": "https://investor.fb.com/investor-events/",
        "snapshot_id": "snap_meta_001",
        "date": "2025-01-15",
        "source_type": "transcript",
        "title": "Meta Q4 2024 Earnings Call",
        "claims": [
          {
            "driver": "growth",
            "statement": "Management guidance suggests 15-20% revenue growth for 2025",
            "direction": "+",
            "magnitude_units": "%",
            "magnitude_value": 17.5,
            "horizon": "y1",
            "confidence": 0.88,
            "quote": "We expect revenue growth of 15-20% in 2025 driven by AI investments"
          }
        ]
      }
    ]
  }
}
```

### Model-PR Log Format

```json
{
  "model_pr_log": {
    "ticker": "META",
    "timestamp": "2025-01-27T10:05:00Z",
    "validation_summary": {
      "total_attempted": 5,
      "total_applied": 3,
      "total_rejected": 2,
      "confidence_threshold": 0.80
    },
    "changes": [
      {
        "evidence_id": "ev_meta_q4_2024",
        "target_path": "drivers.sales_growth[0]",
        "before_value": 0.10,
        "after_value": 0.175,
        "change_magnitude": 0.075,
        "change_reason": "Management guidance Q4 2024 call",
        "applied_rule": "growth_cap_y1_500bps",
        "cap_applied": false,
        "confidence_threshold": 0.80,
        "claim_confidence": 0.88,
        "timestamp": "2025-01-27T10:05:00Z"
      }
    ]
  }
}
```

## Safety Mechanisms

### Confidence Filtering
- **Default Threshold**: 0.80 (only high-confidence claims applied)
- **Configurable**: `--evidence-threshold` parameter
- **Validation**: Claims below threshold are logged but not applied

### Safety Caps
- **Growth Changes**: ≤500 basis points (5%) per evidence item
- **Margin Changes**: ≤200 basis points (2%) per evidence item
- **Application**: Caps applied per evidence item, multiple items can compound
- **Logging**: Cap applications recorded in Model-PR log

### Conflict Resolution
- **Strategy**: Highest confidence claim wins
- **Logging**: All conflicts and resolutions logged
- **Validation**: Ensures consistent driver modifications

## File Structure

### Output Directory Layout
```
out/<TICKER>/
├── evidence/
│   ├── frozen_evidence_<TICKER>_<timestamp>.json    # Immutable evidence bundle
│   ├── model_pr_log_<TICKER>.json                   # Complete change log
│   └── snapshots/                                   # Source content captures
│       ├── <snapshot_id>.html                       # Raw source content
│       └── <snapshot_id>_meta.json                 # Snapshot metadata
├── report.md                                        # Enhanced report with evidence
├── inputs.json                                      # Evidence-modified inputs
├── valuation.json                                   # Valuation results
└── manifest.json                                    # Complete provenance record
```

### Evidence Files
- **Frozen Evidence**: Immutable evidence bundles with content hashes
- **Model-PR Log**: Complete audit trail of all driver changes
- **Snapshots**: Raw source content with integrity verification
- **Manifest**: Provenance tracking and artifact inventory

## Integration Patterns

### Backward Compatibility
The evidence pipeline can be completely disabled for backward compatibility:

```python
# Disable evidence pipeline
python scripts/report_with_evidence.py TICKER --disable-evidence

# This is equivalent to using the standard report.py
python scripts/report.py TICKER
```

### Progressive Enhancement
Evidence pipeline enhances existing reports without breaking changes:

```python
from investing_agent.orchestration.evidence_integration import integrate_evidence_pipeline

# Standard valuation
inputs_standard = build_inputs(ticker)
valuation_standard = kernel_value(inputs_standard)

# Evidence-enhanced valuation  
inputs_enhanced, evidence_artifacts = integrate_evidence_pipeline(
    ticker=ticker,
    inputs=inputs_standard,
    manifest=manifest,
    confidence_threshold=0.80
)
valuation_enhanced = kernel_value(inputs_enhanced)
```

### Cassette-Based Testing
Evidence pipeline supports deterministic testing through cassettes:

```python
# Record evidence generation for testing
evidence_bundle = research_agent.execute_research_pass(
    ticker="META",
    inputs=inputs,
    cassette_path="cassettes/meta_evidence.json"
)

# Replay recorded evidence in CI/testing
evidence_bundle = research_agent.execute_research_pass(
    ticker="META", 
    inputs=inputs,
    cassette_path="cassettes/meta_evidence.json"
)
```

## Evaluation and Quality Assurance

### Integration Testing
The evidence pipeline includes comprehensive integration tests:

- **Evidence Generation**: Mock evidence creation and quality validation
- **Driver Changes**: Accuracy of evidence→driver change mapping
- **Freezing Workflow**: Evidence immutability and integrity verification
- **Provenance Chain**: Complete source→valuation tracking validation
- **Safety Validation**: Confidence filtering and cap enforcement

### Quality Metrics
- **Evidence Coverage**: Percentage of claims backed by evidence
- **Confidence Distribution**: Analysis of evidence quality
- **Driver Impact**: Quantitative assessment of evidence→valuation impact
- **Audit Completeness**: Validation of complete provenance chain

### Performance Monitoring
- **Test Success Rate**: Currently 83% (5/6 tests passing)
- **Evidence Quality Score**: Comprehensive bundle quality assessment
- **Integration Stability**: Backward compatibility and error handling

## Best Practices

### Development Workflow
1. **Always test with evidence disabled first** to ensure backward compatibility
2. **Use appropriate confidence thresholds** based on evidence quality
3. **Validate frozen evidence integrity** before using in production
4. **Monitor Model-PR logs** for unexpected driver changes

### Production Deployment
1. **Start with evidence disabled** for existing systems
2. **Gradually enable with high confidence thresholds** (0.85+)
3. **Monitor audit trails** for quality assurance
4. **Validate evidence freezing** prevents value drift

### Troubleshooting
1. **Check evidence bundle quality** if results seem unusual
2. **Review Model-PR log** for applied changes
3. **Validate snapshot integrity** for provenance issues
4. **Use `--disable-evidence`** to isolate evidence-related problems

## Future Development

The evidence pipeline provides the foundation for Priority 2: Writer/Critic Upgrade, which will:

- **Read-Only Writer**: Prevent number generation, only cite evidence IDs
- **Strict Citation Discipline**: Per-sentence evidence tagging requirement
- **Professional Narrative**: Rich storytelling with evidence backing
- **Enhanced Critic**: Detect and block uncited claims or novel numbers

This architecture ensures that the investment analysis system can scale to professional-grade story-to-numbers reports while maintaining complete auditability and deterministic reproducibility.