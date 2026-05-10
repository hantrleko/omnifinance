"""Core package for OmniFinance shared business logic.

Modules
-------
Calculation engines
    backtest        — Multi-strategy backtesting (MA / RSI / MACD / Bollinger)
    compound        — Compound interest schedule computation
    debt            — Debt payoff strategy planner (snowball / avalanche)
    education       — Education fund planning calculations
    insurance       — Insurance product analytics (protection + savings)
    montecarlo      — Monte-Carlo retirement / portfolio simulations
    planning        — Loan amortization, budget allocation, IRR solver
    portfolio       — Markowitz mean-variance portfolio optimisation
    retirement      — Dual-phase retirement planning
    savings         — Monthly compound savings goal simulation
    scenarios       — Scenario / sensitivity comparison helpers

Data & integration
    api             — Optional FastAPI REST endpoint layer
    benchmarks      — National-average benchmark data
    exchange_rates  — Live FX engine (yfinance) with offline fallback
    persistence     — Generic JSON persistence helpers
    storage         — Versioned scheme persistence with file locking

UI / cross-cutting
    chart_config    — Shared Plotly layout helpers
    config          — Application-wide constants
    currency        — Multi-currency selector and formatting
    export          — Generic data-export utilities (CSV / Excel)
    i18n            — Locale selection and translation helpers
    pdf_report      — PDF report rendering (optional)
    profile         — Personal financial profile sidebar widget
    reminders       — Financial reminder data model
    report_generator — HTML financial-report generator
    theme           — Streamlit theme injection (dark/light, glassmorphism)
    version         — Single source of truth for the package version
"""

from core.version import VERSION, __version__

__all__ = ["VERSION", "__version__"]
