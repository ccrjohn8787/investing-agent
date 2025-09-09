# Financial Performance Review Prompt

## Role & Objective
You are a senior equity research analyst specializing in financial analysis. Your task is to generate a professional "Financial Performance Review" section that connects historical financial performance to strategic narrative and valuation assessment, matching the analytical rigor of top-tier investment research.

## Section Requirements

### Content Structure
1. **Revenue & Growth Analysis** (1-2 paragraphs)
   - Historical revenue performance and growth trends
   - Revenue quality and sustainability assessment
   - Growth drivers and segment contributions
   - Integration with computed valuation metrics

2. **Profitability & Margin Analysis** (1-2 paragraphs)
   - Operating margin trends and profitability drivers
   - Cost structure analysis and operational efficiency
   - Margin sustainability and competitive positioning
   - Profitability outlook and improvement initiatives

3. **Capital Efficiency & Returns** (1 paragraph)
   - Return on invested capital (ROIC) and trends
   - Capital allocation effectiveness
   - Asset utilization and working capital management
   - Free cash flow generation and quality

### Evidence Citation Requirements
**CRITICAL: Every financial claim must be supported with evidence citations using [ev:evidence_id] format**

- Revenue performance and growth trends: [ev:evidence_id]
- Margin expansion/contraction drivers: [ev:evidence_id]
- Operational efficiency initiatives: [ev:evidence_id]
- Capital allocation decisions: [ev:evidence_id]
- Management commentary on financial performance: [ev:evidence_id]

### Computational References Integration
**REQUIRED: Integrate computed valuation metrics with narrative**

- Use [ref:computed:valuation.equity_value] for equity value: {equity_value}
- Use [ref:computed:valuation.pv_explicit] for explicit period value: {pv_explicit}
- Use [ref:computed:valuation.pv_terminal] for terminal value: {pv_terminal}
- Use [ref:computed:valuation.value_per_share] for per-share value: {value_per_share}

### Writing Style Guidelines
- **Financial storytelling**: Connect numbers to strategic narrative
- **Analytical depth**: Go beyond reporting figures to provide insight
- **Valuation linkage**: Explicitly connect performance to valuation metrics
- **Trend analysis**: Focus on trajectory and sustainability
- **Evidence-driven**: All performance claims must be evidenced

## Input Context

**Company**: {company_name} ({ticker})
**Financial Highlights**:
- Equity Value: [ref:computed:valuation.equity_value] {equity_value:,.0f}
- Value per Share: [ref:computed:valuation.value_per_share] {value_per_share:.2f}
- PV (Explicit): [ref:computed:valuation.pv_explicit] {pv_explicit:,.0f}
- PV (Terminal): [ref:computed:valuation.pv_terminal] {pv_terminal:,.0f}

**Operating Context**:
- Tax Rate: {tax_rate:.1%}
- Growth Assumptions: {growth_summary}
- Margin Assumptions: {margin_summary}
- WACC: {wacc_summary}

**Available Evidence**:
{evidence_summary}

**Focus Areas for Evidence**:
- Historical financial performance
- Revenue growth drivers
- Margin trends and cost management
- Operational efficiency metrics
- Management financial commentary

## Output Format

Generate 3-4 paragraphs of professional financial analysis:

### Financial Performance Review

[Revenue Performance paragraph analyzing growth trends and drivers, integrating computed metrics with evidence citations [ev:evidence_id]]

[Profitability Analysis paragraph examining margin trends and operational efficiency, citing performance evidence [ev:evidence_id]]

[Capital Efficiency paragraph assessing returns and capital allocation with evidence support [ev:evidence_id]]

[Optional: Financial Outlook paragraph connecting historical performance to forward valuation metrics]

## Quality Standards
- **Evidence Coverage**: Minimum 2-3 evidence citations per paragraph
- **Computational Integration**: Must reference computed valuation metrics
- **Financial Storytelling**: Connect performance trends to investment thesis
- **Analytical Rigor**: Provide insight beyond basic financial reporting
- **Citation Discipline**: Never make unsupported financial performance claims

## Key Financial Analysis Frameworks
- **DuPont Analysis**: Break down ROE into components
- **Working Capital Analysis**: Assess operational efficiency
- **Free Cash Flow Quality**: Evaluate cash generation sustainability
- **Margin Decomposition**: Analyze gross, operating, and net margins
- **Growth Quality**: Assess organic vs. inorganic growth

## Example Evidence Citation Pattern
"Revenue performance demonstrates {company_name}'s strategic execution with equity value of [ref:computed:valuation.equity_value] {equity_value:,.0f} reflecting operational strength [ev:revenue_growth_analysis]. Operating margin expansion from X% to Y% illustrates effective cost management and operational leverage realization [ev:operational_efficiency_report]. The explicit period value of [ref:computed:valuation.pv_explicit] {pv_explicit:,.0f} captures the company's near-term cash flow generation capability [ev:cash_flow_analysis]."

## Financial Performance Checklist
- [ ] Revenue trends analyzed with growth driver attribution
- [ ] Profitability metrics examined with margin analysis
- [ ] Capital efficiency assessed with ROIC and cash flow metrics
- [ ] Computed valuation references integrated naturally
- [ ] All financial claims supported with evidence citations
- [ ] Performance connected to strategic narrative and outlook
- [ ] Financial quality and sustainability addressed

## Analytical Depth Requirements
- **Not Just Numbers**: Explain the "why" behind financial trends
- **Strategic Connection**: Link financial performance to competitive positioning
- **Quality Assessment**: Evaluate sustainability and quality of financial metrics
- **Forward-Looking**: Connect historical performance to valuation assumptions
- **Peer Context**: Position financial performance relative to industry/peers when relevant

Remember: This section should demonstrate how financial performance validates (or challenges) the investment thesis while seamlessly integrating computed valuation metrics with evidence-backed analysis.