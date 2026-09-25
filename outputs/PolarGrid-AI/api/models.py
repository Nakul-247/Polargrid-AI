"""Request and response contracts for PolarGrid AI."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    temperature_c: float
    wind_speed_ms: float
    solar_wm2: float
    station_demand_kw: float
    state: Literal['STABLE','WARNING','RESPONSE MODE']

class ScenarioDetail(ScenarioSummary):
    critical_load_kw: float
    non_critical_load_kw: float
    battery_soc_pct: float
    battery_condition: str
    generators: list[dict[str, Any]]

class SimulationRequest(BaseModel):
    scenario_id: str = 'polar_night'
    reserve_floor_pct: float | None = Field(None, ge=0, le=95)
    wind_cutout_ms: float | None = Field(None, gt=0)

class Alert(BaseModel):
    severity: Literal['SAFE','WARNING','CRITICAL']
    title: str
    cause: str
    effect: str
    recommended_response: str

class SimulationResponse(BaseModel):
    overall_status: str
    critical_load_protection: bool
    fuel_consumed_l: float
    renewable_contribution_pct: float
    minimum_battery_soc_pct: float
    battery_temperature_c: float
    non_critical_energy_shed_kwh: float
    alerts: list[Alert]
    recommendation: str
    explanation: str
    hourly_dispatch: list[dict[str, Any]]
    event_timeline: list[dict[str, str]]
    solver_status: str
    solve_time_ms: float
    emergency_fallback: bool = False
    units: dict[str, str]

class CompareResponse(BaseModel):
    baseline: SimulationResponse
    optimized: SimulationResponse
    fuel_savings_pct: float

