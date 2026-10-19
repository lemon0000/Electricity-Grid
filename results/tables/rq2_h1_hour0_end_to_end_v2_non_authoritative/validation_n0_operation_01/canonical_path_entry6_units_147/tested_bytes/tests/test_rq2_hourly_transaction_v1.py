from dataclasses import replace
from fractions import Fraction as Q

import pytest

from test_rq2_common_request_adapter_v1 import mapping, normal_source, source
from test_rq2_reference_grid_v1 import args
from test_rq2_reference_selector_v1 import SELECTOR as REF_SELECTOR, SHORT as REF_BUDGET, run as select
from test_rq2_actual_dispatch_selector_v1 import SELECTOR, SHORT, install
from test_rq2_continuous_grid_candidate_v1 import SPEC
from test_rq2_current_grid_step_v1 import current, view
from test_rq2_continuous_capacity_policy_v1 import init
from test_rq2_continuous_recovery_controller_v1 import obs
from src.rq2_joint_deliverability_boundary_v1 import hourly_transaction as tx
from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as dispatch
from src.rq2_joint_deliverability_boundary_v1 import common_request_adapter as adapter
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import normal_input_identity
from src.rq2_joint_deliverability_boundary_v1.capacity_policy import initialize_capacity_policy
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current


def audit(info):
    normal, prepared = normal_source()
    return adapter.bind_request_source(normal, prepared, info, expected_normal_identity=normal_input_identity(normal),
        expected_prepared_identity=prepared.audit_identity)


def make_origin(inputs=None, unit='45'):
    inputs = args() if inputs is None else inputs
    return tx.initialize_common_hours(*inputs, source(inputs, unit), mapping(unit), audit(inputs[0]),
        reference_selector=REF_SELECTOR, solver_specification=SPEC, budget=REF_BUDGET)


def publish(before, info, disclosure, cfe=0., **changes):
    reference = select((info, disclosure, before.reference_state))
    hour = replace(source((info, disclosure, before.reference_state), before.mapping.normalized_unit_mw, cfe),
        power_source_hour=info.current.source_hour, workload_source_hour=100+info.current.source_hour)
    values = dict(limits=obs(1, g=0., c=0., due=None).limits,
        due_hour=5 if (reference.selected_request_exact not in (None, ('0', '1')) or cfe) else None,
        available_flexibility=1.)
    values.update(changes)
    return tx.publish_common_hour(before, info, disclosure, reference, hour, audit(info), **values)


@pytest.fixture(scope='module')
def first():
    inputs = args()
    origin = make_origin(inputs)
    attempt = publish(origin, inputs[0], inputs[1])
    assert attempt.publication is not None, attempt.mapping_result.errors
    return inputs, origin, attempt


def arm_origin(inputs, common, arm=JOINT, capacity=1.):
    business = init(arm=arm, committed_capacity=capacity, curtailment_ramp_per_hour=1., response_time_hours=1.)
    track = business.initial.tracks[0][1]
    business = initialize_capacity_policy(business.spec, anchor=common.source_anchor,
        envelope=dict(track.physical.envelope), accounting_period_id=track.ledger.accounting_period_id,
        zero_carry_in_assumption=True)
    physical = inputs[2].physical_origin
    grid = dispatch.initialize_dispatch_origin(inputs[0], physical.disclosure, grid_protocol=physical.protocol,
        generation_mw=physical.generation_mw, base_availability=physical.base_availability,
        selector=SELECTOR, solver_specification=SPEC, budget=SHORT)
    return tx.initialize_arm_hours(common, business, grid, selector=SELECTOR, solver_specification=SPEC, budget=SHORT)


def advance(before, publication):
    return tx.advance_arm_hour(before, publication)


def next_hour(common, demand=20., cap=25.):
    _, prepared = normal_source()
    info = view(prepared, replace(current(2, demand=demand), dc_baseline_mw=25.,
        dc_connected_capacity_mw=cap, dc_physical_maximum_mw=max(30., cap)))
    prior = common.reference_state.physical_carry.disclosure
    return info, disclose_current(prior, CurrentOutageReport(2, None, None))


def test_real_four_arms_share_request_but_commit_physical_states_independently(first):
    inputs, origin, common = first
    results = [advance(arm_origin(inputs, origin, arm), common.publication) for arm in (NETWORK, CFE, JOINT, B6)]
    assert {r.exposure_id for r in results} == {common.publication.exposure_id}
    assert {r.publication_identity for r in results} == {common.publication.identity}
    assert common.mapping_result.raw_grid_request_mw == 15
    assert common.mapping_result.normalized_grid_request == Q(1, 3)
    for result in results:
        assert result.business_candidate.records[-1].current.observation.hour == common.mapping_result.mapped_hour
        assert result.capacity_certificate is result.causal_certificate is None
        assert result.formal_result is result.security_certified is False
        if result.arm_id == CFE:
            assert result.status == 'physical_network_unresolved'
            assert not result.grid_service_applicable
            assert result.grid_service_failure is result.candidate_grid_service_failure is None
            assert result.published_pair is None and result.cursor.halted
            assert result.cursor.business.records == ()
        else:
            assert result.status == 'committed', result.error
            assert result.prescribed_power.exact_mw == 10
            assert result.cursor.business.execution.tracks[0][1].ledger.debt == Q(1, 3)
            assert result.cursor.grid.physical_carry.generation_mw == (('G1', 30.),)
            assert result.published_pair == (result.cursor.business, result.cursor.grid)


def test_business_shortfall_never_calls_network_and_halts(first, monkeypatch):
    inputs, origin, common = first
    before = arm_origin(inputs, origin, capacity=.125)
    def forbidden(*a, **kw): raise AssertionError('network must not run for business shortfall')
    monkeypatch.setattr(dispatch, 'select_actual_dispatch', forbidden)
    result = advance(before, common.publication)
    assert result.status == 'business_rejected'
    assert result.candidate_grid_service_failure is True and result.grid_service_failure is None
    assert result.dispatch_result is result.prescribed_power is result.published_pair is None
    assert result.cursor.business == before.business and result.cursor.grid == before.grid
    assert result.cursor.halted
    with pytest.raises(ValueError, match='halted arm'):
        advance(result.cursor, common.publication)


def test_late_network_failure_keeps_business_candidate_but_not_debt(first, monkeypatch):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    calls = install(monkeypatch, 'timeout', 1, overrides={'generation[G1]': 30., 'selector_deviation[G1]': 10.})
    result = advance(before, common.publication)
    assert calls == {'create': 2, 'solve': 2}
    assert result.status == 'physical_network_unresolved'
    assert result.business_candidate.records[-1].committed
    assert result.business_candidate.execution.tracks[0][1].ledger.debt == Q(1, 3)
    assert result.cursor.business.execution.tracks[0][1].ledger.debt == 0
    assert result.cursor.grid == before.grid and result.published_pair is None


def test_reference_continues_after_one_arm_stops_and_active_arm_advances(first):
    inputs, origin, common = first
    active = advance(arm_origin(inputs, origin), common.publication)
    stopped = advance(arm_origin(inputs, origin, capacity=.125), common.publication)
    info, disclosure = next_hour(common.cursor)
    second = publish(common.cursor, info, disclosure)
    assert second.publication.previous_publication_identity == common.publication.identity
    assert second.publication.exposure_id != common.publication.exposure_id
    assert second.cursor.reference_state.physical_carry.source_hour == 2
    with pytest.raises(ValueError, match='halted arm'):
        advance(stopped.cursor, second.publication)
    continued = advance(active.cursor, second.publication)
    assert continued.status == 'committed', continued.error
    assert continued.cursor.grid.physical_carry.source_hour == 2
    assert continued.cursor.business.execution.tracks[0][1].ledger.debt == Q(2, 3)
    assert common.cursor.reference_state.physical_carry.source_hour == 1


def test_recovery_above_baseline_is_checked_as_actual_power(first):
    inputs, origin, common = first
    active = advance(arm_origin(inputs, origin), common.publication)
    info, disclosure = next_hour(common.cursor, demand=0., cap=30.)
    limits = replace(obs(1, g=0., c=0., due=None).limits,
        business_recovery_headroom=Q(1, 45), cfe_compatible_surplus=Q(1, 45), maximum_recovery_power=Q(1, 45))
    second = publish(common.cursor, info, disclosure, limits=limits, due_hour=None)
    assert second.mapping_result.raw_grid_request_mw == 0
    recovered = advance(active.cursor, second.publication)
    assert recovered.status == 'committed', recovered.error
    assert 25 < recovered.prescribed_power.exact_mw <= 26
    record = recovered.business_candidate.records[-1]
    assert recovered.prescribed_power.exact_mw == record.response.action.actual_service_power*45
    assert recovered.cursor.business.execution.tracks[0][1].ledger.debt < Q(1, 3)


@pytest.mark.parametrize('changes', [{'due_hour': -1}, {'available_flexibility': -1.}, {'limits': None}])
def test_invalid_common_business_input_halts_without_reference_commit(first, changes):
    inputs, origin, common = first
    values = dict(limits=common.publication.business_current.observation.limits, due_hour=5, available_flexibility=1.)
    values.update(changes)
    result = tx.publish_common_hour(origin, inputs[0], inputs[1], common.reference_result, source(inputs), audit(inputs[0]), **values)
    assert result.status == 'common_input_rejected' and result.error
    assert result.publication is None
    assert result.cursor.reference_state == origin.reference_state
    assert result.cursor.halted


def test_repeated_or_skipped_common_publication_is_rejected(first):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    active = advance(before, common.publication)
    with pytest.raises(ValueError, match='chain'):
        advance(active.cursor, common.publication)
    info, disclosure = next_hour(common.cursor)
    second = publish(common.cursor, info, disclosure)
    with pytest.raises(ValueError, match='chain'):
        advance(before, second.publication)


def test_different_mapping_episode_cannot_supply_arm_publication(first):
    inputs, origin, common = first
    other = make_origin(inputs, unit='50')
    arm = arm_origin(inputs, other)
    with pytest.raises(ValueError, match='chain'):
        advance(arm, common.publication)


def test_public_wrappers_cannot_be_replaced_and_impl_drift_rejected(first, monkeypatch):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    for obj, field, val in [(origin, 'mapping', mapping('50')), (before, 'halted', False),
            (common.publication, 'exposure_id', 'f'*64)]:
        with pytest.raises(TypeError):
            replace(obj, **{field: val})
    monkeypatch.setattr(tx, '_implementation', lambda: 'f'*64)
    with pytest.raises(ValueError, match='drift'):
        advance(before, common.publication)


def test_dispatch_policy_drift_is_rejected_before_business(first, monkeypatch):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    monkeypatch.setattr(dispatch, '_policy_identity', lambda *a: 'f'*64)
    with pytest.raises(ValueError, match='policy'):
        advance(before, common.publication)


def test_common_resolution_failure_retains_last_reference_and_halts():
    inputs = args()
    origin = make_origin(inputs, unit='15000000')
    attempt = publish(origin, inputs[0], inputs[1])
    assert attempt.publication is None and attempt.cursor.halted
    assert attempt.reference_result.next_reference_state is not None
    assert attempt.cursor.reference_state == origin.reference_state
    assert attempt.mapping_result.raw_grid_request_mw == 15
    with pytest.raises(ValueError, match='active owned'):
        publish(attempt.cursor, inputs[0], inputs[1])


def test_common_cannot_change_source_or_reference_policy(first):
    inputs, origin, common = first
    selected = common.reference_result
    with pytest.raises(ValueError, match='split'):
        tx.publish_common_hour(origin, inputs[0], inputs[1], selected,
            replace(source(inputs), split='holdout'), audit(inputs[0]),
            limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1.)
    other_selector = replace(REF_SELECTOR, absolute_gap_mw=1e-8)
    other = tx.initialize_common_hours(*inputs, source(inputs), mapping(), audit(inputs[0]),
        reference_selector=other_selector, solver_specification=SPEC, budget=REF_BUDGET)
    with pytest.raises(ValueError, match='reference policy'):
        tx.publish_common_hour(other, inputs[0], inputs[1], selected, source(inputs), audit(inputs[0]),
            limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1.)


def test_all_arm_business_conditions_are_fixed_in_publication(first):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    with pytest.raises(TypeError):
        tx.advance_arm_hour(before, common.publication, available_flexibility=.125)
    original = common.publication.business_current
    other = tx.publish_common_hour(origin, inputs[0], inputs[1], common.reference_result,
        source(inputs), audit(inputs[0]), limits=original.observation.limits, due_hour=6, available_flexibility=.5)
    assert other.publication.exposure_id != common.publication.exposure_id
    assert other.publication.business_current != original


def test_chunked_arm_execution_matches_whole_prefix(first, monkeypatch):
    inputs, origin, common = first
    info, disclosure = next_hour(common.cursor)
    second = publish(common.cursor, info, disclosure)
    before = arm_origin(inputs, origin)
    publications = (common.publication, second.publication)
    install(monkeypatch, overrides={'generation[G1]': 30., 'selector_deviation[G1]': 10.})
    whole = before
    for publication in publications:
        result = advance(whole, publication)
        assert result.status == 'committed', result.error
        whole = result.cursor
    install(monkeypatch, overrides={'generation[G1]': 30., 'selector_deviation[G1]': 10.})
    chunked = before
    for chunk in ((publications[0],), (publications[1],)):
        for publication in chunk:
            chunked = advance(chunked, publication).cursor
    assert chunked == whole and chunked.identity == whole.identity
    assert len(whole.business.records) == 2
    assert whole.business.execution.tracks[0][1].ledger.debt == Q(2, 3)


def test_initial_actual_policy_change_is_rejected(first):
    inputs, origin, _ = first
    before = arm_origin(inputs, origin)
    with pytest.raises(ValueError, match='policy'):
        tx.initialize_arm_hours(origin, before.business, before.grid,
            selector=replace(SELECTOR, lock_tolerance_mw=1e-8), solver_specification=SPEC, budget=SHORT)


def test_transaction_fresh_import_dependency_closure():
    from pathlib import Path
    import subprocess
    import sys
    import json
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.hourly_transaction
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(tx.SOURCE_DEPENDENCIES) | set(tx.EXTRA_DEPENDENCIES) | set(tx.IMPLEMENTATION) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in (
            'hourly_transaction', 'common_request_adapter', 'reference_grid', 'reference_selector',
            'actual_dispatch_selector', 'current_grid_step', 'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected


def test_recovery_above_connection_limit_rejects_before_native_solver(first, monkeypatch):
    inputs, origin, common = first
    active = advance(arm_origin(inputs, origin), common.publication)
    info, disclosure = next_hour(common.cursor, demand=0., cap=25.)
    second = publish(common.cursor, info, disclosure)
    def forbidden(*a, **kw): raise AssertionError('invalid fixed power must not enter solver')
    monkeypatch.setattr(dispatch, 'select_actual_dispatch', forbidden)
    result = advance(active.cursor, second.publication)
    assert result.status == 'network_input_rejected'
    assert 'physical or connected limit' in result.error
    assert result.prescribed_power.exact_mw > 25
    assert result.business_candidate.records[-1].committed
    assert result.dispatch_result is result.published_pair is None
    assert result.cursor.business == active.cursor.business
    assert result.cursor.grid == active.cursor.grid and result.cursor.halted


def test_reference_unresolved_never_publishes_a_zero_request(monkeypatch):
    from test_rq2_reference_selector_v1 import install as install_reference
    inputs = args()
    before = make_origin(inputs)
    install_reference(monkeypatch, 'timeout', 0)
    attempt = publish(before, inputs[0], inputs[1])
    assert attempt.publication is None and attempt.cursor.halted
    assert attempt.status == 'request_unresolved'
    assert attempt.reference_result.next_reference_state is None
    assert attempt.mapping_result.raw_grid_request_mw is None
    assert attempt.cursor.reference_state == before.reference_state


def test_dispatch_exception_is_not_classified_as_input_rejection(first, monkeypatch):
    inputs, origin, common = first
    before = arm_origin(inputs, origin)
    def failed(*a, **kw):
        raise ValueError('possible native execution before missing result')
    monkeypatch.setattr(dispatch, 'select_actual_dispatch', failed)
    result = advance(before, common.publication)
    assert result.status == 'dispatch_execution_unresolved'
    assert result.prescribed_power.exact_mw == 10
    assert result.dispatch_result is result.published_pair is None
    assert result.cursor.business == before.business and result.cursor.grid == before.grid
    assert result.cursor.halted


@pytest.mark.parametrize('drift', ['contract', 'implementation'])
def test_common_commit_rechecks_implementation_after_adaptation(first, monkeypatch, drift):
    inputs, origin, common = first
    original_identity = origin.identity
    adapt = adapter.adapt_common_request
    def changed(*a, **kw):
        result = adapt(*a, **kw)
        if drift == 'contract':
            monkeypatch.setattr(tx, 'CONTRACT', 'changed')
        else:
            monkeypatch.setattr(tx, '_implementation', lambda: 'f'*64)
        return result
    monkeypatch.setattr(adapter, 'adapt_common_request', changed)
    with pytest.raises(ValueError, match='contract drift|changed during attempt'):
        tx.publish_common_hour(origin, inputs[0], inputs[1], common.reference_result,
            source(inputs), audit(inputs[0]), limits=common.publication.business_current.observation.limits,
            due_hour=5, available_flexibility=1.)
    assert origin.identity == original_identity and origin.last_publication_identity is None
    assert origin.reference_state.physical_origin.source_hour == 0
