#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


DOCS = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("codex.md"),
    Path("docs/VALUATION_MATH.md"),
    Path("docs/ALGORITHM.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/PROJECT_BOARD.md"),
    Path("docs/PROMPTS.md"),
]


def main() -> int:
    missing: list[str] = []
    code_ref_re = re.compile(r"`([^`]+)`")
    fence_re = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    for p in DOCS:
        if not p.exists():
            missing.append(f"doc missing: {p}")
            continue
        text = p.read_text(encoding="utf-8")
        # Remove fenced code blocks
        text = fence_re.sub("", text)
        for m in code_ref_re.finditer(text):
            ref = m.group(1)
            # Skip long or whitespace-containing spans (not paths)
            if len(ref) > 200 or any(ch.isspace() for ch in ref):
                continue
            # Skip placeholders, artifacts, or segments with special symbols
            if any(sym in ref for sym in ("<", ">", "*", "::")):
                continue
            if ref.startswith("out/"):
                continue
            # Only check path-like refs (not dotted module names)
            if "/" in ref or ref.endswith(('.md', '.py')):
                # Normalize possible dotted paths to file paths
                ref_path = None
                if ref.endswith(('.md', '.py')) and '/' not in ref and '.' in ref:
                    # e.g., investing_agent.kernels.ginzu.value -> investing_agent/kernels/ginzu.py
                    parts = ref.split('.')
                    if parts[-1] in ("py", "md"):
                        ref_path = Path(ref)
                    else:
                        ref_path = Path('/'.join(parts[:-1]) + '.py')
                else:
                    ref_path = Path(ref)
                if ref_path and not ref_path.exists():
                    # If it's a bare filename without a slash, treat as illustrative and skip
                    if '/' not in ref:
                        continue
                    # Allow known planned/illustrative references
                    sref = str(ref_path)
                    if "orchestration/fsm" in sref:
                        continue
                    if "/<agent>/" in sref or sref.startswith("prompts/") or sref.startswith("evals/"):
                        continue
                    if sref.endswith("SYN_report.md"):
                        continue
                    missing.append(f"{p}: reference not found: {ref}")
    if missing:
        print("Docs check found issues:\n" + "\n".join(missing))
        return 1
    print("Docs check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
