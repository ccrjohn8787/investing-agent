# LLM Integration Guide

## 🔐 **Security & Authentication**

### **Security Best Practices**

**🚨 Critical: Never commit API keys to version control**

```bash
# ✅ Good: Use environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# ❌ Bad: Never hardcode in code
OPENAI_API_KEY = "sk-..."  # DON'T DO THIS
```

**Secure .gitignore patterns:**
```gitignore
# Security - API keys and secrets
.env
.env.*
.envrc
*.key
*.pem
secrets/
api_keys.json
config/secrets.*
**/*api_key*
**/*secret*
**/*token*
```

**Environment validation:**
```python
# The enhanced provider includes automatic security validation
provider = get_provider()
report = provider.get_usage_report()

# Check for security issues
if report["security_warnings"]:
    for warning in report["security_warnings"]:
        print(f"⚠ Security Warning: {warning}")
```

## 🔑 **Authentication Setup**

### **Environment Variables Required**

Add these to your shell profile (`.bashrc`, `.zshrc`) or `.env` file:

```bash
# Primary providers (at least one required)
export OPENAI_API_KEY="sk-..."           # OpenAI API key
export ANTHROPIC_API_KEY="sk-ant-..."    # Anthropic Claude API key

# Optional providers
export TOGETHER_API_KEY="..."            # Together AI (optional)

# Development settings
export LLM_DEBUG=true                     # Enable debug logging
export LLM_COST_TRACKING=true           # Track usage and costs
```

### **Getting API Keys**

**OpenAI (Primary):**
1. Visit https://platform.openai.com/api-keys
2. Create new secret key
3. Add payment method (required for API access)
4. Set usage limits to prevent unexpected charges

**Anthropic (Premium Narrative):**
1. Visit https://console.anthropic.com/settings/keys
2. Create new API key
3. Add payment method
4. Higher quality for story/narrative generation

## 🎯 **Model Selection Guide**

### **Use Case to Model Mapping**

```python
from investing_agent.llm.enhanced_provider import LLMProvider

provider = LLMProvider()

# Story & Narrative Generation (Creative)
response = provider.call("story-premium", messages)      # Claude 3.5 Sonnet
response = provider.call("story-standard", messages)     # GPT-4 Turbo

# Research & Analysis (Analytical)  
response = provider.call("research-premium", messages)   # GPT-4 Turbo
response = provider.call("research-standard", messages)  # GPT-4o

# Evaluation & Judging (Consistent)
response = provider.call("judge-primary", messages)      # GPT-4 (deterministic)

# Quick Tasks (Cost Effective)
response = provider.call("quick-task", messages)         # GPT-4o Mini

# Development/Testing
response = provider.call("dev-test", messages)           # GPT-3.5 Turbo
```

### **Quality vs Cost Trade-offs**

| Model Tier | Quality | Speed | Cost/1K tokens | Use Case |
|------------|---------|-------|----------------|-----------|
| **story-premium** | Exceptional | Medium | $0.015 | Investment narratives, strategic analysis |
| **research-premium** | Very High | Fast | $0.015 | Market research, competitive analysis |
| **judge-primary** | Consistent | Medium | $0.030 | Report evaluation, quality scoring |
| **quick-task** | Good | Fast | $0.0006 | Summaries, quick analysis |
| **dev-test** | Good | Fast | $0.0006 | Development, testing, prototypes |

## 🏗️ **Architecture Best Practices**

### **1. Easy Model Switching**

```python
# Bad: Hard-coded model
def analyze_company(text):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",  # Hard-coded
        messages=[{"role": "user", "content": text}]
    )

# Good: Configurable model
def analyze_company(text, model="research-premium"):
    provider = get_provider()
    messages = [{"role": "user", "content": text}]
    response = provider.call(model, messages)
    return response["choices"][0]["message"]["content"]
```

### **2. Fallback Strategies**

```python
def generate_investment_thesis(company_data):
    provider = get_provider()
    messages = build_thesis_prompt(company_data)
    
    # Primary model with fallback
    response = provider.call(
        model_name="story-premium",           # Primary: Claude 3.5 Sonnet
        messages=messages,
        fallback_model="story-standard"      # Fallback: GPT-4 Turbo
    )
    
    return response
```

### **3. Cost Management**

```python
def analyze_with_budget(text, max_cost_usd=0.10):
    provider = get_provider()
    
    # Check if we should use cheaper model
    estimated_tokens = len(text) / 4  # Rough estimate
    
    if estimated_tokens > 10000:  # Large document
        model = "quick-task"      # Cheaper option
    else:
        model = "research-premium"  # Higher quality
    
    response = provider.call(model, messages)
    
    # Track spending
    usage = provider.get_usage_report()
    if usage["total_cost"] > max_cost_usd:
        print(f"Warning: Cost limit exceeded: ${usage['total_cost']:.3f}")
    
    return response
```

### **4. Development vs Production**

```python
def get_model_for_env():
    """Get appropriate model based on environment."""
    if os.getenv("ENVIRONMENT") == "development":
        return "dev-test"        # GPT-4o Mini for development
    elif os.getenv("ENVIRONMENT") == "staging":
        return "quick-task"      # GPT-4o Mini for staging
    else:
        return "research-premium"  # GPT-4o for production
```

## 🔄 **Cassette System for Testing**

### **Recording Cassettes**

```python
# Development: Record new responses
def generate_story(prompt, record_cassette=False):
    provider = get_provider()
    messages = [{"role": "user", "content": prompt}]
    
    response = provider.call("story-premium", messages)
    
    if record_cassette:
        # Save response to cassette for future testing
        with open("cassettes/story_response.json", "w") as f:
            json.dump(response, f, indent=2)
    
    return response

# CI/Testing: Use recorded responses
def test_story_generation():
    response = provider.call(
        "story-premium", 
        messages, 
        cassette_path="cassettes/story_response.json"
    )
    assert "investment thesis" in response["choices"][0]["message"]["content"]
```

## 📊 **Usage Monitoring**

### **Cost Tracking**

```python
# Monitor usage and costs
provider = get_provider()

# Make multiple calls...
provider.call("story-premium", messages)
provider.call("research-premium", messages)

# Get detailed report
report = provider.get_usage_report()
print(f"Total cost: ${report['total_cost']:.3f}")
print(f"Total calls: {report['total_calls']}")

# Per-model breakdown
for model, stats in report["by_model"].items():
    print(f"{model}: {stats['calls']} calls, ${stats['total_cost']:.3f}")
```

### **Authentication Status Check**

```python
provider = get_provider()
status = provider.get_usage_report()["auth_status"]

for provider_name, status in status.items():
    print(f"{provider_name}: {status}")

# Output:
# openai: ✓ Available
# anthropic: ✗ Missing ANTHROPIC_API_KEY
# together: ✗ Missing TOGETHER_API_KEY (optional)
```

## 🎨 **Usage Examples**

### **Investment Story Generation**

```python
from investing_agent.llm.enhanced_provider import call_story_model

def generate_investment_narrative(company, fundamentals, market_data):
    prompt = f"""
    Write a compelling investment narrative for {company}.
    
    Company Data: {fundamentals}
    Market Context: {market_data}
    
    Structure:
    1. Investment Thesis
    2. Key Growth Drivers  
    3. Competitive Advantages
    4. Risk Factors
    5. Valuation Perspective
    """
    
    messages = [
        {"role": "system", "content": "You are a senior equity research analyst."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_story_model(messages, temperature=0.3)
    return response["choices"][0]["message"]["content"]
```

### **Market Research**

```python
from investing_agent.llm.enhanced_provider import call_research_model

def analyze_industry_trends(industry, time_horizon="5 years"):
    prompt = f"""
    Analyze {industry} industry trends over the next {time_horizon}.
    
    Focus on:
    - Market size and growth projections
    - Key technological disruptions
    - Regulatory changes
    - Competitive dynamics
    - Investment opportunities and risks
    """
    
    messages = [
        {"role": "system", "content": "You are an expert industry analyst."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_research_model(messages)
    return response["choices"][0]["message"]["content"]
```

### **Report Evaluation**

```python
from investing_agent.llm.enhanced_provider import call_judge_model

def evaluate_report_quality(report_text):
    prompt = f"""
    Evaluate this investment report across 5 dimensions:
    1. Strategic Narrative (0-10)
    2. Analytical Rigor (0-10)  
    3. Industry Context (0-10)
    4. Professional Presentation (0-10)
    5. Citation Discipline (0-10)
    
    Report: {report_text}
    
    Provide scores, reasoning, and improvement suggestions.
    """
    
    messages = [
        {"role": "system", "content": "You are a senior investment analyst evaluating report quality."},
        {"role": "user", "content": prompt}
    ]
    
    # Deterministic evaluation
    response = call_judge_model(messages, temperature=0, seed=2025)
    return response["choices"][0]["message"]["content"]
```

## ⚡ **Quick Start**

```python
# 1. Set up environment variables
export OPENAI_API_KEY="your-key-here"

# 2. Use in your code
from investing_agent.llm.enhanced_provider import get_provider

provider = get_provider()

# 3. Make calls with appropriate models
story_response = provider.call("story-premium", messages)
research_response = provider.call("research-premium", messages)  
evaluation_response = provider.call("judge-primary", messages)

# 4. Track usage
print(provider.get_usage_report())
```

This architecture provides:
- ✅ **Easy model switching** - Change models without code changes
- ✅ **Cost management** - Built-in usage tracking and model selection
- ✅ **Authentication handling** - Environment-based API key management
- ✅ **Fallback strategies** - Automatic fallback if primary model fails
- ✅ **Testing support** - Cassette system for deterministic testing
- ✅ **Production ready** - Rate limiting, error handling, monitoring