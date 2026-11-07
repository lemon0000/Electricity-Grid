"""D-tier action replay: execute a fixed (q, r) command under full temporal physics.

Why this module exists
----------------------
`staged_deliverability_development_v1.advance()` derives q and r internally from the
current observation. The two approximate methods only ever run a *diagnostic* schedule:
`instantaneous` bypasses the event envelope entirely and `fixed_headroom` substitutes a
constant recovery limit for the real device/supply/clean headroom. Neither produces a
plan that can be replayed under the full temporal constraints, so the "method verdict vs.
replayed verdict" comparison D requires does not exist yet.

This module adds exactly that: extract the method's own (q, r) sequence, then execute it
as a *given command* against full temporal physics, recording violations without ever
re-planning the action.

Successor note (v2)
-------------------
`staged_deliverability_replay_v1.py` is unchanged and must stay byte-identical: the D
attempt_01 report pins its SHA-256. This successor fixes exactly one R3 review finding
(`results/tables/staged_deliverability_d_v1_non_authoritative/r3_review.md`, point one):
a supplied `q` larger than the hour's total service request was decomposed into
`grid_served + cfe_served < q`, produced two zero shortfalls, and was then booked in full
as `incurred=q` — silently swallowing the excess. It is now rejected as an illegal
command. Every q that `extract_actions()` can produce satisfies
`q <= grid/slope + green/slope` (it is the sum of the two served terms, each capped by
its own request), so this guard is unreachable on the D grid and leaves every recorded
result byte-identical.

Scope and limits
----------------
- DRAFT_NONAUTHORITATIVE. No solver, no F/X certificate, no formal result.
- The frozen B1 module is imported, never modified; its pinned bytes are untouched.
- Decomposition of a given q back into grid/cfe service follows the same order `advance()`
  uses (grid first, then clean), so the accounting convention is identical, not re-chosen.
- A given r above the full temporal recovery limit is a real violation, not a rounding
  artefact. That single check is the mechanism by which `fixed_headroom` is exposed.
"""
from dataclasses import replace
from fractions import Fraction as Q

from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import advance_debt_ledger
from src.staged_deliverability_development_v1 import (
    METHODS, ZERO, StepRecord, advance, assessment, initialize, power_mapping,
)

REPLAY_VIOLATION_ORDER = (
    "grid_service_shortfall", "cfe_call_shortfall", "device_capacity", "scalar_supply",
    "hourly_cfe", "call_ramp", "event_envelope", "call_energy", "recovery_debt",
    "recovery_headroom",
)
NON_BLOCKING = frozenset({"hourly_cfe", "cfe_call_shortfall"})


def _require_fraction(value, name):
    if not isinstance(value, Q) or value < 0:
        raise ValueError(f"{name} must be a nonnegative Fraction")


def extract_actions(state):
    """Recover the (hour, q, r) command sequence a method actually issued."""
    if state.method not in METHODS:
        raise ValueError("unknown method")
    actions = []
    for record in state.records:
        q = record.grid_served + record.cfe_served
        actions.append((record.observation.hour, q, record.recovery))
    return tuple(actions)


def _full_temporal_recovery_limit(params, state, observation, reference):
    """The limit `advance()` applies to r when method is full_temporal."""
    p, o = params, observation
    limit = min(p.capacity, p.max_recovery, state.ledger.debt / p.eta)
    limit = min(limit, max(o.compute_capacity - o.workload, ZERO),
                max((o.supply_mw - reference) / p.slope, ZERO))
    if p.alpha:
        limit = min(limit, max((o.clean_mwh / p.alpha - reference) / p.slope, ZERO))
    return limit


def replay_step(params, state, observation, q, r):
    """Execute one given (q, r) command under full temporal constraints.

    Mirrors the violation set of `advance()` in full_temporal mode, but the action is
    supplied rather than planned. Returns (new_state, violations).
    """
    _require_fraction(q, "q")
    _require_fraction(r, "r")
    if state.stopped or observation.hour != state.next_hour:
        raise ValueError("stopped or nonconsecutive replay")
    o, p = observation, params

    _, _, reference = power_mapping(p, o)
    grid = max(reference - o.supply_mw, ZERO)
    green = max(reference - o.clean_mwh / p.alpha, ZERO) if p.alpha else ZERO

    # Decompose the given q in advance()'s own order: grid service first, then clean.
    # A command above both requests at once is not a service shortfall; it is an illegal
    # callback amount, so it must not be silently truncated (R3 finding, point one).
    if q > grid / p.slope + green / p.slope:
        raise ValueError("command exceeds the hour's total service request")
    grid_served = min(q, grid / p.slope)
    cfe_served = min(q - grid_served, green / p.slope)

    activity, _, power = power_mapping(p, o, q, r)
    events = state.events + int(q > 0 and state.previous_call == 0)
    duration = state.duration + 1 if q else 0
    energy = state.call_energy + q
    grid_short = grid - p.slope * grid_served
    green_short = green - p.slope * cfe_served
    cfe_short = max(p.alpha * power - o.clean_mwh, ZERO)

    headroom = _full_temporal_recovery_limit(params, state, o, reference)

    violations = []
    for failed, code in (
        (grid_short > 0, "grid_service_shortfall"),
        (green_short > 0, "cfe_call_shortfall"),
        (activity < 0 or activity > o.compute_capacity, "device_capacity"),
        (power > o.supply_mw, "scalar_supply"),
        (cfe_short > 0, "hourly_cfe"),
        (abs(q - state.previous_call) > p.call_ramp, "call_ramp"),
        (events > p.max_events or duration > p.max_duration or
         (q > 0 and not state.previous_call and state.rest < p.minimum_rest), "event_envelope"),
        (energy > p.max_call_energy, "call_energy"),
        (state.ledger.debt + q - p.eta * r > p.max_debt, "recovery_debt"),
        (r > headroom, "recovery_headroom"),
    ):
        if failed:
            violations.append(code)

    blocking = set(violations) - NON_BLOCKING
    committed = not blocking

    ledger = state.ledger
    allocations = []
    if committed and r > 0:
        # Re-derive cohort allocations for the given recovery amount, same rule as advance().
        budget = r * p.eta
        remaining_budget = budget
        for cohort in sorted(state.ledger.cohorts,
                             key=lambda c: (c.due_hour, c.created_hour)):
            effective = min(cohort.remaining, max(remaining_budget, ZERO))
            if effective:
                allocations.append((cohort.created_hour - state.hour_offset, effective))
                remaining_budget -= effective
        if remaining_budget < 0:
            raise ValueError("cumulative allocation exceeded supplied recovery work")
    if committed:
        ledger = advance_debt_ledger(
            ledger, hour=o.hour + state.hour_offset,
            trajectory_identity=state.trajectory_id, accounting_period_id="continuous_case",
            incurred=q, due_hour=o.due + state.hour_offset if q else None,
            deadline_evidence="mechanism_assumption" if q else "unidentified",
            allocations=tuple((birth + state.hour_offset, amount) for birth, amount in allocations),
        )

    from src.staged_deliverability_development_v1 import StepRecord
    record = StepRecord(o, reference, grid, green, grid_served, cfe_served,
                        r, tuple(allocations), activity, power,
                        min(o.clean_mwh, max(power, ZERO)), grid_short,
                        green_short, cfe_short, tuple(violations), committed)

    if not committed:
        return replace(state, records=state.records + (record,), stopped=True), tuple(violations)
    new_state = replace(state, ledger=ledger, records=state.records + (record,),
                        call_energy=energy, previous_call=q, events=events,
                        duration=duration, rest=0 if q else state.rest + 1)
    return new_state, tuple(violations)


def replay_full_temporal(params, observations, actions, trajectory_id="replay"):
    """Replay a fixed command under full temporal physics; never re-plans.

    `actions` may be either the (hour, q, r) triples from `extract_actions()` or a bare
    sequence of (q, r) pairs aligned with `observations`. It may also be a *prefix*: a
    method that stopped early issued fewer actions than the window has hours, and replay
    must mirror that stop rather than invent actions for the unexecuted remainder.
    Hours beyond the supplied command are left unexecuted, so coverage reports honestly.
    """
    if not observations:
        raise ValueError("nonempty observations required")
    if len(actions) > len(observations):
        raise ValueError("action count exceeds observation count")
    state = initialize(params, "full_temporal", trajectory_id, observations[0].hour)
    # Replay is a full_temporal execution of a fixed command, so keep that method label.
    for observation, item in zip(observations, actions):
        if state.stopped:
            break
        if len(item) == 3:
            hour, q, r = item
            if hour != observation.hour:
                raise ValueError("action hour differs from observation hour")
        else:
            q, r = item
        state, _ = replay_step(params, state, observation, q, r)
    return state


LABELS = ("D1_false_pass", "D2_false_reject", "D3_agree_pass",
          "D4_agree_fail", "D5_undetermined")


def label_from(method_verdict, reference_verdict):
    """Map one verdict pair to the shared D label vocabulary.

    `True` means deliverable, `False` means not deliverable, `None` means undetermined
    (right-censored coverage or missing evidence). Undetermined is never folded into
    either side of the comparison.
    """
    for value in (method_verdict, reference_verdict):
        if value is not None and not isinstance(value, bool):
            raise ValueError("verdicts must be bool or None")
    if method_verdict is None or reference_verdict is None:
        return "D5_undetermined"
    if method_verdict and reference_verdict:
        return "D3_agree_pass"
    if method_verdict and not reference_verdict:
        return "D1_false_pass"
    if not method_verdict and reference_verdict:
        return "D2_false_reject"
    return "D4_agree_fail"


def verdicts(method_state, replay_state, registration_end=4, expected_last_hour=7):
    """Two verdicts plus the D-tier label.

    method verdict  = the method's own assessment (unchanged B1 semantics)
    replay verdict  = the same assessment applied to the fixed command's full temporal
                      execution, i.e. "was the method's own arrangement actually viable?"
    """
    if method_state.method not in METHODS:
        raise ValueError("unknown method")
    if replay_state.method != "full_temporal":
        raise ValueError("replay state must be full temporal")
    m = assessment(method_state, registration_end, expected_last_hour)
    r = assessment(replay_state, registration_end, expected_last_hour)
    mv, rv = m["method_conditions_satisfied"], r["method_conditions_satisfied"]
    return dict(method=method_state.method, method_verdict=mv, replay_verdict=rv,
                label=label_from(mv, rv), method_scope=m["scope"], replay_scope=r["scope"],
                method_coverage_complete=m["coverage_complete"],
                replay_coverage_complete=r["coverage_complete"],
                replay_stopped=r["stopped"],
                replay_observed_through=r["observed_through"],
                method_observed_primary_deadline_miss=m["observed_primary_deadline_miss"],
                replay_observed_primary_deadline_miss=r["observed_primary_deadline_miss"],
                replay_violations=r["physical_replay_violations"])


def identity_check(params, observations, method="full_temporal",
                   trajectory_id="identity", registration_end=4, expected_last_hour=7):
    """Contract P4: replaying a method's own actions must reproduce its own record.

    Only meaningful for full_temporal, where the method already plans under full physics.
    """
    native = initialize(params, method, trajectory_id, observations[0].hour)
    native = advance_all(params, native, observations)
    replay = replay_full_temporal(params, observations, extract_actions(native),
                                  trajectory_id=trajectory_id + "_replay")
    same_records = native.records == replay.records
    same_stop = native.stopped == replay.stopped
    n = assessment(native, registration_end, expected_last_hour)
    r = assessment(replay, registration_end, expected_last_hour)
    return dict(records_identical=same_records, stop_identical=same_stop,
                verdict_identical=n["method_conditions_satisfied"] == r["method_conditions_satisfied"],
                native_verdict=n["method_conditions_satisfied"],
                replay_verdict=r["method_conditions_satisfied"],
                hour_count=len(observations))


def advance_all(params, state, observations):
    for observation in observations:
        if state.stopped:
            break
        state = advance(params, state, observation)
    return state
