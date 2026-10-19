import pytest

from test_rq2_normal_execution_gurobi_direct_v1 import fixture, model_for, install, SPEC, BUDGET, api
from src.rq2_joint_deliverability_boundary_v1 import grid_structure_fast as fast


@pytest.mark.parametrize('fault', [None, 'exception', 'timeout', 'missing', 'unknown', 'nan',
    'objective', 'inverted_bounds', 'solution_status', 'multi_solution', 'multi_solver',
    'multi_problem', 'options', 'structure', 'root_deactivation', 'preload', 'load',
    'none', 'nonfinite_bound', 'native_infeasible'])
def test_entire_native_record_matches_with_fake_solver(monkeypatch, fault):
    inputs = fixture(2)
    results = []
    for structure in (fast.legacy._structure, fast.structure):
        with monkeypatch.context() as patch:
            calls = install(patch, inputs, **({} if fault is None else {'fault': fault}))
            patch.setattr(api.native, '_structure', structure)
            result = api.native._solve(lambda: model_for(inputs), SPEC, BUDGET, 'event_blind_normal')
            assert calls['solve'] == 1
            results.append(result)
    assert results[0] == results[1]
