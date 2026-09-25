"""Deterministic, synthetic 24-hour Antarctic station scenarios."""
from __future__ import annotations
import numpy as np
from .models import ScenarioDetail, ScenarioSummary

BASE_GENERATORS = [
    {'id':'G1','rated_kw':80.0,'minimum_stable_fraction':0.30,'available':True,'fuel_intercept_lph':3.0,'fuel_slope_l_per_kwh':0.235},
    {'id':'G2','rated_kw':60.0,'minimum_stable_fraction':0.30,'available':True,'fuel_intercept_lph':2.4,'fuel_slope_l_per_kwh':0.255},
]
CONFIG = {
 'normal_summer': dict(name='Normal Summer',description='Mild conditions with dependable wind and solar.',temperature_c=-16,wind_speed_ms=11,solar_wm2=380,demand=54,soc=76,state='STABLE',condition='Nominal'),
 'polar_night': dict(name='Polar Night',description='No solar generation; preserve the battery reserve.',temperature_c=-29,wind_speed_ms=8,solar_wm2=0,demand=61,soc=58,state='WARNING',condition='Nominal'),
 'blizzard': dict(name='Blizzard',description='Wind exceeds safe turbine operating limit.',temperature_c=-34,wind_speed_ms=32,solar_wm2=0,demand=66,soc=47,state='RESPONSE MODE',condition='Cold-limited'),
 'cold_battery': dict(name='Cold Battery',description='Extreme cold lowers usable battery capability.',temperature_c=-43,wind_speed_ms=10,solar_wm2=0,demand=63,soc=42,state='WARNING',condition='Heated / derated'),
 'generator_failure': dict(name='Generator Failure',description='Generator 1 is unavailable; reserve protection is tight.',temperature_c=-31,wind_speed_ms=6,solar_wm2=0,demand=65,soc=51,state='RESPONSE MODE',condition='Nominal'),
}
def _loads(base: float) -> tuple[list[float], list[float]]:
    x=np.arange(24); total=base + np.where((x<6)|(x>=17),5.0,0.0) + np.where((x>=11)&(x<=15),-2.0,0.0)
    return (total*0.72).round(2).tolist(), (total*0.28).round(2).tolist()
def get_scenario(scenario_id: str) -> dict:
    if scenario_id not in CONFIG: raise KeyError(scenario_id)
    c=CONFIG[scenario_id]; critical,noncritical=_loads(c['demand']); generators=[dict(g) for g in BASE_GENERATORS]
    if scenario_id=='generator_failure': generators[0]['available']=False
    wind=[c['wind_speed_ms'] + (3 if 7<=h<=15 else -1) for h in range(24)]
    solar=[max(0.0,c['solar_wm2']*np.sin(np.pi*(h-7)/10)) if 7<h<17 else 0.0 for h in range(24)]
    return dict(id=scenario_id, **c, critical_load_kw=critical, non_critical_load_kw=noncritical, wind_speed_series_ms=wind, solar_irradiance_wm2=solar, battery_soc_pct=c['soc'], generators=generators)
def scenario_detail(scenario_id: str) -> ScenarioDetail:
    d=get_scenario(scenario_id); return ScenarioDetail(id=d['id'],name=d['name'],description=d['description'],temperature_c=d['temperature_c'],wind_speed_ms=d['wind_speed_ms'],solar_wm2=d['solar_wm2'],station_demand_kw=d['demand'],state=d['state'],critical_load_kw=d['critical_load_kw'][0],non_critical_load_kw=d['non_critical_load_kw'][0],battery_soc_pct=d['battery_soc_pct'],battery_condition=d['condition'],generators=d['generators'])
def summaries() -> list[ScenarioSummary]:
    return [ScenarioSummary(id=k,name=v['name'],description=v['description'],temperature_c=v['temperature_c'],wind_speed_ms=v['wind_speed_ms'],solar_wm2=v['solar_wm2'],station_demand_kw=v['demand'],state=v['state']) for k,v in CONFIG.items()]
