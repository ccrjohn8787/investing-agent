from __future__ import annotations

import base64
import html
import json
from typing import Optional

import numpy as np

from investing_agent.kernels import ginzu as K
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def _b64_img(b: Optional[bytes]) -> str:
    if not b:
        return ""
    enc = base64.b64encode(b).decode("ascii")
    return f"data:image/png;base64,{enc}"


def render_html_report(
    I: InputsI,
    V: ValuationV,
    sensitivity_png: Optional[bytes] = None,
    driver_paths_png: Optional[bytes] = None,
    fundamentals: Optional[Fundamentals] = None,
    companyfacts_json: Optional[dict] = None,
    pv_bridge_png: Optional[bytes] = None,
    price_vs_value_png: Optional[bytes] = None,
) -> str:
    """Single-file HTML report with tables and embedded images."""
    S = K.series(I)
    rev = S.revenue
    ebit = S.ebit
    fcff = S.fcff
    wacc = S.wacc
    df = S.discount_factors

    T = len(rev)
    g = np.array(I.drivers.sales_growth[:T], dtype=float)
    m = np.array(I.drivers.oper_margin[:T], dtype=float)
    s2c = np.array(I.sales_to_capital[:T], dtype=float)
    tax = float(I.tax_rate)
    roic = m * (1.0 - tax) * s2c
    rev0 = float(I.revenue_t0)
    rev_prev = np.array([rev0] + list(rev[:-1]), dtype=float)
    reinvest = (np.array(rev) - rev_prev) / np.where(s2c > 0, s2c, 1.0)
    pv_fcff = np.array(fcff) * np.array(df)

    fcff_T1 = S.fcff_T1
    tv_T = S.terminal_value_T
    pv_terminal = float(tv_T * df[-1])

    def pct(x: float) -> str:
        return f"{x*100:.2f}%"

    def money(x: float) -> str:
        return f"{x:,.0f}"

    sens_src = _b64_img(sensitivity_png)
    drv_src = _b64_img(driver_paths_png)
    bridge_src = _b64_img(pv_bridge_png)
    price_src = _b64_img(price_vs_value_png)

    cf_pretty = ""
    if companyfacts_json is not None:
        try:
            text = json.dumps(companyfacts_json, indent=2)[:200000]
            cf_pretty = html.escape(text)
        except Exception:
            cf_pretty = html.escape(str(companyfacts_json)[:200000])

    styles = """
    <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; }
    h1, h2, h3 { margin: 0.6em 0 0.3em; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; font-size: 13px; }
    th { background: #f4f4f4; cursor: pointer; }
    .meta { color: #555; }
    .charts img { max-width: 100%; height: auto; border: 1px solid #ddd; }
    details { margin: 8px 0; }
    pre { background: #f9f9f9; padding: 10px; overflow: auto; border: 1px solid #eee; }
    .kpis { display: flex; flex-wrap: wrap; gap: 16px; }
    .kpis .card { border: 1px solid #ddd; padding: 10px 12px; border-radius: 6px; background: #fafafa; }
    .kpis .label { color: #666; font-size: 12px; }
    .kpis .value { font-size: 18px; font-weight: 600; }
    </style>
    <script>
    // Simple column sort for the first table on click
    function sortTable(tableId, colIndex, asNumeric) {
      const table = document.getElementById(tableId);
      if (!table) return;
      const rows = Array.from(table.querySelectorAll('tbody tr'));
      const dir = table.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
      table.setAttribute('data-sort-dir', dir);
      rows.sort((a,b) => {
        const av = a.children[colIndex].innerText;
        const bv = b.children[colIndex].innerText;
        if (asNumeric) {
          const an = parseFloat(av.replace(/[, %]/g,'')) || 0;
          const bn = parseFloat(bv.replace(/[, %]/g,'')) || 0;
          return dir==='asc' ? an - bn : bn - an;
        } else {
          return dir==='asc' ? av.localeCompare(bv) : bv.localeCompare(av);
        }
      });
      const tbody = table.querySelector('tbody');
      rows.forEach(r => tbody.appendChild(r));
    }
    </script>
    """

    # Build per-year table rows
    per_year_rows = []
    for t in range(T):
        per_year_rows.append(
            f"<tr>"
            f"<td>{t+1}</td>"
            f"<td>{money(float(rev[t]))}</td>"
            f"<td>{pct(float(g[t]))}</td>"
            f"<td>{pct(float(m[t]))}</td>"
            f"<td>{float(s2c[t]):.2f}</td>"
            f"<td>{pct(float(roic[t]))}</td>"
            f"<td>{money(float(reinvest[t]))}</td>"
            f"<td>{money(float(fcff[t]))}</td>"
            f"<td>{pct(float(wacc[t]))}</td>"
            f"<td>{float(df[t]):.4f}</td>"
            f"<td>{money(float(pv_fcff[t]))}</td>"
            f"</tr>"
        )

    fundamentals_table = ""
    if fundamentals is not None and fundamentals.revenue:
        rows = []
        for y in sorted(fundamentals.revenue.keys()):
            r = float(fundamentals.revenue.get(y, 0.0))
            e = float(fundamentals.ebit.get(y, 0.0))
            rows.append(f"<tr><td>{y}</td><td>{money(r)}</td><td>{money(e)}</td></tr>")
        meta_bits = []
        if fundamentals.revenue_ttm:
            meta_bits.append(f"Revenue TTM: {money(float(fundamentals.revenue_ttm))}")
        if fundamentals.ebit_ttm:
            meta_bits.append(f"EBIT TTM: {money(float(fundamentals.ebit_ttm))}")
        if fundamentals.shares_out is not None:
            meta_bits.append(f"Shares out: {float(fundamentals.shares_out):,.0f}")
        if fundamentals.tax_rate is not None:
            meta_bits.append(f"Tax rate: {pct(float(fundamentals.tax_rate))}")
        # Extras (D&A, capex, leases, working capital)
        if fundamentals.dep_amort:
            y = max(fundamentals.dep_amort.keys())
            da = float(fundamentals.dep_amort[y])
            meta_bits.append(f"D&A (FY{y}): {money(da)}")
            rv = fundamentals.revenue.get(y)
            if rv and rv != 0:
                meta_bits.append(f"D&A % rev (FY{y}): {pct(da/float(rv))}")
        if fundamentals.capex:
            y = max(fundamentals.capex.keys())
            meta_bits.append(f"Capex (FY{y}): {money(float(fundamentals.capex[y]))}")
        if fundamentals.lease_assets:
            y = max(fundamentals.lease_assets.keys())
            meta_bits.append(f"Lease ROU Assets (FY{y}): {money(float(fundamentals.lease_assets[y]))}")
        if fundamentals.lease_liabilities:
            y = max(fundamentals.lease_liabilities.keys())
            meta_bits.append(f"Lease Liabilities (FY{y}): {money(float(fundamentals.lease_liabilities[y]))}")
        if fundamentals.current_assets and fundamentals.current_liabilities:
            years = set(fundamentals.current_assets.keys()) & set(fundamentals.current_liabilities.keys())
            if years:
                y = max(years)
                wc = float(fundamentals.current_assets[y]) - float(fundamentals.current_liabilities[y])
                meta_bits.append(f"Working capital (FY{y}): {money(wc)}")
        meta_html = ("<p class=meta>" + " | ".join(meta_bits) + "</p>") if meta_bits else ""
        fundamentals_table = (
            "<section><h2>Fundamentals (Parsed)</h2>" + meta_html +
            "<table><thead><tr><th>Year</th><th>Revenue</th><th>EBIT</th></tr></thead><tbody>" +
            "".join(rows) + "</tbody></table></section>"
        )

    cf_section = ""
    if cf_pretty:
        cf_section = (
            "<section><h3>Raw Companyfacts (JSON)</h3>"
            "<details><summary>Show/Hide JSON</summary>"
            f"<pre>{cf_pretty}</pre>"
            "</details></section>"
        )

    html_doc = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Valuation — {html.escape(I.company)} ({html.escape(I.ticker)})</title>
{styles}
</head>
<body>
  <h1>Investing Agent Valuation — {html.escape(I.company)} ({html.escape(I.ticker)})</h1>
  <p class="meta">As of: {html.escape(str(I.asof_date or 'N/A'))} &nbsp;|&nbsp; Currency: {html.escape(I.currency)}</p>
  <div class="kpis">
    <div class="card"><div class="label">Value per share</div><div class="value">{V.value_per_share:,.2f}</div></div>
    <div class="card"><div class="label">Equity value</div><div class="value">{V.equity_value:,.0f}</div></div>
    <div class="card"><div class="label">PV (explicit)</div><div class="value">{V.pv_explicit:,.0f}</div></div>
    <div class="card"><div class="label">PV (terminal)</div><div class="value">{V.pv_terminal:,.0f}</div></div>
    <div class="card"><div class="label">Shares out</div><div class="value">{V.shares_out:,.0f}</div></div>
  </div>
  <p class="meta">Refs: [ref:computed:valuation.value_per_share] [ref:computed:valuation.equity_value] [ref:computed:valuation.pv_explicit;table:Per-Year Detail] [ref:computed:valuation.pv_terminal;section:Terminal Value]{f" [ref:snap:{html.escape(I.provenance.content_sha256)}]" if I.provenance and I.provenance.content_sha256 else ""}</p>

  <section>
    <h2>Drivers & Assumptions</h2>
    <p class="meta">Discounting: {html.escape(I.discounting.mode)} &nbsp;|&nbsp; Tax: {pct(tax)} &nbsp;|&nbsp; Stable growth: {pct(I.drivers.stable_growth)} &nbsp;|&nbsp; Stable margin: {pct(I.drivers.stable_margin)} &nbsp;|&nbsp; S2C (last): {I.sales_to_capital[-1]:.2f} &nbsp;|&nbsp; WACC (last): {pct(I.wacc[-1])}</p>
  </section>

  <section>
    <h2>Per-Year Detail</h2>
    <table id="perYear" data-sort-dir="asc">
      <thead>
        <tr>
          <th onclick="sortTable('perYear',0,false)">Year</th>
          <th onclick="sortTable('perYear',1,true)">Revenue</th>
          <th onclick="sortTable('perYear',2,true)">Growth</th>
          <th onclick="sortTable('perYear',3,true)">Margin</th>
          <th onclick="sortTable('perYear',4,true)">Sales/Capital</th>
          <th onclick="sortTable('perYear',5,true)">ROIC</th>
          <th onclick="sortTable('perYear',6,true)">Reinvest</th>
          <th onclick="sortTable('perYear',7,true)">FCFF</th>
          <th onclick="sortTable('perYear',8,true)">WACC</th>
          <th onclick="sortTable('perYear',9,true)">DF</th>
          <th onclick="sortTable('perYear',10,true)">PV(FCFF)</th>
        </tr>
      </thead>
      <tbody>
        {''.join(per_year_rows)}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Terminal Value</h2>
    <p class="meta">Next-year FCFF (T+1): {money(float(fcff_T1))} &nbsp;|&nbsp; r - g: {pct(float(I.wacc[-1]) - float(I.drivers.stable_growth))} &nbsp;|&nbsp; TV@T: {money(float(tv_T))} &nbsp;|&nbsp; DF@T: {float(df[-1]):.4f} &nbsp;|&nbsp; PV(TV): {money(float(pv_terminal))}</p>
  </section>

  <section class="charts grid">
    {f'<div><h2>Sensitivity</h2><img alt="Sensitivity Heatmap" src="{sens_src}" /></div>' if sens_src else ''}
    {f'<div><h2>Driver Paths</h2><img alt="Driver Paths" src="{drv_src}" /></div>' if drv_src else ''}
    {f'<div><h2>PV Bridge</h2><img alt="PV Bridge" src="{bridge_src}" /></div>' if bridge_src else ''}
    {f'<div><h2>Price vs Value</h2><img alt="Price vs Value" src="{price_src}" /></div>' if price_src else ''}
  </section>

  {fundamentals_table}
  {cf_section}

  <section>
    <h2>Provenance</h2>
    <p class="meta">Vendor: {html.escape(I.provenance.vendor or 'unknown')} &nbsp;{f'| Source: {html.escape(I.provenance.source_url)}' if I.provenance.source_url else ''} &nbsp;{f'| Retrieved: {html.escape(I.provenance.retrieved_at)}' if I.provenance.retrieved_at else ''} &nbsp;{f'| SHA-256: {html.escape(I.provenance.content_sha256)}' if I.provenance.content_sha256 else ''}</p>
  </section>

  <p class="meta">Generated by Investing Agent. Deterministic given the same inputs.</p>
</body>
</html>
"""
    return html_doc
