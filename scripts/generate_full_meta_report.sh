#!/bin/bash
# Generate full professional META report with all P1-7 features

echo "====================================="
echo "GENERATING FULL PROFESSIONAL REPORT"
echo "====================================="
echo ""

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY not set"
    echo "Please run: export OPENAI_API_KEY='your-api-key'"
    exit 1
fi

echo "✅ API Key is set"
echo ""

# Activate virtual environment
echo "📦 Activating virtual environment..."
. .venv/bin/activate

# Run full report generation with all features
echo "🚀 Generating professional report for META..."
echo "   - Evidence Pipeline: ENABLED"
echo "   - LLM Narratives: ENABLED" 
echo "   - Comparables: ENABLED"
echo "   - Sensitivity: ENABLED"
echo "   - Evaluation: ENABLED"
echo ""

python scripts/generate_full_report.py META \
    --output-dir out \
    2>&1 | tee out/META/generation.log

echo ""
echo "====================================="
echo "REPORT GENERATION COMPLETE"
echo "====================================="
echo ""
echo "📊 View reports at:"
echo "   - Markdown: out/META/META_professional_report.md"
echo "   - HTML: out/META/META_professional_report.html"
echo "   - Evaluation: out/META/META_evaluation.json"
echo "   - Log: out/META/generation.log"
echo ""

# Show evaluation summary
if [ -f "out/META/META_evaluation.json" ]; then
    echo "📈 Evaluation Summary:"
    python -c "
import json
with open('out/META/META_evaluation.json') as f:
    eval_data = json.load(f)
    print(f\"   Overall Score: {eval_data.get('overall_score', 'N/A')}/10\")
    print(f\"   Quality Gates: {'PASS' if eval_data.get('passes_quality_gates') else 'FAIL'}\")
    for score in eval_data.get('dimensional_scores', []):
        print(f\"   - {score['dimension']}: {score['score']}/10\")
"
fi