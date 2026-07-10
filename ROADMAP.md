# OmniFinance Roadmap

This roadmap records the current development direction of OmniFinance. The project is maintained as a personal finance planning and lightweight investment analysis platform, not as a regulated financial advisory product.

## Product Direction

The next stage of OmniFinance should move from a broad tool collection toward a clearer decision workflow:

```text
Financial profile
  → Health diagnosis
  → Opportunity detection
  → Scenario and stress testing
  → Prioritized action plan
  → Exported report and review loop
```

The long-term goal is to make each module contribute to this workflow instead of existing as an isolated calculator.

---

## v2.3 — Presentation and Onboarding

Focus: make the project easier to understand, try, and present.

- [ ] Add screenshots for the dashboard, portfolio optimizer, backtest engine, and action plan pages.
- [ ] Add an online demo link when the deployment is stable.
- [ ] Provide sample input data for quick testing.
- [ ] Improve the home page to emphasize the main decision workflow.
- [ ] Add a short English project summary for international readers.
- [ ] Add basic usage examples for common user scenarios.

Suggested user scenarios:

1. A beginner wants to check whether monthly savings are enough for a target.
2. A household wants to compare loan repayment options.
3. An investor wants to compare portfolio weights and risk.
4. A retiree wants to test withdrawal and longevity risk.
5. A user wants a 90-day financial action plan.

---

## v2.4 — Investment Analysis Upgrade

Focus: strengthen the investment analysis engine while keeping it understandable.

- [ ] Add buy-and-hold benchmark comparison to backtest results.
- [ ] Add parameter sensitivity heatmaps for MA, RSI, MACD, and Bollinger strategies.
- [ ] Add rolling return and rolling drawdown charts.
- [ ] Add risk contribution analysis to the portfolio optimizer.
- [ ] Add VaR and CVaR indicators.
- [ ] Add correlation heatmaps and asset-level contribution tables.
- [ ] Add warning messages for overfitting-prone parameter choices.

Possible future extensions:

- [x] Black-Litterman allocation. *(shipped in `core/allocation.py` + 高级资产配置 page)*
- [x] Risk parity allocation. *(shipped in `core/allocation.py`)*
- [x] Walk-forward testing. *(shipped in `core/walkforward.py`, integrated into the backtester)*
- [x] Out-of-sample validation. *(stitched OOS equity curve + overfit verdict)*
- Multi-asset portfolio backtesting.

---

## v2.5 — Engineering Quality Upgrade

Focus: make the codebase safer to extend.

- [ ] Raise coverage threshold from 45% to 60%.
- [ ] Add edge-case tests for all core financial formulas.
- [ ] Add tests for missing data, empty inputs, invalid dates, and extreme parameters.
- [ ] Make selected mypy checks mandatory for stable core modules.
- [ ] Add more explicit error messages for user input validation.
- [ ] Reduce duplicated Streamlit UI patterns across pages.
- [ ] Create shared display helpers for metrics, charts, warnings, and export buttons.

High-priority test areas:

- Backtest transaction costs and slippage.
- Portfolio optimization constraints.
- Retirement projection assumptions.
- Loan repayment schedules.
- Insurance IRR and cash value calculations.
- Currency conversion fallbacks.

---

## v2.6 — Report and Review Loop

Focus: help users turn calculations into decisions.

- [ ] Improve Markdown and HTML report templates.
- [ ] Add a one-page financial diagnosis report.
- [x] Add action status tracking: planned, in progress, completed, skipped. *(复盘中心 action board)*
- [x] Add monthly review summary. *(exportable Markdown report)*
- [x] Add comparison between previous and current financial health scores. *(automatic health snapshots + trend chart)*
- [ ] Add exportable decision logs for major financial choices.

---

## v3.0 — Integrated Personal Finance Workspace

Focus: make OmniFinance feel like a coherent financial workspace.

Potential directions:

- Personal profile persistence with import/export.
- Local-first storage for user records.
- Modular plugin-style page registration.
- More robust data-source abstraction.
- Multi-language documentation.
- Stronger accessibility and mobile layout support.

---

## Non-goals

OmniFinance should not be presented as:

- A guaranteed investment recommendation system.
- A replacement for certified financial, tax, legal, or insurance professionals.
- A high-frequency trading or institutional-grade portfolio platform.
- A system that promises returns based on backtested results.

The project should stay honest: useful for learning, scenario analysis, financial self-review, and software portfolio demonstration.
