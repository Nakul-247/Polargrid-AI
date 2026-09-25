"""Small, testable physical approximations used by both planning policies."""
from __future__ import annotations

def wind_power_kw(speed_ms: float, cutout_ms: float, rated_kw: float = 28.0) -> float:
    if speed_ms >= cutout_ms or speed_ms < 3: return 0.0
    return round(min(rated_kw, rated_kw * ((speed_ms - 3) / 12) ** 3), 3)
def solar_power_kw(irradiance_wm2: float, capacity_kw: float = 18.0) -> float:
    return round(max(0.0, min(capacity_kw, capacity_kw * irradiance_wm2 / 1000)), 3)
def battery_limits(temperature_c: float, cold_scenario: bool) -> tuple[float,float,float]:
    """charge kW, discharge kW, usable capacity kWh."""
    if temperature_c <= -45: return 0.0, 0.0, 0.0
    if cold_scenario or temperature_c <= -38: return 8.0, 12.0, 144.0
    if temperature_c <= -30: return 12.0, 18.0, 192.0
    return 20.0, 25.0, 240.0
def battery_heating_kw(temperature_c: float) -> float:
    return 4.0 if temperature_c <= -40 else 2.0 if temperature_c <= -30 else 0.8 if temperature_c <= -20 else 0.0
def fuel_lph(power_kw: float, intercept_lph: float, slope_l_per_kwh: float) -> float:
    return intercept_lph + slope_l_per_kwh * power_kw if power_kw > 0 else 0.0
