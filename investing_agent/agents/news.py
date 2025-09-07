from __future__ import annotations

"""
News agent (M6 v1)

Searches for recent, valuation-relevant news and ingests it into InputsI via bounded,
schema-checked code updates. LLM may assist with extraction/summarization but must be
deterministic (temp=0, top_p=1, seed=2025) and proposals are validated.
"""

from typing import List, Dict, Any, Optional

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.news import NewsItem, NewsBundle, NewsImpact, NewsSummary


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _tag_item(title: str, snippet: str) -> List[str]:
    t = (title or "").lower()
    s = (snippet or "").lower()
    tags: List[str] = []
    def has(*keys: str) -> bool:
        return any(k in t or k in s for k in keys)
    if has("guidance", "raises outlook", "updates outlook", "beats", "misses"):
        tags.append("guidance")
    if has("tariff", "sanction", "ban", "export control", "regulation"):
        tags.append("regulation")
    if has("capacity", "fab", "factory", "plant"):
        tags.append("capacity")
    if has("capex", "capital expenditure"):
        tags.append("capex")
    if has("layoff", "restructuring"):
        tags.append("restructuring")
    if has("lawsuit", "litigation", "fine"):
        tags.append("legal")
    if has("launch", "unveil", "product"):
        tags.append("product")
    return tags


def heuristic_summarize(bundle: NewsBundle, I: InputsI, scenario: Optional[Dict[str, Any]] = None) -> NewsSummary:
    # Tagging
    facts: List[NewsItem] = []
    for it in bundle.items:
        tags = _tag_item(it.title, it.snippet or "")
        # Avoid duplicating 'tags' when copying
        payload = it.model_dump(exclude_none=True, exclude={"tags"})
        facts.append(NewsItem(**payload, tags=tags))

    # Scenario caps
    news_cfg = (scenario or {}).get("news", {}) if isinstance(scenario, dict) else {}
    caps = news_cfg.get("caps") or (scenario or {}).get("news_caps") or {}
    cap_g = float(caps.get("growth_bps", 50)) / 10000.0  # 50 bps default
    cap_m = float(caps.get("margin_bps", 30)) / 10000.0  # 30 bps default
    cap_s = float(caps.get("s2c_abs", 0.1))              # absolute

    impacts: List[NewsImpact] = []
    # Simple heuristics
    for f in facts:
        if "guidance" in f.tags:
            impacts.append(NewsImpact(driver="growth", start_year_offset=0, end_year_offset=1, delta=cap_g, confidence=0.6, rationale="Positive guidance", fact_ids=[f.id]))
        if "regulation" in f.tags:
            impacts.append(NewsImpact(driver="margin", start_year_offset=0, end_year_offset=0, delta=-cap_m, confidence=0.5, rationale="Regulatory/tariff risk", fact_ids=[f.id]))
        if "capacity" in f.tags or "capex" in f.tags:
            impacts.append(NewsImpact(driver="s2c", start_year_offset=1, end_year_offset=3, delta=cap_s * 0.2, confidence=0.5, rationale="Capacity/Capex expands", fact_ids=[f.id]))

    return NewsSummary(facts=facts[:10], impacts=impacts[:5])


def ingest_and_update(I: InputsI, V: ValuationV, summary: NewsSummary, scenario: Optional[Dict[str, Any]] = None) -> InputsI:
    J = I.model_copy(deep=True)
    T = J.horizon()
    g = list(J.drivers.sales_growth)
    m = list(J.drivers.oper_margin)
    s2c = list(J.sales_to_capital)

    news_cfg = (scenario or {}).get("news", {}) if isinstance(scenario, dict) else {}
    caps = news_cfg.get("caps") or (scenario or {}).get("news_caps") or {}
    min_conf = float(news_cfg.get("min_confidence", 0.0))
    cap_g = float(caps.get("growth_bps", 50)) / 10000.0
    cap_m = float(caps.get("margin_bps", 30)) / 10000.0
    cap_s = float(caps.get("s2c_abs", 0.1))

    for imp in summary.impacts:
        if imp.confidence is not None and float(imp.confidence) < min_conf:
            continue
        a = max(0, int(imp.start_year_offset))
        b = max(a, min(T - 1, int(imp.end_year_offset)))
        if imp.driver == "growth":
            delta = _clamp(float(imp.delta), -cap_g, cap_g)
            for t in range(a, b + 1):
                g[t] = _clamp(float(g[t]) + delta, -0.99, 0.60)
        elif imp.driver == "margin":
            delta = _clamp(float(imp.delta), -cap_m, cap_m)
            for t in range(a, b + 1):
                m[t] = _clamp(float(m[t]) + delta, 0.0, 0.60)
        elif imp.driver == "s2c":
            delta = _clamp(float(imp.delta), -cap_s, cap_s)
            for t in range(a, b + 1):
                s2c[t] = _clamp(float(s2c[t]) + delta, 0.10, 10.0)
        else:
            continue

    # Respect terminal constraint indirectly by not changing stable_growth here.
    J.drivers.sales_growth = g
    J.drivers.oper_margin = m
    J.sales_to_capital = s2c
    return J


def llm_summarize(
    bundle: NewsBundle,
    I: InputsI,
    scenario: Optional[Dict[str, Any]] = None,
    *,
    cassette_path: Optional[str] = None,
    model_id: str = "gpt-4.1-mini",
) -> NewsSummary:
    """
    Deterministic LLM summarizer shim.
    - If cassette_path is provided, load JSON as NewsSummary.
    - Otherwise, fall back to heuristic summarizer.
    Note: Live LLM calls are not performed in CI.
    """
    if cassette_path:
        try:
            from pathlib import Path
            text = Path(cassette_path).read_text()
            import json
            data = json.loads(text)
            return NewsSummary.model_validate(data)
        except Exception:
            pass
    return heuristic_summarize(bundle, I, scenario=scenario)
