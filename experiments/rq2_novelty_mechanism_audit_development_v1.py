"""Read-only source audit and exact, small scheduling examples; no solver calls."""
from __future__ import annotations

import argparse
from collections import Counter, deque
import csv
from datetime import datetime, timedelta
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction as Q
import gzip
from hashlib import sha256
import io
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/rq2_novelty_mechanism_audit_v1.DRAFT.yaml"
RULE = "baseline_proportional_preaction_clean_allowance_v1"
TAU = Q(1, 1000000)
CATALOG = "results/tables/rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit_v2_final.json"
SUPPORTED_TOY = dict(
    role="constructed_diagnostic_not_a_finite_v2_cell_or_empirical_sample", hours=6,
    baseline="1/5", cfe_target="1/2", flexible_fraction="1/2",
    recovery_headroom_coefficient="3/10", grid_requests=["1/10","0","0","0","0","0"],
    ordinary_clean_share="1/2", deficit_hour=1, deficit_clean_share="1/4",
    recovery_candidate_hours=[2,3,4,5], clean_slots_per_profile=2,
    clean_share_at_recovery_slots="1", deadline_lags=[2,3,4], efficiencies=["1","17/20"],
    debt_initial="0", recovery_release="strictly_after_birth",
    deadline_check="after_recovery_at_due_hour", capacity_rule="q_plus_r_le_D",
    minimum_capacity_domain=["0","1"],
    controls=["remove_clean_recovery_limit","wait_until_deadline_policy"],
    construction_link="compare_installed_capacity_3_over_10_and_2_over_5")
SUPPORTED_PLAN = dict(solver_calls=0, network_calls=0, concurrency=1, source_cells=1900,
    arithmetic_groups=300, toy_profiles=6, toy_cases=36, maximum_jobs_per_case=2,
    maximum_subset_checks_per_case=3, maximum_output_bytes=4194304,
    maximum_input_file_bytes=16777216, maximum_peak_rss_bytes=536870912,
    wall_limit_seconds=45, output_directory_policy="create_once_preserve_attempts")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def validate_config(config):
    """This bounded diagnostic supports exactly the declared small design."""
    if (config["schema"] != "rq2_novelty_mechanism_audit_development_v1"
            or config["status"] != "DRAFT_NONAUTHORITATIVE"
            or config["purpose"] != "audit_retained_exclusions_and_construct_small_recovery_timing_examples"
            or any(config[name] is not False for name in
                   ("formal_result","formal_execution_ready","native_execution_authorized"))):
        raise ValueError("non-authoritative diagnostic contract required")
    if canonical(config["toy"]) != canonical(SUPPORTED_TOY):
        raise ValueError("unsupported toy semantics or design")
    if canonical(config["resource_plan"]) != canonical(SUPPORTED_PLAN):
        raise ValueError("unsupported resource plan or work inventory")


def validate_power_clock(rows):
    times = [datetime.fromisoformat(row["timestamp"]) for row in rows]
    if any(t.utcoffset() != timedelta(0) or t.minute or t.second or t.microsecond for t in times):
        raise ValueError("power timestamps must be whole UTC hours")
    origins = {t-timedelta(hours=int(row["source_hour"])) for t,row in zip(times,rows,strict=True)}
    if len(origins) != 1 or any(b-a != timedelta(hours=1) for a,b in zip(times,times[1:])):
        raise ValueError("power UTC clock differs from source-hour continuity")
    return dict(utc_start=times[0].isoformat(),utc_end=times[-1].isoformat(),
                utc_hour_rows_verified=len(times),source_hour_origin=next(iter(origins)).isoformat())


def validate_source_protocol(protocol):
    if (protocol["clean_allocation"], protocol["physical_capacity_rule"],
            protocol["joint_service"]) != ("action_independent_current_baseline_R_times_w",
            "q_plus_r_le_D", "additive_disjoint_service_commitment_benchmark"):
        raise ValueError("same finite-v2 contract required")
    anchor, mapping = protocol["business_anchor"],protocol["source_mapping"]
    if (Q(anchor["service_tolerance"]) != TAU or Q(anchor["minimum_event_power"]) != TAU
            or Q(anchor["time_step_hours"]) != 1 or protocol["window"]["enrollment_hours"] != 168
            or mapping["workload_projection_decimal_places"] != 12
            or mapping["workload_projection_rounding"] != "half_even"
            or mapping["power_rule"] != "linear_without_idle_offset"
            or protocol["capacity_domain"] != ["0","1"]):
        raise ValueError("protocol tolerance, clock, projection or capacity domain differs")


def exact_projection(text):
    if not 0 < Q(text) <= 1:
        raise ValueError("witness workload must be positive and in the declared domain")
    with localcontext() as ctx:
        ctx.prec = 70
        rounded = Decimal(text).quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
    result = Q(str(float(rounded)))
    if result == 0:
        raise ValueError("positive workload projects to zero")
    return result


def allocation(w, R, alpha):
    w, R, alpha = map(Q, (w, R, alpha))
    if not (0 <= w <= 1 and 0 <= R <= 1 and 0 < alpha <= 1):
        raise ValueError("allocation domain")
    raw = max(Q(0), w - R * w / alpha)
    return dict(workload=str(w), renewable_share=str(R), target=str(alpha),
                allowance=str(R*w), raw_request=str(raw),
                effective_request=str(raw if raw > TAU else Q(0)),
                compatible_surplus=str(max(Q(0), R*w/alpha-w)), rule=RULE)


def local_arithmetic(w, R, alpha, f, mapping_sha):
    a = allocation(w, R, alpha)
    w, f = Q(w), Q(f)
    if not 0 <= f <= 1:
        raise ValueError("flexible fraction domain")
    q = Q(a["effective_request"])
    gap = q-f*w
    return dict(allocation=a, allocation_identity=digest(dict(allocation=a,
        implementation_sha256=mapping_sha, service_tolerance="1e-06")),
        flexible_fraction=str(f), availability=str(f*w), activity_threshold=str(TAU),
        approved_contract_gap=str(gap), approved_contract_contradiction=q > TAU and gap > 0,
        relaxed_service_upper=str(f*w+TAU), relaxed_service_lower=str(q-TAU),
        contradiction_gap=str(gap-2*TAU), local_relaxation_empty=gap > 2*TAU,
        absence_of_contradiction_is_feasibility=False)


def audit_sources(config, read):
    """Rebuild selected raw witnesses and all saved arithmetic, not the H1 chain."""
    validate_config(config)
    spec = config["source_audit"]
    report = json.loads(read(spec["exclusion_report"], spec["exclusion_sha256"]))
    protocol = yaml.safe_load(read(spec["protocol"], spec["protocol_sha256"]))
    coverage = json.loads(read(spec["coverage"], spec["coverage_sha256"]))
    witness = report["witness"]
    if digest(witness) != report["witness_sha256"]:
        raise ValueError("witness content hash")
    if report["protocol_sha256"] != spec["protocol_sha256"]:
        raise ValueError("old or different protocol")
    if report["catalog_sha256"] != spec["catalog_sha256"] or report["source_sha256"][CATALOG] != spec["catalog_sha256"]:
        raise ValueError("catalog identity differs")
    validate_source_protocol(protocol)
    selected = {}
    clocks = {}
    for kind, path_key, hour_key in (("power", "power_rows", "source_hour"),
                                    ("workload", "workload_rows", "source_relative_hour")):
        name = spec[path_key]
        raw = read(name, report["source_sha256"][name])
        window = witness[kind+"_window"]
        if window not in coverage["windows"] or window["split"] != "training":
            raise ValueError("witness not in complete training support")
        start, end = window["source_start"], window["enrollment_end_inclusive"]
        rows = [row for row in csv.DictReader(io.StringIO(gzip.decompress(raw).decode()))
                if row["split"] == "training" and start <= int(row[hour_key]) <= end
                and (kind != "power" or int(row["outage_seed"]) == window["outage_seed"])]
        rows.sort(key=lambda row: int(row[hour_key]))
        if len(rows) != 168 or [int(row[hour_key]) for row in rows] != list(range(start, end+1)):
            raise ValueError("complete ordered enrollment source required")
        if rows != witness["whole_enrollment_source_windows"][kind]["rows"]:
            raise ValueError("saved window rows differ from raw CSV")
        offset = witness["relative_offset"]
        if rows[offset] != witness["selected_source_rows"][kind]:
            raise ValueError("selected raw source hour differs")
        clocks[kind] = validate_power_clock(rows) if kind == "power" else dict(
            source_relative_start=start,source_relative_end=end,relative_hour_rows_verified=len(rows),
            absolute_utc_timestamp_available=False)
        if kind == "power" and any(not 0 <= Q(row["cfe_call_fraction"]) <= 1 for row in rows):
            raise ValueError("invalid CFE source row")
        if kind == "workload":
            projections = [exact_projection(row["workload_fraction"]) for row in rows]
            saved = witness["whole_enrollment_workload_projection"]
            if len(saved) != 168 or any(p != Q(str(s["workload_occupancy"]))
                                       or s["status"] != "projected"
                                       for p, s in zip(projections, saved, strict=True)):
                raise ValueError("whole-window projection differs")
            selected[kind] = projections[offset]
        else:
            selected[kind] = 1-Q(rows[offset]["cfe_call_fraction"])
    w, R = selected["workload"], selected["power"]
    if w != Q(witness["projected_workload"]) or R != 1-Q(witness["source_cfe"]):
        raise ValueError("witness scalar mapping differs")
    mapping_path = "src/rq2_joint_deliverability_boundary_v1/cfe_preallocation.py"
    mapping_sha = report["source_sha256"][mapping_path]
    for name in (mapping_path, "src/rq2_joint_deliverability_boundary_v1/workload_projection.py",
                 "experiments/rq2_v2_cfe_exclusion_development_v1.py"):
        read(name, report["source_sha256"][name])
    # Recover theta independently from the approved YAML, keeping original order.
    thetas = []
    for f in protocol["design"]["primary_factorial"]["flexible_fraction"]:
        for rho in protocol["design"]["primary_factorial"]["recovery_headroom_coefficient"]:
            thetas.append(dict(protocol["business_anchor"], flexible_fraction=f,
                               recovery_headroom_coefficient=rho))
    for field in sorted(protocol["design"]["oat_non_anchor"]):
        for value in protocol["design"]["oat_non_anchor"][field]:
            thetas.append(dict(protocol["business_anchor"], **{field:value}))
    rows, counts, groups = [], Counter(), {}
    used_proofs, used_groups, used_cells = set(),set(),set()
    for cell in report["cells"]:
        ti, ai = cell["theta_index"], cell["alpha_index"]
        if not 0 <= ti < len(thetas) or not 0 <= ai < 100:
            raise ValueError("cell outside registered indices")
        if cell["theta"] != thetas[ti] or Q(cell["alpha"]) != Q(ai+1, 100):
            raise ValueError("cell is not the declared factorial/OAT grid")
        a, f = Q(cell["alpha"]), Q(cell["theta"]["flexible_fraction"])
        group_key = (a, f)
        if group_key not in groups:
            groups[group_key] = local_arithmetic(w, R, a, f, mapping_sha)
        rebuilt = groups[group_key]
        group_pin = digest(rebuilt)
        if group_pin != cell["arithmetic_group_sha256"] or rebuilt != report["arithmetic_groups"][group_pin]:
            raise ValueError("independent local arithmetic differs")
        identity = dict(protocol_sha256=spec["protocol_sha256"], theta=cell["theta"], alpha=cell["alpha"])
        if digest(identity) != cell["cell_sha256"]:
            raise ValueError("cell identity differs")
        excluded = rebuilt["local_relaxation_empty"]
        if excluded:
            proof = report["proofs"][cell["proof_sha256"]]
            expected_proof = dict(schema="rq2_v2_cfe_exclusion_development_v1",
                lemma="local_service_relaxation_contradiction_v1",protocol_sha256=spec["protocol_sha256"],
                catalog_sha256=spec["catalog_sha256"],witness_sha256=report["witness_sha256"],
                arithmetic=rebuilt,registered_capacity_domain=protocol["capacity_domain"],
                affected_arms=["CFE-only","joint-correct","joint-B6"],
                policy_quantifier="every complete causal policy in the named v2 contract",
                normal_reference_feasibility_not_assumed=True,formal_result=False)
            if digest(proof) != cell["proof_sha256"] or canonical(proof) != canonical(expected_proof):
                raise ValueError("proof identity, envelope or arithmetic differs")
            used_proofs.add(cell["proof_sha256"])
        elif cell["proof_sha256"] is not None:
            raise ValueError("nonpositive gap has a proof")
        expected_status="cell_local_relaxation_contradiction" if excluded else "no_contradiction_from_selected_witness"
        if cell["status"] != expected_status:
            raise ValueError("cell disposition differs")
        if cell["network_only_conclusion"] is not None:
            raise ValueError("CFE evidence must not resolve network-only")
        counts[ti, excluded] += 1
        used_cells.add(cell["cell_sha256"]);used_groups.add(group_pin)
        rows.append(dict(theta_index=ti, alpha=str(a), flexible_fraction=str(f),
                         cell_sha256=cell["cell_sha256"],arithmetic_group_sha256=group_pin,
                         proof_sha256=cell["proof_sha256"],saved_status=cell["status"],
                         excluded_by_instantaneous_witness=excluded,
                         raw_request=rebuilt["allocation"]["raw_request"],
                         available=rebuilt["availability"], relaxed_gap=rebuilt["contradiction_gap"]))
    if (len(rows),len(groups),len(used_cells)) != (config["resource_plan"]["source_cells"],
            config["resource_plan"]["arithmetic_groups"],config["resource_plan"]["source_cells"]):
        raise ValueError("full cell inventory differs")
    if used_groups != set(report["arithmetic_groups"]) or used_proofs != set(report["proofs"]) or len(used_proofs) != 292:
        raise ValueError("arithmetic/proof inventories do not close")
    excluded_count = sum(r["excluded_by_instantaneous_witness"] for r in rows)
    if excluded_count != report["contradicted_cell_count"]:
        raise ValueError("saved exclusion count differs")
    summary = [dict(theta_index=i, flexible_fraction=t["flexible_fraction"],
                    recovery_headroom_coefficient=t["recovery_headroom_coefficient"],
                    excluded=counts[i,True], unresolved=counts[i,False],
                    unresolved_alpha=[r["alpha"] for r in rows if r["theta_index"] == i
                                      and not r["excluded_by_instantaneous_witness"]])
               for i,t in enumerate(thetas)]
    inventory = dict(cell_sha256=sorted(used_cells),arithmetic_group_sha256=sorted(used_groups),
                     proof_sha256=sorted(used_proofs))
    return dict(status="DRAFT_NONAUTHORITATIVE", source_hours=witness["raw_source_hours"],source_clocks=clocks,
        projected_workload=str(w), clean_share=str(R), excluded_cells=excluded_count,
        unresolved_cfe_cells=1900-excluded_count, unresolved_network_cells=1900,
        exact_arithmetic_groups=len(groups), independent_projection_rows=168,
        exact_proof_count=len(used_proofs),identity_inventories=inventory,
        identity_inventory_sha256=digest(inventory),identity_sets_closed=True,
        threshold_without_activity_tolerance={str(f):str(R/(1-f)) for f in (Q(1,20),Q(1,5),Q(1,2))},
        all_recorded_exclusions_have_instantaneous_cause=True, recovery_conflicts_evaluated=False,
        full_nested_source_reaudit=False, runtime_reachability_proven=False,
        holdout_outcomes_evaluated=False, per_theta=summary, cells=rows)


def subset_capacity(work, caps):
    """Invert sum(min(D,u)) >= work exactly; None means insufficient total supply."""
    work = Q(work)
    caps = [Q(c) for c in caps]
    if work < 0 or any(c < 0 for c in caps):
        raise ValueError("nonnegative work/caps required")
    caps = sorted(c for c in caps if c > 0)
    if work == 0:
        return Q(0)
    if sum(caps) < work:
        return None
    used = Q(0)
    for i, cap in enumerate(caps):
        candidate = (work-used)/(len(caps)-i)
        if candidate <= cap:
            return max(Q(0), candidate)
        used += cap
    raise AssertionError("unreachable capacity inversion")


def minimum_capacity(jobs, q, u):
    if len(q) != len(u) or any(v < 0 for v in (*q,*u)) or any(a and b for a,b in zip(q,u)):
        raise ValueError("this diagnostic requires separate call and recovery slots")
    required, cuts = max(q, default=Q(0)), []
    for size in range(1,len(jobs)+1):
        for chosen in combinations(range(len(jobs)),size):
            slots = sorted({t for j in chosen for t in range(jobs[j]["birth"]+1,jobs[j]["due"]+1)})
            work = sum((jobs[j]["recovery_energy"] for j in chosen),Q(0))
            bound = subset_capacity(work,[u[t] for t in slots])
            cut = dict(jobs=list(chosen),slots=slots, recovery_energy=str(work),
                       total_supply=str(sum((u[t] for t in slots),Q(0))),
                       minimum_D=None if bound is None else str(bound))
            cuts.append(cut)
            if bound is None:
                return None,cuts
            required = max(required,bound)
    return required,cuts


def flow_schedule(jobs, u, capacity):
    """Independent exact bipartite maximum flow, with an explicit recovery witness."""
    n, T = len(jobs),len(u)
    sink = n+T+1
    residual = [dict() for _ in range(sink+1)]
    original = {}
    def edge(a,b,cap):
        residual[a][b] = cap
        residual[b][a] = Q(0)
        original[a,b] = cap
    total = sum((j["recovery_energy"] for j in jobs),Q(0))
    for j,job in enumerate(jobs):
        edge(0,1+j,job["recovery_energy"])
        for t in range(job["birth"]+1,job["due"]+1):
            edge(1+j,1+n+t,total)
    for t,cap in enumerate(u):
        edge(1+n+t,sink,min(capacity,cap))
    sent = Q(0)
    while True:
        parents = {0:None}
        queue = deque([0])
        while queue and sink not in parents:
            a=queue.popleft()
            for b,cap in residual[a].items():
                if cap > 0 and b not in parents:
                    parents[b]=a
                    queue.append(b)
        if sink not in parents:
            break
        amount=total
        b=sink
        while parents[b] is not None:
            a=parents[b];amount=min(amount,residual[a][b]);b=a
        b=sink
        while parents[b] is not None:
            a=parents[b];residual[a][b]-=amount;residual[b][a]+=amount;b=a
        sent+=amount
    schedule = [[original.get((1+j,1+n+t),Q(0))-residual[1+j].get(1+n+t,Q(0))
                 for t in range(T)] for j in range(n)]
    return sent,schedule


def causal_edf(case, capacity, *, wait=False):
    """Read only the current q/u and pending cohorts; no future availability lookup."""
    pending, recovered, actions = [],Q(0),[]
    eta=case["eta"]
    missed=False;violations=[]
    for t,(q,u) in enumerate(zip(case["q"],case["u"],strict=True)):
        if q:
            pending.append([t,t+case["lag"],q])
        remaining=min(u,max(Q(0),capacity-q))
        if wait and not any(birth < t and due <= t and debt > 0 for birth,due,debt in pending):
            remaining=Q(0)
        r=Q(0)
        for item in sorted(pending,key=lambda item:(item[1],item[0])):
            if item[0] < t:
                take=min(remaining,item[2]/eta)
                item[2]-=eta*take;remaining-=take;r+=take
        recovered+=eta*r
        for birth,due,debt in pending:
            if due == t and debt > 0:
                violations.append(dict(hour=t,birth=birth,due=due,unfinished_work=str(debt)))
        missed |= any(due <= t and debt > 0 for birth,due,debt in pending)
        actions.append(r)
    return dict(success=not missed and all(debt == 0 for _,_,debt in pending),
                recovered_work=str(recovered),recovery=[str(r) for r in actions],deadline_violations=violations)


def make_case(toy, slots, lag, eta, *, installed_capacity=None):
    w,alpha,f=map(Q,(toy["baseline"],toy["cfe_target"],toy["flexible_fraction"]))
    R=[Q(toy["ordinary_clean_share"])]*toy["hours"]
    R[toy["deficit_hour"]]=Q(toy["deficit_clean_share"])
    for t in slots:
        R[t]=Q(toy["clean_share_at_recovery_slots"])
    allocations=[allocation(w,v,alpha) for v in R]
    grid_q=list(map(Q,toy["grid_requests"]))
    cfe_q=[Q(a["effective_request"]) for a in allocations]
    q=[g+c for g,c in zip(grid_q,cfe_q,strict=True)]
    if any(v > f*w for v in q):
        raise ValueError("constructed case violates pointwise available work")
    h=Q(toy["recovery_headroom_coefficient"])*(1-w) if installed_capacity is None else Q(installed_capacity)-w
    if h < 0:
        raise ValueError("installed capacity below baseline")
    surplus=[Q(a["compatible_surplus"]) for a in allocations]
    u=[min(h,s) for s in surplus]
    jobs=[dict(birth=t,due=t+lag,work=v,recovery_energy=v/eta) for t,v in enumerate(q) if v]
    if any(j["due"] >= len(q) for j in jobs):
        raise ValueError("incomplete deadline coverage")
    return dict(slots=tuple(slots),lag=lag,eta=eta,q=q,grid_request=grid_q,cfe_request=cfe_q,
        u=u,R=R,allowance=[Q(a["allowance"]) for a in allocations],jobs=jobs)


def analyze_case(case):
    D,cuts=minimum_capacity(case["jobs"],case["q"],case["u"])
    if D is not None and not Q(0) <= D <= Q(1):
        raise ValueError("constructed minimum D outside diagnostic domain")
    probe=D if D is not None else Q(1)
    sent,schedule=flow_schedule(case["jobs"],case["u"],probe)
    total=sum((j["recovery_energy"] for j in case["jobs"]),Q(0))
    if (sent == total) != (D is not None):
        raise AssertionError("cut oracle and independent max flow disagree")
    if D is not None:
        for j,job in enumerate(case["jobs"]):
            if sum(schedule[j]) != job["recovery_energy"]:
                raise AssertionError("unfinished work in successful flow")
        for t,q in enumerate(case["q"]):
            r=sum((row[t] for row in schedule),Q(0))
            if q+r > D or r > case["u"][t] or any(row[t] < 0 for row in schedule):
                raise AssertionError("invalid power/recovery witness")
    edf=causal_edf(case,probe)
    if D is not None and not edf["success"]:
        raise AssertionError("constructed success lacks this current-information witness")
    return dict(clean_slots=list(case["slots"]),deadline_lag=case["lag"],eta=str(case["eta"]),
        grid_request=[str(x) for x in case["grid_request"]],cfe_request=[str(x) for x in case["cfe_request"]],
        clean_share=[str(x) for x in case["R"]],allowance=[str(x) for x in case["allowance"]],
        q=[str(x) for x in case["q"]],recovery_caps=[str(x) for x in case["u"]],
        minimum_D=None if D is None else str(D),cuts=cuts,
        maxflow_recovery_energy=str(sent),required_recovery_energy=str(total),
        flow_recovery_by_job=[[str(x) for x in row] for row in schedule],
        causal_edf=edf,wait_until_deadline_policy=causal_edf(case,probe,wait=True))


def toy_audit(toy):
    if canonical(toy) != canonical(SUPPORTED_TOY):
        raise ValueError("unsupported toy semantics or design")
    cases=[]
    prefix_checks=0
    for slots in combinations(toy["recovery_candidate_hours"],toy["clean_slots_per_profile"]):
        for lag in toy["deadline_lags"]:
            for eta in map(Q,toy["efficiencies"]):
                case=make_case(toy,slots,lag,eta)
                actual_D,_=minimum_capacity(case["jobs"],case["q"],case["u"])
                probe=actual_D if actual_D is not None else Q(1)
                for prefix in range(toy["hours"]):
                    for future_q in (Q(0),Q(1,10)):
                        changed=dict(case,u=[v if t <= prefix else Q(0) for t,v in enumerate(case["u"])],
                            q=[v if t <= prefix else future_q for t,v in enumerate(case["q"])])
                        if (causal_edf(changed,probe)["recovery"][:prefix+1]
                                != causal_edf(case,probe)["recovery"][:prefix+1]):
                            raise AssertionError("future request/recovery suffix changed a current action")
                        prefix_checks+=1
                if len(case["jobs"]) > SUPPORTED_PLAN["maximum_jobs_per_case"] or 2**len(case["jobs"])-1 > SUPPORTED_PLAN["maximum_subset_checks_per_case"]:
                    raise ValueError("job/subset work inventory exceeded")
                cases.append(analyze_case(case))
    if len(cases) != SUPPORTED_PLAN["toy_cases"] or len({tuple(c["clean_slots"]) for c in cases}) != SUPPORTED_PLAN["toy_profiles"]:
        raise ValueError("toy profile/case inventory differs")
    good=make_case(toy,(2,3),3,Q(1));late=make_case(toy,(3,5),3,Q(1))
    if (any(good[k] != late[k] for k in ("q","grid_request","cfe_request"))
            or sorted(good["R"]) != sorted(late["R"])
            or sum(good["allowance"]) != sum(late["allowance"])
            or max(good["allowance"]) != max(late["allowance"])):
        raise AssertionError("matched comparison changes non-timing inputs")
    controls=[]
    for case in (good,late):
        h=Q(toy["recovery_headroom_coefficient"])*(1-Q(toy["baseline"]))
        control=dict(case,u=[Q(0) if q else h for q in case["q"]])
        controls.append(analyze_case(control))
    bridge=[dict(installed_capacity=K,**analyze_case(make_case(toy,slots,3,Q(1),installed_capacity=K)))
            for slots in ((2,3),(3,5)) for K in ("3/10","2/5")]
    return dict(role=toy["role"],cases=cases,clean_limit_controls=controls,
        installed_capacity_headroom_examples=bridge,
        common_prefix_future_perturbation_checks=prefix_checks,
        prefix_check_scope="finite_future_q_and_u_suffix_perturbations_at_case_D_or_unit_probe",
        full_support_causal_policy_proven=False,
        exact_toy_capacity_is_not_original_protocol_bound=True,
        stochastic_construction_planning_implemented=False)


def peak_rss():
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("faults",wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
          ("peak_ws","ws","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile")]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    get_process=ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype=ctypes.c_void_p
    get_info=ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),wintypes.DWORD]
    if not get_info(get_process(),ctypes.byref(counters),counters.cb):
        raise OSError("process memory observation failed")
    return counters.peak_ws


def run(config_path, output):
    start=perf_counter()
    output.mkdir(parents=True,exist_ok=False)
    config_raw=config_path.read_bytes();config=yaml.safe_load(config_raw)
    plan=config["resource_plan"]
    pins={};phases={}
    def check():
        if perf_counter()-start > plan["wall_limit_seconds"]:
            raise TimeoutError("declared whole-path wall budget exceeded")
        if peak_rss() > plan["maximum_peak_rss_bytes"]:
            raise MemoryError("declared peak RSS budget exceeded")
    def read(name,pin=None):
        check();path=ROOT/name
        if path.stat().st_size > plan["maximum_input_file_bytes"]:
            raise ValueError("input file byte cap")
        raw=path.read_bytes();h=sha256(raw).hexdigest()
        if pin is not None and h != pin:
            raise ValueError("pinned input differs: "+name)
        pins[name]=h
        return raw
    try:
        validate_config(config)
        read(config_path.relative_to(ROOT).as_posix(),sha256(config_raw).hexdigest())
        read(Path(__file__).relative_to(ROOT).as_posix())
        t=perf_counter();source=audit_sources(config,read);phases["source_and_1900_cells"]=perf_counter()-t
        check();t=perf_counter();toys=toy_audit(config["toy"]);phases["exact_toys_and_oracles"]=perf_counter()-t
        result=dict(schema=config["schema"],status="DRAFT_NONAUTHORITATIVE",formal_result=False,
            formal_execution_ready=False,resource_admission=False,native_execution_authorized=False,
            solver_calls=0,source_audit=source,toy_audit=toys,source_sha256=pins)
        for name,h in list(pins.items()):
            if sha256((ROOT/name).read_bytes()).hexdigest() != h:
                raise ValueError("input changed during read-only audit: "+name)
        check();t=perf_counter()
        rows=source.pop("cells")
        with (output/"cell_causes.csv").open("x",encoding="utf-8-sig",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        raw=canonical(result)
        with (output/"analysis.json").open("xb") as f:f.write(raw+b"\n")
        if json.loads((output/"analysis.json").read_bytes()) != result:
            raise ValueError("result readback differs")
        phases["write_and_readback"]=perf_counter()-t
        size=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        if size+8192 > plan["maximum_output_bytes"]:
            raise ValueError("output byte budget exceeded")
        check()
        terminal=dict(status="completed_development_diagnostic",wall_seconds=perf_counter()-start,
            phase_wall_seconds=phases,peak_rss_bytes=peak_rss(),output_bytes_before_terminal=size,
            source_files_verified=len(pins),source_before_after_sha_equal=True,solver_calls=0,
            formal_result=False,formal_execution_ready=False,production_resource_admission=False)
        with (output/"terminal.json").open("xb") as f:f.write(canonical(terminal)+b"\n")
        print(json.dumps(dict(excluded=source["excluded_cells"],unknown=source["unresolved_cfe_cells"],
            toy_cases=len(toys["cases"]),wall_seconds=terminal["wall_seconds"],output=str(output))))
        return result
    except Exception as error:
        with (output/"failed.json").open("xb") as f:
            f.write(canonical(dict(status="failed_preserved",error_type=type(error).__name__,
                                  message=str(error),elapsed=perf_counter()-start))+b"\n")
        raise


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/CONFIG)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.config.resolve(),args.output.resolve())
