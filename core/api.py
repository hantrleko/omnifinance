"""FastAPI endpoint layer for OmniFinance core calculations.

Provides REST API access to core financial calculation engines.
Run separately: `uvicorn core.api:app --host 0.0.0.0 --port 8000`

This module wraps core business logic functions as HTTP endpoints,
enabling mobile app integration and third-party access.
"""

from __future__ import annotations

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="OmniFinance API",
        description="Financial calculation endpoints for OmniFinance",
        version="1.9.8",
    )

    class CompoundRequest(BaseModel):
        principal: float = 100000
        annual_rate_pct: float = 6.0
        years: int = 20
        compound_freq: int = 12
        contribution: float = 0.0
        contrib_freq: int = 12
        inflation_pct: float = 0.0

    class SavingsRequest(BaseModel):
        current: float = 50000
        goal: float = 1000000
        annual_rate_pct: float = 6.0
        monthly_deposit: float = 10000

    class LoanRequest(BaseModel):
        principal: float = 1000000
        annual_rate_pct: float = 4.5
        years: int = 30
        periods_per_year: int = 12
        method: str = "等额本息"

    class BudgetRequest(BaseModel):
        income: float = 60000
        fixed_expense: float = 15000
        pct_needs: int = 50
        pct_wants: int = 30

    @app.get("/")
    def root():
        return {"app": "OmniFinance API", "version": "1.9.8", "status": "running"}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.post("/api/compound")
    def api_compound(req: CompoundRequest):
        from core.compound import compute_schedule
        df = compute_schedule(
            principal=req.principal, annual_rate_pct=req.annual_rate_pct,
            years=req.years, compound_freq=req.compound_freq,
            contribution=req.contribution, contrib_freq=req.contrib_freq,
            inflation_pct=req.inflation_pct,
        )
        return {"schedule": df.to_dict(orient="records"), "final_balance": float(df.iloc[-1]["年末余额"])}

    @app.post("/api/savings")
    def api_savings(req: SavingsRequest):
        from core.savings import calculate_savings_goal
        result = calculate_savings_goal(
            current=req.current, goal=req.goal,
            annual_rate_pct=req.annual_rate_pct, monthly_deposit=req.monthly_deposit,
        )
        return {
            "reached": result.reached,
            "months_needed": result.months_needed,
            "total_deposited": result.total_deposited,
            "total_interest": result.total_interest,
        }

    @app.post("/api/loan")
    def api_loan(req: LoanRequest):
        from core.planning import calculate_loan
        df, summary = calculate_loan(
            principal=req.principal, annual_rate_pct=req.annual_rate_pct,
            years=req.years, periods_per_year=req.periods_per_year, method=req.method,
        )
        return {"summary": summary, "periods": len(df)}

    @app.post("/api/budget")
    def api_budget(req: BudgetRequest):
        from core.planning import calculate_budget
        result = calculate_budget(
            income=req.income, fixed_expense=req.fixed_expense,
            pct_needs=req.pct_needs, pct_wants=req.pct_wants,
        )
        return {
            "amt_needs": result.amt_needs,
            "amt_wants": result.amt_wants,
            "amt_save": result.amt_save,
            "pct_save": result.pct_save,
        }

else:
    # Stub when FastAPI is not installed
    app = None

    def create_app():
        raise ImportError(
            "FastAPI is not installed. Install with: pip install fastapi uvicorn"
        )
