# PolarGrid AI

A local, offline-first Antarctic microgrid decision-support prototype. The frontend can run independently, while the FastAPI service provides deterministic scenarios and a 24-hour PuLP/CBC dispatch optimizer.

## Requirements

- Python 3.11+
- Node 20+ for the React UI

## Start the API

```bash
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## Start the frontend

```bash
npm install
npm run dev
```

The mock API module exposes the same endpoint surface and can be configured to call `http://127.0.0.1:8000`. CORS is enabled only for local Vite development origins.

## Example calls

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/scenarios
curl http://127.0.0.1:8000/api/scenarios/polar_night
curl http://127.0.0.1:8000/api/assumptions
curl -X POST http://127.0.0.1:8000/api/simulate -H "Content-Type: application/json" -d '{"scenario_id":"blizzard"}'
curl -X POST http://127.0.0.1:8000/api/compare -H "Content-Type: application/json" -d '{"scenario_id":"polar_night"}'
```

## Architecture

- `api/scenarios.py`: deterministic synthetic scenario data.
- `api/physics.py`: isolated physical constraints and fuel approximation.
- `api/optimizer.py`: PuLP/CBC MILP and a non-fake emergency fallback when the model is infeasible.
- `api/baseline.py`: a rule-based dispatcher using the same hourly inputs.
- `api/explanations.py`: plain-language operator explanations and alert construction.
- `api/models.py`: Pydantic contracts.

The optimizer never includes critical-load shedding as a decision variable. The fallback treats flexible demand as the only shed-able load and reports any inability to protect critical load truthfully.

## Validation tests

```bash
pytest
npm run test:ui
```

The Python suite verifies all five scenarios, critical-load protection for feasible plans, reserve and generator constraints, deterministic results, baseline input parity, and emergency fallback. The UI suite checks loading, completed, warning, and no-feasible-plan states plus the presence of populated chart sections. Results are prototype simulations using configurable assumptions and synthetic demonstration data; they do not claim real-world accuracy.
