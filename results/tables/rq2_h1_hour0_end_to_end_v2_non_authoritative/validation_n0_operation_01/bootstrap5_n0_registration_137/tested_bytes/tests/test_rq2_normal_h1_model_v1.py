from copy import deepcopy
from dataclasses import replace

import pytest
from pyomo.environ import Var, value

from tests.test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_model as h1


def model(request):
    return h1.build_h1_stage_model(request, expected_identity=h1.h1_stage_identity(request))


def test_declared_modes_and_ceil_are_order_independent():
    x = fixture(1)
    base = x.data.generators[0]
    units = (replace(base, uid='thermal', minimum_down_time_hours=2.2),
             replace(base, uid='fixed', dispatch_mode='fixed'),
             replace(base, uid='renewable', dispatch_mode='curtailable'),
             replace(base, uid='disabled', dispatch_mode='disabled', enabled=False))
    row = replace(x.data.hourly_points[0],
                  generator_min_mw=dict(thermal=10., fixed=25., renewable=3., disabled=0.),
                  generator_max_mw=dict(thermal=100., fixed=25., renewable=50., disabled=0.))
    initial = h1.declared_normal_initial(units, row)
    assert initial == h1.declared_normal_initial(tuple(reversed(units)), row)
    assert initial.commitment == dict(disabled=False, fixed=True, renewable=True, thermal=False)
    assert initial.generation_mw == dict(disabled=0., fixed=25., renewable=3., thermal=0.)
    assert initial.time_in_state_hours == dict(disabled=0, fixed=0, renewable=0, thermal=3)
    assert tuple(initial.commitment) == tuple(sorted(initial.commitment))


@pytest.mark.parametrize('bad', [True, float('nan'), float('inf'), -1.])
def test_bad_current_bounds_rejected(bad):
    x = fixture(1)
    row = replace(x.data.hourly_points[0], generator_max_mw={'G1': bad})
    with pytest.raises(ValueError):
        h1.declared_normal_initial(x.data.generators, row)


def test_invalid_mode_inventory_and_fixed_bounds():
    x = fixture(1)
    g, row = x.data.generators[0], x.data.hourly_points[0]
    for units in ((g, g), (replace(g, enabled=False),), (replace(g, dispatch_mode='other'),)):
        with pytest.raises(ValueError):
            h1.declared_normal_initial(units, row)
    with pytest.raises(ValueError, match='unequal'):
        h1.declared_normal_initial((replace(g, dispatch_mode='fixed'),), row)
    with pytest.raises(ValueError, match='complete'):
        h1.declared_normal_initial((g,), replace(row, generator_min_mw={}))
    with pytest.raises(ValueError, match='disabled generator'):
        h1.declared_normal_initial((replace(g, dispatch_mode='disabled', enabled=False),), row)


def test_objective_chain_locks_and_original_constraints():
    x = fixture(1)
    assert h1.stage_order(x) == (('operating_cost', None), ('commitment', 'G1'), ('generation', 'G1'))
    assignment = assignment_for(x)
    for frozen, expected in (((), 20.), ((20.,), 1.), ((20., 1.), 20.)):
        m = model(h1.H1StageRequest(x, frozen))
        for v in m.component_data_objects(Var):
            v.set_value(assignment[v.name])
        assert value(m.objective) == expected
        assert len(m.h1_prior_objective_locks) == len(frozen)
        for lock in m.h1_prior_objective_locks.values():
            assert value(lock.body) == value(lock.lower) == value(lock.upper)
        assert len(m.initial_residual_dwell) == 1


def test_cost_lock_does_not_silently_become_a_band():
    x = fixture(1)
    m = model(h1.H1StageRequest(x, (20.000001,)))
    assignment = assignment_for(x)
    for v in m.component_data_objects(Var):
        v.set_value(assignment[v.name])
    lock = m.h1_prior_objective_locks[1]
    assert value(lock.lower) == value(lock.upper) == 20.000001
    assert abs(value(lock.body)-value(lock.lower)) > 1e-9


@pytest.mark.parametrize('frozen', [[20.], (20,), (True,), (-1.,), (float('nan'),),
                                    (-0.0,), (20., -0.0), (20., .5), (20., 1., 20.)])
def test_bad_stage_prefix(frozen):
    with pytest.raises(ValueError):
        h1.H1StageRequest(fixture(1), frozen)


def test_future_rows_and_old_types_rejected():
    x = fixture(2)
    with pytest.raises(ValueError, match='H1'):
        h1.H1StageRequest(x)
    one = fixture(1)
    with pytest.raises(ValueError, match='H1'):
        h1.H1StageRequest(replace(one, data=x.data))
    with pytest.raises(ValueError, match='exact H1'):
        h1.h1_stage_identity(one)


def test_stage_identity_binds_locks_and_detects_mutation():
    x = fixture(1)
    req = h1.H1StageRequest(x, (20.,))
    old = h1.h1_stage_identity(req)
    assert old != h1.h1_stage_identity(h1.H1StageRequest(x, (21.,)))
    changed = deepcopy(req)
    changed.inputs.initial.generation_mw['G1'] = 21.
    with pytest.raises(ValueError, match='inventory or values differ'):
        h1.build_h1_stage_model(changed, expected_identity=old)
    changed = replace(req, inputs=replace(x, initial=replace(x.initial, source_scope='other_declared_origin')))
    with pytest.raises(ValueError, match='identity mismatch'):
        h1.build_h1_stage_model(changed, expected_identity=old)


def test_new_initial_state_builds_h1_with_open_future_dwell():
    x = fixture(1, committed=False, age=3, minimum=2.2)
    initial = h1.declared_normal_initial(x.data.generators, x.data.hourly_points[0])
    x = replace(x, initial=initial, request=replace(x.request,
        initial_commitment=initial.commitment, initial_generation_mw=initial.generation_mw,
        initial_time_in_state_hours=initial.time_in_state_hours))
    m = model(h1.H1StageRequest(x))
    assert len(m.initial_residual_dwell) == 0
    assert tuple(m.TIME) == (0,)


def test_fresh_audit_recomputes_cost_and_all_locks_without_solver_claim():
    x = fixture(1)
    req = h1.H1StageRequest(x, (20., 1.))
    audit = h1.audit_h1_assignment(req, assignment_for(x), expected_identity=h1.h1_stage_identity(req))
    assert audit.errors == ()
    assert audit.canonical_objective == 20.
    assert audit.lock_residuals == (0., 0.)
    assert not hasattr(audit, 'optimality_certificate')
    assert audit.evidence_role == 'derived_h1_assignment_audit_no_native_optimality'
    with pytest.raises(TypeError, match='canonical reconstruction'):
        h1.H1AssignmentAudit(errors=())


def test_strict_lock_residual_rejects_legacy_tolerance_pass():
    x = fixture(1)
    req = h1.H1StageRequest(x, (20.00000001,))
    audit = h1.audit_h1_assignment(req, assignment_for(x), expected_identity=h1.h1_stage_identity(req))
    assert 'h1_normal_constraint_violation' in audit.errors
    assert 1e-9 < audit.lock_residuals[0] < 1e-6


@pytest.mark.parametrize('bad', [True, float('inf'), float('nan')])
def test_invalid_assignment_values(bad):
    x = fixture(1)
    req = h1.H1StageRequest(x)
    assignment = assignment_for(x)
    assignment[next(iter(assignment))] = bad
    with pytest.raises(ValueError, match='finite built-in'):
        h1.audit_h1_assignment(req, assignment, expected_identity=h1.h1_stage_identity(req))


def test_assignment_inventory_and_gate_drift(monkeypatch):
    req = h1.H1StageRequest(fixture(1))
    identity = h1.h1_stage_identity(req)
    with pytest.raises(ValueError, match='complete H1'):
        h1.audit_h1_assignment(req, {}, expected_identity=identity)
    monkeypatch.setattr(h1, 'RESIDUAL_LIMIT', 1e-6)
    with pytest.raises(ValueError, match='gate drift'):
        h1.audit_h1_assignment(req, {}, expected_identity=identity)


def test_hostile_identity_equality_cannot_bypass_binding():
    class Anything:
        def __eq__(self, other):
            return True
        def __ne__(self, other):
            return False
    with pytest.raises(ValueError, match='built-in lowercase'):
        h1.build_h1_stage_model(h1.H1StageRequest(fixture(1)), expected_identity=Anything())


def test_mixed_uid_order_is_independent_of_input_inventory_order():
    x = fixture(1)
    g = x.data.generators[0]
    units = (replace(g, uid='Z'), replace(g, uid='A', dispatch_mode='curtailable'),
             replace(g, uid='B'), replace(g, uid='D', dispatch_mode='disabled', enabled=False),
             replace(g, uid='F', dispatch_mode='fixed'))
    expected = (('operating_cost', None), ('commitment', 'B'), ('commitment', 'Z'),
                ('generation', 'A'), ('generation', 'B'), ('generation', 'D'), ('generation', 'F'), ('generation', 'Z'))
    row = replace(x.data.hourly_points[0],
                  generator_min_mw={'A': 0., 'B': 10., 'D': 0., 'F': 25., 'Z': 10.},
                  generator_max_mw={'A': 100., 'B': 100., 'D': 0., 'F': 25., 'Z': 100.})
    initial = h1.declared_normal_initial(units, row)
    request = replace(x.request, initial_commitment=initial.commitment,
                      initial_generation_mw=initial.generation_mw,
                      initial_time_in_state_hours=initial.time_in_state_hours,
                      generator_availability=({'A': True, 'B': True, 'D': False, 'F': True, 'Z': True},))
    carry = replace(x.carry,
                    limits=tuple(replace(x.carry.limits[0], uid=uid) for uid in ('B', 'Z')),
                    points=tuple(replace(x.carry.points[0], uid=uid, committed=False, generation_mw=0.)
                                 for uid in ('B', 'Z')), elapsed_state_hours=(3, 3))
    for sequence in (units, tuple(reversed(units))):
        current = replace(x, data=replace(x.data, generators=sequence, hourly_points=(row,)),
                          initial=initial, request=request, carry=carry)
        assert h1.stage_order(current) == expected
        assert tuple(model(h1.H1StageRequest(current)).TIME) == (0,)
