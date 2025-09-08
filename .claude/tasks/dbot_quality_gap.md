# DBOT Quality Gap Implementation Plan

**Goal:** Transform the current numbers-focused valuation system into a story-to-numbers approach matching the quality demonstrated in the DBOT paper's BYD report, with research-once-then-freeze architecture for scientific rigor and reproducibility.

## Background Context

**Current State:**
- Robust valuation engine (Ginzu) with deterministic NumPy calculations ✅
- Complete data pipeline from EDGAR, Yahoo/Stooq, UST sources ✅
- Basic agent structure with LLM integration framework ✅
- Comprehensive evaluation and testing infrastructure ✅
- Basic template-based report generation with minimal narrative context
- Limited strategic analysis and industry context

**Target State (BYD Report Quality):**
- Rich storytelling connecting numbers to business reality
- Industry context and competitive positioning analysis  
- Strategic narrative with bull/bear scenarios
- Compelling titles and thematic structure
- Forward-looking market dynamics integration
- Research-once-then-freeze architecture for reproducibility
- Full auditability with evidence→driver change tracking

## Implementation Priorities

### Priority 0: LLM-Based Report Evaluation Framework (CRITICAL FOUNDATION)
**Status:** Ready to Start
**Description:** Build evaluation system that grades reports like Professor Damodaran or investment professionals would, using sub-agent for development

**Key Components:**
- LLM judge sub-agent for holistic report evaluation  
- Hard metric gates for CI: evidence_coverage ≥ 0.80, citation_density ≥ 0.70, contradiction_rate ≤ 0.20
- Multi-dimensional rubric scoring system
- BYD report as evaluation benchmark

### Priority 1: Research-Once Evidence Pipeline + Model-PR Log
**Status:** Pending
**Description:** Single research pass that maps evidence to driver changes with full auditability

### Priority 2: Writer/Critic Upgrade (Read-Only + Strict Citations)
**Status:** Pending
**Description:** Rich narrative with strict citation discipline and zero number hallucination

### Priority 3: Comparables + WACC Foundation Fix
**Status:** Pending
**Description:** Correct numeric foundation with deterministic code

### Priority 4-7: Enhanced Prompts, Router, Report Polish, and Evaluation Dashboard
**Status:** Pending
**Description:** Professional presentation and continuous improvement system

## Success Metrics
- Hard gates: evidence_coverage ≥ 0.80, citation_density ≥ 0.70
- LLM judge scores >8/10 on strategic insight, narrative quality, analytical rigor
- Match BYD report depth while maintaining deterministic numeric accuracy

**Current Priority:** P0 (LLM-Based Report Evaluation Framework)
**Next Action:** Use sub-agent to build comprehensive evaluation system