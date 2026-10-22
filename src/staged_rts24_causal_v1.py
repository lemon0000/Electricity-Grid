"""Evidence-driven causal business transition; no scalar supply or solver."""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
import json
from math import isfinite

from src.staged_deliverability_development_v1 import initialize, power_mapping, Parameters
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import advance_debt_ledger
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import assess_debt_cohorts
from src import staged_rts24_development_v1 as c
from src.staged_rts24_audit_v1 import audit_point, audit_economic_base, TOL_MW
from src.staged_rts24_child_optimality_v1 import audit_child_lp

ZERO = Q(0)


@dataclass(frozen=True)
class PointEvidence:
    query: c.BoundQuery
    point: c.PointWitness
    economic: c.EconomicEvidence | None = None
    child_lp: object | None = None


@dataclass(frozen=True)
class HourEvidence:
    reference: PointEvidence
    raw: PointEvidence | None = None
    lower: PointEvidence | None = None
    upper: PointEvidence | None = None


@dataclass(frozen=True)
class ExecutionState:
    fixture_identity: str
    plan: str
    clean_path: str
    method: str
    parameters: Parameters
    first_hour: int
    registration_end: int
    observation_end: int
    trajectory_identity: str
    ledger: object
    records: tuple = ()
    call_energy: Q = ZERO
    previous_call: Q = ZERO
    events: int = 0
    duration: int = 0
    rest: int = 0
    x_previous: Q = ZERO
    x_energy: Q = ZERO
    x_events: int = 0
    x_duration: int = 0
    x_rest: int = 0
    stopped: bool = False

    @property
    def hour_offset(self): return 1-self.first_hour

    @property
    def next_hour(self): return self.ledger.last_hour+1-self.hour_offset


@dataclass(frozen=True)
class PreparedHour:
    state_sha: str
    observation: c.PublicObservation
    evidence: HourEvidence
    reference_mw: Q
    grid_request_mw: Q
    firm: Q
    conditional: Q
    legal_x_mw: Q
    lower_meter_mw: Q | None
    upper_meter_mw: Q | None
    actual_outage: c.Outage
    x_envelope_json: str


@dataclass(frozen=True)
class Proposal:
    state_sha: str
    prepared_sha: str
    grid_deferred: Q
    cfe_deferred: Q
    recovery: Q
    allocations: tuple[tuple[int, Q], ...]
    activity: Q
    power_mw: Q
    cfe_request_mw: Q
    grid_shortfall_mw: Q
    cfe_call_shortfall_mw: Q
    cfe_shortfall_mwh: Q
    attributed_clean_mwh: Q
    violations: tuple[str, ...]

    @property
    def deferred(self): return self.grid_deferred+self.cfe_deferred


def initialize_execution(fixture, plan, clean, method):
    c.observe(fixture, plan, clean, fixture.first_hour)
    identity = c.digest(dict(fixture=fixture.source_identity, plan=plan, clean=clean, method=method,
                             first_hour=fixture.first_hour, registration_end=fixture.registration_end,
                             observation_end=fixture.observation_end, parameters=fixture.parameters))
    legacy = initialize(fixture.parameters, method, identity, fixture.first_hour)
    x = json.loads(fixture.x_envelope_json)
    return ExecutionState(fixture.source_identity, plan, clean, method, fixture.parameters,
        fixture.first_hour, fixture.registration_end, fixture.observation_end, identity, legacy.ledger,
        rest=legacy.rest, x_rest=x["minimum_rest_hours"])


def audit_execution_context(fixture, state):
    c.require((state.fixture_identity, state.parameters, state.first_hour, state.registration_end, state.observation_end) ==
              (fixture.source_identity, fixture.parameters, fixture.first_hour, fixture.registration_end, fixture.observation_end),
              "execution context or horizon changed")
    identity = c.digest(dict(fixture=fixture.source_identity, plan=state.plan, clean=state.clean_path, method=state.method,
        first_hour=fixture.first_hour, registration_end=fixture.registration_end, observation_end=fixture.observation_end, parameters=fixture.parameters))
    c.require(state.trajectory_identity == state.ledger.trajectory_identity == identity
              and state.ledger.accounting_period_id == "continuous_case", "execution trajectory identity changed")
    from src.staged_rts24_causal_audit_v1 import audit_execution
    return audit_execution(fixture, state)


def reported_quantity(value):
    """Encode the returned finite decimal as a rational; do not round or certify it."""
    c.require(type(value) in (int, float) and isfinite(value) and value >= 0, "unusable numeric decision input")
    return Q(str(value))


def _root(evidence, request):
    c.require(isinstance(evidence, PointEvidence) and evidence.query.request == request
              and evidence.query.base_query is None and evidence.query.base_point is None
              and evidence.query.base_economic is None and evidence.child_lp is None, "reference root binding differs")
    c.require(evidence.economic is not None and audit_economic_base(evidence.query, evidence.point, evidence.economic)["economic_kkt_satisfied"],
              "missing or invalid reference economic evidence")


def _child(evidence, request, reference):
    c.require(isinstance(evidence, PointEvidence) and evidence.query.request == request
              and evidence.query.base_query == reference.query and evidence.query.base_point == reference.point
              and evidence.query.base_economic == reference.economic and evidence.economic is None,
              "child/reference binding differs")
    c.require(evidence.child_lp is not None and audit_child_lp(evidence.query, evidence.point, evidence.child_lp)["lp_optimality_conditions_satisfied"],
              "missing or invalid child optimum evidence")


def prepare_hour(fixture, state, evidence):
    c.require(not state.stopped, "stopped execution")
    audit_execution_context(fixture, state)
    h = c.hour_requests(fixture, state.plan, state.clean_path, state.method, state.next_hour)
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


def propose_hour(state, prepared):
    c.require(not state.stopped and prepared.state_sha == c.digest(state)
              and prepared.observation.hour == state.next_hour, "proposal prior state differs")
    p, o = state.parameters, prepared.observation
    c.require(power_mapping(p, o)[2] == prepared.reference_mw, "reference power mapping differs")
    grid = prepared.grid_request_mw
    green = max(prepared.reference_mw-o.clean_mwh/p.alpha, ZERO) if p.alpha else ZERO
    room = min(p.capacity, o.workload*o.flexible_fraction, o.workload,
               max(p.max_call_energy-state.call_energy, ZERO), max(p.max_debt-state.ledger.debt, ZERO), state.previous_call+p.call_ramp)
    if state.duration >= p.max_duration or (not state.previous_call and (state.rest < p.minimum_rest or state.events >= p.max_events)):
        room = ZERO
    if state.method == "instantaneous": room = min(p.capacity, o.workload*o.flexible_fraction, o.workload)
    grid_q = min(grid/p.slope, room)
    green_q = min(green/p.slope, room-grid_q)
    q = grid_q+green_q
    recovery, allocations = ZERO, []
    if grid+green == 0 and state.method != "instantaneous":
        limit = min(p.capacity, p.max_recovery, state.ledger.debt/p.eta)
        if state.method == "fixed_headroom": limit = min(limit, p.fixed_headroom)
        else:
            c.require(prepared.lower_meter_mw is not None and prepared.upper_meter_mw is not None, "recovery interval missing")
            limit = min(limit, max(o.compute_capacity-o.workload, ZERO), max((prepared.upper_meter_mw-prepared.reference_mw)/p.slope, ZERO))
            if p.alpha: limit = min(limit, max((o.clean_mwh/p.alpha-prepared.reference_mw)/p.slope, ZERO))
        for cohort in sorted(state.ledger.cohorts, key=lambda row: (row.due_hour, row.created_hour)):
            effective = min(cohort.remaining, max(limit-recovery, ZERO)*p.eta)
            if effective:
                allocations.append((cohort.created_hour-state.hour_offset, effective))
                recovery += effective/p.eta
    activity, _, power = power_mapping(p, o, q, recovery)
    events = state.events+int(q > 0 and state.previous_call == 0)
    duration = state.duration+1 if q else 0
    grid_short, green_short = grid-p.slope*grid_q, green-p.slope*green_q
    cfe_short = max(p.alpha*power-o.clean_mwh, ZERO)
    x = json.loads(prepared.x_envelope_json)
    xcall = p.slope*grid_q
    xevents = state.x_events+int(xcall > 0 and state.x_previous == 0)
    xduration = state.x_duration+1 if xcall else 0
    flags = (
        (grid_short > 0, "grid_service_shortfall"), (green_short > 0, "cfe_call_shortfall"),
        (q+recovery > p.capacity or q*recovery != 0, "shared_flexibility"),
        (activity < 0 or activity > o.compute_capacity, "device_capacity"),
        (power > prepared.firm+prepared.conditional, "connection_capacity"),
        (prepared.lower_meter_mw is not None and power < prepared.lower_meter_mw, "network_projection_lower"),
        (prepared.upper_meter_mw is not None and power > prepared.upper_meter_mw, "network_projection_upper"),
        (cfe_short > 0, "hourly_cfe"), (abs(q-state.previous_call) > p.call_ramp, "call_ramp"),
        (abs(xcall-state.x_previous) > c.quantity(x["max_ramp_mw_per_hour"]), "X_ramp"),
        (xcall > prepared.legal_x_mw or state.x_energy+xcall > c.quantity(x["max_energy_mwh"])
         or xevents > x["max_events"] or xduration > x["max_duration_hours"]
         or (xcall > 0 and not state.x_previous and state.x_rest < x["minimum_rest_hours"]), "X_envelope"),
        (events > p.max_events or duration > p.max_duration or (q > 0 and not state.previous_call and state.rest < p.minimum_rest), "event_envelope"),
        (state.call_energy+q > p.max_call_energy, "call_energy"),
        (state.ledger.debt+q-p.eta*recovery > p.max_debt, "recovery_debt"))
    return Proposal(c.digest(state), c.digest(prepared), grid_q, green_q, recovery, tuple(allocations), activity, power, green,
                    grid_short, green_short, cfe_short, min(o.clean_mwh, max(power, ZERO)), tuple(code for failed, code in flags if failed))


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
