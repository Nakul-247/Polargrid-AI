"""Rule-based baseline dispatch used as an apples-to-apples comparator."""
from __future__ import annotations
from .physics import battery_limits,battery_heating_kw,fuel_lph,solar_power_kw,wind_power_kw

def run_baseline(data:dict,reserve_floor_pct:float=30,cutout_ms:float=30)->dict:
    cap= battery_limits(data['temperature_c'],data['id']=='cold_battery')[2]; charge_limit,discharge_limit,_=battery_limits(data['temperature_c'],data['id']=='cold_battery'); soc=data['battery_soc_pct']/100*cap; floor=cap*reserve_floor_pct/100; rows=[]
    for h in range(24):
        wind=wind_power_kw(data['wind_speed_series_ms'][h],cutout_ms); solar=solar_power_kw(data['solar_irradiance_wm2'][h]); heat=battery_heating_kw(data['temperature_c']); demand=data['critical_load_kw'][h]+data['non_critical_load_kw'][h]+heat; remaining=demand-wind-solar
        discharge=min(discharge_limit,max(0,soc-floor),max(0,remaining)); soc-=discharge; remaining-=discharge; diesel=0.; gen={}
        for g in data['generators']:
            p=min(g['rated_kw'],max(0,remaining)) if g['available'] else 0
            if p and p<g['rated_kw']*g['minimum_stable_fraction']: p=g['rated_kw']*g['minimum_stable_fraction']
            p=min(p,g['rated_kw']); diesel+=p; remaining-=p; gen[g['id']]=p
        shed=max(0,remaining); # baseline may incorrectly overshed flexible but never critical in feasible cases
        noncrit=min(data['non_critical_load_kw'][h],shed); critical_shed=max(0,shed-noncrit)
        fuel=sum(fuel_lph(gen[g['id']],g['fuel_intercept_lph'],g['fuel_slope_l_per_kwh']) for g in data['generators'])
        rows.append(dict(hour=h,wind_kw=round(wind,2),solar_kw=round(solar,2),diesel_kw=round(diesel,2),battery_discharge_kw=round(discharge,2),battery_charge_kw=0,battery_soc_pct=round(100*soc/cap if cap else 0,2),battery_temperature_c=data['temperature_c'],battery_heating_kw=heat,critical_load_kw=data['critical_load_kw'][h],non_critical_load_kw=data['non_critical_load_kw'][h],non_critical_shed_kw=round(noncrit,2),critical_shed_kw=round(critical_shed,2),fuel_l=fuel,wind_speed_ms=data['wind_speed_series_ms'][h]))
    return rows
