"""Real grouped scopes with explicit fake context/numerical/lease interfaces.

These counts establish the twenty-two-common state machine, not saved source,
live Parent admission, complete Handoff or native execution.
"""
import json

import pytest

from tests import test_h1_group_operation_witness_development_v2 as prior
from experiments import h1_operation_historical_witness_development_v3 as original


@pytest.fixture
def case(tmp_path, monkeypatch, request):
    fresh = prior.fresh
    monkeypatch.setattr(prior, 'original', original)
    names = dict(h1_operation_historical_witness_development_v2='h1_operation_historical_witness_development_v3',
        h1_phase_exact_source_current_development_v3='h1_phase_exact_source_current_development_v4',
        h1_group_n0_common_input_binding_development_v3='h1_group_n0_common_input_binding_development_v4')
    def successor(patch, name):
        if name == 'h1_operation_historical_witness_development_v2':
            # The inherited explicit lease fixture supplies no live authority.
            bridge = original.operation_bridge
            verify = bridge._VERIFY_LEASE
            def twenty_two(lease):
                roster, declarations, _ = verify(lease)
                return roster, declarations, 22
            patch.setattr(bridge, '_VERIFY_LEASE', twenty_two)
        return fresh(patch, names[name])
    monkeypatch.setattr(prior, 'fresh', successor)
    yield from prior.case.__wrapped__(tmp_path, monkeypatch, request)


def complete(case, *, fail_arm=None, fail_round=1):
    session, m = case.session, case.m
    try:
        ticket = session._start_common()
        for round_ in range(2):
            for arm, _ in session._original_arms:
                owner = session._arm(arm, ticket)
                prior.arm_prepare(case, owner,
                    fail_prefix=1 if (arm, round_) == (fail_arm, fail_round) else None)
                if session._common_calls == 0:
                    assert not session._reuse_active
        payload = m.io.encode(dict(explicit_fake_counter_science=True))
        result = case.source.normal._owned(case.common.PreparedCommonInput,
            manifest=None, source_binding=None, predecessor_report_payload=b'{}',
            validation_report_payload=payload, execution_receipt=session._execution(ticket, payload),
            _session_nonce=session._nonce)
        session._finish_common(ticket, result)
        return result
    except BaseException as error:
        session._poison(error)
        raise


def test_exact_twenty_two_common_counts_first_full_and_twenty_one_reuses(case):
    for ordinal in range(1, 23):
        result = complete(case)
        row = json.loads(result.execution_receipt)
        assert row['common_call'] == ordinal
        assert tuple(row[key] for key in ('full_numerical_hour_replays',
            'within_prefix_revalidations', 'cross_common_numerical_proof_reuses')) == (
                (24, 24, 0) if ordinal == 1 else (0, 0, 48))
        assert len(case.calls) == 24
        assert len(case.contexts) == ordinal * 96
    case.session.close()
    receipt = case.session.receipt()
    assert receipt['complete'] and receipt['common_calls'] == 22
    assert all(row['proof_cleared'] for row in receipt['arm_receipts'].values())
    assert sum(row['cross_common_numerical_proof_reuses'] for row in receipt['common_executions']) == 1008


@pytest.mark.parametrize('arm', ['cfe-only', 'joint-correct', 'network-only'])
@pytest.mark.parametrize('round_', [0, 1])
def test_incomplete_first_common_never_activates_any_reuse(case, arm, round_):
    with pytest.raises(RuntimeError, match='prefix failure'):
        complete(case, fail_arm=arm, fail_round=round_)
    assert not case.session._reuse_active and case.session._failure
    assert all(owner._proof is None for owner in case.session._arms.values())
    with pytest.raises(ValueError):
        case.session._start_common()


@pytest.mark.parametrize('fault', ['arm_swap', 'proof_swap', 'closed_lease', 'project_drift'])
def test_cross_common_freshness_and_ownership_change_poison_all_proofs(case, fault):
    complete(case)
    session = case.session
    left, right = list(session._arms.values())[:2]
    if fault == 'arm_swap':
        session._arms = dict(reversed(list(session._arms.items())))
    elif fault == 'proof_swap':
        left._proof = right._proof
    elif fault == 'closed_lease':
        case.lease_state[0] = False
    else:
        case.dispatch[0] = ('changed',)
    with pytest.raises(ValueError):
        complete(case)
    assert session._failure and not session._reuse_active
    assert all(owner._proof is None for owner in session._arms.values())
