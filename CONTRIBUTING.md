# Contributing to OmniFinance

Thanks for helping improve OmniFinance. This project is a Streamlit-based personal finance planning and lightweight investment analysis application.

## Development Principles

### 1. Keep the workflow clear

New features should support the main workflow:

```text
Financial profile
  -> Health diagnosis
  -> Opportunity detection
  -> Scenario and stress testing
  -> Prioritized action plan
  -> Exported report and review loop
```

Avoid adding isolated calculators unless they clearly connect to this workflow.

### 2. Separate logic from UI

Preferred structure:

- Put formulas, simulations, and data processing in `core/`.
- Put Streamlit display and user interaction in `pages/`.
- Add reusable helpers when page patterns repeat.
- Add tests for `core/` functions whenever possible.

### 3. Make assumptions visible

Financial calculations should show important assumptions, such as return rate, inflation rate, transaction cost, time horizon, data source, and whether results are nominal or inflation-adjusted.

## Local Setup

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the app:

```bash
streamlit run app.py
```

## Checks Before Committing

```bash
python -m compileall app.py home.py pages core tests
pytest -q
ruff check .
mypy core --ignore-missing-imports
```

## Testing Guidelines

Prioritize tests for financial logic in `core/`.

Useful test cases include:

- normal input;
- empty or missing input;
- invalid parameters;
- extreme values;
- zero interest or zero return;
- high inflation;
- negative cash flow;
- transaction costs and slippage;
- infeasible portfolio constraints.

## Code Style

- Use clear function names.
- Keep formulas readable.
- Prefer typed dataclasses for structured results.
- Avoid hidden magic constants.
- Keep Streamlit pages focused on presentation.
- Reduce duplicated chart, table, and export logic.

## Documentation

Update documentation when user-facing behavior changes:

- `README.md` for main features;
- `ROADMAP.md` for planned work;
- docstrings for non-trivial formulas;
- page descriptions for assumptions and limitations.

## Pull Request Checklist

- [ ] The change supports the main workflow.
- [ ] Core logic is separated from UI where practical.
- [ ] New core logic has tests.
- [ ] Assumptions are visible to users.
- [ ] `pytest -q` passes locally.
- [ ] `ruff check .` passes locally.
- [ ] Documentation is updated if needed.
