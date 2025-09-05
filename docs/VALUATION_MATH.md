# Valuation math

Drivers → Financials → Cashflows → PV → Equity

Drivers
- g_t, m_t, τ, σ_t, WACC_t, (shares, currency)

Projection
- R_t = R_{t-1}(1 + g_t)
- EBIT_t = m_t · R_t
- NOPAT_t = EBIT_t · (1 − τ)
- Reinv_t = max((R_t − R_{t-1}) / σ_t, 0)

FCFF
- FCFF_t = NOPAT_t − Reinv_t

PV
- End-year or mid-year discounting via WACC_t
- PV = Σ_{t=1..T} FCFF_t / Π_{k=1..t}(1 + WACC_k)
- Mid-year convention applies a half-year uplift factor

Terminal
- FCFF_{T+1} from terminal growth and margin
- TV_T = FCFF_{T+1} / (WACC_∞ − g_∞), with g_∞ < WACC_∞ − 50bps

Equity Bridge
- PV_ops = PV_explicit + PV_terminal
- Equity = PV_ops − NetDebt + NonOpCash
- Value per share = Equity / Shares

