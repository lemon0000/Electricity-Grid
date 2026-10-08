"""Exact, non-authoritative accounting of explicit recovery-debt allocations.

This ledger consumes effective work-energy, not power, and does not choose a
policy or certify power/headroom feasibility. Unknown deadlines remain unknown.
"""

from dataclasses import dataclass, replace
from fractions import Fraction


def _hour(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("hour must be a nonnegative integer")


def _energy(value: Fraction) -> None:
    if not isinstance(value, Fraction) or value < 0:
        raise ValueError("energy must be a nonnegative exact Fraction")


@dataclass(frozen=True)
class DebtCohort:
    created_hour: int
    due_hour: int | None
    deadline_evidence: str
    incurred: Fraction
    remaining: Fraction
    missed_at_deadline: Fraction | None = None

    def __post_init__(self) -> None:
        _hour(self.created_hour)
        if self.due_hour is None:
            if self.deadline_evidence != "unidentified":
                raise ValueError("missing deadline must remain unidentified")
        else:
            _hour(self.due_hour)
            if self.due_hour < self.created_hour:
                raise ValueError("deadline precedes debt creation")
            if self.deadline_evidence != "mechanism_assumption":
                raise ValueError("this draft supports only assumed known deadlines")
        _energy(self.incurred)
        _energy(self.remaining)
        if self.incurred <= 0 or self.remaining > self.incurred:
            raise ValueError("invalid cohort balance")
        if self.missed_at_deadline is not None:
            _energy(self.missed_at_deadline)
            if self.due_hour is None or self.missed_at_deadline > self.incurred:
                raise ValueError("invalid deadline observation")


@dataclass(frozen=True)
class DebtLedger:
    trajectory_identity: str
    accounting_period_id: str
    last_hour: int
    cohorts: tuple[DebtCohort, ...] = ()

    def __post_init__(self) -> None:
        _hour(self.last_hour)
        if any(not isinstance(v, str) or not v for v in (
            self.trajectory_identity, self.accounting_period_id,
        )):
            raise ValueError("explicit trajectory and accounting period required")
        if not isinstance(self.cohorts, tuple):
            raise ValueError("cohorts must be immutable")
        ids = [c.created_hour for c in self.cohorts]
        if ids != sorted(set(ids)):
            raise ValueError("cohort hours must be unique and ordered")
        for c in self.cohorts:
            if c.created_hour > self.last_hour:
                raise ValueError("future debt cannot be carried")
            due_observed = c.due_hour is not None and c.due_hour <= self.last_hour
            if due_observed != (c.missed_at_deadline is not None):
                raise ValueError("deadline observation history must be complete")
            if due_observed and c.remaining > c.missed_at_deadline:
                raise ValueError("remaining debt exceeds historical deadline shortfall")
            if c.due_hour == self.last_hour and c.remaining != c.missed_at_deadline:
                raise ValueError("due-hour snapshot must equal current remaining debt")

    @property
    def debt(self) -> Fraction:
        return sum((c.remaining for c in self.cohorts), Fraction(0))


def advance_debt_ledger(
    ledger: DebtLedger, *, hour: int, trajectory_identity: str,
    accounting_period_id: str, incurred: Fraction,
    due_hour: int | None, deadline_evidence: str,
    allocations: tuple[tuple[int, Fraction], ...] = (),
) -> DebtLedger:
    """Accrue, apply explicit recovery, then audit deadlines at the hour end.

    Allocations are effective recovered work (eta * recovery_power * dt).
    No deadline is inferred, no overdue balance is discarded, and each due-time
    shortfall is recorded once, even if the cohort is repaid later.
    """
    _hour(hour)
    _energy(incurred)
    if hour != ledger.last_hour + 1:
        raise ValueError("observed hours must be consecutive")
    if trajectory_identity != ledger.trajectory_identity:
        raise ValueError("trajectory identity drift")
    if accounting_period_id != ledger.accounting_period_id:
        raise ValueError("accounting period reset forbidden")
    if not isinstance(allocations, tuple):
        raise ValueError("allocations must be an explicit immutable tuple")
    if incurred == 0 and (due_hour is not None or deadline_evidence != "unidentified"):
        raise ValueError("deadline metadata without new debt")
    cohorts = list(ledger.cohorts)
    if incurred:
        cohorts.append(DebtCohort(hour, due_hour, deadline_evidence, incurred, incurred))
    by_id = {c.created_hour: i for i, c in enumerate(cohorts)}
    seen = set()
    recovered = Fraction(0)
    for cohort_id, amount in allocations:
        _hour(cohort_id)
        _energy(amount)
        if cohort_id in seen or cohort_id not in by_id:
            raise ValueError("duplicate or unknown recovery cohort")
        seen.add(cohort_id)
        i = by_id[cohort_id]
        if amount > cohorts[i].remaining:
            raise ValueError("recovery exceeds cohort debt")
        cohorts[i] = replace(cohorts[i], remaining=cohorts[i].remaining - amount)
        recovered += amount
    if incurred and recovered:
        raise ValueError("active call and recovery cannot coincide")
    for i, c in enumerate(cohorts):
        if c.due_hour == hour:
            cohorts[i] = replace(c, missed_at_deadline=c.remaining)
    result = DebtLedger(ledger.trajectory_identity, ledger.accounting_period_id,
                        hour, tuple(cohorts))
    if result.debt != ledger.debt + incurred - recovered:
        raise ArithmeticError("cohort debt conservation failed")
    return result


def assess_debt_cohorts(ledger: DebtLedger) -> tuple[tuple[int, str], ...]:
    """Assess observed cohorts only; never infer completion of a service horizon."""
    result = []
    for c in ledger.cohorts:
        if c.due_hour is None:
            status = "deadline_unidentified"
        elif c.missed_at_deadline is not None and c.missed_at_deadline > 0:
            status = "deadline_missed"  # Persists after late recovery.
        elif c.remaining == 0:
            status = "recovered_by_deadline"
        else:
            status = "right_censored_before_deadline"
        result.append((c.created_hour, status))
    return tuple(result)
