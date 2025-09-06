from __future__ import annotations

import io
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from investing_agent.agents.sensitivity import SensitivityResult
from investing_agent.schemas.prices import PriceSeries
from investing_agent.schemas.valuation import ValuationV


def plot_sensitivity_heatmap(res: SensitivityResult, title: str = "Sensitivity") -> bytes:
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    im = ax.imshow(res.grid, origin="lower", cmap="viridis")
    ax.set_xticks(range(len(res.growth_axis)))
    ax.set_xticklabels([f"{x*100:.1f}%" for x in res.growth_axis], rotation=45, ha="right")
    ax.set_yticks(range(len(res.margin_axis)))
    ax.set_yticklabels([f"{x*100:.1f}%" for x in res.margin_axis])
    ax.set_xlabel("Growth path shift")
    ax.set_ylabel("Margin path shift")
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Value per share")

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def plot_driver_paths(years: int, growth: np.ndarray, margin: np.ndarray, wacc: np.ndarray) -> bytes:
    x = np.arange(1, years + 1)
    fig, ax = plt.subplots(3, 1, figsize=(6, 6), dpi=150, sharex=True)

    ax[0].plot(x, growth * 100)
    ax[0].set_ylabel("Growth %")
    ax[0].grid(True, alpha=0.3)

    ax[1].plot(x, margin * 100)
    ax[1].set_ylabel("Margin %")
    ax[1].grid(True, alpha=0.3)

    ax[2].plot(x, wacc * 100)
    ax[2].set_ylabel("WACC %")
    ax[2].set_xlabel("Year")
    ax[2].grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def plot_price_vs_value(ps: PriceSeries, value_per_share: float, title: str = "Price vs Value") -> bytes:
    dates = [b.date for b in ps.bars]
    closes = [b.close for b in ps.bars]
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    if dates and closes:
        ax.plot(dates, closes, label="Price")
    ax.axhline(value_per_share, color="red", linestyle="--", label="Intrinsic Value")
    ax.set_title(title)
    ax.set_ylabel("$ per share")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    buf = io.BytesIO()
    fig.tight_layout()
    fig.autofmt_xdate()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def plot_pv_bridge(V: ValuationV, title: str = "PV Bridge") -> bytes:
    labels = ["PV explicit", "PV terminal", "Op assets", "Net debt", "Cash non-op", "Equity"]
    values = [V.pv_explicit, V.pv_terminal, V.pv_oper_assets, -V.net_debt, V.cash_nonop, V.equity_value]
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#000000"]
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    ax.bar(labels, values, color=colors)
    ax.set_title(title)
    ax.set_ylabel("$")
    ax.tick_params(axis='x', rotation=20)
    ax.grid(True, axis='y', alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
