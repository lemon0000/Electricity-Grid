"""Selective-query independent audit; v1 numeric and policy checks retained."""
from dataclasses import replace
from fractions import Fraction as Q
import json

from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import DebtLedger, DebtCohort
from src.staged_rts24_audit_v1 import audit_point, audit_economic_base, check
from src.staged_rts24_child_optimality_v1 import audit_child_lp
from src import staged_rts24_development_v1 as c
from src.staged_rts24_reference_queries_v1 import reference_requests


def audit_execution(fixture, state):
    p = fixture.parameters
    check(state.parameters == p and state.fixture_identity == fixture.source_identity and state.first_hour == fixture.first_hour
          and state.registration_end == fixture.registration_end and state.observation_end == fixture.observation_end
          and state.method in c.METHODS, "execution context differs")
    expected_id = c.digest(dict(fixture=fixture.source_identity, plan=state.plan, clean=state.clean_path, method=state.method,
                               first_hour=fixture.first_hour, registration_end=fixture.registration_end,
                               observation_end=fixture.observation_end, parameters=p))
    check(state.trajectory_identity == state.ledger.trajectory_identity == expected_id
          and state.ledger.accounting_period_id == "continuous_case", "trajectory identity differs")
    x = json.loads(fixture.x_envelope_json)
    prior = replace(state, ledger=DebtLedger(expected_id, "continuous_case", 0), records=(), call_energy=Q(0), previous_call=Q(0),
        events=0, duration=0, rest=p.minimum_rest, x_previous=Q(0), x_energy=Q(0), x_events=0, x_duration=0,
        x_rest=x["minimum_rest_hours"], stopped=False)
    cohort_rows = {}
    for n, row in enumerate(state.records):
        prepared, proposal = row["prepared"], row["proposal"]
        o = prepared.observation
        check(not prior.stopped and o == c.observe(fixture, state.plan, state.clean_path, prior.next_hour), "observed prefix differs")
        check(prepared.state_sha == proposal.state_sha == c.digest(prior) and proposal.prepared_sha == c.digest(prepared), "prior/prepared identity differs")
        h = reference_requests(fixture, state.plan, state.clean_path, state.method, o.hour)
        roles = {r.role: r for r in h["requests"] if not r.role.startswith("fault_")}
        evidence, root = prepared.evidence, prepared.evidence.reference
        check(root.query.request == roles["reference_base_P0"] and root.economic is not None
              and root.child_lp is None and root.query.base_query is None and root.query.base_point is None and root.query.base_economic is None,
              "reference evidence differs")
        check(audit_economic_base(root.query, root.point, root.economic)["economic_kkt_satisfied"], "reference economic audit failed")
        for name, role in (("raw", "reference_raw_need"), ("lower", "recovery_min_meter"), ("upper", "recovery_max_meter")):
            item = getattr(evidence, name)
            if role not in roles:
                check(item is None, "unexpected child evidence")
                continue
            check(item is not None and item.query.request == roles[role] and item.economic is None
                  and item.query.base_query == root.query and item.query.base_point == root.point and item.query.base_economic == root.economic,
                  "child evidence differs")
            check(item.child_lp is not None and audit_child_lp(item.query, item.point, item.child_lp)["lp_optimality_conditions_satisfied"], "child optimum audit failed")
        g = Q(str(evidence.raw.point.curtailment_mw)) if evidence.raw else Q(0)
        low = Q(str(evidence.lower.point.meter_load_mw)) if evidence.lower else None
        high = Q(str(evidence.upper.point.meter_load_mw)) if evidence.upper else None
        reference = p.facility_factor*(o.idle_mw+p.beta*o.workload)+p.auxiliary_mw
        active = min(h["conditional"], max(reference-h["firm"], Q(0)))
        legal = min(active, c.quantity(x["max_call_mw"]), max(c.quantity(x["max_energy_mwh"])-prior.x_energy, Q(0)),
                    prior.x_previous+c.quantity(x["max_ramp_mw_per_hour"]))
        if prior.x_duration >= x["max_duration_hours"] or (prior.x_previous == 0 and
                (prior.x_events >= x["max_events"] or prior.x_rest < x["minimum_rest_hours"])): legal = Q(0)
        check(h["reference_connection_shortfall_mw"] == 0 and Q(0) <= g <= legal, "reference rights/request differ")
        check((prepared.reference_mw, prepared.grid_request_mw, prepared.firm, prepared.conditional, prepared.legal_x_mw,
               prepared.lower_meter_mw, prepared.upper_meter_mw, prepared.actual_outage, prepared.x_envelope_json) ==
              (reference, g, h["firm"], h["conditional"], legal, low, high, h["actual_outage"], fixture.x_envelope_json), "prepared quantities differ")
        qg, qc, recovery = proposal.grid_deferred, proposal.cfe_deferred, proposal.recovery
        check(all(isinstance(v, Q) and v >= 0 for v in (qg, qc, recovery)), "nonexact or negative action")
        q = qg+qc
        green = max(reference-o.clean_mwh/p.alpha, Q(0)) if p.alpha else Q(0)
        # Independently select the fixed policy from the manually reconstructed prefix.
        q_limit = min(p.capacity, o.workload*o.flexible_fraction, o.workload)
        if state.method != "instantaneous":
            q_limit = min(q_limit, max(p.max_call_energy-prior.call_energy, Q(0)),
                          max(p.max_debt-prior.ledger.debt, Q(0)), prior.previous_call+p.call_ramp)
            if prior.duration >= p.max_duration or (prior.previous_call == 0 and
                    (prior.rest < p.minimum_rest or prior.events >= p.max_events)): q_limit = Q(0)
        expected_grid = min(g/p.slope, q_limit)
        expected_green = min(green/p.slope, q_limit-expected_grid)
        expected_allocations = []
        if g+green == 0 and state.method != "instantaneous":
            r_limit = min(p.capacity, p.max_recovery, prior.ledger.debt/p.eta)
            if state.method == "fixed_headroom": r_limit = min(r_limit, p.fixed_headroom)
            else:
                r_limit = min(r_limit, max(o.compute_capacity-o.workload, Q(0)), max((high-reference)/p.slope, Q(0)))
                if p.alpha: r_limit = min(r_limit, max((o.clean_mwh/p.alpha-reference)/p.slope, Q(0)))
            remaining_allowance = r_limit*p.eta
            for birth, cohort in sorted(cohort_rows.items(), key=lambda item: (item[1]["due"], item[0])):
                effective = min(cohort["remaining"], remaining_allowance)
                if effective:
                    expected_allocations.append((birth, effective))
                    remaining_allowance -= effective
        expected_recovery = sum((v for _, v in expected_allocations), Q(0))/p.eta
        check((qg, qc, recovery, proposal.allocations) == (expected_grid, expected_green, expected_recovery, tuple(expected_allocations)),
              "fixed causal policy selection differs")
        activity = o.workload-q+recovery
        power = p.facility_factor*(o.idle_mw+p.beta*activity)+p.auxiliary_mw
        grid_short, green_short, cfe_short = g-p.slope*qg, green-p.slope*qc, max(p.alpha*power-o.clean_mwh, Q(0))
        check(grid_short >= 0 and green_short >= 0 and
              (proposal.activity, proposal.power_mw, proposal.cfe_request_mw, proposal.grid_shortfall_mw, proposal.cfe_call_shortfall_mw,
               proposal.cfe_shortfall_mwh, proposal.attributed_clean_mwh) ==
              (activity, power, green, grid_short, green_short, cfe_short, min(o.clean_mwh, max(power, Q(0)))), "work/power/service balance differs")
        xcall = p.slope*qg
        events = prior.events+int(q > 0 and prior.previous_call == 0)
        duration = prior.duration+1 if q else 0
        xe = prior.x_events+int(xcall > 0 and prior.x_previous == 0)
        xd = prior.x_duration+1 if xcall else 0
        conditions = (
            (grid_short > 0, "grid_service_shortfall"), (green_short > 0, "cfe_call_shortfall"),
            (q+recovery > p.capacity or q*recovery != 0, "shared_flexibility"),
            (activity < 0 or activity > o.compute_capacity, "device_capacity"), (power > h["firm"]+h["conditional"], "connection_capacity"),
            (low is not None and power < low, "network_projection_lower"), (high is not None and power > high, "network_projection_upper"),
            (cfe_short > 0, "hourly_cfe"), (abs(q-prior.previous_call) > p.call_ramp, "call_ramp"),
            (abs(xcall-prior.x_previous) > c.quantity(x["max_ramp_mw_per_hour"]), "X_ramp"),
            (xcall > legal or prior.x_energy+xcall > c.quantity(x["max_energy_mwh"]) or xe > x["max_events"] or xd > x["max_duration_hours"]
             or (xcall > 0 and prior.x_previous == 0 and prior.x_rest < x["minimum_rest_hours"]), "X_envelope"),
            (events > p.max_events or duration > p.max_duration or (q > 0 and prior.previous_call == 0 and prior.rest < p.minimum_rest), "event_envelope"),
            (prior.call_energy+q > p.max_call_energy, "call_energy"),
            (prior.ledger.debt+q-p.eta*recovery > p.max_debt, "recovery_debt"))
        flags = tuple(code for failed, code in conditions if failed)
        check(proposal.violations == flags, "proposal violation flags differ")
        actual = row["actual"]
        if actual is not None:
            expected = replace(root.query.request, role="actual_P", meter_min=power, meter_max=power, outages=h["actual_outage"], anchor_id=root.query.request.identity)
            check(actual.query.request == expected and actual.query.base_query == root.query and actual.query.base_point == root.point
                  and actual.query.base_economic == root.economic and actual.economic is None and actual.child_lp is None
                  and actual.point.curtailment_mw == 0., "actual binding differs")
            numeric = audit_point(actual.query, actual.point)
            check(numeric == row["actual_audit"], "reported actual audit differs")
            if not numeric["point_constraints_satisfied"]: flags += ("actual_network_point",)
        else:
            check(any(code.startswith("network_projection_") or code == "connection_capacity" for code in flags)
                  and row["actual_audit"] is None, "missing actual evidence")
        accepted = state.method == "full_temporal" and not (set(flags)-{"hourly_cfe", "cfe_call_shortfall"})
        applied = accepted or state.method != "full_temporal"
        scope = "accepted_static_dc_policy_execution" if state.method == "full_temporal" else "hypothetical_approximation"
        check((row["violations"], row["actual_accepted"], row["proposal_ledger_applied"], row["full_replay_conditions_satisfied"], row["ledger_scope"], row["fx_contract_status"]) ==
              (flags, accepted, applied, not flags, scope, "not_evaluated_by_actual_path_step"), "acceptance/scope differs")
        if not applied:
            check(n == len(state.records)-1, "rejected physical prefix continued")
            prior = replace(prior, records=prior.records+(row,), stopped=True)
            continue
        check(q <= min(p.capacity, o.workload*o.flexible_fraction, o.workload) and not q*recovery, "applied schedule exceeds current task envelope")
        if q: cohort_rows[o.hour] = dict(due=o.due, incurred=q, remaining=q, missed=None)
        seen, recovered = set(), Q(0)
        for birth, amount in proposal.allocations:
            check(birth in cohort_rows and birth < o.hour and birth not in seen and isinstance(amount, Q)
                  and Q(0) <= amount <= cohort_rows[birth]["remaining"], "recovery allocation differs")
            seen.add(birth); cohort_rows[birth]["remaining"] -= amount; recovered += amount
        check(recovered == p.eta*recovery, "effective recovery balance differs")
        for cohort in cohort_rows.values():
            if cohort["due"] == o.hour: cohort["missed"] = cohort["remaining"]
        ledger = DebtLedger(expected_id, "continuous_case", o.hour+state.hour_offset,
            tuple(DebtCohort(birth+state.hour_offset, value["due"]+state.hour_offset, "mechanism_assumption", value["incurred"],
                             value["remaining"], value["missed"]) for birth, value in sorted(cohort_rows.items())))
        prior = replace(prior, ledger=ledger, records=prior.records+(row,), call_energy=prior.call_energy+q, previous_call=q,
            events=events, duration=duration, rest=0 if q else prior.rest+1, x_previous=xcall, x_energy=prior.x_energy+xcall,
            x_events=xe, x_duration=xd, x_rest=0 if xcall else prior.x_rest+1)
    check(prior == state, "final execution carry differs")
    return dict(record_consistency_satisfied=True, rows=len(state.records), actual_accepted_hours=sum(row["actual_accepted"] for row in state.records),
                remaining_debt=state.ledger.debt, fixed_policy_selection_recomputed=True,
                method=state.method, stopped=state.stopped, policy_applied_through=state.next_hour-1,
                accepted_through=state.next_hour-1 if state.method == "full_temporal" else None,
                ledger_scope="accepted_static_dc_policy_execution" if state.method == "full_temporal" else "hypothetical_approximation",
                scope="independent_saved_point_work_power_deadline_and_carry_consistency", fx_temporal_backing="not_established")
