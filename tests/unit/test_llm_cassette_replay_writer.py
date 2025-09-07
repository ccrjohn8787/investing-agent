from __future__ import annotations

import json
from pathlib import Path

from investing_agent.llm.cassette import record, replay
from investing_agent.schemas.writer_llm import WriterLLMOutput
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="CassetteCo",
        ticker="CAS",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.05] * T,
            oper_margin=[0.15] * T,
            stable_growth=0.02,
            stable_margin=0.15,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.06] * T,
        macro=Macro(risk_free_curve=[0.04] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode="end"),
    )


def test_writer_replay_identity(tmp_path):
    # Prepare a deterministic fake response (WriterLLMOutput)
    response = {
        "metadata": {"model": "gpt-4.1-mini", "params": {"temperature": 0, "top_p": 1, "seed": 2025}},
        "sections": [
            {"title": "Business Model", "paragraphs": ["BM paragraph"], "refs": ["table:Per-Year Detail"]}
        ],
    }
    request = {
        "model_id": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": "writer"}],
        "params": {"temperature": 0, "top_p": 1, "seed": 2025},
        "task": "writer_sections",
    }
    # Record
    cassette = tmp_path / "writer.jsonl"
    record(request, response, cassette)
    # Replay
    replayed = replay(request, cassette)
    # Build WriterLLMOutput from both paths and ensure identical merged report
    I = base_inputs()
    V = kernel_value(I)
    out1 = WriterLLMOutput.model_validate(response)
    out2 = WriterLLMOutput.model_validate(replayed)
    md1 = render_report(I, V, llm_output=out1)
    md2 = render_report(I, V, llm_output=out2)
    assert md1 == md2

