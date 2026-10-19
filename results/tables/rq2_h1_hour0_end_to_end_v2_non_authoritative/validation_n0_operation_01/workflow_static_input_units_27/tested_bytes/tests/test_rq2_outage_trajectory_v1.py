from dataclasses import fields, replace

import pytest
from pyomo.environ import Var, value

from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from src.grid.rts_gmlc_scuc import _constraint_violation
from src.rq2_joint_deliverability_boundary_v1.grid_carry import UnitPoint, UnitLimits
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import run_short_grid_candidate
from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import (
    ActualGridOrigin, OutageTrajectoryInputs, build_outage_trajectory_model, outage_trajectory_identity)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent


@pytest.fixture(scope='module')
def normal_base():
    base = fixture(3)
    g1 = replace(base.data.generators[0], p_min_mw=20., p_max_mw=80.,
        ramp_mw_per_hour=5., ramp_mw_per_minute=5./60., minimum_up_time_hours=5.,
        cost_breakpoints_mw=(20., 40., 60., 80.), cost_values_usd_per_hour=(20., 40., 60., 80.))
    g2 = replace(g1, uid='G2', ramp_mw_per_hour=40., ramp_mw_per_minute=40./60.)
    gens = (g1, g2)
    points = tuple(replace(p, demand_by_bus_mw={1: 40., 2: 0.},
        generator_min_mw={'G1': 20., 'G2': 20.}, generator_max_mw={'G1': 80., 'G2': 80.})
        for p in base.data.hourly_points)
    initial = replace(base.initial, commitment={'G1': True, 'G2': True},
        generation_mw={'G1': 20., 'G2': 20.}, time_in_state_hours={'G1': 1, 'G2': 1})
    normal = replace(base, data=replace(base.data, generators=gens, hourly_points=points), initial=initial,
        carry=replace(base.carry, limits=tuple(UnitLimits(g.uid, 20., 80., g.ramp_mw_per_hour, 5., 3.) for g in gens),
            points=tuple(UnitPoint(g.uid, True, 20.) for g in gens), elapsed_state_hours=(1, 1)),
        request=replace(base.request, system_demand_by_bus_mw=tuple(p.demand_by_bus_mw for p in points),
            generator_availability=tuple({'G1': True, 'G2': True} for p in points),
            initial_commitment=initial.commitment, initial_generation_mw=initial.generation_mw,
            initial_time_in_state_hours=initial.time_in_state_hours))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    return normal, candidate


def inputs(normal_base, *, event=True, cap=20., mode='weighted_total_curtailment'):
    normal, candidate = normal_base
    events = (N1OutageEvent(1, 'trip_then_repair', 'generator', 'G1', 1, 2),) if event else ()
    origin = ActualGridOrigin(normal.carry.identity, 0, (('G1', 20.), ('G2', 20.)),
                              (('G1', True), ('G2', True)), 'mechanism_assumption')
    return OutageTrajectoryInputs(normal, candidate, candidate.result_id, events, origin,
        'fixed_normal_commitment__outage_as_availability', 'committable_only_inherited_normal_scuc',
        'offline_full_event_path', 'generation_zero__downward_ramp_exempt_on_1_to_0_availability',
        (('trip_then_repair', 'G1', cap),) if event else (), 'mechanism_assumption', mode,
        (1., 1., 1.) if mode == 'weighted_total_curtailment' else (),
        (0., 0., 0.) if mode == 'fixed_curtailment_vector' else ())


@pytest.fixture(scope='module')
def flexible_base(normal_base):
    base, _ = normal_base
    g1, g2 = base.data.generators
    g2 = replace(g2, cost_values_usd_per_hour=(40., 80., 120., 160.))
    points = tuple(replace(p, demand_by_bus_mw={1: 50., 2: 0.}) for p in base.data.hourly_points)
    initial = replace(base.initial, generation_mw={'G1': 20., 'G2': 30.})
    normal = replace(base, data=replace(base.data, generators=(g1, g2), hourly_points=points),
        initial=initial, carry=replace(base.carry, points=(UnitPoint('G1', True, 20.), UnitPoint('G2', True, 30.))),
        request=replace(base.request, system_demand_by_bus_mw=tuple(p.demand_by_bus_mw for p in points),
                        initial_generation_mw=initial.generation_mw))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    contract = inputs((normal, candidate), cap=25.)
    return replace(contract, actual_origin=replace(contract.actual_origin, generation_mw=(('G1', 20.), ('G2', 30.))))


def build(contract):
    return build_outage_trajectory_model(contract, expected_identity=outage_trajectory_identity(contract))


def assign(model, trajectory):
    for variable in model.component_data_objects(Var):
        variable.set_value(0., skip_validation=True)
    for t, (g1, g2) in enumerate(trajectory):
        model.generation[t, 'G1'].set_value(g1)
        model.generation[t, 'G2'].set_value(g2)


def test_trip_exempts_only_failed_unit_and_repair_has_explicit_cap(normal_base):
    contract = inputs(normal_base)
    model = build(contract)
    assign(model, ((20., 20.), (0., 40.), (20., 20.)))
    assert _constraint_violation(model) == 0.
    assert value(model.generation[1, 'G1']) == 0
    assert model.generation[2, 'G1'].lb == 20.
    assert tuple(model.TIME) == (0, 1, 2)


def test_repair_cap_below_pmin_is_not_silently_relaxed(normal_base):
    model = build(inputs(normal_base, cap=19.))
    assign(model, ((20., 20.), (0., 40.), (20., 20.)))
    assert _constraint_violation(model) == 1.


def test_surviving_unit_first_boundary_uses_actual_not_normal_origin(normal_base):
    contract = inputs(normal_base, event=False)
    contract = replace(contract, actual_origin=replace(contract.actual_origin,
        generation_mw=(('G1', 20.), ('G2', 70.))))
    model = build(contract)
    assign(model, ((20., 20.),) * 3)
    assert _constraint_violation(model) == 10.


def test_no_outage_does_not_force_actual_equal_normal(flexible_base):
    model = build(flexible_base)
    assign(model, ((25., 25.), (0., 50.), (25., 25.)))
    assert _constraint_violation(model) == 0.
    assert model.curtailment[2].ub == 0.
    normal_values = dict(flexible_base.normal_candidate.normal.loaded_values)
    assert normal_values['generation[normal,2,G1]'] == pytest.approx(30.)
    assert value(model.generation[2, 'G1']) == 25.


def test_individually_valid_hours_fail_coupled_ramp(flexible_base):
    contract = replace(flexible_base, events=(N1OutageEvent(1, 'branch', 'branch', 'AC1', 0, 3),),
                       repair_return_limits_mw=())
    model = build(contract)
    assign(model, ((20., 30.), (30., 20.), (30., 20.)))
    assert _constraint_violation(model) == 5.
    model.actual_ramp.deactivate()
    assert _constraint_violation(model) == 0.


@pytest.mark.parametrize('mode', ['weighted_total_curtailment', 'fixed_curtailment_vector'])
def test_objective_mode_explicit_and_fixed_vector_is_equality(normal_base, mode):
    model = build(inputs(normal_base, mode=mode))
    assert all(model.curtailment[t].fixed == (mode == 'fixed_curtailment_vector') for t in model.TIME)


@pytest.mark.parametrize('field,bad', [('repair_return_limits_mw', ()),
    ('repair_return_limits_mw', (('trip_then_repair', 'G1', 81.),)),
    ('repair_return_limits_mw', (('trip_then_repair', 'G1', True),)),
    ('objective_mode', ''), ('curtailment_weights', (1., 0., 1.)),
    ('commitment_response_mode', 'adaptive_actual_commitment'),
    ('interhour_ramp_scope', 'all_generators'), ('information_mode', 'causal'),
    ('forced_trip_rule', 'ordinary_shutdown'), ('parameter_role', 'observed'),
    ('expected_normal_candidate_id', '0' * 64)])
def test_missing_or_drifted_contract_rejected(normal_base, field, bad):
    with pytest.raises(ValueError):
        replace(inputs(normal_base), **{field: bad})


def test_stationary_source_origin_event_does_not_invent_trip(normal_base):
    contract = inputs(normal_base)
    event = replace(contract.events[0], start_hour=0)
    with pytest.raises(ValueError, match='already-active'):
        replace(contract, events=(event,))
    origin = replace(contract.actual_origin, generation_mw=(('G1', 0.), ('G2', 40.)),
                     availability=(('G1', False), ('G2', True)))
    contract = replace(contract, events=(event,), actual_origin=origin)
    model = build(contract)
    assign(model, ((0., 40.), (0., 40.), (20., 20.)))
    assert _constraint_violation(model) == 0.


def test_bare_origin_cannot_claim_verified_prefix(normal_base):
    contract = inputs(normal_base)
    with pytest.raises(ValueError, match='mechanism actual origin'):
        replace(contract, actual_origin=replace(contract.actual_origin, evidence_role='derived_dispatch_witness'))


def test_input_identity_detects_objective_change(normal_base):
    contract = inputs(normal_base)
    identity = outage_trajectory_identity(contract)
    changed = replace(contract, curtailment_weights=(1., 2., 1.))
    with pytest.raises(ValueError, match='identity mismatch'):
        build_outage_trajectory_model(changed, expected_identity=identity)


@pytest.mark.parametrize('mode', ['fixed', 'curtailable'])
def test_noncommittable_repair_limit_without_invented_interhour_ramp(normal_base, mode):
    base, _ = normal_base
    g1, g2 = base.data.generators
    g1 = replace(g1, dispatch_mode=mode)
    points = tuple(replace(p, generator_min_mw={'G1': 20. if mode == 'fixed' else 0., 'G2': 20.},
        generator_max_mw={'G1': 20., 'G2': 80.}) for p in base.data.hourly_points)
    normal = replace(base, data=replace(base.data, generators=(g1, g2), hourly_points=points),
        carry=replace(base.carry, limits=(base.carry.limits[1],), points=(base.carry.points[1],),
                      elapsed_state_hours=(1,)))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    model = build(inputs((normal, candidate), cap=19.))
    returned = 20. if mode == 'fixed' else 19.
    assign(model, ((20., 20.), (0., 40.), (returned, 40. - returned)))
    assert _constraint_violation(model) == (1. if mode == 'fixed' else 0.)


def test_malformed_origin_and_normal_carry_not_accepted(normal_base):
    contract = inputs(normal_base)
    for origin in (contract.normal_inputs.carry,
                   replace(contract.actual_origin, availability=(('G1', 1), ('G2', True))),
                   replace(contract.actual_origin, generation_mw=(('G1', 20.),)),
                   replace(contract.actual_origin, source_hour=1),
                   replace(contract.actual_origin, identity=replace(contract.actual_origin.identity, split='holdout'))):
        with pytest.raises(ValueError):
            replace(contract, actual_origin=origin)


def test_original_event_table_and_return_identity_rejected_on_drift(normal_base):
    contract = inputs(normal_base)
    for events in ((replace(contract.events[0], seed=2),), (contract.events[0], contract.events[0]),
                   (replace(contract.events[0], uid='unknown'),),
                   (replace(contract.events[0], start_hour=1.),),
                   (replace(contract.events[0], end_hour_exclusive=4),)):
        with pytest.raises(ValueError):
            replace(contract, events=events)


def test_repair_at_chunk_boundary_retains_original_event_and_actual_origin(normal_base):
    base, _ = normal_base
    initial = replace(base.initial, time_in_state_hours={'G1': 3, 'G2': 3})
    request = replace(base.request, **{f.name: getattr(base.request, f.name)[2:]
        for f in fields(base.request)
        if type(getattr(base.request, f.name)) is tuple and len(getattr(base.request, f.name)) == 3},
        initial_time_in_state_hours=initial.time_in_state_hours)
    normal = replace(base, initial=initial, request=request, source_hours=(3,),
        carry=replace(base.carry, source_hour=2, elapsed_state_hours=(3, 3)))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    origin = ActualGridOrigin(normal.carry.identity, 2, (('G1', 0.), ('G2', 40.)),
        (('G1', False), ('G2', True)), 'mechanism_assumption')
    contract = replace(inputs(normal_base), normal_inputs=normal, normal_candidate=candidate,
        expected_normal_candidate_id=candidate.result_id, actual_origin=origin, curtailment_weights=(1.,))
    model = build(contract)
    assign(model, ((20., 20.),))
    assert _constraint_violation(model) == 0.
    restricted = replace(contract, repair_return_limits_mw=(('trip_then_repair', 'G1', 19.),))
    model = build(restricted)
    assign(model, ((20., 20.),))
    assert _constraint_violation(model) == 1.
    with pytest.raises(ValueError, match='preceding source event'):
        replace(contract, actual_origin=replace(origin, availability=(('G1', True), ('G2', True))))


def test_outage_identity_covers_fresh_import_dependencies():
    import json
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.outage_trajectory
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/outage_trajectory.py'}
    assert set(json.loads(result.stdout)) == expected
