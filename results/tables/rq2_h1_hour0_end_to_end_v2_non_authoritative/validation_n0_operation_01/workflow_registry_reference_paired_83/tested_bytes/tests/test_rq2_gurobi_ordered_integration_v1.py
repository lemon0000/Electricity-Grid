"""Successor-specific routing and identity guards; no real solver calls."""
from dataclasses import replace

import pytest

from test_rq2_normal_execution_gurobi_ordered_v1 import api, SPEC, arguments, fixture, install


def test_exact_helper_routes():
    from src.rq2_joint_deliverability_boundary_v1 import grid_structure_fast, identity_stream_ordered
    assert api.native._structure is grid_structure_fast.structure
    assert api.normal_input_identity is identity_stream_ordered.normal_input_identity
    assert api.streaming.normal_input_identity is identity_stream_ordered.normal_input_identity


@pytest.mark.parametrize('field,value', [
    ('time_limit_seconds', 5.), ('time_limit_seconds', 16.), ('threads', 2),
    ('mip_relative_gap', 1e-6), ('random_seed', 1), ('tee', True),
    ('optimality_tolerance', 1e-8), ('integer_feasibility_tolerance', 1e-8)])
def test_adapter_fixed_scope_before_factory(monkeypatch, field, value):
    def forbidden(*a, **k):
        raise AssertionError('factory must not be called')
    monkeypatch.setattr(api.native.adapter, 'SolverFactory', forbidden)
    with pytest.raises(ValueError):
        api.native.adapter.create_solver(replace(SPEC, **{field: value}))


def test_structure_helper_identity_drift_rejected_before_solver(monkeypatch):
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    monkeypatch.setattr(api.native.structure, 'implementation_identity', lambda: '0'*64)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}


def test_direct_predecessor_pin_rejected_before_solver(monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_execution_gurobi_direct as prior
    inputs = fixture(2)
    calls = install(monkeypatch, inputs)
    kw = arguments(inputs)
    old_spec = replace(SPEC, time_limit_seconds=5.)
    old_budget = replace(kw['budget'], max_seconds_per_solve=5.)
    kw['expected_execution_identity'] = prior.normal_execution_identity(
        kw['expected_input_identity'], kw['expected_scale'], old_spec, old_budget)
    with pytest.raises(ValueError, match='execution identity drift'):
        api.run_normal_only(inputs, **kw)
    assert calls == {'create': 0, 'solve': 0}
