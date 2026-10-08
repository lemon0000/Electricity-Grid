from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest
from pyomo.environ import SolverFactory

from experiments import h1_report_byte_bound_development_v1 as old_grammar
from experiments import h1_report_byte_bound_development_v2 as grammar

spec = importlib.util.spec_from_file_location('producer_shape', Path(__file__).resolve().parents[1]/
    'experiments/h1_producer_shape_development_v1.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


@pytest.fixture(scope='module')
def evidence():
    # Independent test assertion that constructing all evidence cannot solve.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(type(SolverFactory), '__call__', lambda *a, **k: pytest.fail('solver forbidden'))
        return api.audit()


def test_fixed_static_inventory_and_shape_counterexample(evidence):
    inventory = evidence['static_inventory']
    assert inventory['counts'] == dict(thermal=73,generators=158,buses=73,branches=120,
        dc_branches=1,reserve=101,areas=3,variables=891,stages=232)
    assert len(inventory['variable_names']) == 891
    assert inventory['max_name_json_token_bytes'] == 38
    assert inventory['cost_term_breakdown'] == dict(commitment=73, segment_power=216,startup=73,shutdown=0)
    assert len(inventory['cost_coefficients']) == 362
    assert inventory['constraints'] == dict(core_without_conditional=954,pinned_loader_origin_final=1211,
        pinned_loader_future_final=1272,boundary_valid_arbitrary_bounds_final=1465,
        generic_initial_arbitrary_bounds_final=1477)
    example = evidence['counterexample']
    assert example['constraints'] == 1272 and example['dwell_constraints'] == 61
    assert not example['old_limit_covers'] and not example['scientific_witness']
    assert not example['reachable_assignment_proven']
    assert evidence['source_pin_equal'] and evidence['loader_rows_checked'] == 192
    assert not evidence['producer_coverage_proven'] and not evidence['native_export_coverage']
    assert evidence['dependency_closure_verified'] and evidence['dependency_outer_members'] == 1695
    assert evidence['dependency_outer_sha256'] == api.OUTER_SHA
    assert 'src/rq2_joint_deliverability_boundary_v1/continuous_grid_normal.py' in evidence['source_sha256']
    assert 'src/rq2_joint_deliverability_boundary_v1/normal_h1_full_job_v3.py' in evidence['source_sha256']


def test_proof_rejects_wrong_dependency_closure_before_source_loading(monkeypatch):
    monkeypatch.setattr(api, 'OUTER_SHA', '0'*64)
    with pytest.raises(ValueError):
        api.audit()


def test_pinned_loader_assumption_rejects_derated_thermal_and_area_change():
    from tests.test_rq2_continuous_grid_normal_v1 import fixture
    data = fixture(1).data
    g, row = data.generators[0], data.hourly_points[0]
    # The proof predicate is narrower than ordinary validated grid inputs.
    with pytest.raises(ValueError):
        api.validate_loader_rows(data, [replace(row, generator_max_mw={g.uid:g.p_max_mw-1})])
    with pytest.raises(ValueError):
        api.validate_loader_rows(data, [replace(row, spin_up_requirement_by_area_mw={999:0.})])


def test_future_grammar_keeps_old_cap_and_bytes_bound():
    assert old_grammar.grammar()['constraints'] == ('int', 0, 1211)
    assert grammar.grammar()['constraints'] == ('int', 0, 1272)
    assert old_grammar.bound(grammar.grammar()) == 929218
    for value in (1211, 1212, 1272):
        old_grammar.validate(value, grammar.grammar()['constraints'])
    for value in (True, 1273, -1):
        with pytest.raises(ValueError):
            old_grammar.validate(value, grammar.grammar()['constraints'])
    with pytest.raises(ValueError):
        old_grammar.validate(1272, old_grammar.grammar()['constraints'])


def test_zero_costs_and_long_uid_cannot_be_hidden_in_descriptor():
    from tests.test_rq2_continuous_grid_normal_v1 import fixture
    from src.grid.rts_gmlc_scuc import _THERMAL_RESERVE_CATEGORIES
    data = fixture(1).data
    g = data.generators[0]
    changed = replace(data, generators=(replace(g,uid='long_'+'x'*100),))
    assert api.static_inventory(changed,_THERMAL_RESERVE_CATEGORIES)['max_name_json_token_bytes'] > 38
    zero = replace(data,generators=(replace(g,cost_values_usd_per_hour=(0.,)*4,
                                          cold_start_cost_usd=0.,shutdown_cost_usd=0.),))
    assert api.static_inventory(zero,_THERMAL_RESERVE_CATEGORIES)['cost_coefficients'] == []
