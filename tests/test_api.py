from fastapi.testclient import TestClient
from api.main import app
client=TestClient(app)

def test_health_and_scenario_endpoints():
    assert client.get('/api/health').status_code == 200
    scenarios=client.get('/api/scenarios').json()
    assert {x['id'] for x in scenarios} == {'normal_summer','polar_night','blizzard','cold_battery','generator_failure'}
    assert client.get('/api/scenarios/polar_night').json()['solar_wm2'] == 0

def test_compare_uses_identical_hourly_inputs():
    response=client.post('/api/compare',json={'scenario_id':'polar_night'})
    assert response.status_code == 200
    data=response.json()
    for base,opt in zip(data['baseline']['hourly_dispatch'],data['optimized']['hourly_dispatch']):
        assert base['critical_load_kw'] == opt['critical_load_kw']
        assert base['non_critical_load_kw'] == opt['non_critical_load_kw']
        assert base['wind_speed_ms'] == opt['wind_speed_ms']
        assert base['solar_kw'] == opt['solar_kw']
