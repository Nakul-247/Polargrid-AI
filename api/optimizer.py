"""PuLP/CBC 24-hour dispatch optimization and safe emergency fallback."""
from __future__ import annotations
import time
import pulp
from .physics import battery_limits,battery_heating_kw,fuel_lph,solar_power_kw,wind_power_kw
from .explanations import build_explanation

def _summarize(data:dict,rows:list[dict],solver_status:str,solve_time:float,emergency:bool,cutout:float)->dict:
    fuel=sum(r['fuel_l'] for r in rows); demand=sum(r['critical_load_kw']+r['non_critical_load_kw']+r['battery_heating_kw'] for r in rows); renewable=sum(r['wind_kw']+r['solar_kw'] for r in rows); noncritical=sum(r['non_critical_shed_kw'] for r in rows); critical=sum(r['critical_shed_kw'] for r in rows)
    out=dict(overall_status='EMERGENCY' if emergency else data['state'],critical_load_protection=critical<1e-5,fuel_consumed_l=round(fuel,2),renewable_contribution_pct=round(100*renewable/demand,2) if demand else 0,minimum_battery_soc_pct=round(min(r['battery_soc_pct'] for r in rows),2),battery_temperature_c=data['temperature_c'],non_critical_energy_shed_kwh=round(noncritical,2),hourly_dispatch=rows,solver_status=solver_status,solve_time_ms=round(solve_time*1000,2),emergency_fallback=emergency,units={'power':'kW','energy':'kWh','fuel':'liters','state_of_charge':'percent','temperature':'degrees Celsius','time_step':'hour'},wind_cutout_ms=cutout)
    rec,exp,alerts,timeline=build_explanation(data,out); out.update(recommendation=rec,explanation=exp,alerts=[a.model_dump() for a in alerts],event_timeline=timeline); out.pop('wind_cutout_ms'); return out

def _fallback(data:dict,reserve_floor_pct:float,cutout:float,start:float,status:str)->dict:
    charge_lim,discharge_lim,cap=battery_limits(data['temperature_c'],data['id']=='cold_battery'); floor=cap*reserve_floor_pct/100; soc=data['battery_soc_pct']/100*cap; rows=[]
    for h in range(24):
        wind=wind_power_kw(data['wind_speed_series_ms'][h],cutout); solar=solar_power_kw(data['solar_irradiance_wm2'][h]); heat=battery_heating_kw(data['temperature_c']); critical=data['critical_load_kw'][h]; noncritical=data['non_critical_load_kw'][h]; supply=wind+solar; gen_out={};
        # emergency policy: all available generators are started only as needed, inside rating limits.
        for g in data['generators']:
            need=max(0,critical+noncritical+heat-supply)
            p=min(g['rated_kw'],max(0,need)) if g['available'] else 0.0
            if p>0: p=max(p,g['rated_kw']*g['minimum_stable_fraction'])
            p=min(p,g['rated_kw']); gen_out[g['id']]=p; supply+=p
        battery=min(discharge_lim,max(0,soc-floor),max(0,critical+noncritical+heat-supply)); soc-=battery; supply+=battery
        # Flexible energy is curtailed before any critical demand.
        short=max(0,critical+noncritical+heat-supply); non_shed=min(noncritical,short); critical_shed=max(0,short-non_shed)
        diesel=sum(gen_out.values()); fuel=sum(fuel_lph(gen_out[g['id']],g['fuel_intercept_lph'],g['fuel_slope_l_per_kwh']) for g in data['generators'])
        rows.append(dict(hour=h,wind_kw=round(wind,2),solar_kw=round(solar,2),diesel_kw=round(diesel,2),generator_kw=gen_out,battery_discharge_kw=round(battery,2),battery_charge_kw=0,battery_soc_pct=round(100*soc/cap if cap else 0,2),battery_temperature_c=data['temperature_c'],battery_heating_kw=heat,critical_load_kw=critical,non_critical_load_kw=noncritical,non_critical_shed_kw=round(non_shed,2),critical_shed_kw=round(critical_shed,2),fuel_l=round(fuel,3),wind_speed_ms=data['wind_speed_series_ms'][h]))
    return _summarize(data,rows,status,time.perf_counter()-start,True,cutout)

def optimize(data:dict,reserve_floor_pct:float=30,cutout_ms:float=30)->dict:
    started=time.perf_counter(); n=24; charge_lim,discharge_lim,cap=battery_limits(data['temperature_c'],data['id']=='cold_battery')
    if cap<=0: return _fallback(data,reserve_floor_pct,cutout_ms,started,'INFEASIBLE: battery unavailable')
    floor=cap*reserve_floor_pct/100; initial=cap*data['battery_soc_pct']/100; prob=pulp.LpProblem('polargrid_dispatch',pulp.LpMinimize)
    gen={(g['id'],h):pulp.LpVariable(f'g_{g["id"]}_{h}',lowBound=0) for g in data['generators'] for h in range(n)}; on={(g['id'],h):pulp.LpVariable(f'on_{g["id"]}_{h}',cat='Binary') for g in data['generators'] for h in range(n)}
    charge=[pulp.LpVariable(f'charge_{h}',lowBound=0,upBound=charge_lim) for h in range(n)]; discharge=[pulp.LpVariable(f'discharge_{h}',lowBound=0,upBound=discharge_lim) for h in range(n)]; soc=[pulp.LpVariable(f'soc_{h}',lowBound=floor,upBound=cap) for h in range(n+1)]; shed=[pulp.LpVariable(f'shed_{h}',lowBound=0,upBound=data['non_critical_load_kw'][h]) for h in range(n)]; risk=[pulp.LpVariable(f'risk_{h}',lowBound=0) for h in range(n)]
    prob += soc[0]==initial
    objective=[]
    for h in range(n):
        wind=wind_power_kw(data['wind_speed_series_ms'][h],cutout_ms); solar=solar_power_kw(data['solar_irradiance_wm2'][h]); heat=battery_heating_kw(data['temperature_c']);
        for g in data['generators']:
            avail=1 if g['available'] else 0; prob += gen[g['id'],h] <= g['rated_kw']*on[g['id'],h]*avail; prob += gen[g['id'],h] >= g['rated_kw']*g['minimum_stable_fraction']*on[g['id'],h]*avail
            objective.append(g['fuel_slope_l_per_kwh']*gen[g['id'],h]+g['fuel_intercept_lph']*on[g['id'],h])
        prob += sum(gen[g['id'],h] for g in data['generators'])+wind+solar+discharge[h] == data['critical_load_kw'][h]+data['non_critical_load_kw'][h]-shed[h]+heat+charge[h]
        prob += soc[h+1] == soc[h]+0.92*charge[h]-discharge[h]/0.92
        prob += risk[h] >= (floor+0.05*cap)-soc[h+1]
        objective += [1200*shed[h],0.012*(charge[h]+discharge[h]),0.15*risk[h]]
    prob += pulp.lpSum(objective)
    try: prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
    except Exception as exc: return _fallback(data,reserve_floor_pct,cutout_ms,started,f'CBC ERROR: {exc}')
    status=pulp.LpStatus.get(prob.status,'UNKNOWN')
    if status!='Optimal': return _fallback(data,reserve_floor_pct,cutout_ms,started,status)
    rows=[]
    for h in range(n):
        gvals={g['id']:max(0,pulp.value(gen[g['id'],h]) or 0) for g in data['generators']}; wind=wind_power_kw(data['wind_speed_series_ms'][h],cutout_ms); solar=solar_power_kw(data['solar_irradiance_wm2'][h]); heat=battery_heating_kw(data['temperature_c']); fuel=sum(fuel_lph(gvals[g['id']],g['fuel_intercept_lph'],g['fuel_slope_l_per_kwh']) for g in data['generators'])
        rows.append(dict(hour=h,wind_kw=round(wind,2),solar_kw=round(solar,2),diesel_kw=round(sum(gvals.values()),2),generator_kw={k:round(v,2) for k,v in gvals.items()},battery_discharge_kw=round(max(0,pulp.value(discharge[h]) or 0),2),battery_charge_kw=round(max(0,pulp.value(charge[h]) or 0),2),battery_soc_pct=round(100*(pulp.value(soc[h+1]) or 0)/cap,2),battery_temperature_c=data['temperature_c'],battery_heating_kw=heat,critical_load_kw=data['critical_load_kw'][h],non_critical_load_kw=data['non_critical_load_kw'][h],non_critical_shed_kw=round(max(0,pulp.value(shed[h]) or 0),2),critical_shed_kw=0.0,fuel_l=round(fuel,3),wind_speed_ms=data['wind_speed_series_ms'][h]))
    return _summarize(data,rows,status,time.perf_counter()-started,False,cutout_ms)

