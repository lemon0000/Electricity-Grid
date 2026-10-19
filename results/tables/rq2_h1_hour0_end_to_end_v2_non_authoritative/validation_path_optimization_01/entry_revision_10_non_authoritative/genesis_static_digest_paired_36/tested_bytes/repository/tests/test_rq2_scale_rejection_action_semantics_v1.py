"""Cross-layer rejection evidence, using tiny synthetic selector archives."""
from dataclasses import replace
from fractions import Fraction as Q
from types import SimpleNamespace

import pytest
from pyomo.opt import TerminationCondition

from test_rq2_scale_hourly_transaction_v1 import (
    request, execute, source, mapping, audit, obs, arm, ACT, SPEC, tx,
)
from test_rq2_hourly_transaction_v1 import next_hour
from test_rq2_actual_dispatch_selector_v1 import install


def first_publication(tmp_path, cfe=0., due=5):
    req = request()
    inputs = (req.info, req.disclosure, req.before)
    data, pins = execute(tmp_path/'reference_non_authoritative', req)
    hour = replace(source(inputs, '45'), cfe_request=cfe)
    pub = tx.publish_common_record(data, req, hour, mapping('45'), audit(req.info),
        limits=obs(1, g=0., c=0., due=None).limits, due_hour=due,
        available_flexibility=1., **pins)
    return req, pub


def timeout_archive(root, req, monkeypatch):
    mw = float(req.power.exact_mw)
    demand = sum(value for _, value in req.info.current.demand_by_bus_mw)
    generation = demand+mw
    planned = dict(req.info.normal.generation_mw)['G1']
    calls = install(monkeypatch, 'timeout', 1, overrides={
        'generation[G1]': generation, 'selector_deviation[G1]': abs(planned-generation)})
    original = tx.replay.store.selector.select_hour
    observed = []
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        observed.append(result)
        return result
    monkeypatch.setattr(tx.replay.store.selector, 'select_hour', capture)
    archive = execute(root, req)
    assert calls == {'create': 2, 'solve': 2}
    assert len(observed) == 1
    stages = observed[0].stages
    assert len(stages) == 2 and stages[0].accepted and not stages[1].accepted
    assert stages[1].raw_solve.assignment_valid and not stages[1].raw_solve.optimal
    assert not stages[1].raw_solve.native_infeasible
    raw = stages[1].raw_solve
    assert raw.errors == ()
    assert raw.maximum_residual <= 1e-6 and raw.maximum_integrality_violation <= 1e-6
    assert stages[1].errors == ('dispatch_stage_requires_owned_optimal_assignment',)
    assert stages[1].assignment_witness.physical_assignment_valid
    assert raw.solver_records[0][1] == tx.replay.scale.native._enum(TerminationCondition.maxTimeLimit)
    return archive


@pytest.mark.parametrize('arm_id', [tx.JOINT, tx.B6])
@pytest.mark.parametrize('timeout', [False, True])
def test_partial_cfe_response_is_executed_only_after_grid_commit(tmp_path, monkeypatch, arm_id, timeout):
    req, pub = first_publication(tmp_path, cfe=.25)
    before, budget = arm(req, pub, arm_id, capacity=.4)
    pending = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=budget)
    response = pending.business_candidate.records[-1].response
    # Original requests exceed baseline; only actual deferred work creates debt.
    assert pub.current.observation.hour.grid_request == Q(1, 3)
    assert pub.current.observation.hour.cfe_request == .25
    assert Q(1, 3)+Q(1, 4) > Q(5, 9)
    assert response.grid_shortfall == 0
    assert response.cfe_shortfall == Q(11, 60)
    assert response.cfe_service_failure is True
    assert pending.business_candidate.execution.tracks[0][1].ledger.debt == Q(2, 5)
    assert pending.dispatch_request.power.exact_mw == 7
    if timeout:
        data, pins = timeout_archive(tmp_path/'actual_non_authoritative', pending.dispatch_request, monkeypatch)
    else:
        data, pins = execute(tmp_path/'actual_non_authoritative', pending.dispatch_request)
    result = tx.finish_arm(pending, data, **pins)
    if timeout:
        assert result['status'] == 'physical_network_unresolved'
        assert result['published_pair'] is None
        assert result['cursor'].business == before.business
        assert result['cursor'].grid == before.grid
        assert result['cursor'].last_publication_identity is None
        assert result['grid_service_failure'] is None
        with pytest.raises(ValueError, match='active matching'):
            tx.prepare_arm(result['cursor'], pub, selector=ACT, solver_specification=SPEC, budget=budget)
    else:
        assert result['status'] == 'committed'
        assert result['cursor'].business.records[-1].response.cfe_service_failure is True
        assert result['cursor'].business.execution.tracks[0][1].ledger.debt == Q(2, 5)
        assert result['grid_service_failure'] is False
        assert result['cursor'].grid.physical_carry.generation_mw == (('G1', 27.),)
    assert result['formal_result'] is result['security_certified'] is False


@pytest.mark.parametrize('timeout', [False, True])
def test_due_hour_candidate_recovery_and_miss_require_grid_commit(tmp_path, monkeypatch, timeout):
    req, first = first_publication(tmp_path, due=2)
    before, budget = arm(req, first, tx.JOINT)
    pending = tx.prepare_arm(before, first, selector=ACT, solver_specification=SPEC, budget=budget)
    data, pins = execute(tmp_path/'first_actual_non_authoritative', pending.dispatch_request)
    active = tx.finish_arm(pending, data, **pins)['cursor']
    prior_ledger = active.business.execution.tracks[0][1].ledger
    assert prior_ledger.debt == Q(1, 3)
    assert prior_ledger.cohorts[0].missed_at_deadline is None
    info, disclosure = next_hour(SimpleNamespace(reference_state=first.reference_result.next_state),
        demand=0., cap=30.)
    inputs = (info, disclosure, first.reference_result.next_state)
    req2 = replace(req, info=info, disclosure=disclosure, before=inputs[2],
        budget=replace(req.budget, source_hour=2),
        expected_identity=tx.replay.scale.reference.reference_input_identity(*inputs))
    data, pins = execute(tmp_path/'second_reference_non_authoritative', req2)
    hour = replace(source(inputs, '45'), power_source_hour=2, workload_source_hour=102)
    limits = replace(first.current.observation.limits, business_recovery_headroom=Q(1, 45),
        cfe_compatible_surplus=Q(1, 45), maximum_recovery_power=Q(1, 45))
    second = tx.publish_common_record(data, req2, hour, first.mapping, audit(info), previous=first,
        limits=limits, due_hour=None, available_flexibility=1., **pins)
    pending = tx.prepare_arm(active, second, selector=ACT, solver_specification=SPEC,
        budget=replace(budget, source_hour=2))
    candidate_ledger = pending.business_candidate.execution.tracks[0][1].ledger
    assert 0 < candidate_ledger.debt < prior_ledger.debt
    assert candidate_ledger.cohorts[0].missed_at_deadline == candidate_ledger.debt
    assert candidate_ledger.last_hour == 2
    if timeout:
        data, pins = timeout_archive(tmp_path/'second_actual_non_authoritative', pending.dispatch_request, monkeypatch)
    else:
        data, pins = execute(tmp_path/'second_actual_non_authoritative', pending.dispatch_request)
    result = tx.finish_arm(pending, data, **pins)
    if timeout:
        assert result['status'] == 'physical_network_unresolved'
        assert result['published_pair'] is None and result['cursor'].halted
        assert result['cursor'].business == active.business
        assert result['cursor'].grid == active.grid
        assert result['cursor'].business.execution.tracks[0][1].ledger == prior_ledger
        assert result['cursor'].last_publication_identity == first.identity
        assert result['grid_service_failure'] is None
        assert result['cursor'].business.execution.tracks[0][1].ledger.cohorts[0].missed_at_deadline is None
    else:
        assert result['status'] == 'committed'
        assert result['cursor'].business.execution.tracks[0][1].ledger == candidate_ledger
        assert result['cursor'].grid.physical_carry.source_hour == 2
    # A candidate miss is retained for diagnosis even when neither state advances.
    assert result['business_candidate'].execution.tracks[0][1].ledger == candidate_ledger
    assert prior_ledger.last_hour == 1 and prior_ledger.cohorts[0].missed_at_deadline is None
