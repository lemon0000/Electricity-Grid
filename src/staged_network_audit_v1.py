"""Independent Fraction corridor/contract audit, without PYPOWER or B2 policy.

Uses Kirchhoff balance and exact parallel impedances; no assertion can disappear
under python -O. Actual task accounting uses the separate B1 arithmetic auditor.
"""
from fractions import Fraction as Q
import json

from src.staged_deliverability_audit_v1 import audit_records

TOL = 1e-9


def check(value, message="independent B2 audit failed"):
    if not value:
        raise AssertionError(message)


def q(value):
    return Q(str(value))


def capacity(data, outages, angle_limit):
    online = [b for b in data["branches"] if b["in_service"] and b["index"] not in outages]
    check(bool(online), "islanded audit topology")
    weights = [1 / (q(b["reactance_pu"]) * q(b["tap_ratio"])) for b in online]
    total = sum(weights, Q(0))
    source_limit = q(data["generators"][0]["p_max_mw"])
    limits = [q(b["rate_a_mw"]) * total / w for b, w in zip(online, weights)]
    limits += [source_limit, q(angle_limit) * q(data["base_mva"]) * total]
    return min(limits) - sum((q(b["demand_mw"]) for b in data["buses"]), Q(0))


def audit_point(data, poi, point, load, outages, angle_limit):
    check(q(point["load"]) == load and tuple(point["outages"]) == tuple(outages), "point load/topology drift")
    online = [b for b in data["branches"] if b["in_service"] and b["index"] not in outages]
    weights = {b["index"]: 1 / (q(b["reactance_pu"]) * q(b["tap_ratio"])) for b in online}
    total_weight = sum(weights.values(), Q(0))
    background = sum((q(b["demand_mw"]) for b in data["buses"]), Q(0))
    generation = load + background
    expected_angle = -generation / (q(data["base_mva"]) * total_weight)
    source = data["reference_bus"]
    for i, bus in enumerate(data["buses"]):
        angle = 0 if bus["index"] == source else expected_angle
        check(abs(point["angles_rad"][i] - float(angle)) <= TOL, "angle differs from exact KCL")
    check(abs(point["generation_mw"] - float(generation)) <= TOL, "source balance differs")
    thermal, outage_flow = Q(0), 0.
    injections = {b["index"]: -q(b["demand_mw"]) for b in data["buses"]}
    injections[source] += generation
    injections[poi] -= load
    for i, branch in enumerate(data["branches"]):
        expected = generation * weights.get(branch["index"], Q(0)) / total_weight
        observed = point["branch_flows_mw"][i]
        check(abs(observed - float(expected)) <= TOL, "branch flow differs from exact split")
        injections[branch["from_bus"]] -= expected
        injections[branch["to_bus"]] += expected
        if branch in online:
            thermal = max(thermal, abs(expected) - q(branch["rate_a_mw"]))
        else:
            outage_flow = max(outage_flow, abs(observed))
    check(all(v == 0 for v in injections.values()), "exact node balances failed")
    residuals = dict(balance_mw=0., flow_equation_mw=0., thermal_mw=float(thermal),
                     outage_flow_mw=outage_flow,
                     generation_mw=float(max(generation - q(data["generators"][0]["p_max_mw"]), -generation, Q(0))),
                     angle_rad=float(max(abs(expected_angle) - q(angle_limit), Q(0))))
    check(set(point["residuals"]) == set(residuals), "incomplete numerical residuals")
    for key, value in residuals.items():
        check(abs(point["residuals"][key] - value) <= TOL, f"residual differs: {key}")
    feasible = all(v <= TOL for v in residuals.values())
    check(point["numerical_conditions_satisfied"] is feasible, "numerical status differs")
    return feasible


def audit_contract(c, p, o, data, firm, conditional, contract):
    check(contract["status"] == "evaluated")
    total, alpha = firm + conditional, q(p["alpha"])
    a = q(p["beta"]) * q(p["facility_factor"])
    green = max(total - q(o["clean_mwh"]) / alpha, Q(0)) if alpha else Q(0)
    w_hat = (total - q(p["facility_factor"]) * q(o["idle_mw"]) - q(p["auxiliary_mw"])) / a
    enrolled = conditional <= a * q(p["capacity"]) and w_hat >= 0 and conditional <= a * w_hat * q(o["flexible_fraction"])
    check((q(contract["firm"]), q(contract["conditional"]), q(contract["total"])) == (firm, conditional, total))
    normal_ok = audit_point(data, c["poi_bus"], contract["normal"], total, (), c["angle_limit"])
    check(tuple(tuple(s["outages"]) for s in contract["scenarios"]) == ((), (0,), (1,)))
    network_ok, backing_ok = True, True
    for scenario in contract["scenarios"]:
        outages = tuple(scenario["outages"])
        cap = capacity(data, outages, c["angle_limit"])
        grid = max(total - cap, Q(0)) if outages else Q(0)
        required_work = (grid + green) / a
        backing = (w_hat >= 0 and required_work <= q(p["capacity"])
                   and required_work <= w_hat * q(o["flexible_fraction"])
                   and 0 <= w_hat - required_work <= q(o["compute_capacity"]))
        check(q(scenario["physical_cap"]) == cap and q(scenario["required_grid_mw"]) == grid)
        check(q(scenario["counterfactual_cfe_mw"]) == green and q(scenario["counterfactual_workload"]) == w_hat)
        check(q(scenario["shared_requirement"]) == required_work and scenario["business_necessary"] is backing)
        if outages:
            response = (grid == 0 or (grid <= conditional and grid <= q(c["max_x_call"]) and grid <= q(c["max_x_ramp"])
                        and grid <= q(c["max_x_energy"]) and c["max_x_events"] >= 1 and c["max_x_duration"] >= 1))
            f_ok = audit_point(data, c["poi_bus"], scenario["firm_point"], firm, outages, c["angle_limit"])
            after_ok = audit_point(data, c["poi_bus"], scenario["post_call_point"], total-grid, outages, c["angle_limit"])
            check(total-grid >= firm)
            state_ok = f_ok and after_ok and response
        else:
            response, state_ok = True, normal_ok
            check(scenario["firm_point"] is None)
            check(json.dumps(scenario["post_call_point"],sort_keys=True)==json.dumps(contract["normal"],sort_keys=True))
        check(scenario["response_necessary"] is response and scenario["network_conditions_satisfied"] is state_ok)
        network_ok, backing_ok = network_ok and state_ok, backing_ok and backing
    check(contract["network_conditions_satisfied"] is network_ok and contract["business_necessary"] is (enrolled and backing_ok))
    check(contract["enrolled_X_backing_necessary"] is enrolled and contract["aggregate_contract_release"] is False)
    check(contract["joint_temporal_support"] == ("unresolved" if network_ok and enrolled and backing_ok else "necessary_condition_failed"))


def audit_partial_contract(c, p, o, data, firm, conditional, contract):
    check(set(contract)=={"firm","conditional","total","normal","scenarios","status","aggregate_contract_release"})
    check(contract["status"] == "pending" and contract["aggregate_contract_release"] is False)
    check((q(contract["firm"]),q(contract["conditional"]),q(contract["total"]))==(firm,conditional,firm+conditional))
    if contract["normal"] is not None:
        audit_point(data,c["poi_bus"],contract["normal"],firm+conditional,(),c["angle_limit"])
    signatures=tuple(tuple(s["outages"]) for s in contract["scenarios"])
    check(signatures == ((),(0,),(1,))[:len(signatures)], "partial contract scenario order differs")
    check(contract["normal"] is not None or not signatures, "partial contract lacks its normal point")
    if contract["normal"] is not None:
        check(len(signatures) in (2,3) and contract["scenarios"][-1]["post_call_point"] is None,
              "partial contract must end at the unfinished outage")
    a=q(p["beta"])*q(p["facility_factor"])
    green=max(firm+conditional-q(o["clean_mwh"])/q(p["alpha"]),Q(0)) if q(p["alpha"]) else Q(0)
    w_hat=(firm+conditional-q(p["facility_factor"])*q(o["idle_mw"])-q(p["auxiliary_mw"]))/a
    base_fields={"outages","physical_cap","required_grid_mw","counterfactual_cfe_mw","counterfactual_workload",
                 "shared_requirement","business_necessary","firm_point","post_call_point"}
    for i,s in enumerate(contract["scenarios"]):
        outages=tuple(s["outages"])
        cap=capacity(data,outages,c["angle_limit"])
        grid=max(firm+conditional-cap,Q(0)) if outages else Q(0)
        check(q(s["physical_cap"])==cap and q(s["required_grid_mw"])==grid
              and q(s["counterfactual_cfe_mw"])==green and q(s["shared_requirement"])==(grid+green)/a)
        req=(grid+green)/a
        backing=(w_hat>=0 and req<=q(p["capacity"]) and req<=w_hat*q(o["flexible_fraction"])
                 and 0<=w_hat-req<=q(o["compute_capacity"]))
        check(q(s["counterfactual_workload"])==w_hat and s["business_necessary"] is backing)
        if s["post_call_point"] is None:
            check(set(s)==base_fields and bool(outages) and i==len(contract["scenarios"])-1)
        else:
            check(set(s)==base_fields|{"response_necessary","network_conditions_satisfied"})
            check(i < len(contract["scenarios"])-1, "pending contract cannot end with a completed scenario")
        if s["firm_point"] is not None:
            check(bool(outages), "normal scenario cannot contain a firm fault point")
            audit_point(data,c["poi_bus"],s["firm_point"],firm,outages,c["angle_limit"])
        if s["post_call_point"] is not None:
            after_ok=audit_point(data,c["poi_bus"],s["post_call_point"],firm+conditional-grid,outages,c["angle_limit"])
            response=(not outages or grid==0 or (grid<=conditional and grid<=q(c["max_x_call"])
                      and grid<=q(c["max_x_ramp"]) and grid<=q(c["max_x_energy"])
                      and c["max_x_events"]>=1 and c["max_x_duration"]>=1))
            firm_ok=True if not outages else audit_point(data,c["poi_bus"],s["firm_point"],firm,outages,c["angle_limit"])
            check(s["response_necessary"] is response and s["network_conditions_satisfied"] is (firm_ok and after_ok and response))


def audit_network(config, parameters, state):
    check(json.dumps(config,sort_keys=True) == json.dumps(state["config"],sort_keys=True), "configuration drift")
    c, p = config, parameters
    a = q(p["beta"]) * q(p["facility_factor"])
    previous_source, previous_x, energy, events, duration, rest = None, Q(0), Q(0), 0, 0, c["x_minimum_rest"]
    accepted, last, stopped, points, rejected_proposal = [], None, False, 0, None
    for row in state["records"]:
        check(not stopped, "network records continued after stop")
        t, o = row["hour"], row["input"]
        check(t == o["hour"] and (last is None or t == last+1), "physical hours differ")
        last = t
        online = t >= c["project_start"] + c["project_lead"] + dict(c["delays"])[state["plan"]]
        check(row["commissioned"] is online and o["grid_online"] is online)
        data = c["after"] if online else c["before"]
        firm, conditional = map(q,c["rights_after"] if online else c["rights_before"])
        branch = dict(c["actual_outages"]).get(t)
        outages = () if branch is None else (branch,)
        cap = capacity(data,outages,c["angle_limit"])
        base = q(p["facility_factor"])*(q(o["idle_mw"])+q(p["beta"])*q(o["workload"]))+q(p["auxiliary_mw"])
        raw_grid, active = max(base-cap,Q(0)), min(conditional,max(base-firm,Q(0)))
        legal = min(active,q(c["max_x_call"]),max(q(c["max_x_energy"])-energy,Q(0)),previous_x+q(c["max_x_ramp"]))
        if duration >= c["max_x_duration"] or (previous_x == 0 and (events >= c["max_x_events"] or rest < c["x_minimum_rest"])):
            legal=Q(0)
        check(q(row["physical_cap"])==cap and q(row["reference_mw"])==base and q(row["raw_grid_mw"])==raw_grid)
        check(q(row["firm"])==firm and q(row["conditional"])==conditional and tuple(row["outages"])==outages)
        check(q(row["active_x_mw"])==active and q(row["legal_grid_cap_mw"])==legal)
        check(q(row["connection_shortfall_mw"])==max(base-firm-conditional,Q(0)))
        unresolved=row["status"]=="upstream_network_unresolved"
        if unresolved and row["contract"]["status"]=="pending":
            audit_partial_contract(c,p,o,data,firm,conditional,row["contract"])
            check(row["failure_stage"]=="contract_checks" and row["reference_point"] is None and row["proposal"] is None)
        else:
            audit_contract(c,p,o,data,firm,conditional,row["contract"])
            points+=5
        if row["reference_point"] is not None:
            audit_point(data,c["poi_bus"],row["reference_point"],base,outages,c["angle_limit"])
            points+=1
        elif not unresolved:
            check(False,"missing resolved reference point")
        proposal=row["proposal"]
        blocked=False
        if proposal is not None:
            expected_input=dict(o, supply_mw=str(min(cap,firm+conditional)))
            check(json.dumps(expected_input,sort_keys=True)==json.dumps(proposal["observation"],sort_keys=True))
            check(q(proposal["grid_request_mw"])==raw_grid)
            blocked=any(v not in {"hourly_cfe","cfe_call_shortfall"} for v in proposal["violations"])
            if not row["committed"]:
                rejected_proposal=dict(proposal,ledger_applied=not blocked)
        if unresolved:
            check(row["committed"] is False and isinstance(row["error"],str) and bool(row["error"]))
            if row["proposal"] is not None:
                check(row["failure_stage"]=="actual_flow" and row["proposal"]["ledger_applied"] is False
                      and row["actual_point"] is None and row["reference_point"] is not None)
            elif row["contract"]["status"]=="evaluated":
                check(row["failure_stage"]=="reference_flow" and row["reference_point"] is None)
            stopped=True
            continue
        if proposal is None:
            check(row["committed"] is False and row["actual_point"] is None)
            status=row["status"]
            if status=="reference_connection_shortfall":
                check(base>firm+conditional)
            elif status=="request_exceeds_legal_X":
                check(base<=firm+conditional and raw_grid>legal and q(row["grid_unbacked_request_mw"])==raw_grid-legal)
            elif status=="normal_state_has_no_X_call_authority":
                check(base<=firm+conditional and raw_grid>0 and not outages)
            else:
                check(False,"unknown admission rejection")
            stopped=True
            continue
        load=q(proposal["power_mw"])
        actual_ok=audit_point(data,c["poi_bus"],row["actual_point"],load,outages,c["angle_limit"])
        points+=1
        x=a*q(proposal["grid_served"])
        source=load+sum((q(b["demand_mw"]) for b in data["buses"]),Q(0))
        next_events=events+int(x>0 and previous_x==0)
        next_duration=duration+1 if x else 0
        response_ok=(x<=active and x<=q(c["max_x_call"]) and abs(x-previous_x)<=q(c["max_x_ramp"])
                     and energy+x<=q(c["max_x_energy"]) and next_events<=c["max_x_events"]
                     and next_duration<=c["max_x_duration"]
                     and not(x and not previous_x and rest<c["x_minimum_rest"])
                     and (previous_source is None or abs(source-previous_source)<=q(c["hourly_ramp"])))
        check(q(row["x_call_mw"])==x and row["response_conditions_satisfied"] is response_ok)
        if not row["committed"]:
            check(proposal["ledger_applied"] is False)
            if row["status"]=="business_proposal_rejected": check(blocked)
            elif row["status"]=="actual_network_point_rejected": check(not blocked and (not actual_ok or load>firm+conditional))
            elif row["status"]=="X_or_source_response_rejected": check(not blocked and actual_ok and load<=firm+conditional and not response_ok)
            else: check(False,"unknown action rejection")
            stopped=True
            continue
        check(row["status"]=="conditional_operating_point_committed" and proposal["ledger_applied"] is True)
        check(not blocked and actual_ok and response_ok and x<=legal and load<=firm+conditional)
        events+=int(x>0 and previous_x==0); duration=duration+1 if x else 0
        rest=0 if x else rest+1; energy+=x
        check(abs(x-previous_x)<=q(c["max_x_ramp"]))
        accepted.append(proposal); previous_source,previous_x=source,x
    check(state["stopped"] is stopped)
    check(accepted==state["business"]["records"], "network/business transaction differs")
    if rejected_proposal is not None:
        # Only the final rejected proposal needs this additional bounded prefix.
        audit_records(p,accepted+[rejected_proposal],"full_temporal")
    business=audit_records(p,accepted,"full_temporal")
    b=state["business"]
    check(b["method"]=="full_temporal" and b["stopped"] is False)
    check(json.dumps(b["parameters"],sort_keys=True)==json.dumps(p,sort_keys=True),"business parameters differ")
    offset=b["first_hour"]
    check(type(offset) is int and (not state["records"] or offset==state["records"][0]["hour"]))
    ledger=b["ledger"]
    check(type(ledger["last_hour"]) is int and ledger["last_hour"]==(accepted[-1]["observation"]["hour"]-offset+1 if accepted else 0))
    check(ledger["trajectory_identity"]==b["trajectory_id"] and ledger["accounting_period_id"]=="continuous_case")
    cohorts=ledger["cohorts"]
    births=[v["created_hour"]-1+offset for v in cohorts]
    check(births==sorted(set(births)) and set(births)==set(business["balances"]),"cohort identity set differs")
    for cohort in cohorts:
        birth=cohort["created_hour"]-1+offset
        check(type(cohort["created_hour"]) is int)
        check(q(cohort["incurred"])==business["balances"][birth]["incurred"])
        check(cohort["due_hour"]==business["balances"][birth]["due"]+1-offset and cohort["deadline_evidence"]=="mechanism_assumption")
        check(q(cohort["remaining"])==business["balances"][birth]["remaining"])
        missed=business["deadline_misses"].get(birth)
        check((None if cohort["missed_at_deadline"] is None else q(cohort["missed_at_deadline"]))==missed)
    for key,expected in business["envelope"].items():
        if isinstance(expected,Q): check(q(b[key])==expected,f"business envelope drift: {key}")
        else: check(type(b[key]) is int and b[key]==expected,f"business envelope drift: {key}")
    for key,expected in dict(x_previous=previous_x,x_energy=energy,x_events=events,x_duration=duration,x_rest=rest).items():
        check((q(state[key]) if isinstance(expected,Q) else state[key])==expected and
              (isinstance(expected,Q) or type(state[key]) is int), f"X carry drift: {key}")
    check((None if state["previous_generation"] is None else q(state["previous_generation"]))==previous_source)
    return dict(audited_network_hours=len(state["records"]),accepted_business_hours=len(accepted),
                audited_pypower_points=points,stopped=stopped,x_energy=energy,x_events=events,
                business_audit=business,scope="B2 fixed_balance_DC_only")
