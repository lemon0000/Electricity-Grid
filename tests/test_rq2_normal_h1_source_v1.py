from dataclasses import replace
from datetime import timedelta
import json

import pytest

from tests.test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source as api
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_current_solve as solve


def packet(data=None, row=None, **kwargs):
    data = fixture(1).data if data is None else data
    row = data.hourly_points[0] if row is None else row
    return api.assemble_current_normal(api.static_network(data), row,
        kwargs.pop('raw_workload', '0'), dc_bus=1, relative_hour=kwargs.pop('relative_hour', 0),
        source_time_basis=kwargs.pop('source_time_basis',
            'naive_source_labelled_utc' if row.timestamp.tzinfo is None else 'aware_source'), **kwargs)


def run(p):
    return solve.solve_current(p, spec(), budget(), expected_key=solve.request_key(p, spec(), budget()))


@pytest.fixture(scope='module')
def first():
    p = packet()
    r = run(p)
    assert r.evidence.numerical_chain_accepted, r.evidence.errors
    return p, r


def test_future_rows_never_read_and_absolute_clock_not_in_key():
    class Poison:
        def __iter__(self):
            raise AssertionError('future rows read')
        def __deepcopy__(self, memo):
            raise AssertionError('future rows copied')
        def __len__(self):
            raise AssertionError('future rows counted')
    x = fixture(3).data
    p = packet(x)
    poison = replace(x, hourly_points=Poison())
    row = replace(x.hourly_points[0], timestamp=x.hourly_points[0].timestamp+timedelta(days=900))
    q = packet(poison, row)
    assert p.source_timestamp != q.source_timestamp
    assert p.audit_identity != q.audit_identity
    assert p.inputs == q.inputs
    assert solve.request_key(p, spec(), budget()) == solve.request_key(q, spec(), budget())
    assert q.network.data.hourly_points == ()
    assert len(q.inputs.data.hourly_points) == 1
    assert q.inputs.request.periods == ('h1',)
    assert not q.inputs.request.incidents


def test_source_labels_are_separate_from_computational_inputs():
    x = fixture(1).data
    keys = []
    for split, pair in [('training', 'pair-A'), ('holdout', 'pair-B')]:
        audit_record = dict(split=split, pair_id=pair, data=x, row=x.hourly_points[0])
        p = packet(audit_record['data'], audit_record['row'])
        keys.append(solve.request_key(p, spec(), budget()))
    assert keys[0] == keys[1]


def test_static_uid_order_and_dictionary_order_are_canonical():
    x = fixture(1).data
    y = replace(x, buses=tuple(reversed(x.buses)))
    row = replace(x.hourly_points[0], demand_by_bus_mw={2: 0., 1: 20.})
    assert solve.request_key(packet(x), spec(), budget()) == solve.request_key(packet(y, row), spec(), budget())


def test_current_values_and_solver_identity_change_key():
    p = packet()
    key = solve.request_key(p, spec(), budget())
    row = replace(p.inputs.data.hourly_points[0], demand_by_bus_mw={1: 21., 2: 0.})
    assert solve.request_key(packet(row=row), spec(), budget()) != key
    assert solve.request_key(packet(raw_workload='0.1'), spec(), budget()) != key
    assert solve.request_key(p, replace(spec(), time_limit_seconds=.5), budget()) != key
    with pytest.raises(ValueError, match='seed'):
        solve.request_key(p, replace(spec(), random_seed=1), budget())


def test_declared_initial_and_linear_workload_mapping():
    p = packet(raw_workload='0.1000000000004')
    assert p.inputs.request.dc_requested_mw == (25.,)
    assert p.inputs.request.dc_physical_maximum_mw == (250.,)
    assert p.inputs.initial.commitment == {'G1': False}
    assert p.inputs.initial.generation_mw == {'G1': 0.}
    assert p.inputs.initial.time_in_state_hours == {'G1': 3}
    assert json.loads(p.workload_projection_payload)['raw_workload_fraction'] == '0.1000000000004'
    same = packet(raw_workload='0.1')
    assert p.audit_identity != same.audit_identity
    assert solve.request_key(p, spec(), budget()) == solve.request_key(same, spec(), budget())


def test_audit_bytes_are_immutable_and_tampering_rejected():
    p = packet(raw_workload='0.1')
    assert type(p.workload_projection_payload) is bytes
    changed = json.loads(p.workload_projection_payload)
    changed['projected_fraction_exact'][0] = '9'
    object.__setattr__(p, 'workload_projection_payload', api._projection_bytes(changed))
    with pytest.raises(ValueError, match='audit drift'):
        api.validate_current(p)
    p = packet()
    object.__setattr__(p, 'source_timestamp', '2021-01-01T00:00:00')
    with pytest.raises(ValueError, match='audit drift'):
        api.validate_current(p)


@pytest.mark.parametrize('basis', ['aware_source', 'unspecified', None])
def test_source_time_basis_must_be_explicit_and_matching(basis):
    with pytest.raises(ValueError, match='source time basis'):
        packet(source_time_basis=basis)


@pytest.mark.parametrize('raw', ['1.0000000000001', '0.0000000000001', '-1', '1e-1', True])
def test_unresolved_or_invalid_workload_never_clipped(raw):
    with pytest.raises(ValueError):
        packet(raw_workload=raw)


@pytest.mark.parametrize('hour', [True, -1, 192, 1])
def test_relative_clock_and_missing_history_rejected(hour):
    with pytest.raises(ValueError):
        packet(relative_hour=hour)


def test_current_row_owned_and_postassembly_drift_detected():
    data = fixture(1).data
    p = packet(data)
    data.hourly_points[0].demand_by_bus_mw[1] = 77.
    assert p.inputs.data.hourly_points[0].demand_by_bus_mw[1] == 20.
    p.inputs.data.hourly_points[0].demand_by_bus_mw[1] = 31.
    with pytest.raises(ValueError):
        solve.request_key(p, spec(), budget())


def test_packet_boundary_cannot_diverge_from_copied_model_initial():
    p = packet()
    forged = api._owned(api.H1NormalBoundary, network_identity=p.network.identity, completed_hours=0,
        units=(('G1', False, 0., 2),), evidence_role='declared_mechanism_initial')
    object.__setattr__(p, 'before', forged)
    with pytest.raises(ValueError, match='binding mismatch'):
        api.validate_current(p)


def test_all_modes_in_boundary_and_static_binding():
    x = fixture(1).data
    g = x.generators[0]
    x = replace(x, generators=(g, replace(g, uid='F', dispatch_mode='fixed'),
        replace(g, uid='R', dispatch_mode='curtailable'),
        replace(g, uid='Z', dispatch_mode='disabled', enabled=False)))
    row = replace(x.hourly_points[0], generator_min_mw=dict(G1=10., F=5., R=0., Z=0.),
                  generator_max_mw=dict(G1=100., F=5., R=30., Z=0.))
    p = packet(x, row)
    assert p.before.units == (('F', True, 5., 0), ('G1', False, 0., 3),
                              ('R', True, 0., 0), ('Z', False, 0., 0))
    assert p.inputs.carry.points == (api.UnitPoint('G1', False, 0.),)
    reordered = packet(replace(x, generators=tuple(reversed(x.generators))), row)
    assert p.input_identity == reordered.input_identity
    changed_row = replace(row, generator_min_mw=dict(G1=10., F=6., R=0., Z=0.),
                          generator_max_mw=dict(G1=100., F=6., R=30., Z=0.))
    with pytest.raises(ValueError, match='declared current-row initial'):
        packet(x, changed_row, before=p.before)
    changed = replace(x, generators=tuple(replace(u, ramp_mw_per_hour=50.) for u in x.generators))
    with pytest.raises(ValueError, match='network'):
        packet(changed, row, before=p.before)


def test_feasibility_candidate_cannot_feed_next_hour_or_claim_lex():
    p = packet()
    transition = api.replay_feasible_boundary(p, assignment_for(p.inputs), expected_input_identity=p.input_identity)
    assert transition.candidate_boundary.completed_hours == 1
    assert not transition.published and not transition.numerical_lex_accepted
    with pytest.raises(ValueError, match='complete numerical lex'):
        packet(relative_hour=1, before=transition.candidate_boundary)


@pytest.mark.parametrize('mode,enabled,on,power,age', [
    ('fixed', True, False, 0., 0), ('fixed', True, True, 5., 99),
    ('curtailable', True, False, 0., 0), ('curtailable', True, True, 101., 0),
    ('disabled', False, True, 0., 0), ('disabled', False, False, 1., 0),
    ('disabled', False, False, 0., 1)])
def test_malformed_noncommittable_successor_rejected(mode, enabled, on, power, age):
    x = fixture(1).data
    x = replace(x, generators=(*x.generators, replace(x.generators[0], uid='X',
                dispatch_mode=mode, enabled=enabled)))
    p = packet(x, replace(x.hourly_points[0],
        generator_min_mw=dict(G1=10., X=0.), generator_max_mw=dict(G1=100., X=0.)))
    # Fault injection bypasses the owned constructor, as a corrupted decode might.
    before = api._owned(api.H1NormalBoundary, network_identity=p.network.identity, completed_hours=1,
        units=(('G1', True, 20., 1), ('X', on, power, age)), evidence_role='numerical_lex_candidate')
    with pytest.raises(ValueError, match='boundary'):
        api.assemble_current_normal(p.network, p.inputs.data.hourly_points[0], '0',
            relative_hour=1, dc_bus=1, before=before, source_time_basis='aware_source')


@pytest.mark.parametrize('on,power,age', [(True, 20., 0), (True, 20., 2),
    (False, 0., 0), (False, 0., 5), (False, 10., 1), (True, 9., 1), (True, 101., 1)])
def test_malformed_committable_successor_rejected(on, power, age):
    p = packet()
    before = api._owned(api.H1NormalBoundary, network_identity=p.network.identity, completed_hours=1,
        units=(('G1', on, power, age),), evidence_role='numerical_lex_candidate')
    with pytest.raises(ValueError, match='boundary'):
        packet(relative_hour=1, before=before)


@pytest.mark.parametrize('mode,epsilon', [('committable', 5e-10), ('disabled', 5e-10),
                                        ('curtailable', -5e-10)])
def test_numerically_feasible_but_exact_carry_domain_rejected(mode, epsilon):
    x = fixture(1, demand=0.).data
    if mode == 'committable':
        p = packet(x)
        assignment = assignment_for(p.inputs, {0: False})
        uid = 'G1'
    else:
        uid = 'X'
        x = replace(x, generators=(*x.generators, replace(x.generators[0], uid=uid,
            dispatch_mode=mode, enabled=mode != 'disabled')))
        row = replace(x.hourly_points[0], generator_min_mw=dict(G1=10., X=0.),
                      generator_max_mw=dict(G1=100., X=0.))
        p = packet(x, row)
        assignment = assignment_for(p.inputs, {0: False})
    assignment[f'generation[normal,0,{uid}]'] = epsilon
    req = api.model_api.H1StageRequest(p.inputs)
    audit = api.model_api.audit_h1_assignment(req, assignment,
        expected_identity=api.model_api.h1_stage_identity(req))
    assert not audit.errors
    with pytest.raises(ValueError):
        api.replay_feasible_boundary(p, assignment, expected_input_identity=p.input_identity)
    assert p.before.completed_hours == 0


def test_boundary_rejection_preserves_accepted_native_chain_evidence(monkeypatch, first):
    p, saved = first
    monkeypatch.setattr(solve.native, 'run_h1_chain', lambda *a, **k: saved.evidence)
    def reject(*args, **kwargs):
        raise ValueError('injected exact carry-domain rejection')
    monkeypatch.setattr(api, 'replay_feasible_boundary', reject)
    result = run(p)
    assert result.evidence is saved.evidence
    assert result.evidence.numerical_chain_accepted and result.evidence.solver_calls == 3
    assert result.decision is None and not result.current_decision_accepted
    assert result.errors and 'current_boundary_rejected' in result.errors[0]
    assert p.before.completed_hours == 0


def test_postsolve_input_check_failure_also_retains_native_evidence(monkeypatch, first):
    p, saved = first
    monkeypatch.setattr(solve.native, 'run_h1_chain', lambda *a, **k: saved.evidence)
    real_key, calls = solve.request_key, []
    def changing_key(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise ValueError('injected post-solve input drift')
        return real_key(*args, **kwargs)
    monkeypatch.setattr(solve, 'request_key', changing_key)
    result = run(p)
    assert result.evidence is saved.evidence and result.evidence.solver_calls == 3
    assert result.decision is None and not result.current_decision_accepted
    assert 'current_input_rejected' in result.errors[0]


def test_two_native_hours_keep_startup_and_residual_dwell(first):
    p, result = first
    first_state = result.decision.candidate_boundary
    assert first_state.units == (('G1', True, 20., 1),)
    assert result.decision.canonical_locks == (20., 1., 20.)
    assert not result.decision.published
    second = packet(relative_hour=1, before=first_state)
    assert second.inputs.source_hours == (1,)
    assert second.inputs.carry.source_hour == 0
    assert second.inputs.initial.time_in_state_hours == {'G1': 1}
    assert second.inputs.initial.generation_mw == {'G1': 20.}
    model = api.model_api.build_h1_stage_model(api.model_api.H1StageRequest(second.inputs),
        expected_identity=api.model_api.h1_stage_identity(api.model_api.H1StageRequest(second.inputs)))
    assert len(model.initial_residual_dwell) == 1
    replay = run(second)
    assert replay.evidence.numerical_chain_accepted, replay.evidence.errors
    assert replay.decision.candidate_boundary.units == (('G1', True, 20., 2),)
    assert replay.decision.candidate_boundary.completed_hours == 2
    assert replay.request_key != result.request_key
    for wrong_hour in (0, 2):
        with pytest.raises(ValueError, match='relative-hour mismatch'):
            packet(relative_hour=wrong_hour, before=first_state)


def test_native_workload_power_and_same_key_projection(first):
    p = packet(raw_workload='0.1')
    result = run(p)
    assert result.evidence.numerical_chain_accepted, result.evidence.errors
    assert result.decision.candidate_boundary.units == (('G1', True, 45., 1),)
    original, saved = first
    row = replace(fixture(1).data.hourly_points[0],
                  timestamp=fixture(1).data.hourly_points[0].timestamp+timedelta(days=700))
    changed = packet(row=row)
    replay = run(changed)
    assert original.source_timestamp != changed.source_timestamp
    assert saved.request_key == replay.request_key
    assert saved.decision.projection_identity == replay.decision.projection_identity


@pytest.mark.parametrize('demand', [0., 90.])
def test_interhour_dwell_and_ramp_violations_reject_without_boundary(first, demand):
    _, result = first
    before = result.decision.candidate_boundary
    data = fixture(1, demand=demand).data
    # Keep static network fixed; change only the revealed demand.
    p = packet(row=data.hourly_points[0], relative_hour=1, before=before)
    assignment = assignment_for(p.inputs, {0: demand != 0.})
    if demand == 0.:
        for name in assignment:
            if name.startswith('segment_power'):
                assignment[name] = 0.
    with pytest.raises(ValueError, match='assignment rejected'):
        api.replay_feasible_boundary(p, assignment, expected_input_identity=p.input_identity)
    assert before.units == (('G1', True, 20., 1),)


def test_failure_in_native_chain_has_no_decision_or_next_state(monkeypatch, first):
    p = packet()
    seen = []
    def fail(*args, **kwargs):
        seen.append(1)
        if len(seen) == 1:
            return first[1].evidence.stages[0].native_payload
        raise RuntimeError('injected collector failure')
    monkeypatch.setattr(solve.native.capture, 'solve_once', fail)
    result = run(p)
    assert result.decision is None
    assert not result.evidence.numerical_chain_accepted
    assert result.evidence.collector_attempts == 2
    assert result.evidence.stages[0].accepted
    assert p.before.completed_hours == 0


def test_public_constructors_and_old_input_type_rejected():
    for cls in (api.H1StaticNetwork, api.H1NormalBoundary, api.H1CurrentNormal,
                api.H1FeasibleTransition, solve.H1NormalDecision, solve.H1CurrentSolve):
        with pytest.raises(TypeError):
            cls()
    with pytest.raises(ValueError, match='exact current'):
        api.validate_current(fixture(1))
