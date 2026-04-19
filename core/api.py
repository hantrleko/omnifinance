"""FastAPI endpoint layer for OmniFinance core calculations.

Provides REST API access to core financial calculation engines.
Run separately: `uvicorn core.api:app --host 0.0.0.0 --port 8000`

This module wraps core business logic functions as HTTP endpoints,
enabling mobile app integration and third-party access.
"""

from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, field_validator
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

        @field_validator("principal", "contribution")
        @classmethod
        def non_negative(cls, v: float) -> float:
            if v < 0:
                raise ValueError("Must be non-negative")
            return v

        @field_validator("annual_rate_pct")
        @classmethod
        def valid_rate(cls, v: float) -> float:
            if not 0.0 <= v <= 100.0:
                raise ValueError("Rate must be between 0 and 100")
            return v

        @field_validator("years")
        @classmethod
        def valid_years(cls, v: int) -> int:
            if not 1 <= v <= 100:
                raise ValueError("Years must be between 1 and 100")
            return v

        @field_validator("compound_freq", "contrib_freq")
        @classmethod
        def valid_freq(cls, v: int) -> int:
            if v not in (1, 2, 4, 12, 52, 365):
                raise ValueError("Frequency must be one of 1, 2, 4, 12, 52, 365")
            return v

    class SavingsRequest(BaseModel):
        current: float = 50000
        goal: float = 1000000
        annual_rate_pct: float = 6.0
        monthly_deposit: float = 10000

        @field_validator("current", "monthly_deposit")
        @classmethod
        def non_negative(cls, v: float) -> float:
            if v < 0:
                raise ValueError("Must be non-negative")
            return v

        @field_validator("goal")
        @classmethod
        def positive_goal(cls, v: float) -> float:
            if v <= 0:
                raise ValueError("Goal must be positive")
            return v

        @field_validator("annual_rate_pct")
        @classmethod
        def valid_rate(cls, v: float) -> float:
            if not 0.0 <= v <= 100.0:
                raise ValueError("Rate must be between 0 and 100")
            return v

    class LoanRequest(BaseModel):
        principal: float = 1000000
        annual_rate_pct: float = 4.5
        years: int = 30
        periods_per_year: int = 12
        method: str = "等额本息"

        @field_validator("principal")
        @classmethod
        def positive_principal(cls, v: float) -> float:
            if v <= 0:
                raise ValueError("Principal must be positive")
            return v

        @field_validator("annual_rate_pct")
        @classmethod
        def valid_rate(cls, v: float) -> float:
            if not 0.0 <= v <= 50.0:
                raise ValueError("Rate must be between 0 and 50")
            return v

        @field_validator("years")
        @classmethod
        def valid_years(cls, v: int) -> int:
            if not 1 <= v <= 50:
                raise ValueError("Years must be between 1 and 50")
            return v

        @field_validator("method")
        @classmethod
        def valid_method(cls, v: str) -> str:
            if v not in ("等额本息", "等额本金"):
                raise ValueError("Method must be 等额本息 or 等额本金")
            return v

    class BudgetRequest(BaseModel):
        income: float = 60000
        fixed_expense: float = 15000
        pct_needs: int = 50
        pct_wants: int = 30

        @field_validator("income")
        @classmethod
        def positive_income(cls, v: float) -> float:
            if v <= 0:
                raise ValueError("Income must be positive")
            return v

        @field_validator("pct_needs", "pct_wants")
        @classmethod
        def valid_pct(cls, v: int) -> int:
            if not 0 <= v <= 100:
                raise ValueError("Percentage must be between 0 and 100")
            return v

    def _success(data: dict) -> dict:
        return {"success": True, "data": data}

    @app.get("/")
    def root() -> dict:
        return {"app": "OmniFinance API", "version": "1.9.8", "status": "running"}

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    @app.post("/api/compound")
    def api_compound(req: CompoundRequest) -> dict:
        try:
            from core.compound import compute_schedule
            df = compute_schedule(
                principal=req.principal, annual_rate_pct=req.annual_rate_pct,
                years=req.years, compound_freq=req.compound_freq,
                contribution=req.contribution, contrib_freq=req.contrib_freq,
                inflation_pct=req.inflation_pct,
            )
            return _success({
                "schedule": df.head(100).to_dict(orient="records"),
                "final_balance": float(df.iloc[-1]["年末余额"]),
                "total_rows": len(df),
            })
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/savings")
    def api_savings(req: SavingsRequest) -> dict:
        try:
            from core.savings import calculate_savings_goal
            result = calculate_savings_goal(
                current=req.current, goal=req.goal,
                annual_rate_pct=req.annual_rate_pct, monthly_deposit=req.monthly_deposit,
            )
            return _success({
                "reached": result.reached,
                "months_needed": result.months_needed,
                "total_deposited": result.total_deposited,
                "total_interest": result.total_interest,
            })
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/loan")
    def api_loan(req: LoanRequest) -> dict:
        try:
            from core.planning import calculate_loan
            df, summary = calculate_loan(
                principal=req.principal, annual_rate_pct=req.annual_rate_pct,
                years=req.years, periods_per_year=req.periods_per_year, method=req.method,
            )
            return _success({"summary": summary, "periods": len(df)})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/budget")
    def api_budget(req: BudgetRequest) -> dict:
        try:
            from core.planning import calculate_budget
            result = calculate_budget(
                income=req.income, fixed_expense=req.fixed_expense,
                pct_needs=req.pct_needs, pct_wants=req.pct_wants,
            )
            return _success({
                "amt_needs": result.amt_needs,
                "amt_wants": result.amt_wants,
                "amt_save": result.amt_save,
                "pct_save": result.pct_save,
            })
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

else:
    app = None

    def create_app():
        raise ImportError(
            "FastAPI is not installed. Install with: pip install fastapi uvicorn"
        )
