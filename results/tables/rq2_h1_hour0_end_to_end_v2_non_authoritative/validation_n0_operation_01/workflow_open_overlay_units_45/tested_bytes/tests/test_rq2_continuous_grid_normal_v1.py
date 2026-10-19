from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pyomo.environ import SolverFactory, Var, value

from src.evaluation import ChronologicalFlexibilityEnvelope
from src.grid.chronological_dispatch import ChronologicalDispatchRequest
from src.grid.rts_gmlc import (RtsGmlcBus, RtsGmlcBranch, RtsGmlcDcBranch,
    RtsGmlcChronologicalGenerator, RtsGmlcChronologicalData, RtsGmlcHourlyPoint)
from src.grid.rts_gmlc_scuc import RtsGmlcInitialState, _validate_inputs
from src.rq2_joint_deliverability_boundary_v1.grid_carry import (
    GridCarry, GridIdentity, GridHour, UnitLimits, UnitPoint, replay_grid_chunk)
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import (
    ContinuousNormalInputs, NormalAssignmentWitness, SOURCE_DEPENDENCIES,
    normal_input_identity, build_continuous_normal_model, audit_normal_assignment)


def fixture(horizon=3, *, committed=True, age=1, minimum=3., demand=20.):
    generator = RtsGmlcChronologicalGenerator(
        uid='G1', bus=1, unit_type='CC', category='Gas CC', fuel='Gas',
        dispatch_mode='committable', enabled=True, disabled_reason=None,
        p_min_mw=10., p_max_mw=100., minimum_down_time_hours=minimum,
        minimum_up_time_hours=minimum, ramp_mw_per_minute=1., ramp_mw_per_hour=60.,
        start_time_cold_hours=0., start_time_warm_hours=0., start_time_hot_hours=0.,
        start_heat_cold_mmbtu=0., start_heat_warm_mmbtu=0., start_heat_hot_mmbtu=0.,
        non_fuel_start_cost_usd=0., shutdown_cost_usd=0., fuel_price_usd_per_mmbtu=1.,
        variable_om_usd_per_mwh=0., cold_start_cost_usd=0., warm_start_cost_usd=0.,
        hot_start_cost_usd=0., cost_breakpoints_mw=(10., 40., 70., 100.),
        cost_values_usd_per_hour=(10., 40., 70., 100.))
    points = tuple(RtsGmlcHourlyPoint(datetime(2020, 1, 1) + timedelta(hours=t),
        {1: demand, 2: 0.}, {'G1': 10.}, {'G1': 100.}, {1: 0.}) for t in range(horizon))
    data = RtsGmlcChronologicalData(100., 1,
        (RtsGmlcBus(1, 'a', 230., 'REF', 1, demand), RtsGmlcBus(2, 'b', 230., 'PQ', 1, 0.)),
        (RtsGmlcBranch('AC1', 1, 2, 0., .1, 0., 100., 100., 100., 1.),),
        (RtsGmlcDcBranch('DC1', 1, 2, 'fixed', 0., -100., 100.),), (generator,), points)
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1., maximum_event_duration_hours=1., minimum_recovery_hours=1.,
        maximum_events_by_period={'p': 0}, maximum_curtailment_energy_mwh_by_period={'p': 0.},
        maximum_recovery_debt_mwh=0., maximum_recovery_power_mw=0., minimum_event_power_mw=1.,
        response_time_hours=1., curtailment_ramp_mw_per_hour=1., recovery_efficiency=1.,
        terminal_debt_limit_mwh_by_period={'p': 0.}, parameter_status='synthetic_normal')
    zeros = (0.,) * horizon
    initial = RtsGmlcInitialState({'G1': committed}, {'G1': 20. if committed else 0.},
                                {'G1': age}, 'synthetic_mechanism_initial')
    request = ChronologicalDispatchRequest(
        timestamps=tuple(p.timestamp.replace(tzinfo=timezone.utc) for p in points),
        periods=('p',) * horizon, time_step_hours=1.,
        system_demand_by_bus_mw=tuple(dict(p.demand_by_bus_mw) for p in points),
        generator_availability=tuple({'G1': True} for _ in points), dc_bus=1,
        dc_requested_mw=zeros, dc_flexible_demand_mw=zeros, dc_recoverable_flexible_mw=zeros,
        dc_physical_maximum_mw=zeros, dc_connected_capacity_mw=zeros, dc_call_limit_mw=zeros,
        recovery_headroom_mw=zeros, flexibility_envelope=envelope,
        flexibility_boundary_state_status='clean_boundary_with_zero_carry_in', completed_periods=frozenset(),
        initial_has_prior_event=False, initial_recovery_debt_mwh=0., initial_grid_call_mw=0.,
        initial_active_event_duration_hours=0., initial_interevent_rest_hours=None,
        initial_event_count_by_period={}, initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=False, incidents=(), initial_commitment=initial.commitment,
        initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours)
    carry = GridCarry(GridIdentity('training', 'synthetic', 1, '1' * 64), 0,
        (UnitLimits('G1', 10., 100., 60., minimum, minimum),),
        (UnitPoint('G1', committed, initial.generation_mw['G1']),), (age,), 'mechanism_assumption')
    return ContinuousNormalInputs(data, request, initial, carry, tuple(range(1, horizon + 1)),
                                  'naive_source_labelled_utc')


def model_for(inputs):
    return build_continuous_normal_model(inputs, expected_identity=normal_input_identity(inputs))


def assignment_for(inputs, states=None):
    model = model_for(inputs)
    for v in model.component_data_objects(Var):
        v.set_value(0., skip_validation=True)
    prior = inputs.initial.commitment['G1']
    for t in model.TIME:
        on = True if states is None else states[t]
        power = inputs.request.system_demand_by_bus_mw[t][1]
        model.commitment[t, 'G1'].set_value(int(on))
        model.startup[t, 'G1'].set_value(int(on and not prior))
        model.shutdown[t, 'G1'].set_value(int(prior and not on))
        model.generation['normal', t, 'G1'].set_value(power)
        remaining = power - 10. * on
        for segment in range(3):
            part = min(30., remaining)
            model.segment_power[t, 'G1', segment].set_value(part)
            remaining -= part
        prior = on
    return {v.name: v.value for v in model.component_data_objects(Var)}


@pytest.mark.parametrize('horizon', [1, 24, 25, 49])
def test_continuous_horizon_and_old_limit(horizon):
    inputs = fixture(horizon)
    assert tuple(model_for(inputs).TIME) == tuple(range(horizon))
    if horizon <= 24:
        assert len(_validate_inputs(inputs.data, inputs.request, 1e-6)) == horizon
    else:
        with pytest.raises(ValueError, match='1 to 24'):
            _validate_inputs(inputs.data, inputs.request, 1e-6)


@pytest.mark.parametrize('committed', [False, True])
@pytest.mark.parametrize('minimum,age,remaining', [(3., 0, 3), (3., 1, 2), (3., 3, 0),
    (2.2, 1, 2), (2.2, 2, 1), (2.2, 3, 0)])
def test_residual_dwell_ceil_and_both_states(committed, minimum, age, remaining):
    inputs = fixture(committed=committed, minimum=minimum, age=age)
    model = model_for(inputs)
    assert len(model.initial_residual_dwell) == remaining
    for constraint in model.initial_residual_dwell.values():
        assert value(constraint.lower) == int(committed)


@pytest.mark.parametrize('age', [True, 1., 1.5, -1])
def test_initial_age_rejected(age):
    with pytest.raises(ValueError):
        fixture(age=age)


def test_analytic_normal_assignment_and_open_terminal():
    inputs = fixture(25)
    audit = audit_normal_assignment(inputs, assignment_for(inputs), expected_identity=normal_input_identity(inputs))
    assert audit.errors == ()
    assert audit.maximum_constraint_violation == 0
    assert audit.terminal_carry.source_hour == 25
    assert audit.terminal_carry.elapsed_state_hours == (26,)


@pytest.mark.parametrize('variable,amount', [('generation[normal,1,G1]', 21.),
    ('branch_flow[normal,1,AC1]', 101.), ('commitment[1,G1]', .5), ('reserve_up[1,G1]', 81.)])
def test_canonical_constraints_reject_tampered_assignment(variable, amount):
    inputs = fixture()
    assignment = assignment_for(inputs)
    assignment[variable] = amount
    audit = audit_normal_assignment(inputs, assignment, expected_identity=normal_input_identity(inputs))
    assert audit.errors and audit.terminal_carry is None


def test_missing_variable_is_not_a_partial_witness():
    inputs = fixture()
    assignment = assignment_for(inputs)
    assignment.pop('reserve_up[0,G1]')
    with pytest.raises(ValueError, match='complete canonical'):
        audit_normal_assignment(inputs, assignment, expected_identity=normal_input_identity(inputs))


def test_post_identity_mutation_detected():
    inputs = fixture()
    identity = normal_input_identity(inputs)
    inputs.initial.generation_mw['G1'] = 21.
    with pytest.raises(ValueError):
        build_continuous_normal_model(inputs, expected_identity=identity)


@pytest.mark.parametrize('kind', ['source_gap', 'clock', 'demand', 'availability', 'reserve', 'carry_limits', 'initial'])
def test_input_drift_rejected(kind):
    inputs = fixture()
    with pytest.raises(ValueError):
        if kind == 'source_gap':
            replace(inputs, source_hours=(1, 3, 4))
        elif kind == 'clock':
            replace(inputs, source_time_basis='aware_source')
        elif kind == 'demand':
            inputs.request.system_demand_by_bus_mw[0][1] = 21.
        elif kind == 'availability':
            inputs.request.generator_availability[0]['G1'] = False
        elif kind == 'reserve':
            inputs.data.hourly_points[0].spin_up_requirement_by_area_mw.clear()
        elif kind == 'carry_limits':
            replace(inputs, carry=replace(inputs.carry, limits=(replace(inputs.carry.limits[0], ramp_mw_per_hour=61.),)))
        else:
            replace(inputs, initial=replace(inputs.initial, generation_mw={'G1': 21.}))
        normal_input_identity(inputs)


def test_final_hour_start_preserves_next_chunk_dwell():
    inputs = fixture(1, committed=False, age=3)
    audit = audit_normal_assignment(inputs, assignment_for(inputs), expected_identity=normal_input_identity(inputs))
    assert audit.errors == ()
    assert audit.terminal_carry.elapsed_state_hours == (1,)
    # Retain the absolute source index and original data clock for the successor.
    base = fixture(2)
    request = replace(inputs.request, timestamps=(base.request.timestamps[1],),
        initial_commitment={'G1': True}, initial_generation_mw={'G1': 20.},
        initial_time_in_state_hours={'G1': 1})
    successor = ContinuousNormalInputs(base.data, request,
        RtsGmlcInitialState({'G1': True}, {'G1': 20.}, {'G1': 1}, 'derived_dispatch_witness'),
        audit.terminal_carry, (2,), inputs.source_time_basis)
    assert len(model_for(successor).initial_residual_dwell) == 1


def test_tiny_real_normal_solve():
    inputs = fixture(2)
    model = model_for(inputs)
    solver = SolverFactory('highs')
    solver.options.update({'time_limit': 1., 'threads': 1})
    result = solver.solve(model)
    assert str(result.solver.termination_condition) == 'optimal'
    assignment = {v.name: v.value for v in model.component_data_objects(Var)}
    audit = audit_normal_assignment(inputs, assignment, expected_identity=normal_input_identity(inputs))
    assert audit.errors == ()
    assert audit.terminal_carry.elapsed_state_hours == (3,)


@pytest.mark.parametrize('initial_on', [False, True])
@pytest.mark.parametrize('age', [0, 1, 2, 3])
@pytest.mark.parametrize('minimum', [2., 2.2])
def test_all_short_binary_trajectories_match_independent_carry(initial_on, age, minimum):
    for states in product((False, True), repeat=3):
        inputs = fixture(3, committed=initial_on, age=age, minimum=minimum)
        for t, on in enumerate(states):
            inputs.data.hourly_points[t].demand_by_bus_mw[1] = 20. * on
            inputs.request.system_demand_by_bus_mw[t][1] = 20. * on
        hours = tuple(GridHour(inputs.carry.identity, t + 1, (UnitPoint('G1', on, 20. * on),))
                      for t, on in enumerate(states))
        try:
            expected = replay_grid_chunk(inputs.carry, hours)
        except ValueError:
            expected = None
        audit = audit_normal_assignment(inputs, assignment_for(inputs, states),
                                         expected_identity=normal_input_identity(inputs))
        assert audit.terminal_carry == expected
        assert bool(audit.errors) == (expected is None)


@pytest.mark.parametrize('committed,demand,valid', [(True, 80., True), (True, 81., False),
    (False, 90., True), (True, 0., True)])
def test_first_hour_ramp_and_start_stop_allowance(committed, demand, valid):
    inputs = fixture(1, committed=committed, age=3, demand=demand)
    audit = audit_normal_assignment(inputs, assignment_for(inputs, (demand > 0,)),
                                     expected_identity=normal_input_identity(inputs))
    assert (audit.terminal_carry is not None) == valid


def test_positive_reserve_requirement_is_not_ignored():
    inputs = fixture(1)
    inputs.data.hourly_points[0].spin_up_requirement_by_area_mw[1] = 5.
    assignment = assignment_for(inputs)
    identity = normal_input_identity(inputs)
    assert audit_normal_assignment(inputs, assignment, expected_identity=identity).errors
    assignment['reserve_up[0,G1]'] = 5.
    assert audit_normal_assignment(inputs, assignment, expected_identity=identity).errors == ()


def test_source_and_request_joint_mutation_cannot_reuse_identity():
    inputs = fixture()
    identity = normal_input_identity(inputs)
    inputs.request.system_demand_by_bus_mw[0][1] = 21.
    inputs.data.hourly_points[0].demand_by_bus_mw[1] = 21.
    with pytest.raises(ValueError, match='identity mismatch'):
        build_continuous_normal_model(inputs, expected_identity=identity)


def test_reference_angle_fixing_cannot_be_overwritten_by_assignment():
    inputs = fixture(1)
    assignment = assignment_for(inputs)
    assignment['angle_degrees[normal,0,1]'] = 1.
    assignment['angle_degrees[normal,0,2]'] = 1.
    audit = audit_normal_assignment(inputs, assignment, expected_identity=normal_input_identity(inputs))
    assert any('fixed_variable_violation' in error for error in audit.errors)
    assert audit.terminal_carry is None


@pytest.mark.parametrize('mode', ['fixed', 'curtailable', 'disabled'])
def test_noncommittable_generation_remains_in_normal_balance(mode):
    base = fixture(1)
    enabled = mode != 'disabled'
    maximum = 5. if enabled else 0.
    minimum = 5. if mode == 'fixed' else 0.
    generator = replace(base.data.generators[0], uid='G2', dispatch_mode=mode,
        enabled=enabled, p_min_mw=minimum, p_max_mw=maximum, category='Solar PV')
    point = replace(base.data.hourly_points[0], generator_min_mw={'G1': 10., 'G2': minimum},
                    generator_max_mw={'G1': 100., 'G2': maximum})
    initial = RtsGmlcInitialState({'G1': True, 'G2': enabled}, {'G1': 20., 'G2': maximum},
                                {'G1': 1, 'G2': 0}, 'synthetic_mechanism_initial')
    inputs = replace(base, data=replace(base.data, generators=(*base.data.generators, generator),
        hourly_points=(point,)), initial=initial, request=replace(base.request,
        generator_availability=({'G1': True, 'G2': enabled},), initial_commitment=initial.commitment,
        initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours))
    assignment = assignment_for(inputs)
    assignment['generation[normal,0,G2]'] = maximum
    assignment['generation[normal,0,G1]'] = 20. - maximum
    assignment['segment_power[0,G1,0]'] = 10. - maximum
    identity = normal_input_identity(inputs)
    assert audit_normal_assignment(inputs, assignment, expected_identity=identity).errors == ()
    assignment['generation[normal,0,G2]'] = maximum + 1.
    assert audit_normal_assignment(inputs, assignment, expected_identity=identity).terminal_carry is None


def test_failed_witness_cannot_be_relabelled_or_publicly_constructed():
    inputs = fixture(1)
    assignment = assignment_for(inputs)
    assignment['commitment[0,G1]'] = .5
    audit = audit_normal_assignment(inputs, assignment, expected_identity=normal_input_identity(inputs))
    assert audit.errors and audit.terminal_carry is None
    with pytest.raises(TypeError, match='only by canonical'):
        replace(audit, errors=(), maximum_constraint_violation=0., maximum_integrality_violation=0.,
                terminal_carry=inputs.carry)
    with pytest.raises(TypeError, match='only by canonical'):
        NormalAssignmentWitness()


@pytest.mark.parametrize('field,bad', [('initial_interevent_rest_hours', 99.),
    ('flexibility_boundary_state_status', 'nonsense'), ('completed_periods', frozenset({'unknown'})),
    ('completed_periods', {'p'}), ('require_terminal_event_inactive', 1),
    ('initial_has_prior_event', 0), ('initial_event_count_by_period', {'p': 0})])
def test_business_boundary_semantics_reused(field, bad):
    inputs = fixture(1)
    with pytest.raises((TypeError, ValueError)):
        replace(inputs, request=replace(inputs.request, **{field: bad}))


def test_envelope_period_inventory_is_validated():
    inputs = fixture(1)
    envelope = replace(inputs.request.flexibility_envelope, maximum_events_by_period={'unknown': 0})
    with pytest.raises(ValueError, match='keys must match'):
        replace(inputs, request=replace(inputs.request, flexibility_envelope=envelope))


def test_runtime_version_drift_changes_expected_identity(monkeypatch):
    import src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal as normal
    inputs = fixture(1)
    identity = normal_input_identity(inputs)
    original = normal.version
    monkeypatch.setattr(normal, 'version', lambda name: 'changed' if name == 'Pyomo' else original(name))
    with pytest.raises(ValueError, match='identity mismatch'):
        build_continuous_normal_model(inputs, expected_identity=identity)


def test_source_manifest_covers_fresh_import_closure():
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
                            text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    assert set(json.loads(result.stdout)) == set(SOURCE_DEPENDENCIES)


def test_identity_equality_override_cannot_bypass_binding():
    class EqualAnything:
        def __eq__(self, other):
            return True

        def __ne__(self, other):
            return False

    inputs = fixture(1)
    assignment = assignment_for(inputs)
    for fake in (EqualAnything(), '', 'A' * 64, 'g' * 64, 123):
        with pytest.raises(ValueError, match='built-in lowercase SHA256'):
            build_continuous_normal_model(inputs, expected_identity=fake)
        with pytest.raises(ValueError, match='built-in lowercase SHA256'):
            audit_normal_assignment(inputs, assignment, expected_identity=fake)


@pytest.mark.parametrize('bad', [1, True, '', '   '])
@pytest.mark.parametrize('field', ['source_scope', 'parameter_status'])
def test_evidence_role_requires_nonempty_builtin_string(field, bad):
    inputs = fixture(1)
    with pytest.raises(ValueError):
        if field == 'source_scope':
            replace(inputs, initial=replace(inputs.initial, source_scope=bad))
        else:
            replace(inputs, request=replace(inputs.request, flexibility_envelope=replace(
                inputs.request.flexibility_envelope, parameter_status=bad)))
