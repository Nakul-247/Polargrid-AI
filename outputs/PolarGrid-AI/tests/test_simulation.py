import copy
import math
from api.optimizer import optimize
from api.scenarios import get_scenario

def plan(scenario_id, **kwargs):
    return optimize(get_scenario(scenario_id), **kwargs)

def assert_common_invariants(result, reserve=30):
    assert result['fuel_consumed_l'] >= 0
    assert result['units']['power'] == 'kW'
    assert result['units']['fuel'] == 'liters'
    for hour in result['hourly_dispatch']:
        assert not (hour['battery_charge_kw'] > 1e-6 and hour['battery_discharge_kw'] > 1e-6)

def test_normal_summer_operation_is_feasible_and_protects_critical_load():
    result=plan('normal_summer')
    assert result['solver_status'] == 'Optimal'
    assert result['critical_load_protection'] is True
    assert result['emergency_fallback'] is False
    assert all(h['critical_shed_kw'] == 0 for h in result['hourly_dispatch'])
    assert_common_invariants(result)

def test_polar_night_has_no_solar_output():
    result=plan('polar_night')
    assert all(h['solar_kw'] == 0 for h in result['hourly_dispatch'])
    assert_common_invariants(result)

def test_blizzard_cuts_wind_at_cutout_speed():
    result=plan('blizzard')
    assert any(h['wind_speed_ms'] >= 30 for h in result['hourly_dispatch'])
    assert all(h['wind_kw'] == 0 for h in result['hourly_dispatch'] if h['wind_speed_ms'] >= 30)

def test_cold_battery_is_restricted():
    result=plan('cold_battery')
    assert all(h['battery_discharge_kw'] <= 12.0 for h in result['hourly_dispatch'])
    assert all(h['battery_charge_kw'] <= 8.0 for h in result['hourly_dispatch'])

def test_failed_generator_produces_zero():
    result=plan('generator_failure')
    assert all(h['generator_kw']['G1'] == 0 for h in result['hourly_dispatch'])

def test_reserve_floor_and_minimum_stable_load_are_enforced():
    result=plan('polar_night', reserve_floor_pct=30)
    assert min(h['battery_soc_pct'] for h in result['hourly_dispatch']) >= 30
    scenario=get_scenario('polar_night')
    ratings={g['id']:(g['rated_kw'],g['minimum_stable_fraction']) for g in scenario['generators']}
    for h in result['hourly_dispatch']:
        for generator, value in h['generator_kw'].items():
            if value > 0:
                rated, minimum=ratings[generator]
                assert value >= rated * minimum - 1e-5

def test_noncritical_load_can_be_shed_without_critical_shedding():
    data=get_scenario('normal_summer')
    data['wind_speed_series_ms']=[0.0]*24; data['solar_irradiance_wm2']=[0.0]*24; data['battery_soc_pct']=30
    data['generators'][0]['rated_kw']=45; data['generators'][1]['available']=False
    result=optimize(data)
    assert result['solver_status'] == 'Optimal'
    assert result['non_critical_energy_shed_kwh'] > 0
    assert result['critical_load_protection'] is True

def test_infeasible_dispatch_returns_truthful_emergency_fallback():
    data=get_scenario('normal_summer')
    data['wind_speed_series_ms']=[0.0]*24; data['solar_irradiance_wm2']=[0.0]*24; data['battery_soc_pct']=30
    for generator in data['generators']:
        generator['available']=False
    result=optimize(data)
    assert result['emergency_fallback'] is True
    assert result['overall_status'] == 'EMERGENCY'
    assert result['solver_status'] != 'Optimal'
    assert 'Emergency fallback' in result['recommendation']
    assert result['critical_load_protection'] is False

def test_repeatable_results_excluding_measured_solve_time():
    first=plan('polar_night'); second=plan('polar_night')
    first.pop('solve_time_ms'); second.pop('solve_time_ms')
    assert first == second
