#!/usr/bin/env python3
"""Generate comparison report for multiple companies."""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals


def generate_comparison_data(tickers: List[str]) -> Dict[str, Any]:
    """Generate comparison data for multiple tickers."""
    
    comparison_data = {
        "companies": [],
        "metrics": {
            "fair_value": [],
            "revenue": [],
            "growth": [],
            "margin": [],
            "wacc": [],
            "roic": []
        }
    }
    
    for ticker in tickers:
        print(f"Processing {ticker}...")
        
        try:
            # Fetch fundamentals
            cf, metadata = fetch_companyfacts(ticker)
            fundamentals = parse_companyfacts_to_fundamentals(cf, ticker, company=metadata.get('entityName'))
            
            # Build inputs and valuation
            inputs = build_inputs_from_fundamentals(fundamentals)
            valuation = kernel_value(inputs)
            
            # Calculate metrics
            roic = inputs.drivers.oper_margin[0] * (1 - inputs.tax_rate) * inputs.sales_to_capital[0]
            
            # Add to comparison data
            company_data = {
                "ticker": ticker,
                "company": inputs.company,
                "fair_value": valuation.value_per_share,
                "revenue": inputs.revenue_t0 / 1e9,  # In billions
                "growth": inputs.drivers.sales_growth[0] * 100,
                "margin": inputs.drivers.oper_margin[0] * 100,
                "wacc": inputs.wacc[0] * 100,
                "roic": roic * 100,
                "pv_explicit": valuation.pv_explicit / 1e9,
                "pv_terminal": valuation.pv_terminal / 1e9
            }
            
            comparison_data["companies"].append(company_data)
            
            # Add to metric arrays for charting
            comparison_data["metrics"]["fair_value"].append(company_data["fair_value"])
            comparison_data["metrics"]["revenue"].append(company_data["revenue"])
            comparison_data["metrics"]["growth"].append(company_data["growth"])
            comparison_data["metrics"]["margin"].append(company_data["margin"])
            comparison_data["metrics"]["wacc"].append(company_data["wacc"])
            comparison_data["metrics"]["roic"].append(company_data["roic"])
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue
    
    return comparison_data


def generate_comparison_html(data: Dict[str, Any]) -> str:
    """Generate HTML comparison report."""
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Comparison Report</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #1e40af;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --bg-color: #ffffff;
            --text-color: #1f2937;
            --border-color: #e5e7eb;
            --card-bg: #f9fafb;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            padding: 2rem;
            line-height: 1.6;
        }
        
        .header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        h1 {
            color: var(--primary-color);
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: var(--text-color);
            opacity: 0.8;
            font-size: 1.1rem;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .company-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .company-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .company-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
        }
        
        .ticker {
            color: var(--text-color);
            opacity: 0.6;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            color: var(--text-color);
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        .metric-value {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .metric-value.positive {
            color: var(--success-color);
        }
        
        .metric-value.negative {
            color: var(--danger-color);
        }
        
        .comparison-table {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: var(--primary-color);
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:hover {
            background: var(--card-bg);
        }
        
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: var(--primary-color);
        }
        
        canvas {
            max-height: 400px;
        }
        
        .best-value {
            background: linear-gradient(135deg, var(--success-color), var(--primary-color));
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        @media (max-width: 768px) {
            .comparison-grid {
                grid-template-columns: 1fr;
            }
            
            body {
                padding: 1rem;
            }
            
            h1 {
                font-size: 2rem;
            }
            
            .comparison-table {
                overflow-x: auto;
            }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>Investment Comparison Report</h1>
        <p class="subtitle">Comparative analysis of {{num_companies}} companies</p>
    </div>
    
    <div class="comparison-grid">
        {{company_cards}}
    </div>
    
    <div class="comparison-table">
        <table>
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Fair Value</th>
                    <th>Revenue (B)</th>
                    <th>Growth %</th>
                    <th>Margin %</th>
                    <th>ROIC %</th>
                    <th>WACC %</th>
                </tr>
            </thead>
            <tbody>
                {{table_rows}}
            </tbody>
        </table>
    </div>
    
    <div class="chart-container">
        <h2 class="chart-title">Valuation Comparison</h2>
        <canvas id="valuationChart"></canvas>
    </div>
    
    <div class="chart-container">
        <h2 class="chart-title">Growth vs Margin Analysis</h2>
        <canvas id="growthMarginChart"></canvas>
    </div>
    
    <div class="chart-container">
        <h2 class="chart-title">Return Metrics</h2>
        <canvas id="returnChart"></canvas>
    </div>
    
    <script>
        const comparisonData = {{json_data}};
        
        // Valuation comparison chart
        new Chart(document.getElementById('valuationChart'), {
            type: 'bar',
            data: {
                labels: comparisonData.companies.map(c => c.ticker),
                datasets: [{
                    label: 'Fair Value per Share ($)',
                    data: comparisonData.companies.map(c => c.fair_value),
                    backgroundColor: '#2563eb',
                    borderColor: '#1e40af',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    }
                }
            }
        });
        
        // Growth vs Margin scatter chart
        new Chart(document.getElementById('growthMarginChart'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Companies',
                    data: comparisonData.companies.map(c => ({
                        x: c.growth,
                        y: c.margin,
                        label: c.ticker
                    })),
                    backgroundColor: '#10b981',
                    borderColor: '#059669',
                    borderWidth: 2,
                    pointRadius: 8,
                    pointHoverRadius: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.raw.label + ': Growth ' + context.raw.x.toFixed(1) + '%, Margin ' + context.raw.y.toFixed(1) + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Revenue Growth (%)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Operating Margin (%)'
                        }
                    }
                }
            }
        });
        
        // Return metrics chart
        new Chart(document.getElementById('returnChart'), {
            type: 'radar',
            data: {
                labels: comparisonData.companies.map(c => c.ticker),
                datasets: [
                    {
                        label: 'ROIC %',
                        data: comparisonData.companies.map(c => c.roic),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderWidth: 2
                    },
                    {
                        label: 'WACC %',
                        data: comparisonData.companies.map(c => c.wacc),
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.2)',
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>'''
    
    # Generate company cards
    company_cards = []
    best_value_ticker = max(data["companies"], key=lambda x: x["fair_value"])["ticker"]
    
    for company in data["companies"]:
        is_best = company["ticker"] == best_value_ticker
        card = f'''
        <div class="company-card">
            <div class="company-name">
                {company["company"][:30]}
                {f'<span class="best-value">BEST VALUE</span>' if is_best else ''}
            </div>
            <div class="ticker">{company["ticker"]}</div>
            <div class="metric">
                <span class="metric-label">Fair Value</span>
                <span class="metric-value">${company["fair_value"]:.2f}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Revenue</span>
                <span class="metric-value">${company["revenue"]:.1f}B</span>
            </div>
            <div class="metric">
                <span class="metric-label">Growth</span>
                <span class="metric-value {'positive' if company['growth'] > 10 else ''}">{company["growth"]:.1f}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Margin</span>
                <span class="metric-value">{company["margin"]:.1f}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">ROIC</span>
                <span class="metric-value {'positive' if company['roic'] > company['wacc'] else 'negative'}">{company["roic"]:.1f}%</span>
            </div>
        </div>'''
        company_cards.append(card)
    
    # Generate table rows
    table_rows = []
    for company in data["companies"]:
        row = f'''
        <tr>
            <td><strong>{company["ticker"]}</strong> - {company["company"][:30]}</td>
            <td>${company["fair_value"]:.2f}</td>
            <td>${company["revenue"]:.1f}B</td>
            <td>{company["growth"]:.1f}%</td>
            <td>{company["margin"]:.1f}%</td>
            <td>{company["roic"]:.1f}%</td>
            <td>{company["wacc"]:.1f}%</td>
        </tr>'''
        table_rows.append(row)
    
    # Replace placeholders
    html = html.replace("{{num_companies}}", str(len(data["companies"])))
    html = html.replace("{{company_cards}}", "\n".join(company_cards))
    html = html.replace("{{table_rows}}", "\n".join(table_rows))
    html = html.replace("{{json_data}}", json.dumps(data, default=str))
    
    return html


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Investment Comparison Report")
    parser.add_argument("tickers", nargs="+", help="Stock ticker symbols to compare")
    parser.add_argument("--output-dir", type=Path, default=Path("out/comparison"),
                       help="Output directory")
    
    args = parser.parse_args()
    
    print(f"Generating comparison report for: {', '.join(args.tickers)}")
    
    # Generate comparison data
    data = generate_comparison_data(args.tickers)
    
    if not data["companies"]:
        print("No data could be generated. Please check the tickers.")
        return
    
    # Generate HTML
    html = generate_comparison_html(data)
    
    # Save report
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "comparison_report.html"
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    # Save data as JSON
    json_path = args.output_dir / "comparison_data.json"
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"✅ Comparison report generated: {output_path}")
    print(f"   Open in browser: file://{output_path.absolute()}")


if __name__ == "__main__":
    main()