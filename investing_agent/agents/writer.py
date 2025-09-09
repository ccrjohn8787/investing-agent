from __future__ import annotations

from datetime import datetime
from typing import Optional, List

import base64
import numpy as np

from investing_agent.kernels import ginzu as K
from investing_agent.schemas.fundamentals import Fundamentals

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.news import NewsSummary
from investing_agent.schemas.research import InsightBundle
try:
    from investing_agent.schemas.writer_llm import WriterLLMOutput
    from investing_agent.agents.writer_llm import merge_llm_sections
except Exception:  # pragma: no cover
    WriterLLMOutput = None  # type: ignore
    def merge_llm_sections(base_md: str, out):  # type: ignore
        return base_md


def render_report(
    I: InputsI,
    V: ValuationV,
    sensitivity_png: Optional[bytes] = None,
    driver_paths_png: Optional[bytes] = None,
    citations: Optional[List[str]] = None,
    fundamentals: Optional[Fundamentals] = None,
    pv_bridge_png: Optional[bytes] = None,
    price_vs_value_png: Optional[bytes] = None,
    news: Optional[NewsSummary] = None,
    insights: Optional[InsightBundle] = None,
    llm_output: Optional["WriterLLMOutput"] = None,
) -> str:
    """
    Create a Markdown report with detailed per-year numbers and embedded charts.

    The report includes the per-year path for revenue, growth, margins, sales-to-capital,
    ROIC, FCFF, WACC, discount factors, and PV(FCFF), plus terminal value details.
    If PNG bytes are provided, they are embedded as base64 data URIs so the report is
    self-contained.
    """
    # Compute detailed series via public kernel API
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
    nopat = np.array(ebit, dtype=float) * (1.0 - tax)
    # Reinvestment reconstructed for reporting
    rev0 = float(I.revenue_t0)
    rev_prev = np.array([rev0] + list(rev[:-1]), dtype=float)
    reinvest = (np.array(rev) - rev_prev) / np.where(s2c > 0, s2c, 1.0)
    pv_fcff = np.array(fcff) * np.array(df)
    roic = m * (1.0 - tax) * s2c

    # Terminal details
    fcff_T1 = S.fcff_T1
    tv_T = S.terminal_value_T
    pv_terminal = float(tv_T * df[-1])

    def _fmt_pct(x: float) -> str:
        return f"{x*100:.2f}%"

    def _fmt_f(x: float) -> str:
        return f"{x:,.0f}"

    def _embed_png(b: Optional[bytes], alt: str) -> Optional[str]:
        if not b:
            return None
        enc = base64.b64encode(b).decode("ascii")
        return f"![{alt}](data:image/png;base64,{enc})"

    lines = []
    lines.append(f"# Investing Agent Valuation — {I.company} ({I.ticker})")
    lines.append("")
    lines.append(f"As of: {I.asof_date or 'N/A'}  ")
    lines.append(f"Currency: {I.currency}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    def _refs(*tokens: str) -> str:
        toks = [t for t in tokens if t]
        return f" [ref:{';'.join(toks)}]" if toks else ""

    snap_ref = f"snap:{I.provenance.content_sha256}" if I.provenance and I.provenance.content_sha256 else None
    lines.append(
        f"- Value per share: {V.value_per_share:,.2f}" + _refs("computed:valuation.value_per_share")
    )
    lines.append(
        f"- Equity value: {V.equity_value:,.0f}" + _refs("computed:valuation.equity_value")
    )
    lines.append(
        f"- PV (explicit): {V.pv_explicit:,.0f}" + _refs("computed:valuation.pv_explicit", "table:Per-Year Detail")
    )
    lines.append(
        f"- PV (terminal): {V.pv_terminal:,.0f}" + _refs("computed:valuation.pv_terminal", "section:Terminal Value")
    )
    lines.append(
        f"- Shares out: {V.shares_out:,.0f}" + _refs("computed:valuation.shares_out", snap_ref)
    )
    lines.append("")

    # Assumptions/Drivers
    lines.append("## Drivers & Assumptions")
    lines.append(f"- Discounting convention: {I.discounting.mode}")
    lines.append(f"- Tax rate: {_fmt_pct(tax)}")
    lines.append(f"- Stable growth: {_fmt_pct(I.drivers.stable_growth)}")
    lines.append(f"- Stable margin: {_fmt_pct(I.drivers.stable_margin)}")
    lines.append(f"- Sales-to-capital (last): {I.sales_to_capital[-1]:.2f}")
    lines.append(f"- WACC (last): {_fmt_pct(I.wacc[-1])}")
    lines.append(f"- Net debt: {I.net_debt:,.0f}; Cash (non-op): {I.cash_nonop:,.0f}")
    lines.append("")

    # Detailed path table
    lines.append("## Per-Year Detail")
    hdr = [
        "Year",
        "Revenue",
        "Growth",
        "Margin",
        "Sales/Capital",
        "ROIC",
        "Reinvest",
        "FCFF",
        "WACC",
        "DF",
        "PV(FCFF)",
    ]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("| " + " | ".join(["---"] * len(hdr)) + " |")
    for t in range(T):
        row = [
            str(t + 1),
            _fmt_f(float(rev[t])),
            _fmt_pct(float(g[t])),
            _fmt_pct(float(m[t])),
            f"{float(s2c[t]):.2f}",
            _fmt_pct(float(roic[t])),
            _fmt_f(float(reinvest[t])),
            _fmt_f(float(fcff[t])),
            _fmt_pct(float(wacc[t])),
            f"{float(df[t]):.4f}",
            _fmt_f(float(pv_fcff[t])),
        ]
        lines.append("| " + " | ".join(row) + " |")

    # Fundamentals section (intermediate parsed output)
    if fundamentals is not None:
        lines.append("")
        lines.append("## Fundamentals (Parsed)")
        # Annuals table
        years = sorted(fundamentals.revenue.keys())
        if years:
            lines.append("| Year | Revenue | EBIT |")
            lines.append("| --- | --- | --- |")
            for y in years:
                r = float(fundamentals.revenue.get(y, 0.0))
                e = float(fundamentals.ebit.get(y, 0.0))
                lines.append(f"| {y} | {_fmt_f(r)} | {_fmt_f(e)} |")
        # TTM and other fields
        ttms = []
        if fundamentals.revenue_ttm:
            ttms.append(f"Revenue TTM: {_fmt_f(float(fundamentals.revenue_ttm))}")
        if fundamentals.ebit_ttm:
            ttms.append(f"EBIT TTM: {_fmt_f(float(fundamentals.ebit_ttm))}")
        if ttms:
            lines.append("")
            lines.append("- " + "; ".join(ttms))
        if fundamentals.shares_out is not None:
            lines.append(f"- Shares out: {float(fundamentals.shares_out):,.0f}")
        if fundamentals.tax_rate is not None:
            lines.append(f"- Approx tax rate: {_fmt_pct(float(fundamentals.tax_rate))}")
        # Additional parsed items (latest year summaries if present)
        def _latest(d: dict) -> tuple[int, float] | None:
            if not d:
                return None
            y = max(d.keys())
            return int(y), float(d[y])

        extras = []
        la = _latest(fundamentals.dep_amort)
        if la:
            extras.append(f"Depreciation & Amortization (FY{la[0]}): {_fmt_f(la[1])}")
            # D&A as % revenue if same year revenue exists
            rv = fundamentals.revenue.get(la[0])
            if rv and rv != 0:
                extras.append(f"D&A as % of revenue (FY{la[0]}): {_fmt_pct(la[1]/float(rv))}")
        cx = _latest(fundamentals.capex)
        if cx:
            extras.append(f"Capex (FY{cx[0]}): {_fmt_f(cx[1])}")
        las = _latest(fundamentals.lease_assets)
        if las:
            extras.append(f"Operating Lease ROU Assets (FY{las[0]}): {_fmt_f(las[1])}")
        lli = _latest(fundamentals.lease_liabilities)
        if lli:
            extras.append(f"Operating Lease Liabilities (FY{lli[0]}): {_fmt_f(lli[1])}")
        # Working capital (latest year both present)
        if fundamentals.current_assets and fundamentals.current_liabilities:
            y = max(set(fundamentals.current_assets.keys()) & set(fundamentals.current_liabilities.keys())) if (set(fundamentals.current_assets.keys()) & set(fundamentals.current_liabilities.keys())) else None
            if y:
                wc = float(fundamentals.current_assets[y]) - float(fundamentals.current_liabilities[y])
                extras.append(f"Working capital (FY{int(y)}): {_fmt_f(wc)}")
        if extras:
            lines.append("- " + "; ".join(extras))

    # Terminal section
    lines.append("")
    lines.append("## Terminal Value")
    r_inf = float(I.wacc[-1])
    g_inf = float(I.drivers.stable_growth)
    lines.append(f"- Next-year FCFF (T+1): {_fmt_f(float(fcff_T1))}")
    lines.append(f"- r - g: {_fmt_pct(r_inf - g_inf)}")
    lines.append(f"- TV at T: {_fmt_f(float(tv_T))}")
    lines.append(f"- Discount factor at T: {float(df[-1]):.4f}")
    lines.append(f"- PV(TV): {_fmt_f(float(pv_terminal))}")
    lines.append("")

    # Optional embedded charts
    sens_md = _embed_png(sensitivity_png, "Sensitivity Heatmap")
    drv_md = _embed_png(driver_paths_png, "Driver Paths")
    bridge_md = _embed_png(pv_bridge_png, "PV Bridge")
    price_md = _embed_png(price_vs_value_png, "Price vs Value")
    if sens_md or drv_md or bridge_md or price_md:
        lines.append("## Charts")
        if sens_md:
            lines.append(sens_md)
        if drv_md:
            lines.append(drv_md)
        if bridge_md:
            lines.append(bridge_md)
        if price_md:
            lines.append(price_md)
        lines.append("")

    # News & Impacts
    if news and (news.facts or news.impacts):
        lines.append("")
        lines.append("## News & Impacts")
        if news.facts:
            lines.append("**Facts:**")
            for f in news.facts[:8]:
                tag_str = f" [{', '.join(f.tags)}]" if getattr(f, 'tags', None) else ""
                lines.append(f"- {f.title}{tag_str} ({f.published_at or ''}) — {f.url} [sha:{(f.content_sha256 or '')[:8]}]")
        if news.impacts:
            lines.append("")
            lines.append("**Proposed Impacts (clamped):**")
            lines.append("| Driver | Window | Delta | Confidence | Facts |")
            lines.append("| --- | --- | --- | --- | --- |")
            for imp in news.impacts[:8]:
                window = f"Y+{imp.start_year_offset}→Y+{imp.end_year_offset}"
                refs = ",".join(imp.fact_ids)
                lines.append(f"| {imp.driver} | {window} | {imp.delta:+.4f} | {imp.confidence:.2f} | {refs} |")

    # Insights section (evidence-backed claims)
    if insights and insights.cards:
        lines.append("")
        lines.append("## Insights")
        for card in insights.cards:
            tags = f" [tags: {', '.join(card.tags)}]" if card.tags else ""
            window = f" [window: Y+{int(card.start_year_offset)}→Y+{int(card.end_year_offset)}]"
            conf = f" [confidence: {float(card.confidence):.2f}]"
            lines.append(f"- {card.claim}{tags}{window}{conf}")
            # Quotes beneath the claim
            for q in card.quotes[:8]:
                snaps = " ".join([f"[snap:{sid}]" for sid in (q.snapshot_ids or [])])
                srcs = " ".join([f"[source:{u}]" for u in (q.sources or [])])
                meta = f" {snaps} {srcs}".strip()
                lines.append(f"  \"{q.text}\"{(' ' + meta) if meta else ''}")

    # Provenance
    lines.append("## Provenance")
    pv = I.provenance
    if pv.source_url or pv.vendor:
        lines.append(f"- Vendor: {pv.vendor or 'unknown'}")
        if pv.source_url:
            lines.append(f"- Source: {pv.source_url}")
        if pv.retrieved_at:
            lines.append(f"- Retrieved: {pv.retrieved_at}")
        if pv.content_sha256:
            lines.append(f"- SHA-256: `{pv.content_sha256}`")
    else:
        lines.append("- No provenance provided (synthetic or local inputs)")

    # Citations to external snapshots
    if citations is None and (pv.source_url or pv.content_sha256):
        auto: List[str] = []
        if pv.source_url or pv.vendor:
            vs = pv.vendor or "vendor"
            auto.append(f"Provenance: {vs}{f' — {pv.source_url}' if pv.source_url else ''}{f' (sha: {pv.content_sha256})' if pv.content_sha256 else ''}")
        citations = auto if auto else None
    if citations:
        lines.append("")
        lines.append("## Citations")
        for c in citations:
            lines.append(f"- {c}")

    lines.append("")
    lines.append("_Generated by Investing Agent. Deterministic given the same inputs._")
    md = "\n".join(lines)
    # Optional LLM narrative merge (deterministic, cassette-based)
    if llm_output is not None:
        try:
            md = merge_llm_sections(md, llm_output, inputs=I, valuation=V)  # type: ignore[arg-type]
        except Exception:
            pass
    return md
