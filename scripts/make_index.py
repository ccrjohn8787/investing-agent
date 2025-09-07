#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from html import escape


def _link(path: Path, base: Path) -> str:
    rel = path.relative_to(base)
    return f"<li><a href=\"{rel.as_posix()}\">{escape(rel.as_posix())}</a></li>"


def main() -> int:
    out = Path("out")
    tickers = [p for p in out.iterdir() if p.is_dir() and p.name != "_backtests" and not p.name.startswith("_")]
    tickers.sort(key=lambda p: p.name)
    lines = ["<html><head><meta charset='utf-8'><title>Investing Agent — Outputs</title></head><body>"]
    lines.append("<h1>Outputs Index</h1>")
    for tdir in tickers:
        lines.append(f"<h2>{escape(tdir.name)}</h2>")
        items = []
        for name in ["report.html", "report.md", "sensitivity.png", "drivers.png", "pv_bridge.png", "price_vs_value.png", "series.csv", "fundamentals.csv", "manifest.json", "insights.json"]:
            p = tdir / name
            if p.exists():
                items.append(_link(p, out))
        # List any cassettes
        cas_dir = tdir / "cassettes"
        if cas_dir.exists():
            for p in sorted(cas_dir.glob("*.jsonl")):
                items.append(_link(p, out))
        if items:
            lines.append("<ul>" + "\n".join(items) + "</ul>")
    lines.append("</body></html>")
    (out / "index.html").write_text("\n".join(lines))
    print((out / "index.html").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

