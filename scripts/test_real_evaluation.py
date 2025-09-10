#!/usr/bin/env python3
"""Test real evaluation to debug why scores are incorrectly high."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.evaluation.evaluation_runner import EvaluationRunner
from investing_agent.schemas.evaluation_metrics import EvaluationConfig


def analyze_report_content(report_path: Path) -> dict:
    """Analyze report content to understand what's being evaluated."""
    
    content = report_path.read_text()
    
    # Count key indicators
    evidence_citations = content.count('[ev:')
    ref_citations = content.count('[ref:computed:')
    total_citations = evidence_citations + ref_citations
    
    # Count narrative paragraphs (non-table, non-header)
    lines = content.split('\n')
    narrative_paragraphs = 0
    qualitative_statements = 0
    
    for line in lines:
        # Skip headers, tables, empty lines
        if line.strip() and not line.startswith('#') and not line.startswith('|'):
            if len(line) > 100:  # Likely a narrative paragraph
                narrative_paragraphs += 1
                
            # Count qualitative statements
            qualitative_words = ['will', 'expect', 'likely', 'believe', 'suggest', 'indicate']
            if any(word in line.lower() for word in qualitative_words):
                qualitative_statements += 1
    
    return {
        'total_lines': len(lines),
        'evidence_citations': evidence_citations,
        'ref_citations': ref_citations,
        'total_citations': total_citations,
        'narrative_paragraphs': narrative_paragraphs,
        'qualitative_statements': qualitative_statements,
        'has_narrative': narrative_paragraphs > 5,
        'citation_ratio': total_citations / max(qualitative_statements, 1)
    }


def test_evaluation_accuracy():
    """Test evaluation on actual reports to see why scores are wrong."""
    
    print("\n" + "="*60)
    print("EVALUATION ACCURACY TEST")
    print("="*60)
    
    # Test on the actual BYD report we have
    reports_to_test = [
        ("out/BYD/report.md", "BYD", "BYD Company Limited"),
        ("out/META/report.md", "META", "Meta Platforms Inc"),
    ]
    
    for report_path, ticker, company in reports_to_test:
        path = Path(report_path)
        if not path.exists():
            print(f"\n❌ Report not found: {report_path}")
            continue
        
        print(f"\n📊 Testing: {ticker}")
        print("-" * 40)
        
        # Analyze content
        analysis = analyze_report_content(path)
        print(f"Content Analysis:")
        print(f"  • Total lines: {analysis['total_lines']}")
        print(f"  • Evidence citations: {analysis['evidence_citations']}")
        print(f"  • Computed references: {analysis['ref_citations']}")
        print(f"  • Narrative paragraphs: {analysis['narrative_paragraphs']}")
        print(f"  • Qualitative statements: {analysis['qualitative_statements']}")
        print(f"  • Has narrative: {analysis['has_narrative']}")
        print(f"  • Citation ratio: {analysis['citation_ratio']:.2f}")
        
        # Now run actual evaluation
        content = path.read_text()
        
        # Test hard metrics calculation
        runner = EvaluationRunner()
        hard_metrics = runner._calculate_hard_metrics(content)
        
        print(f"\nHard Metrics:")
        print(f"  • Evidence coverage: {hard_metrics.evidence_coverage:.2%}")
        print(f"  • Citation density: {hard_metrics.citation_density:.2f}")
        print(f"  • Contradiction rate: {hard_metrics.contradiction_rate:.2%}")
        print(f"  • Numeric accuracy: {hard_metrics.numeric_accuracy:.2%}")
        print(f"  • Passes gates: {hard_metrics.passes_gates}")
        
        # The problem is likely here - when there's no narrative,
        # the evaluation should score very low, but it's not detecting this
        
        print(f"\n⚠️ Issue Identified:")
        if analysis['narrative_paragraphs'] < 5:
            print(f"  This report has NO NARRATIVE (only {analysis['narrative_paragraphs']} paragraphs)")
            print(f"  But evaluation might be giving high scores anyway!")
            print(f"  Expected score: < 4.0/10 (no narrative)")
            print(f"  Likely getting: > 7.0/10 (mock random scores)")
    
    print("\n" + "="*60)
    print("ROOT CAUSE ANALYSIS")
    print("="*60)
    
    print("""
The evaluation is failing because:

1. **Mock Evaluation Used**: The demo used MOCK evaluation with random scores
   - Mock scores were randomly generated between 6.5-8.5
   - Did NOT actually analyze report content
   
2. **Hard Metrics Miscalculation**: When there's no narrative:
   - Few qualitative claims to evaluate
   - Citation metrics become meaningless
   - Should detect "no narrative" condition
   
3. **LLM Not Actually Called**: In the mock, we never called the LLM
   - Real LLM would detect lack of narrative
   - Would score strategic narrative as 0-2/10
   - Would fail on industry context, investment thesis

4. **Solution Required**:
   - Detect "no narrative" condition explicitly
   - Score reports with < 5 narrative paragraphs as automatic fail
   - Ensure LLM is actually called for real evaluations
   - Add specific checks for required sections
""")


if __name__ == "__main__":
    test_evaluation_accuracy()