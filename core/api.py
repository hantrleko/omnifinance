"""FastAPI endpoint layer for OmniFinance core calculations.

Provides REST API access to core financial calculation engines.
Run separately::

    uvicorn core.api:app --host 0.0.0.0 --port 8000

This module wraps core business logic functions as HTTP endpoints,
enabling mobile app integration and third-party access.

Design notes
------------
- FastAPI is an *optional* dependency. When it is unavailable, importing
  this module still succeeds, ``app`` is ``None``, and ``create_app()``
  raises a clear :class:`ImportError`. This avoids silent breakage of the
  Streamlit app whose ``requirements.txt`` does not pin FastAPI.
- All unhandled exceptions are logged and surface to the client as a
  generic 500 error to avoid leaking internal details.
"""

from __future__ import annotations

import logging
from typing import Any

from core.version import __version__

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, field_validator

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover - exercised only without FastAPI installed
    HAS_FASTAPI = False


def _build_app() -> FastAPI:
    """Construct and return a configured FastAPI application instance."""
    application = FastAPI(
        title="OmniFinance API",
        description="Financial calculation endpoints for OmniFinance",
        version=__version__,
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

    def _success(data: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "data": data}

    def _safe_call(action: str, fn):  # type: ignore[no-untyped-def]
        """Run *fn* and convert exceptions to safe HTTP responses.

        ``ValueError`` is treated as 400 (client input error). Anything else
        is logged with traceback and surfaced as a generic 500 to avoid
        leaking internal implementation details.
        """
        try:
            return fn()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 — top-level boundary by design
            logger.exception("Unhandled error in endpoint %s", action)
            raise HTTPException(  # noqa: B904
                status_code=500,
                detail="Internal server error. Please retry or contact support.",
            ) from exc

    @application.get("/")
    def root() -> dict[str, Any]:
        return {"app": "OmniFinance API", "version": __version__, "status": "running"}

    @application.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "healthy"}

    @application.post("/api/compound")
    def api_compound(req: CompoundRequest) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            from core.compound import compute_schedule

            df = compute_schedule(
                principal=req.principal,
                annual_rate_pct=req.annual_rate_pct,
                years=req.years,
                compound_freq=req.compound_freq,
                contribution=req.contribution,
                contrib_freq=req.contrib_freq,
                inflation_pct=req.inflation_pct,
            )
            return _success(
                {
                    "schedule": df.head(100).to_dict(orient="records"),
                    "final_balance": float(df.iloc[-1]["年末余额"]),
                    "total_rows": len(df),
                }
            )

        return _safe_call("compound", _do)

    @application.post("/api/savings")
    def api_savings(req: SavingsRequest) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            from core.savings import calculate_savings_goal

            result = calculate_savings_goal(
                current=req.current,
                goal=req.goal,
                annual_rate_pct=req.annual_rate_pct,
                monthly_deposit=req.monthly_deposit,
            )
            return _success(
                {
                    "reached": result.reached,
                    "months_needed": result.months_needed,
                    "total_deposited": result.total_deposited,
                    "total_interest": result.total_interest,
                }
            )

        return _safe_call("savings", _do)

    @application.post("/api/loan")
    def api_loan(req: LoanRequest) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            from core.planning import calculate_loan

            df, summary = calculate_loan(
                principal=req.principal,
                annual_rate_pct=req.annual_rate_pct,
                years=req.years,
                periods_per_year=req.periods_per_year,
                method=req.method,
            )
            return _success({"summary": summary, "periods": len(df)})

        return _safe_call("loan", _do)

    @application.post("/api/budget")
    def api_budget(req: BudgetRequest) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            from core.planning import calculate_budget

            result = calculate_budget(
                income=req.income,
                fixed_expense=req.fixed_expense,
                pct_needs=req.pct_needs,
                pct_wants=req.pct_wants,
            )
            return _success(
                {
                    "amt_needs": result.amt_needs,
                    "amt_wants": result.amt_wants,
                    "amt_save": result.amt_save,
                    "pct_save": result.pct_save,
                }
            )

        return _safe_call("budget", _do)

    return application


def create_app() -> FastAPI:
    """Application factory.

    Raises:
        ImportError: If FastAPI / Pydantic are not installed.
    """
    if not HAS_FASTAPI:
        raise ImportError(
            "FastAPI is not installed. Install with: pip install -r requirements-api.txt"
        )
    return _build_app()


# Module-level ASGI app: ``uvicorn core.api:app``. ``None`` when FastAPI is
# unavailable, so that importing this module never crashes the Streamlit app.
app: FastAPI | None = _build_app() if HAS_FASTAPI else None
