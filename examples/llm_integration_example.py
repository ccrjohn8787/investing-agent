#!/usr/bin/env python3
"""
Example: LLM Integration for Investment Analysis

Shows how to use the enhanced LLM provider for different investment
analysis tasks with appropriate model selection.
"""

import os
from typing import Dict, Any

# Set up for demo (you'd put these in your environment)
# os.environ["OPENAI_API_KEY"] = "your-openai-key"
# os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-key"

from investing_agent.llm.enhanced_provider import (
    get_provider, 
    call_story_model, 
    call_research_model,
    call_judge_model
)


def demo_investment_story_generation():
    """Demo: Generate compelling investment narrative."""
    print("🎨 Investment Story Generation")
    print("=" * 50)
    
    company_data = {
        "name": "UBER Technologies",
        "sector": "Transportation/Technology",
        "revenue_ttm": "$37.3B",
        "growth_rate": "16%",
        "key_markets": ["Rideshare", "Food Delivery", "Freight"]
    }
    
    prompt = f"""
    Create a compelling investment thesis for {company_data['name']}.
    
    Company Context:
    - Sector: {company_data['sector']}
    - Revenue: {company_data['revenue_ttm']}
    - Growth: {company_data['growth_rate']}
    - Key Markets: {', '.join(company_data['key_markets'])}
    
    Structure as:
    1. Investment Thesis (2-3 sentences)
    2. Key Growth Drivers (3-4 bullet points)
    3. Competitive Moat
    4. Key Risk to Monitor
    
    Write in professional equity research style.
    """
    
    messages = [
        {"role": "system", "content": "You are a senior equity research analyst at a top investment bank."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        # Use premium story model (Claude 3.5 Sonnet)
        response = call_story_model(messages, temperature=0.3)
        story = response["choices"][0]["message"]["content"]
        
        print(f"Generated Investment Story:\n{story}")
        print(f"\nModel Used: Claude 3.5 Sonnet (story-premium)")
        
    except Exception as e:
        print(f"Error (likely missing API key): {str(e)}")
        print("Demo would work with proper authentication.")


def demo_market_research():
    """Demo: Conduct market research analysis."""
    print("\n📊 Market Research Analysis")
    print("=" * 50)
    
    prompt = """
    Analyze the autonomous vehicle market's impact on rideshare companies over the next 5 years.
    
    Focus on:
    1. Technology readiness and timeline
    2. Regulatory approval process
    3. Impact on unit economics for rideshare
    4. Investment implications for traditional rideshare players
    
    Provide data-driven analysis with specific timelines where possible.
    """
    
    messages = [
        {"role": "system", "content": "You are a technology industry analyst specializing in autonomous vehicles and mobility."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        # Use research model (GPT-4o)  
        response = call_research_model(messages)
        research = response["choices"][0]["message"]["content"]
        
        print(f"Market Research Analysis:\n{research}")
        print(f"\nModel Used: GPT-4o (research-premium)")
        
    except Exception as e:
        print(f"Error (likely missing API key): {str(e)}")
        print("Demo would work with proper authentication.")


def demo_report_evaluation():
    """Demo: Evaluate investment report quality."""
    print("\n⚖️ Report Quality Evaluation")
    print("=" * 50)
    
    sample_report = """
    # UBER Technologies Investment Analysis
    
    ## Summary
    - Revenue: $37.3B TTM
    - Growth: 16% YoY
    - Market Cap: $150B
    
    ## Valuation
    Using DCF analysis, we estimate fair value at $65 per share.
    Key assumptions: 15% revenue growth, 12% EBITDA margin.
    
    ## Fundamentals
    Strong market position in rideshare and delivery markets.
    Expanding internationally with focus on profitability.
    """
    
    prompt = f"""
    Evaluate this investment report across our 5 quality dimensions:
    
    1. Strategic Narrative (0-10): Investment thesis clarity and storytelling
    2. Analytical Rigor (0-10): Evidence depth and methodology
    3. Industry Context (0-10): Market dynamics and competitive analysis  
    4. Professional Presentation (0-10): Structure and readability
    5. Citation Discipline (0-10): Source attribution and references
    
    Report to evaluate:
    {sample_report}
    
    Provide numerical scores and specific improvement recommendations.
    Return in JSON format with scores and reasoning.
    """
    
    messages = [
        {"role": "system", "content": "You are a senior investment analyst evaluating report quality with 15+ years experience."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        # Use deterministic judge model (GPT-4 Turbo)
        response = call_judge_model(messages, temperature=0, seed=2025)
        evaluation = response["choices"][0]["message"]["content"]
        
        print(f"Quality Evaluation:\n{evaluation}")
        print(f"\nModel Used: GPT-4 Turbo (judge-primary, deterministic)")
        
    except Exception as e:
        print(f"Error (likely missing API key): {str(e)}")
        print("Demo would work with proper authentication.")


def demo_usage_monitoring():
    """Demo: Monitor LLM usage and costs."""
    print("\n💰 Usage and Cost Monitoring")
    print("=" * 50)
    
    provider = get_provider()
    
    # Show authentication status
    print("Authentication Status:")
    for service, status in provider.auth_status.items():
        print(f"  {service}: {status}")
    
    # Show usage tracking (would show real data after actual calls)
    usage = provider.get_usage_report()
    print(f"\nUsage Summary:")
    print(f"  Total Calls: {usage['total_calls']}")
    print(f"  Total Cost: ${usage['total_cost']:.3f}")
    
    if usage['by_model']:
        print("\nPer-Model Breakdown:")
        for model, stats in usage['by_model'].items():
            print(f"  {model}:")
            print(f"    Calls: {stats['calls']}")
            print(f"    Cost: ${stats['total_cost']:.3f}")
            print(f"    Tokens: {stats['prompt_tokens']} + {stats['completion_tokens']}")


def demo_model_selection_strategy():
    """Demo: Smart model selection based on requirements."""
    print("\n🎯 Smart Model Selection")
    print("=" * 50)
    
    use_cases = [
        ("Creative investment narrative", "story-premium", "Claude 3.5 Sonnet"),
        ("Technical market analysis", "research-premium", "GPT-4o"), 
        ("Report quality evaluation", "judge-primary", "GPT-4 Turbo"),
        ("Quick summary generation", "quick-task", "GPT-4o Mini"),
        ("Development/testing", "dev-test", "GPT-4o Mini")
    ]
    
    print("Recommended Model Selection:")
    for use_case, model_name, actual_model in use_cases:
        config = get_provider().MODELS[model_name]
        cost = config.cost_per_1k_output
        print(f"  {use_case:30} → {model_name:15} ({actual_model}) - ${cost:.4f}/1K tokens")
    
    print("\nModel Selection Logic:")
    print("  📖 Story/Narrative → High creativity, premium quality")
    print("  🔬 Research/Analysis → High reasoning, analytical depth")  
    print("  ⚖️ Evaluation/Judge → Maximum consistency, deterministic")
    print("  ⚡ Quick Tasks → Speed and cost efficiency")
    print("  🔧 Development → Cheap for iteration and testing")


if __name__ == "__main__":
    print("🤖 LLM Integration Demo for Investment Analysis")
    print("=" * 60)
    
    # Check authentication first
    demo_usage_monitoring()
    
    # Show model selection strategy
    demo_model_selection_strategy()
    
    # Run demos (will show errors if no API keys, but demonstrates the pattern)
    demo_investment_story_generation()
    demo_market_research() 
    demo_report_evaluation()
    
    print("\n✅ Demo complete!")
    print("\nTo run with actual LLM calls:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Set ANTHROPIC_API_KEY environment variable (optional)")
    print("3. Run: python examples/llm_integration_example.py")