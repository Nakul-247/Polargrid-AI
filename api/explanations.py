"""Explainable messages derived from a completed plan, never control commands."""
from .models import Alert

def build_explanation(data: dict, result: dict) -> tuple[str,str,list[Alert],list[dict[str,str]]]:
    emergency=result.get('emergency_fallback',False); cutout=any(x['wind_kw']==0 and x['wind_speed_ms']>=result['wind_cutout_ms'] for x in result['hourly_dispatch'])
    alerts=[]
    if emergency:
        alerts.append(Alert(severity='CRITICAL',title='Emergency fallback policy active',cause='The optimizer did not find a feasible plan under the selected constraints.',effect='Available resources are being allocated to critical demand first.',recommended_response='Inspect fuel, generator availability, and flexible-load curtailment immediately.'))
    if cutout:
        alerts.append(Alert(severity='WARNING',title='Wind cut-out active',cause='Wind speed is at or above the turbine safety threshold.',effect='Wind output is set to zero.',recommended_response='Generator support has been included in the plan.'))
    if data['solar_wm2']==0:
        alerts.append(Alert(severity='WARNING',title='Polar night active',cause='Solar irradiance is unavailable.',effect='Solar output is zero for this simulation.',recommended_response='Maintain the battery reserve and forecast diesel fuel.'))
    if not alerts: alerts.append(Alert(severity='SAFE',title='Critical-load protection confirmed',cause='Available generation meets planned critical demand.',effect='No critical energy is scheduled for shedding.',recommended_response='Continue to monitor the simulation plan.'))
    if emergency: recommendation='Emergency fallback: run all available generators within safe limits, use battery only above the reserve floor, and shed flexible demand as required.'
    else: recommendation='Use the optimized generator and battery dispatch; preserve the battery above the reserve floor while accepting renewable energy whenever available.'
    explanation='The generator runs when renewable supply and safe battery discharge cannot meet demand. Battery discharge is capped to preserve contingency reserve; only non-critical demand may be curtailed.'
    timeline=[{'time':'12:00','event':'Scenario evaluated'},{'time':'12:05','event':'Renewable availability checked'},{'time':'12:10','event':'Generator dispatch scheduled'},{'time':'12:15','event':'Reserve floor checked'},{'time':'12:20','event':'Dispatch plan updated'}]
    return recommendation,explanation,alerts,timeline
