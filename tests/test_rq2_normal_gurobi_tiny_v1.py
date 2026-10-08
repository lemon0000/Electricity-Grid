"""Current Gurobi interface check on the unchanged numeric normal kernel."""
from dataclasses import replace
import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_numeric as api
from test_rq2_continuous_grid_normal_v1 import fixture, model_for
from test_rq2_normal_execution_stream_numeric_v1 import BUDGET, SPEC
from src.solvers import rq2_gurobi_direct_development as direct


def test_gurobi_direct_five_second_tiny_normal_has_complete_witness(monkeypatch):
    # Test-only injection isolates adapter compatibility; production remains unmodified.
    monkeypatch.setattr(api.native, 'create_solver', direct.create_solver)
    inputs = fixture(2)
    specification = replace(SPEC, name='gurobi', expected_package_version='13.0.2',
        time_limit_seconds=5.)
    budget = replace(BUDGET, max_seconds_per_solve=5.)
    scale = api.model_scale(model_for(inputs))
    identity = api.normal_input_identity(inputs)
    result = api.run_normal_only(inputs, expected_input_identity=identity,
        expected_execution_identity=api.normal_execution_identity(identity, scale, specification, budget),
        expected_scale=scale, specification=specification, budget=budget)
    assert result.solver_calls == 1 and result.call_count_complete
    assert result.normal_accepted and result.errors == (), (result.errors, result.normal.errors)
    assert result.normal.assignment_valid and result.normal.optimal
    assert result.witness is not None
    assert result.formal_result is False and result.security_certified is False


@pytest.mark.parametrize('change', [dict(name='highs'), dict(time_limit_seconds=10.),
    dict(threads=2), dict(threads=True), dict(expected_package_version='0'), dict(tee=True),
    dict(random_seed=1), dict(mip_relative_gap=1e-4), dict(feasibility_tolerance=1e-6)])
def test_direct_scope_rejects_before_factory(monkeypatch, change):
    specification = replace(SPEC, name='gurobi', expected_package_version='13.0.2', time_limit_seconds=5.)
    monkeypatch.setattr(direct, 'SolverFactory', lambda *a, **k: pytest.fail('factory reached'))
    with pytest.raises(ValueError):
        direct.create_solver(replace(specification, **change))


@pytest.mark.parametrize('name', ['GUROBI', 'gurobi_direct', 'results_', 'solution', 'solver_results'])
def test_factory_and_result_type_sources_bound(tmp_path, monkeypatch, name):
    before = direct.implementation_identity()
    source = tmp_path/'changed.py'
    source.write_text('# alternate local implementation\n')
    monkeypatch.setattr(getattr(direct, name), '__file__', str(source))
    assert direct.implementation_identity() != before
