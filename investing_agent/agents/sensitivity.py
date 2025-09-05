from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import InputsI


@dataclass
class SensitivityResult:
    grid: np.ndarray  # values per share, shape (len(margins), len(growths))
    growth_axis: List[float]
    margin_axis: List[float]
    base_value_per_share: float


def compute_sensitivity(
    I: InputsI,
    growth_delta: float = 0.02,
    margin_delta: float = 0.01,
    steps: Tuple[int, int] = (5, 5),
) -> SensitivityResult:
    """
    Compute a grid sensitivity for terminal paths by shifting entire growth and margin paths.
    Deterministic and side-effect free.
    """
    base_v = kernel_value(I).value_per_share

    g0 = [g for g in I.drivers.sales_growth]
    m0 = [m for m in I.drivers.oper_margin]

    g_steps = np.linspace(-growth_delta, growth_delta, steps[0])
    m_steps = np.linspace(-margin_delta, margin_delta, steps[1])

    grid = np.zeros((steps[1], steps[0]), dtype=float)

    for i, dm in enumerate(m_steps):
        for j, dg in enumerate(g_steps):
            J = I.model_copy(deep=True)
            J.drivers.sales_growth = [max(-0.99, g + dg) for g in g0]
            J.drivers.oper_margin = [min(0.6, max(-0.6, m + dm)) for m in m0]
            vps = kernel_value(J).value_per_share
            grid[i, j] = vps

    return SensitivityResult(
        grid=grid, growth_axis=list(g_steps), margin_axis=list(m_steps), base_value_per_share=base_v
    )

