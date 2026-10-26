"""Selective-query successor; reuse v1 policy, types and scientific outputs."""
from dataclasses import replace
import json

from src import staged_rts24_development_v1 as c
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import advance_debt_ledger, assess_debt_cohorts
from src.staged_rts24_audit_v1 import audit_point, TOL_MW
from src.staged_rts24_reference_queries_v1 import reference_requests
from src.staged_rts24_causal_v1 import (
    PointEvidence, HourEvidence, ExecutionState, PreparedHour, Proposal, ZERO,
    initialize_execution, propose_hour, reported_quantity, _root, _child,
)


def audit_execution_context(fixture, state):
    c.require((state.fixture_identity, state.parameters, state.first_hour, state.registration_end, state.observation_end) ==
              (fixture.source_identity, fixture.parameters, fixture.first_hour, fixture.registration_end, fixture.observation_end),
              "execution context or horizon changed")
    identity = c.digest(dict(fixture=fixture.source_identity, plan=state.plan, clean=state.clean_path, method=state.method,
        first_hour=fixture.first_hour, registration_end=fixture.registration_end, observation_end=fixture.observation_end, parameters=fixture.parameters))
    c.require(state.trajectory_identity == state.ledger.trajectory_identity == identity
              and state.ledger.accounting_period_id == "continuous_case", "execution trajectory identity changed")
    from src.staged_rts24_causal_audit_v2 import audit_execution
    return audit_execution(fixture, state)


def prepare_hour(fixture, state, evidence):
    c.require(not state.stopped, "stopped execution")
    audit_execution_context(fixture, state)
    h = reference_requests(fixture, state.plan, state.clean_path, state.method, state.next_hour)
    c.require(h["reference_connection_shortfall_mw"] == 0, "reference_connection_shortfall")
    c.require(isinstance(evidence, HourEvidence), "complete hour evidence required")
    roles = {r.role: r for r in h["requests"] if not r.role.startswith("fault_")}
    _root(evidence.reference, roles["reference_base_P0"])
    if "reference_raw_need" in roles:
        _child(evidence.raw, roles["reference_raw_need"], evidence.reference)
        grid = reported_quantity(evidence.raw.point.curtailment_mw)
    else:
        c.require(evidence.raw is None, "unexpected raw evidence in healthy state")
        grid = ZERO
    lower = upper = None
    if state.method != "instantaneous":
        _child(evidence.lower, roles["recovery_min_meter"], evidence.reference)
        _child(evidence.upper, roles["recovery_max_meter"], evidence.reference)
        lower, upper = reported_quantity(evidence.lower.point.meter_load_mw), reported_quantity(evidence.upper.point.meter_load_mw)
        c.require(lower <= upper, "reversed numeric recovery endpoints")
    else:
        c.require(evidence.lower is None and evidence.upper is None, "instantaneous method has no recovery endpoint queries")
    x = json.loads(fixture.x_envelope_json)
    active = min(h["conditional"], max(h["reference_mw"]-h["firm"], ZERO))
    legal = min(active, c.quantity(x["max_call_mw"]), max(c.quantity(x["max_energy_mwh"])-state.x_energy, ZERO),
                state.x_previous+c.quantity(x["max_ramp_mw_per_hour"]))
    if state.x_duration >= x["max_duration_hours"] or (not state.x_previous and
            (state.x_events >= x["max_events"] or state.x_rest < x["minimum_rest_hours"])):
        legal = ZERO
    c.require(grid <= legal, "raw_request_exceeds_legal_X")
    return PreparedHour(c.digest(state), h["observation"], evidence, h["reference_mw"], grid, h["firm"], h["conditional"],
                        legal, lower, upper, h["actual_outage"], fixture.x_envelope_json)


def accept_hour(fixture, state, prepared, proposal, actual=None):
    """Apply the true ledger only after actual audit; approximations stay hypothetical."""
    c.require(prepared == prepare_hour(fixture, state, prepared.evidence), "prepared evidence or inputs differ")
    c.require(proposal == propose_hour(state, prepared), "proposal differs from causal policy")
    reference = prepared.evidence.reference
    expected = replace(reference.query.request, role="actual_P", meter_min=proposal.power_mw, meter_max=proposal.power_mw,
                       outages=prepared.actual_outage, anchor_id=reference.query.request.identity)
    excluded = any(code.startswith("network_projection_") or code == "connection_capacity" for code in proposal.violations)
    actual_audit = None
    if actual is None:
        c.require(excluded, "missing_actual_point_evidence")
    else:
        c.require(isinstance(actual, PointEvidence) and actual.query.request == expected and actual.economic is None and actual.child_lp is None
                  and actual.query.base_query == reference.query and actual.query.base_point == reference.point
                  and actual.query.base_economic == reference.economic, "actual evidence binding differs")
        c.require(abs(actual.point.meter_load_mw-float(proposal.power_mw)) <= TOL_MW and actual.point.curtailment_mw == 0., "actual meter or curtailment differs")
        actual_audit = audit_point(actual.query, actual.point)
    violations = list(proposal.violations)
    if actual_audit is not None and not actual_audit["point_constraints_satisfied"]: violations.append("actual_network_point")
    blocking = set(violations)-{"hourly_cfe", "cfe_call_shortfall"}
    accepted = state.method == "full_temporal" and not blocking
    applied = accepted or state.method != "full_temporal"
    ledger = state.ledger
    if applied:
        ledger = advance_debt_ledger(ledger, hour=prepared.observation.hour+state.hour_offset,
            trajectory_identity=state.trajectory_identity, accounting_period_id="continuous_case", incurred=proposal.deferred,
            due_hour=prepared.observation.due+state.hour_offset if proposal.deferred else None,
            deadline_evidence="mechanism_assumption" if proposal.deferred else "unidentified",
            allocations=tuple((birth+state.hour_offset, amount) for birth, amount in proposal.allocations))
    row = dict(prepared=prepared, proposal=proposal, actual=actual, actual_audit=actual_audit, violations=tuple(violations),
        proposal_ledger_applied=applied, actual_accepted=accepted,
        full_replay_conditions_satisfied=not violations,
        ledger_scope="accepted_static_dc_policy_execution" if state.method == "full_temporal" else "hypothetical_approximation",
        fx_contract_status="not_evaluated_by_actual_path_step")
    if not applied: return replace(state, records=state.records+(row,), stopped=True)
    q, xcall = proposal.deferred, state.parameters.slope*proposal.grid_deferred
    return replace(state, ledger=ledger, records=state.records+(row,), call_energy=state.call_energy+q,
        previous_call=q, events=state.events+int(q > 0 and state.previous_call == 0), duration=state.duration+1 if q else 0,
        rest=0 if q else state.rest+1, x_previous=xcall, x_energy=state.x_energy+xcall,
        x_events=state.x_events+int(xcall > 0 and state.x_previous == 0), x_duration=state.x_duration+1 if xcall else 0,
        x_rest=0 if xcall else state.x_rest+1)


def execution_summary(fixture, state):
    audit_execution_context(fixture, state)
    registration_end, observation_end = fixture.registration_end, fixture.observation_end
    cohorts = {row.created_hour-state.hour_offset: row for row in state.ledger.cohorts}
    statuses = dict(assess_debt_cohorts(state.ledger))
    tasks = []
    for row in state.records:
        if not row["proposal_ledger_applied"]: continue
        o, p = row["prepared"].observation, row["proposal"]
        cohort = cohorts.get(o.hour)
        remaining = cohort.remaining if cohort else ZERO
        tasks.append(dict(birth=o.hour, due=o.due, original=o.workload, immediate=o.workload-p.deferred,
            recovered=p.deferred-remaining, remaining=remaining, deadline_miss=cohort.missed_at_deadline if cohort else ZERO,
            status=statuses[cohort.created_hour] if cohort else "completed_on_arrival"))
    primary = [row for row in tasks if 0 <= row["birth"] < registration_end]
    missed = sum((row["deadline_miss"] or ZERO for row in primary), ZERO)
    censored = any(row["status"] == "right_censored_before_deadline" for row in primary)
    complete = not state.stopped and state.next_hour >= observation_end
    instant = {"grid_service_shortfall", "cfe_call_shortfall", "device_capacity", "connection_capacity", "actual_network_point", "hourly_cfe", "shared_flexibility"}
    recovery_omissions = {"device_capacity", "connection_capacity", "network_projection_lower", "network_projection_upper", "actual_network_point", "hourly_cfe"}
    relevant_by_hour = tuple((row["prepared"].observation.hour, tuple(code for code in row["violations"]
        if not (state.method == "fixed_headroom" and row["proposal"].recovery and code in recovery_omissions)
        and (state.method != "instantaneous" or code in instant))) for row in state.records)
    relevant_by_hour = tuple((hour, codes) for hour, codes in relevant_by_hour if codes)
    relevant = tuple(code for _, codes in relevant_by_hour for code in codes)
    method_ok = not relevant and not state.stopped and (state.method == "instantaneous" or not missed)
    if method_ok and (not complete or (censored and state.method != "instantaneous")): method_ok = None
    replay_ok = not any(row["violations"] for row in state.records) and not missed and not state.stopped
    if replay_ok and (not complete or censored): replay_ok = None
    return dict(method=state.method, method_conditions_satisfied=method_ok, full_replay_conditions_satisfied=replay_ok,
        coverage_complete=complete, policy_applied_through=state.next_hour-1, observed_primary_deadline_miss=missed,
        primary_right_censored=censored, remaining_debt=state.ledger.debt, tasks=tuple(tasks),
        stopped=state.stopped, attempted_through=state.records[-1]["prepared"].observation.hour if state.records else state.first_hour-1,
        accepted_through=state.next_hour-1 if state.method == "full_temporal" else None,
        physical_replay_violations=tuple((row["prepared"].observation.hour, row["violations"]) for row in state.records if row["violations"]),
        method_relevant_violations=relevant_by_hour,
        terminal_violations=state.records[-1]["violations"] if state.stopped else (),
        unapplied_attempts=tuple(dict(observation=row["prepared"].observation, reference_mw=row["prepared"].reference_mw,
            grid_request_mw=row["prepared"].grid_request_mw, proposal=row["proposal"], violations=row["violations"], actual_audit=row["actual_audit"])
            for row in state.records if not row["proposal_ledger_applied"]),
        actual_accepted_hours=sum(row["actual_accepted"] for row in state.records),
        ledger_scope="accepted_static_dc_policy_execution" if state.method == "full_temporal" else "hypothetical_approximation",
        fx_contract_status="not_evaluated_by_actual_path_step")

