from dataclasses import replace
from fractions import Fraction as Q

import pytest
from pyomo.environ import Var, value

from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_continuous_grid_candidate_v1 import SPEC, BUDGET
from test_rq2_continuous_capacity_policy_v1 import init, current
from src.rq2_joint_deliverability_boundary_v1.capacity_policy import initialize_capacity_policy, advance_capacity_policy
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1.grid_carry import UnitPoint
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import run_short_grid_candidate
from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import ActualGridOrigin, OutageTrajectoryInputs
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import export_prefix_handoff, prefix_digest
from src.rq2_joint_deliverability_boundary_v1 import business_grid as bridge


def network(ramp=60., maximum=40., backup=False):
    base = fixture(3)
    g = replace(base.data.generators[0], ramp_mw_per_hour=ramp, ramp_mw_per_minute=ramp/60.)
    initial = replace(base.initial, generation_mw={'G1': 40.})
    normal = replace(base, data=replace(base.data, generators=(g,)), initial=initial,
        carry=replace(base.carry, points=(UnitPoint('G1', True, 40.),),
            limits=(replace(base.carry.limits[0], ramp_mw_per_hour=ramp),)),
        request=replace(base.request, dc_requested_mw=(20.,)*3, dc_physical_maximum_mw=(maximum,)*3,
            dc_connected_capacity_mw=(maximum,)*3, initial_generation_mw=initial.generation_mw))
    if backup:
        g = replace(g, minimum_up_time_hours=5.)
        g2 = replace(g, uid='G2', cost_values_usd_per_hour=tuple(2*x for x in g.cost_values_usd_per_hour))
        points = tuple(replace(p, generator_min_mw={'G1': 10., 'G2': 10.},
            generator_max_mw={'G1': 100., 'G2': 100.}) for p in normal.data.hourly_points)
        initial = replace(initial, commitment={'G1': True, 'G2': True},
            generation_mw={'G1': 30., 'G2': 10.}, time_in_state_hours={'G1': 1, 'G2': 1})
        normal = replace(normal, data=replace(normal.data, generators=(g, g2), hourly_points=points), initial=initial,
            carry=replace(normal.carry, points=(UnitPoint('G1', True, 30.), UnitPoint('G2', True, 10.)),
                limits=(replace(normal.carry.limits[0], minimum_up_hours=5.),
                    replace(normal.carry.limits[0], uid='G2', minimum_up_hours=5.)), elapsed_state_hours=(1, 1)),
            request=replace(normal.request, initial_commitment=initial.commitment, initial_generation_mw=initial.generation_mw,
                initial_time_in_state_hours=initial.time_in_state_hours, generator_availability=({'G1': True, 'G2': True},)*3))
    candidate = run_short_grid_candidate(normal, expected_identity=normal_input_identity(normal), events=(),
        event_evidence_role='mechanism_assumption', solver_specification=SPEC, budget=BUDGET)
    assert candidate.normal.optimal, candidate.normal.errors
    origin = ActualGridOrigin(normal.carry.identity, 0, tuple(sorted(initial.generation_mw.items())),
        tuple(sorted(initial.commitment.items())), 'mechanism_assumption')
    return OutageTrajectoryInputs(normal, candidate, candidate.result_id, (), origin,
        'fixed_normal_commitment__outage_as_availability', 'committable_only_inherited_normal_scuc',
        'offline_full_event_path', 'generation_zero__downward_ramp_exempt_on_1_to_0_availability',
        (), 'mechanism_assumption', 'weighted_total_curtailment', (1.,)*3, ())


@pytest.fixture(scope='module')
def grid():
    return network()


def business(arm=JOINT, g=0., c=.125, **source):
    original = init(arm)
    track = original.initial.tracks[0][1]
    metadata = dict(split='training', power_outage_seed=1)
    metadata.update(source)
    anchor = replace(track.physical.anchor, **metadata)
    cursor = initialize_capacity_policy(original.spec, anchor=anchor, envelope=dict(track.physical.envelope),
        accounting_period_id=track.ledger.accounting_period_id, zero_carry_in_assumption=True)
    for t in (1, 2, 3):
        observation = current(t, g=g if t == 1 else 0., c=c if t == 1 else 0.)
        observation = replace(observation, observation=replace(observation.observation,
            hour=replace(observation.observation.hour, **dict(metadata, power_source_hour=anchor.power_source_hour+t)),
            due_hour=None if observation.observation.due_hour is None else observation.observation.due_hour+anchor.power_source_hour))
        cursor = advance_capacity_policy(cursor, observation)
        if cursor.stopped:
            break
    return cursor


def contract(grid, cursor=None):
    cursor = business() if cursor is None else cursor
    return bridge.BusinessGridInputs(grid, cursor, prefix_digest(export_prefix_handoff(cursor)), '20',
        'linear_workload_power_no_idle_offset_v1', 'declared_power_source_and_workload_pairing_mechanism_v1',
        'mechanism_assumption')


def assigned(inputs):
    model = bridge.build_business_grid_model(inputs, expected_identity=bridge.business_grid_identity(inputs))
    for variable in model.component_data_objects(Var):
        variable.set_value(0., skip_validation=True)
    for t in model.TIME:
        model.generation[t, 'G1'].set_value(20. + value(model.actual_dc_power[t]))
    return model, {v.name: v.value for v in model.component_data_objects(Var)}


def audit(inputs, values):
    return bridge.audit_business_grid_assignment(inputs, values, expected_identity=bridge.business_grid_identity(inputs))


def test_no_outage_cfe_reduction_and_recovery_above_baseline(grid):
    inputs = contract(grid)
    model, values = assigned(inputs)
    assert not hasattr(model, 'curtailment')
    assert tuple(value(model.actual_dc_power[t]) for t in model.TIME) == (17.5, 23.125, 20.)
    result = audit(inputs, values)
    assert result.physical_network_assignment_valid
    assert result.effective_applicable_requests_fully_served
    assert dict(result.mapped_hours[1].exact_mw)['recovery'] == ('25', '8')
    assert dict(result.mapped_hours[1].projected_hex)['actual_power'] == (23.125).hex()
    assert result.full_service_completion is result.causal_grid_dispatch_certificate is None
    assert result.formal_result is result.security_certified is False
    assert inputs.business_prefix.execution.tracks[0][1].ledger.debt == 0


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_four_arms_preserve_obligation_applicability(grid, arm):
    inputs = contract(grid, business(arm, g=.0625, c=.0625))
    result = audit(inputs, assigned(inputs)[1])
    assert result.physical_network_assignment_valid
    assert result.grid_service_applicable == (arm != CFE)
    assert result.cfe_service_applicable == (arm != NETWORK)
    assert result.grid_obligation_certificate is None
    row = dict(result.mapped_hours[0].projected_mw)
    assert row['original_grid_request'] == 1.25
    if arm == CFE:
        assert row['grid_served'] == 0 and row['grid_shortfall'] is None
    if arm == NETWORK:
        assert row['cfe_served'] == 0 and row['cfe_shortfall'] is None


@pytest.mark.parametrize('arm', [JOINT, B6])
def test_committed_cfe_shortfall_is_not_full_request_fulfillment(grid, arm):
    inputs = contract(grid, business(arm, c=.5))
    result = audit(inputs, assigned(inputs)[1])
    assert result.physical_network_assignment_valid
    assert not result.effective_applicable_requests_fully_served
    assert dict(result.mapped_hours[0].projected_mw)['cfe_shortfall'] == 7.5
    assert result.full_service_completion is None


def test_business_valid_trajectory_can_violate_network_crosshour_ramp():
    inputs = contract(network(ramp=4.))
    model, values = assigned(inputs)
    result = audit(inputs, values)
    assert not result.physical_network_assignment_valid
    assert result.maximum_constraint_violation == 1.625
    from src.grid.rts_gmlc_scuc import _constraint_violation
    model.actual_ramp.deactivate()
    assert _constraint_violation(model) == 0.
    assert not inputs.business_prefix.stopped


def test_recovery_over_connected_or_physical_power_is_rejected():
    with pytest.raises(ValueError, match='physical or connected'):
        contract(network(maximum=20.))


@pytest.mark.parametrize('scale', [20., True, '20.0', '0', '-1', '2e1', '21', '20.000000000000001'])
def test_scale_requires_explicit_exact_mapping(grid, scale):
    with pytest.raises(ValueError):
        replace(contract(grid), normalized_unit_mw=scale)


def test_positive_underflow_is_rejected(grid):
    with pytest.raises(ValueError, match='underflowed'):
        replace(contract(grid), normalized_unit_mw='0.' + '0'*400 + '1')


def test_stopped_business_cannot_create_network_history(grid):
    cursor = business(g=.5)
    assert cursor.stopped
    with pytest.raises(ValueError, match='fully committed'):
        bridge.BusinessGridInputs(grid, cursor, '0'*64, '20',
            'linear_workload_power_no_idle_offset_v1', 'declared_power_source_and_workload_pairing_mechanism_v1',
            'mechanism_assumption')


def test_short_prefix_and_changed_hash_are_rejected(grid):
    inputs = contract(grid)
    short = replace(inputs.business_prefix, records=inputs.business_prefix.records[:2])
    with pytest.raises(ValueError, match='horizon alignment'):
        replace(inputs, business_prefix=short, expected_business_prefix_sha256=prefix_digest(export_prefix_handoff(short)))
    with pytest.raises(ValueError, match='prefix identity'):
        replace(inputs, expected_business_prefix_sha256='0'*64)


@pytest.mark.parametrize('kind', ['missing', 'extra', 'nan', 'fixed', 'balance'])
def test_fresh_assignment_audit_catches_tampering(grid, kind):
    inputs = contract(grid)
    _, values = assigned(inputs)
    if kind == 'missing':
        values.pop('generation[0,G1]')
    elif kind == 'extra':
        values['curtailment[0]'] = 0.
    elif kind == 'nan':
        values['generation[0,G1]'] = float('nan')
    elif kind == 'fixed':
        values['angle_degrees[0,1]'] = values['angle_degrees[0,2]'] = 1.
    else:
        values['generation[1,G1]'] = 40.
    if kind in ('missing', 'extra', 'nan'):
        with pytest.raises(ValueError):
            audit(inputs, values)
    else:
        assert not audit(inputs, values).physical_network_assignment_valid


def test_witness_is_owned_and_identity_cannot_be_reused(grid, monkeypatch):
    inputs = contract(grid)
    witness = audit(inputs, assigned(inputs)[1])
    identity = witness.result_id
    with pytest.raises(TypeError):
        replace(witness, errors=())
    with pytest.raises(TypeError):
        bridge.BusinessGridWitness()
    monkeypatch.setattr(bridge, 'CONTRACT', 'changed')
    assert witness.result_id == identity
    with pytest.raises(ValueError, match='contract drift'):
        bridge.business_grid_identity(inputs)


@pytest.mark.parametrize('source', [{'split': 'holdout'}, {'power_outage_seed': 2}, {'power_source_hour': 10}])
def test_split_or_seed_pairing_mismatch_rejected(grid, source):
    with pytest.raises(ValueError, match='split, seed'):
        contract(grid, business(**source))


def test_both_source_hash_namespaces_are_bound_without_overwriting(grid):
    old = contract(grid)
    assert old.business_prefix.initial.tracks[0][1].physical.anchor.power_provenance_sha256 != grid.normal_inputs.carry.identity.source_sha256
    changed = contract(grid, business(power_provenance_sha256='9'*64))
    assert bridge.business_grid_identity(changed) != bridge.business_grid_identity(old)
    with pytest.raises(ValueError, match='identity mismatch'):
        bridge.build_business_grid_model(changed, expected_identity=bridge.business_grid_identity(old))


def test_recovery_during_generator_outage_cannot_inherit_business_validity(grid):
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    event = N1OutageEvent(1, 'recovery_outage', 'generator', 'G1', 1, 2)
    grid = replace(grid, events=(event,), repair_return_limits_mw=(('recovery_outage', 'G1', 100.),))
    inputs = contract(grid)
    before = inputs.expected_business_prefix_sha256
    result = audit(inputs, assigned(inputs)[1])
    assert not result.physical_network_assignment_valid
    assert result.maximum_bound_violation == 43.125
    assert prefix_digest(export_prefix_handoff(inputs.business_prefix)) == before


def test_zero_action_matches_original_zero_curtailment_network(grid):
    from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import outage_trajectory_identity
    from src.rq2_joint_deliverability_boundary_v1.outage_assignment import audit_outage_assignment
    inputs = contract(grid, business(c=0.))
    _, values = assigned(inputs)
    assert audit(inputs, values).physical_network_assignment_valid
    old = replace(grid, objective_mode='fixed_curtailment_vector', curtailment_weights=(), fixed_curtailment_mw=(0.,)*3)
    old_values = dict(values, **{f'curtailment[{t}]': 0. for t in range(3)})
    assert not audit_outage_assignment(old, old_values, expected_identity=outage_trajectory_identity(old)).errors


def test_exact_power_balance_retains_load_with_large_cancelling_flows(grid):
    inputs = contract(grid)
    _, values = assigned(inputs)
    # Independently retain the original demand when two huge flows cancel.
    values['branch_flow[0,AC1]'] = 1e20
    values['dc_flow[0,DC1]'] = -1e20
    values['generation[0,G1]'] = 0.
    result = audit(inputs, values)
    assert 'exact_mapped_power_balance_violation' in result.errors
    assert result.maximum_exact_power_balance_violation == 37.5


def test_fresh_import_dependencies_covered():
    import json
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import IMPLEMENTATION
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.business_grid
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | set(IMPLEMENTATION) | {
        'src/rq2_joint_deliverability_boundary_v1/' + name + '.py'
        for name in ('business_grid', 'outage_trajectory', 'outage_assignment')}
    assert set(json.loads(result.stdout)) == expected


def test_joint_trajectory_keeps_trip_and_exact_repair_cap():
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    grid = network(backup=True)
    event = N1OutageEvent(1, 'repair', 'generator', 'G1', 1, 2)
    grid = replace(grid, events=(event,), repair_return_limits_mw=(('repair', 'G1', 30.),))
    inputs = contract(grid)
    model = bridge.build_business_grid_model(inputs, expected_identity=bridge.business_grid_identity(inputs))
    for v in model.component_data_objects(Var):
        v.set_value(0., skip_validation=True)
    for t, (g1, g2) in enumerate(((27.5, 10.), (0., 43.125), (30., 10.))):
        model.generation[t, 'G1'].set_value(g1)
        model.generation[t, 'G2'].set_value(g2)
    values = {v.name: v.value for v in model.component_data_objects(Var)}
    assert audit(inputs, values).physical_network_assignment_valid
    restricted = contract(replace(grid, repair_return_limits_mw=(('repair', 'G1', 29.),)))
    failed = audit(restricted, values)
    assert not failed.physical_network_assignment_valid
    assert failed.maximum_constraint_violation == 1.


def test_branch_outage_zero_flow_bound_survives_balance_replacement(grid):
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    event = N1OutageEvent(1, 'branch', 'branch', 'AC1', 1, 2)
    inputs = contract(replace(grid, events=(event,)))
    _, values = assigned(inputs)
    values['branch_flow[1,AC1]'] = 1.
    values['dc_flow[1,DC1]'] = -1.
    failed = audit(inputs, values)
    assert not failed.physical_network_assignment_valid
    assert failed.maximum_bound_violation == 1.
    assert failed.maximum_exact_power_balance_violation == 0.


def test_nonbinary_projection_preserves_exact_mw_and_error(grid):
    inputs = contract(grid, business(c=.11))
    result = audit(inputs, assigned(inputs)[1])
    assert result.physical_network_assignment_valid
    row = result.mapped_hours[0]
    assert dict(row.exact_mw)['actual_power'] == ('89', '5')
    assert dict(row.projected_mw)['actual_power'] == 17.8
    assert dict(row.projection_error_mw)['actual_power'] > 0
    assert result.maximum_exact_power_balance_violation == 0.
