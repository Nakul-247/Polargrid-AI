"""PolarGrid AI local FastAPI service."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import CompareResponse, SimulationRequest, SimulationResponse
from .scenarios import get_scenario, scenario_detail, summaries
from .optimizer import optimize, _summarize
from .baseline import run_baseline

app=FastAPI(title='PolarGrid AI API',version='0.1.0',description='Offline Antarctic microgrid dispatch simulation API')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
DEFAULTS={'generator_rating_kw':80,'minimum_stable_load_pct':30,'battery_capacity_kwh':240,'battery_reserve_floor_pct':30,'wind_cutout_ms':30,'simulation_horizon_hours':24,'time_step_hours':1,'data_source':'synthetic demonstration data'}
def data_for(scenario_id:str):
    try:return get_scenario(scenario_id)
    except KeyError:raise HTTPException(status_code=404,detail=f'Unknown scenario: {scenario_id}')
@app.get('/api/health')
def health():return {'status':'ok','mode':'offline-local-demo','solver':'PuLP/CBC'}
@app.get('/api/scenarios')
def list_scenarios():return summaries()
@app.get('/api/scenarios/{scenario_id}')
def scenario(scenario_id:str):data_for(scenario_id);return scenario_detail(scenario_id)
@app.get('/api/assumptions')
def assumptions():return DEFAULTS
@app.post('/api/simulate',response_model=SimulationResponse)
def simulate(request:SimulationRequest):
    data=data_for(request.scenario_id); return optimize(data,request.reserve_floor_pct or DEFAULTS['battery_reserve_floor_pct'],request.wind_cutout_ms or DEFAULTS['wind_cutout_ms'])
@app.post('/api/compare',response_model=CompareResponse)
def compare(request:SimulationRequest):
    data=data_for(request.scenario_id); reserve=request.reserve_floor_pct or DEFAULTS['battery_reserve_floor_pct']; cutout=request.wind_cutout_ms or DEFAULTS['wind_cutout_ms']; optimized=optimize(data,reserve,cutout); rows=run_baseline(data,reserve,cutout); baseline=_summarize(data,rows,'RULE_BASED',0.0,any(r['critical_shed_kw']>0 for r in rows),cutout); savings=round(100*(baseline['fuel_consumed_l']-optimized['fuel_consumed_l'])/baseline['fuel_consumed_l'],2) if baseline['fuel_consumed_l'] else 0; return {'baseline':baseline,'optimized':optimized,'fuel_savings_pct':savings}
