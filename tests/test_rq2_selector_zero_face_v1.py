from dataclasses import replace
from hashlib import sha256
from fractions import Fraction
import json

import pytest
from pyomo.environ import Reals, maximize

from test_rq2_scale_selector_v1 import budget, REF, ACT, SPEC, args, many_inputs
from test_rq2_actual_dispatch_selector_v1 import inputs as actual_inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face as api
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face_replay as replay


def arguments(role='reference', zero=True, many=False):
    selector = REF if role == 'reference' else ACT
    if role == 'reference':
        info, disclosure, before = many_inputs() if many else args(baseline=0. if zero else 25.)
        power = None
    else:
        info, disclosure, old, power = actual_inputs(dc=0. if zero else 5.)
        physical = old.physical_origin
        before = None
    b = budget(role, tuple(g.uid for g in info.network.units))
    policy = api.policy_identity(selector, SPEC, b)
    if role != 'reference':
        before = api.initialize_actual_origin(info, physical.disclosure,
            grid_protocol=physical.protocol, generation_mw=physical.generation_mw,
            base_availability=physical.base_availability, selector=selector,
            solver_specification=SPEC, budget=b, expected_policy_identity=policy)
    identity = (api.reference.reference_input_identity(info, disclosure, before) if role == 'reference'
                else api.actual.dispatch_input_identity(info, disclosure, before, power))
    return (info, disclosure, before), dict(expected_identity=identity, selector=selector,
        solver_specification=SPEC, budget=b, expected_policy_identity=policy, power=power)


@pytest.mark.parametrize('role,count', [('reference', 2), ('actual:0', 1)])
def test_zero_face_preserves_stage_order_and_carry(role, count):
    inputs, kw = arguments(role)
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'selected', result.errors
    assert result.solver_calls == count
    assert len(result.stages) == count+1
    stage = result.stages[-1]
    assert type(stage) is api.analytic.AnalyticStage
    assert stage.objective_label == 'generation:G1'
    assert stage.objective_exact == ('20', '1')
    assert stage.solver_calls_by_certificate == 0
    assert stage.analytic_lexicographic_objective_proved
    assert not stage.rigorous_exact_physical_feasibility
    assert result.next_state.physical_carry.generation_mw == (('G1', 20.),)
    assert not result.formal_result and not result.security_certified


@pytest.mark.parametrize('role', ['reference', 'actual:0'])
def test_nonzero_l1_retains_native_path(role):
    inputs, kw = arguments(role, zero=False)
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'selected', result.errors
    assert result.solver_calls == result.planned_solver_calls
    assert all(hasattr(stage, 'raw_solve') for stage in result.stages)
    data = replay.encode(result)
    report, reproduced = replay.replay(data, *inputs, **kw,
        expected_sha256=sha256(data).hexdigest(), expected_implementation=replay.implementation_identity())
    assert report['analytic_stages_recomputed'] == 0 and reproduced == result


@pytest.mark.parametrize('role', ['reference', 'actual:0'])
def test_zero_solver_replay_rebuilds_both_evidence_kinds(role, monkeypatch):
    inputs, kw = arguments(role)
    result = api.select_hour(*inputs, **kw)
    data = replay.encode(result)
    def forbidden(*args, **kwargs):
        pytest.fail('replay called solver')
    monkeypatch.setattr(api.native, '_solve', forbidden)
    report, reproduced = replay.replay(data, *inputs, **kw,
        expected_sha256=sha256(data).hexdigest(), expected_implementation=replay.implementation_identity())
    assert report['archive_reproduced'] and reproduced == result
    assert report['analytic_stages_recomputed'] == 1
    assert report['solver_calls_by_replay'] == 0


def test_many_uid_complete_suffix_and_compact_assignment():
    inputs, kw = arguments(many=True)
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'selected', result.errors
    assert result.solver_calls == 2 and len(result.stages) == 23
    suffix = result.stages[2:]
    assert tuple(s.objective_label for s in suffix) == tuple('generation:'+g.uid for g in inputs[0].network.units)
    assert sum(bool(s.assignment) for s in suffix) == 1
    assert sum(s.assignment_witness is not None for s in suffix) == 1
    old_kw = dict(kw, expected_policy_identity=api.legacy.policy_identity(REF, SPEC, kw['budget']))
    old_result = api.legacy.select_hour(*inputs, **old_kw)
    assert old_result.status == 'selected', old_result.errors
    assert old_result.solver_calls == 23
    assert old_result.next_state.physical_carry == result.next_state.physical_carry
    assert old_result.selected_request_exact == result.selected_request_exact
    assert tuple(s.canonical_objective_hex for s in result.stages) == tuple(s.canonical_objective_hex for s in old_result.stages)
    data = replay.encode(result)
    report, reproduced = replay.replay(data, *inputs, **kw,
        expected_sha256=sha256(data).hexdigest(), expected_implementation=replay.implementation_identity())
    assert report['analytic_stages_recomputed'] == 21 and reproduced == result


@pytest.mark.parametrize('fault', ['near_zero', 'generation', 'missing_flow', 'wrong_identity', 'wrong_power'])
def test_analytic_preconditions_fail_closed(fault):
    inputs, kw = arguments('actual:0')
    result = api.select_hour(*inputs, **kw)
    raw = result.stages[0].raw_solve
    assignment = dict(raw.loaded_values)
    frozen = (0.,)
    if fault == 'near_zero':
        assignment['selector_deviation[G1]'] = 1e-12
        frozen = (1e-12,)
    if fault == 'generation': assignment['generation[G1]'] += 1e-12
    if fault == 'missing_flow': assignment.pop(next(k for k in assignment if 'flow' in k))
    if fault == 'wrong_identity': kw['expected_identity'] = '0'*64
    if fault == 'wrong_power': kw['power'] = replace(kw['power'], numerator='1')
    with pytest.raises((ValueError, KeyError)):
        api.analytic.certify_suffix(*inputs, power=kw['power'], budget=kw['budget'], selector=kw['selector'],
            specification=SPEC, expected_identity=kw['expected_identity'], policy_identity=kw['expected_policy_identity'],
            frozen=frozen, assignment=tuple(assignment.items()), expected_implementation=api.analytic.implementation_identity())


def test_tampered_analytic_claim_rejected_even_with_new_archive_hash():
    inputs, kw = arguments()
    result = api.select_hour(*inputs, **kw)
    wire = json.loads(replay.encode(result))
    fields = dict(wire[1])
    stage = fields['stages'][1][-1]
    for row in stage[1]:
        if row[0] == 'objective_exact': row[1] = ['tuple', ['19', '1']]
    data = replay.old.store._bytes(wire)
    with pytest.raises(ValueError, match='differs'):
        replay.replay(data, *inputs, **kw, expected_sha256=sha256(data).hexdigest(),
            expected_implementation=replay.implementation_identity())


def test_analytic_failure_retains_prefix_without_successor(monkeypatch):
    inputs, kw = arguments()
    def failed(*args, **kwargs):
        raise ValueError('injected physical proof failure')
    monkeypatch.setattr(api.analytic, 'certify_suffix', failed)
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'unresolved' and result.next_state is None
    assert len(result.stages) == result.solver_calls == 2
    assert result.errors == ('analytic_suffix_unresolved:ValueError',)


@pytest.mark.parametrize('kind', ['budget', 'policy', 'input'])
def test_binding_failure_before_any_solver(kind, monkeypatch):
    inputs, kw = arguments()
    if kind == 'budget': kw['budget'] = replace(kw['budget'], generator_uids=('wrong',))
    if kind == 'policy': kw['expected_policy_identity'] = '0'*64
    if kind == 'input': kw['expected_identity'] = '0'*64
    def forbidden(*args, **kwargs):
        pytest.fail('bad binding reached solver')
    monkeypatch.setattr(api.native, '_solve', forbidden)
    with pytest.raises(ValueError): api.select_hour(*inputs, **kw)


@pytest.mark.parametrize('fault', ['domain', 'deviation_row', 'missing_side', 'zero_lock', 'objective', 'inactive', 'maximize'])
def test_actual_model_algebra_is_checked(fault):
    inputs, kw = arguments()
    model = api.reference._stage_model(*inputs, kw['expected_identity'], 2, (0., 0.))
    if fault == 'domain':
        model.selector_deviation['G1'].domain = Reals
        model.selector_deviation['G1'].setlb(-1.)
    if fault == 'deviation_row':
        model.selector_constraints[1].set_value(model.selector_deviation['G1'] >= model.generation['G1']-21.)
    if fault == 'missing_side': model.selector_constraints[2].deactivate()
    if fault == 'zero_lock': model.selector_fixed[2].set_value(model.selector_deviation['G1'] <= 1e-9)
    if fault == 'objective': model.objective.set_value(model.generation['G1']+model.reference_power)
    if fault == 'inactive': model.objective.deactivate()
    if fault == 'maximize': model.objective.sense = maximize
    with pytest.raises(ValueError): api.analytic._prove_model_face(model, inputs[0].normal.generation_mw, True, 2)


def test_policy_drift_inside_suffix_rejected(monkeypatch):
    inputs, kw = arguments('actual:0')
    result = api.select_hour(*inputs, **kw)
    calls = []
    def drift(*args):
        calls.append(1)
        return kw['expected_policy_identity'] if len(calls) == 1 else '0'*64
    monkeypatch.setattr(api, 'policy_identity', drift)
    with pytest.raises(ValueError, match='drift'):
        api.analytic.certify_suffix(*inputs, power=kw['power'], budget=kw['budget'], selector=kw['selector'],
            specification=SPEC, expected_identity=kw['expected_identity'], policy_identity=kw['expected_policy_identity'],
            frozen=(0.,), assignment=result.stages[0].raw_solve.loaded_values,
            expected_implementation=api.analytic.implementation_identity())


def test_near_zero_integrated_path_still_solves_uid(monkeypatch):
    from test_rq2_actual_dispatch_selector_v1 import install
    inputs, kw = arguments('actual:0')
    calls = install(monkeypatch, overrides={'generation[G1]': 20.+1e-12, 'selector_deviation[G1]': 1e-12})
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'selected', result.errors
    assert calls['solve'] == result.solver_calls == 2
    assert all(hasattr(s, 'raw_solve') for s in result.stages)


@pytest.mark.parametrize('fault', ['timeout', 'missing_variable'])
def test_native_prefix_failure_never_attempts_analytic(monkeypatch, fault):
    from test_rq2_actual_dispatch_selector_v1 import install
    inputs, kw = arguments('actual:0')
    calls = install(monkeypatch, fault=fault, stage=0,
        overrides={'generation[G1]': 20., 'selector_deviation[G1]': 0.})
    def forbidden(*args, **kwargs):
        pytest.fail('invalid prefix reached analytic proof')
    monkeypatch.setattr(api.analytic, 'certify_suffix', forbidden)
    result = api.select_hour(*inputs, **kw)
    assert result.status == 'unresolved' and result.next_state is None
    assert calls['solve'] == result.solver_calls == 1


@pytest.mark.parametrize('fault', ['calls', 'purpose', 'order'])
def test_native_prefix_or_order_tampering_rejected(fault):
    inputs, kw = arguments()
    wire = json.loads(replay.encode(api.select_hour(*inputs, **kw)))
    stages = dict(wire[1])['stages'][1]
    if fault == 'order': stages[0], stages[-1] = stages[-1], stages[0]
    else:
        raw = dict(stages[0][1])['raw_solve']
        for row in raw[1]:
            if row[0] == fault: row[1] = 0 if fault == 'calls' else 'wrong-purpose'
    data = replay.old.store._bytes(wire)
    with pytest.raises(ValueError):
        replay.replay(data, *inputs, **kw, expected_sha256=sha256(data).hexdigest(),
            expected_implementation=replay.implementation_identity())


def test_reference_two_hour_state_continuity():
    from test_rq2_current_grid_step_v1 import prepared, current, view
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
    inputs, kw = arguments()
    first = api.select_hour(*inputs, **kw)
    info = view(prepared(10.), replace(current(t=2, demand=20.), dc_baseline_mw=0.))
    before = first.next_state
    disclosure = disclose_current(before.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    second_args = (info, disclosure, before)
    b = replace(kw['budget'], source_hour=2)
    second = api.select_hour(*second_args, **dict(kw, budget=b,
        expected_identity=api.reference.reference_input_identity(*second_args)))
    assert second.status == 'selected', second.errors
    assert second.policy_identity == first.policy_identity
    assert second.next_state.previous_state_identity == first.next_state.identity
    assert second.next_state.physical_carry.source_hour == 2
    assert second.solver_calls == 2


def test_actual_two_hour_state_continuity():
    from test_rq2_current_grid_step_v1 import prepared, current, view
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
    inputs, kw = arguments('actual:0')
    first = api.select_hour(*inputs, **kw)
    info = view(prepared(10.), current(t=2, demand=20.))
    before = first.next_state
    disclosure = disclose_current(before.physical_carry.disclosure, CurrentOutageReport(2, None, None))
    power = replace(kw['power'], source_hour=2)
    second_args = (info, disclosure, before)
    b = replace(kw['budget'], source_hour=2)
    second = api.select_hour(*second_args, **dict(kw, budget=b, power=power,
        expected_identity=api.actual.dispatch_input_identity(*second_args, power)))
    assert second.status == 'selected', second.errors
    assert second.policy_identity == first.policy_identity
    assert second.next_state.previous_state_identity == first.next_state.identity
    assert second.next_state.physical_carry.source_hour == 2
    assert second.solver_calls == 1


def test_positive_reference_request_can_have_zero_l1_suffix():
    inputs = args(ramp=0., baseline=25.)
    b = budget()
    result = api.select_hour(*inputs, expected_identity=api.reference.reference_input_identity(*inputs),
        selector=REF, solver_specification=SPEC, budget=b,
        expected_policy_identity=api.policy_identity(REF, SPEC, b))
    assert result.status == 'selected', result.errors
    assert result.selected_request_exact == ('25', '1')
    assert result.solver_calls == 2 and type(result.stages[-1]) is api.analytic.AnalyticStage


def test_non_dyadic_objective_fraction_is_binary64_exact():
    # Synthetic complete assignment with analytically known zero prefix; this
    # conditional helper test does not fabricate a native prefix record.
    from pyomo.environ import Var
    from test_rq2_continuous_grid_normal_v1 import fixture
    from test_rq2_grid_information_v1 import prepare
    from test_rq2_current_grid_step_v1 import current, view, origin, protocol
    from src.rq2_joint_deliverability_boundary_v1 import reference_grid
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
    info = view(prepare(fixture(demand=20.1)), replace(current(demand=20.1), dc_baseline_mw=0.))
    physical = origin(info, generation=20.1)
    before = reference_grid.initialize_reference_origin(info, physical.disclosure,
        reference_protocol=args()[2].protocol, grid_protocol=protocol(),
        generation_mw=physical.generation_mw, base_availability=physical.base_availability)
    disclosure = disclose_current(physical.disclosure, CurrentOutageReport(1, None, None))
    inputs = (info, disclosure, before)
    identity = api.reference.reference_input_identity(*inputs)
    model = api.reference._stage_model(*inputs, identity, 2, (0., 0.))
    values = {v.name: 0. for v in model.component_data_objects(Var)}
    values['generation[G1]'] = 20.1
    b = budget()
    stages = api.analytic.certify_suffix(*inputs, power=None, budget=b, selector=REF, specification=SPEC,
        expected_identity=identity, policy_identity=api.policy_identity(REF, SPEC, b), frozen=(0., 0.),
        assignment=tuple(values.items()), expected_implementation=api.analytic.implementation_identity())
    expected = Fraction.from_float(20.1)
    assert expected != Fraction('20.1')
    assert stages[-1].objective_exact == (str(expected.numerator), str(expected.denominator))
