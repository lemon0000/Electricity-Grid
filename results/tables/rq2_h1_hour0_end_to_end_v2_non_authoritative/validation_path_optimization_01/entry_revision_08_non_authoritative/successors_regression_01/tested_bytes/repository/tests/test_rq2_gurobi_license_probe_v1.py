import json

import pytest

from experiments.diagnose_rq2_gurobi_license_environment_v1 import validate_result


def record():
    return dict(schema='synthetic_license_capacity_observation_v1', variables=22275,
        constraints=28004, status=2, solution_count=1, objective=0.,
        solver_runtime_seconds=.01, formal_result=False, research_model_solved=False,
        threads=1, time_limit_seconds=5., seed=0)


def test_exact_synthetic_observation():
    assert validate_result(json.dumps(record()).encode()) == record()


@pytest.mark.parametrize('key,value', [('variables', 2000), ('constraints', 28004.),
    ('threads', True), ('status', 9), ('solution_count', 0), ('seed', 1),
    ('objective', 1.), ('solver_runtime_seconds', float('nan')),
    ('solver_runtime_seconds', -1.), ('formal_result', True),
    ('research_model_solved', True), ('time_limit_seconds', 30.), ('extra', 0)])
def test_wrong_or_incomplete_capacity_is_rejected(key, value):
    body = record(); body[key] = value
    with pytest.raises(ValueError): validate_result(json.dumps(body).encode())
