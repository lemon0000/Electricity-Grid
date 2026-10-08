from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import (
    DebtCohort, DebtLedger, advance_debt_ledger, assess_debt_cohorts,
)
from src.rq2_joint_deliverability_boundary_v1.boundary import (
    TemporalCarryState, advance_continuous_state,
)

ROOT = Path(__file__).resolve().parents[1]


def step(ledger, incurred='0', due=None, allocations=(), **changes):
    args = dict(hour=ledger.last_hour+1, trajectory_identity=ledger.trajectory_identity,
                accounting_period_id=ledger.accounting_period_id, incurred=Q(incurred),
                due_hour=due, deadline_evidence='unidentified' if due is None else 'mechanism_assumption',
                allocations=tuple((i, Q(v)) for i, v in allocations))
    args.update(changes)
    return advance_debt_ledger(ledger, **args)


def empty(hour=22):
    return DebtLedger('synthetic-training-chain', 'single-period', hour)


def test_fixture_cross_day_matches_aggregate_replay_and_analytic_oracle():
    cfg = yaml.safe_load((ROOT/'configs/rq2_continuous_debt_cohorts_v1.DRAFT.yaml').read_text(encoding='utf-8'))
    fixture = cfg['synthetic_fixture']
    old = yaml.safe_load((ROOT/'configs/rq2_continuous_multiday_service_v1.DRAFT.yaml').read_text(encoding='utf-8'))
    ledger = DebtLedger(fixture['trajectory_identity'], fixture['accounting_period_id'],
                        fixture['first_observed_hour']-1)
    aggregate = TemporalCarryState('joint_correct_shared', 'shared', 0., False, 0., None,
                                  0, 0., 0., False, fixture['accounting_period_id'])
    expected = [Q(1,4), Q(1,2), Q(3,4), Q(1,2), Q(1,4), Q(0)]
    assert len(fixture['actions']) == len(expected)
    history = []
    for row, debt in zip(fixture['actions'], expected):
        ledger = step(ledger, row['incurred'], row['due_hour'], row['allocations'], hour=row['hour'])
        recovered = sum((Q(amount) for _, amount in row['allocations']), Q(0))
        aggregate = advance_continuous_state(
            aggregate, call=float(Q(row['incurred'])), recovery=float(recovered/Q(fixture['eta'])),
            call_limit=.5, recovery_headroom=.5, maximum_recovery_power=.5,
            **old['synthetic_fixture']['envelope'])
        assert ledger.debt == debt
        assert float(ledger.debt) == aggregate.recovery_debt
        history.append(ledger)
    assert history[1].debt == Q(1,2)  # End hour 24: retained, no day reset.
    assert ledger.last_hour == fixture['last_observed_hour']
    assert all(status == 'recovered_by_deadline' for _, status in assess_debt_cohorts(ledger))
    # Chunking is only loop partitioning; the entire immutable ledger is carried.
    cursor = empty()
    for chunk in [fixture['actions'][:2], fixture['actions'][2:]]:
        for row in chunk:
            cursor = step(cursor, row['incurred'], row['due_hour'], row['allocations'])
    assert cursor.cohorts == ledger.cohorts


def test_late_recovery_keeps_deadline_violation_and_no_double_count():
    ledger = step(empty(), '.5', 24)
    ledger = step(ledger, allocations=((23, '.25'),))
    assert ledger.cohorts[0].missed_at_deadline == Q(1,4)
    assert assess_debt_cohorts(ledger) == ((23, 'deadline_missed'),)
    ledger = step(ledger, allocations=((23, '.25'),))
    for _ in range(24):
        ledger = step(ledger)
    assert ledger.debt == 0
    assert ledger.cohorts[0].missed_at_deadline == Q(1,4)
    assert assess_debt_cohorts(ledger) == ((23, 'deadline_missed'),)


def test_end_before_due_is_censored_but_exact_due_with_residual_is_missed():
    ledger = step(empty(), '.25', 25)
    assert assess_debt_cohorts(ledger) == ((23, 'right_censored_before_deadline'),)
    ledger = step(step(ledger))
    assert assess_debt_cohorts(ledger) == ((23, 'deadline_missed'),)


def test_unknown_deadline_remains_unknown_after_full_recovery():
    ledger = step(empty(), '.25')
    assert assess_debt_cohorts(ledger) == ((23, 'deadline_unidentified'),)
    ledger = step(ledger, allocations=((23, '.25'),))
    assert ledger.debt == 0
    assert assess_debt_cohorts(ledger) == ((23, 'deadline_unidentified'),)


def test_cohort_allocations_matter_even_when_aggregate_debt_matches():
    ledger = step(empty(), '.25', 25)
    ledger = step(ledger, '.25', 27)
    early = step(ledger, allocations=((23, '.25'),))
    late = step(ledger, allocations=((24, '.25'),))
    assert early.debt == late.debt == Q(1,4)
    assert assess_debt_cohorts(early)[0][1] == 'recovered_by_deadline'
    assert assess_debt_cohorts(late)[0][1] == 'deadline_missed'


@pytest.mark.parametrize('changes,error', [
    ({'hour': 25}, 'consecutive'),
    ({'trajectory_identity': 'holdout-other-chain'}, 'identity drift'),
    ({'accounting_period_id': 'next-day'}, 'reset'),
    ({'allocations': ((23, Q(1)),)}, 'exceeds'),
    ({'allocations': ((25, Q(1,4)),)}, 'unknown'),
    ({'allocations': ((23, Q(1,8)), (23, Q(1,8)))}, 'duplicate'),
])
def test_reject_invalid_transitions(changes, error):
    ledger = step(empty(), '.25', 26)
    with pytest.raises(ValueError, match=error):
        step(ledger, **changes)


@pytest.mark.parametrize('value', [float('nan'), .25, True, Q(-1)])
def test_public_api_rejects_inexact_or_invalid_energy(value):
    with pytest.raises(ValueError, match='exact Fraction'):
        advance_debt_ledger(empty(), hour=23, trajectory_identity='synthetic-training-chain',
                            accounting_period_id='single-period', incurred=value,
                            due_hour=None, deadline_evidence='unidentified')


def test_no_simultaneous_call_and_recovery_or_future_debt_borrowing():
    with pytest.raises(ValueError, match='unknown'):
        step(empty(), allocations=((23, '.25'),))
    ledger = step(empty(), '.25', 26)
    with pytest.raises(ValueError, match='cannot coincide'):
        step(ledger, '.25', 27, ((23, '.25'),))


@pytest.mark.parametrize('due,evidence,error', [
    (22, 'mechanism_assumption', 'precedes'),
    (24, 'observed', 'assumed'),
    (None, 'mechanism_assumption', 'unidentified'),
])
def test_deadline_provenance_is_not_invented(due, evidence, error):
    with pytest.raises(ValueError, match=error):
        step(empty(), '.25', due, deadline_evidence=evidence)


def test_partial_history_and_changed_deadline_are_not_supported():
    c = DebtCohort(23, 24, 'mechanism_assumption', Q(1,4), Q(1,4))
    with pytest.raises(ValueError, match='history'):
        DebtLedger('chain', 'period', 25, (c,))
    with pytest.raises(ValueError, match='historical'):
        DebtLedger('chain', 'period', 25, (replace(c, missed_at_deadline=Q(0)),))
    ledger = step(empty(), '.25', 26)
    with pytest.raises(TypeError):
        step(ledger, replace_existing_deadline=48)


def test_due_hour_snapshot_equals_current_balance_but_late_recovery_can_reduce_it():
    c = DebtCohort(23, 24, 'mechanism_assumption', Q(1,2), Q(1,4), Q(1,2))
    with pytest.raises(ValueError, match='snapshot must equal'):
        DebtLedger('chain', 'period', 24, (c,))
    late = DebtLedger('chain', 'period', 25, (c,))
    assert late.debt == Q(1,4)
    assert assess_debt_cohorts(late) == ((23, 'deadline_missed'),)


def test_exact_arithmetic_retains_small_debt_instead_of_dropping_it():
    ledger = step(empty(), '0.00000000000000000001', 24)
    ledger = step(ledger)
    assert ledger.debt == Q('0.00000000000000000001')
    assert ledger.cohorts[0].missed_at_deadline == ledger.debt
