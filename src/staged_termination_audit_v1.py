"""Independent B3 terminal arithmetic; never imports its writer or PYPOWER."""
from fractions import Fraction as Q
import hashlib
import json

from src.staged_network_audit_v1 import audit_network, check


def same(a,b):
    return json.dumps(a,sort_keys=True,separators=(",",":"),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(",",":"),allow_nan=False)


def sha(value):
    return hashlib.sha256((json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()).hexdigest()


def audit_termination(report):
    fields={"schema","status","scope","termination_reason","state_certainty","resume_permitted",
        "last_accepted_hour","last_verified_accepted_hour","next_required_hour","attempted_hour",
        "declared_registration_end","declared_observation_last_hour","observation_end_reached","policy_outcome",
        "pending_arrival","future_arrivals_unobserved","business_prefix_assessment","all_arrived_tasks",
        "primary_remaining_debt","pending","io_error","last_verified_state","genesis_sha","head_sha","state_sha","aggregate_contract_release",
        "audit_validity","publication_outcome"}
    check(set(report)==fields,"terminal schema differs")
    check(type(report["schema"]) is int and report["schema"]==1 and report["status"]=="DRAFT_NONAUTHORITATIVE"
          and report["scope"]=="B3 filesystem_visible_simulation_only")
    check(report["resume_permitted"] is False and report["aggregate_contract_release"] is False)
    state=report["last_verified_state"]
    check(state["stopped"] is False,"accepted state cannot include a stopped attempt")
    p,c=state["business"]["parameters"],state["config"]
    pending=report["pending"]
    if pending is not None:
        check(isinstance(pending,dict) and pending["role"] in {"step","attempt","network_attempt","out_of_order_input","incomplete_publication"})
        check(pending["adoption"] in {"not_adopted","unknown"})
        expected_fields={"step":{"role","b2_candidate_record","adoption","b2_candidate_state"},
            "attempt":{"role","b2_candidate_record","adoption","b2_candidate_state"},
            "network_attempt":{"role","b2_candidate_record","adoption"},
            "out_of_order_input":{"role","provided_hour","adoption"},
            "incomplete_publication":{"role","target","adoption","observation","b2_candidate_record","evidence_status"}}
        check(set(pending)==expected_fields[pending["role"]],"pending schema differs")
        if pending["role"]=="incomplete_publication":
            check(pending["evidence_status"] in {"external_witness","canonical_envelope","saved_attempt","unreadable"})
            if pending["evidence_status"]=="unreadable":
                check(pending["observation"] is None and pending["b2_candidate_record"] is None)
    row=(pending or {}).get("b2_candidate_record")
    if pending is not None and pending["role"] in {"attempt","network_attempt"}: check(row["committed"] is False)
    audit_state=json.loads(json.dumps(state))
    if row is not None and row["committed"] is False:
        audit_state["records"].append(row); audit_state["stopped"]=True
    network=audit_network(c,p,audit_state)
    hypothetical=None
    if pending is not None and pending["role"]=="step":
        candidate=pending["b2_candidate_state"]
        check(candidate["records"][:-1]==state["records"] and candidate["records"][-1]==row)
        check(candidate["business"]["trajectory_id"]==state["business"]["trajectory_id"]
              and candidate["plan"]==state["plan"])
        hypothetical=audit_network(c,p,candidate)
        check(row["committed"] is True and len(candidate["business"]["records"])==len(state["business"]["records"])+1
              and candidate["business"]["first_hour"]==state["business"]["first_hour"])
    check(sha(state)==report["state_sha"],"accepted state digest differs")
    b=state["business"]
    last=b["first_hour"]+len(b["records"])-1
    check(type(report["last_verified_accepted_hour"]) is int and report["last_verified_accepted_hour"]==last)
    check(type(report["next_required_hour"]) is int and report["next_required_hour"]==last+1)
    end,registration=report["declared_observation_last_hour"],report["declared_registration_end"]
    check(type(end) is int and type(registration) is int and 0<registration<=end+1
          and end-b["first_hour"]<10 and last<=end)
    check(report["observation_end_reached"] is (last>=end))
    reason=report["termination_reason"]
    uncertain=reason in {"commit_outcome_unknown","reopen_failure"}
    check(report["state_certainty"]==("unresolved" if uncertain else "known"))
    check(report["last_accepted_hour"] is None if uncertain else
          type(report["last_accepted_hour"]) is int and report["last_accepted_hour"]==last)
    observation=(row or {}).get("input") or (pending or {}).get("observation")
    observed=last if observation is None else observation["hour"]
    evidence_unresolved=(pending or {}).get("evidence_status")=="unreadable"
    check(report["future_arrivals_unobserved"] is (None if evidence_unresolved else observed<end))
    arrival_status="observed_pending_unaccepted" if observation is not None else "evidence_unresolved" if evidence_unresolved else "none" if reason in {
        "observation_complete","followup_horizon_insufficient"} else "not_observed"
    check(report["pending_arrival"]==dict(status=arrival_status,observation=observation))
    check(report["attempted_hour"]==(None if observation is None else observation["hour"]))
    if observation is not None:
        check(type(observation["hour"]) is int and observation["hour"]==last+1
              and type(report["attempted_hour"]) is int and observation["hour"]<=end)
    if pending is not None and pending["role"]=="out_of_order_input":
        check(type(pending["provided_hour"]) is int and pending["provided_hour"]>last+1 and row is None and reason=="missing_input")
    check(report["audit_validity"] in {"not_established","passed","failed"})
    expected_publication="unresolved" if reason in {"commit_outcome_unknown","publication_outcome_unknown","reopen_failure"} else "not_published" if reason in {"persistence_failure","incomplete_publication"} else "not_applicable"
    if reason=="initialization_failure": expected_publication="unresolved" if report["io_error"]["may_have_published"] else "not_published"
    check(report["publication_outcome"]==expected_publication)
    for name in ("genesis_sha","head_sha","state_sha"):
        value=report[name]
        check(isinstance(value,str) and ((len(value)==64 and all(c in "0123456789abcdef" for c in value))
              or (reason=="reopen_failure" and name!="state_sha" and value=="")),"invalid terminal SHA")
    error=report["io_error"]
    if error is not None:
        check(set(error)=={"operation","phase","error","may_have_published","planned_reason","target","expected_sha"},"I/O evidence schema differs")
        check(type(error["may_have_published"]) is bool and isinstance(error["error"],str) and error["error"])
        check(error["expected_sha"] is None or (isinstance(error["expected_sha"],str) and len(error["expected_sha"])==64
              and all(c in "0123456789abcdef" for c in error["expected_sha"])))
    if reason in {"policy_or_admission_rejected","network_unresolved"}:
        check(pending["role"]=="network_attempt" and pending["adoption"]=="not_adopted" and row["committed"] is False)
        check((row["status"]=="upstream_network_unresolved") is (reason=="network_unresolved"))
    elif reason in {"initialization_failure","persistence_failure","commit_outcome_unknown","publication_outcome_unknown","incomplete_publication"}:
        check(error["operation"] in {"genesis","step","attempt","checkpoint","terminal"} and isinstance(error["error"],str) and error["error"])
        check(error["target"]==pending["target"] if (pending or {}).get("role")=="incomplete_publication" else isinstance(error["target"],str))
        check(error["phase"] in {"open","write","flush","fsync","close","pending_readback","publish","readback","reopen_pending","reopen_missing"})
        check((error["operation"]=="step" and error["may_have_published"]) is (reason=="commit_outcome_unknown"))
        if reason=="publication_outcome_unknown": check(error["operation"]!="step" and error["may_have_published"])
        if reason=="incomplete_publication": check(error["may_have_published"] is False and error["phase"] in {"reopen_pending","reopen_missing"})
        if reason=="initialization_failure": check(error["operation"]=="genesis" and not b["records"])
        if error["operation"]=="step" and pending["role"]=="step":
            check(pending["role"]=="step" and pending["adoption"]==("unknown" if uncertain else "not_adopted"))
    elif reason=="reopen_failure":
        check(error["operation"]=="reopen" and error["phase"]=="integrity")
    elif reason=="independent_audit_failure":
        check(error["operation"]=="independent_audit" and error["phase"]=="audit" and report["audit_validity"]=="failed")
    else: check(reason in {"observation_complete","missing_input","followup_horizon_insufficient"})
    if reason in {"observation_complete","missing_input","followup_horizon_insufficient","policy_or_admission_rejected","network_unresolved"}:
        check(error is None)
    policy="unresolved" if row is not None and row["status"]=="upstream_network_unresolved" else "rejected" if row is not None and row["status"]!="conditional_operating_point_committed" else "unresolved" if uncertain or evidence_unresolved or reason in {"network_unresolved","publication_outcome_unknown","independent_audit_failure"} else "not_rejected_in_accepted_prefix"
    check(report["policy_outcome"]==policy)
    balances=network["business_audit"]["balances"]
    misses=network["business_audit"]["deadline_misses"]
    tasks=[]
    for record in b["records"]:
        o=record["observation"]; birth=o["hour"]; deferred=Q(record["grid_served"])+Q(record["cfe_served"])
        remainder=balances[birth]["remaining"] if deferred else Q(0)
        missed=misses.get(birth) if deferred else Q(0)
        status="completed_on_arrival" if not deferred else "deadline_missed" if missed else "recovered_by_deadline" if not remainder else "right_censored_before_deadline"
        tasks.append(dict(birth=birth,due=o["due"],original=str(Q(o["workload"])),immediate=str(Q(o["workload"])-deferred),
            recovered=str(deferred-remainder),remaining=str(remainder),deadline_miss=None if missed is None else str(missed),
            balance_scope="scalar_policy_execution",status=status))
    check(tasks==report["all_arrived_tasks"],"arrived task accounting differs")
    primary=[v for v in tasks if 0<=v["birth"]<registration]
    censored=any(v["status"]=="right_censored_before_deadline" for v in primary)
    missed=sum((Q(v["deadline_miss"] or "0") for v in primary),Q(0))
    remaining=sum((Q(v["remaining"]) for v in primary),Q(0))
    check(Q(report["primary_remaining_debt"])==remaining)
    if reason=="observation_complete": check(last>=end and not censored)
    elif reason=="followup_horizon_insufficient": check(last>=end and censored)
    elif reason=="missing_input": check(last<end)
    relevant=[r for r in b["records"] if r["violations"]]
    satisfied=not relevant and not missed
    if satisfied and (last<end or censored): satisfied=None
    expected_assessment=dict(method="full_temporal",scope="scalar_fixed_policy",method_conditions_satisfied=satisfied,
        coverage_complete=last>=end,observed_through=last,observed_primary_deadline_miss=str(missed),primary_right_censored=censored,
        stopped=False,remaining_debt=str(sum((Q(v["remaining"]) for v in tasks),Q(0))),
        physical_replay_violations=[[r["observation"]["hour"],r["violations"]] for r in relevant],fx_contract_status="not_assessed_scalar_stub")
    check(same(report["business_prefix_assessment"],expected_assessment),"business assessment differs")
    return dict(scope="B3 independent terminal audit",accepted_hours=len(b["records"]),
        task_rows=len(tasks),network_audit=network,hypothetical_candidate_audit=hypothetical,
        termination_reason=reason,known_primary_miss=missed,primary_remaining_debt=remaining)
