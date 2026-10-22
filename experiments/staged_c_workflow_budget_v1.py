"""Static budget reconciliation from retained bytes; imports only stdlib."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NATIVE = "results/tables/staged_rts24_native_v1_non_authoritative/registration_v1.json"
NATIVE_SHA = "23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2"
COST_BASE = "results/tables/staged_rts24_append_cost_v1_non_authoritative/"
COST = COST_BASE+"execution_observations_01/checkpoint.json"
COST_SHA = "77cfe137b5836da41dcadb95744d1a9b6cd5dfe23d8c598b5b6724ec63ecbbb5"
FRAMES = "results/tables/staged_deliverability_rts24_v1_non_authoritative/build_01/network_frames.json"
FRAMES_SHA = "0102fce573222c14a87ba4f2a49f0eb00c3927bbe53ebebb79e0579f8afae406"
OUT = ROOT/"results/tables/staged_deliverability_c_budget_v1_non_authoritative/audit_01"
ROLES = ("reference_base_P0", "reference_raw_need", "recovery_min_meter", "recovery_max_meter")
NEW_SOURCES = ("experiments/staged_c_workflow_budget_v1.py", "tests/test_staged_c_workflow_budget_v1.py",
    "docs/plan/staged_deliverability_c_workflow_budget_reconciliation_v1.md")


def require(value, message):
    if not value: raise ValueError(message)


def profile(hour_roles, weights=None):
    """Count compiler invocations separately from the requests they describe."""
    require(type(hour_roles) in (list, tuple) and len(hour_roles) <= 10, "only existing <=10-hour shapes")
    n = len(hour_roles)
    if weights is None: weights = [3*(n-i)+2 for i in range(n)]
    require(len(weights) == n and all(type(w) is int and w >= 0 for w in weights), "invalid multiplicity")
    roles = Counter({r:0 for r in ROLES})
    for items, weight in zip(hour_roles, weights):
        require(type(items) in (tuple,list) and len(items) == len(set(items)) and "reference_base_P0" in items
            and set(items) <= set(ROLES), "invalid selective role set")
        require(("recovery_min_meter" in items) == ("recovery_max_meter" in items), "recovery pair missing")
        roles.update({role:weight for role in items})
    return dict(calls=sum(weights), descriptions=sum(roles.values()), roles=dict(roles), hour_calls=list(weights))


def combine(*values):
    require(values and len({len(v["hour_calls"]) for v in values}) == 1, "incompatible prefix profiles")
    roles = Counter({r:0 for r in ROLES})
    for value in values: roles.update(value["roles"])
    return dict(calls=sum(v["calls"] for v in values), descriptions=sum(v["descriptions"] for v in values),
        roles=dict(roles), hour_calls=[sum(v["hour_calls"][i] for v in values) for i in range(len(values[0]["hour_calls"]))])


def public_request_caps(selected_count):
    require(selected_count == 69,"only declared public scope")
    contract = 1+2*selected_count
    actual_full,actual_instant = 10+1+20+10,10+1+10
    def row(actual,frames,actual_qp):
        qp = actual_qp+frames*(1+selected_count)
        lp = actual-actual_qp+frames*selected_count
        return dict(actual=actual,contract=frames*contract,total=qp+lp,qp=qp,lp=lp,
            runtime_implemented=False,wall_estimate_seconds=None)
    return dict(basis="declared_ten_hour_one_actual_event_identity_specific_request_caps_not_runtime_budget",
        P2_two_contract_frames=row(actual_full,2,20),single_method_all_ten_frames=row(actual_full,10,20),
        three_methods_all_ten_frames=row(actual_instant+2*actual_full,30,60),
        three_method_actual_representative=dict(total=actual_instant+2*actual_full,per_method=[actual_instant,actual_full,actual_full],
            runtime_implemented=False,wall_estimate_seconds=None),D_points=None,E_holdout_paths=None,total_resource_estimate=None)


def p1_accounting(schedule, selected):
    require(len(schedule) == 31 and [row["ordinal"] for row in schedule] == list(range(1,32)), "P1 slots differ")
    hours = list(range(-2,3))
    role_sets = [[row["role"] for row in schedule if row["hour"] == hour and row["role"] in ROLES] for hour in hours]
    require(role_sets == [[ROLES[0],*ROLES[2:]], [ROLES[0],*ROLES[2:]], [ROLES[0],*ROLES[2:]],
        list(ROLES), [ROLES[0],*ROLES[2:]]], "registered actual-path shape differs")
    require(Counter(row["role"] for row in schedule) == Counter(dict(reference_base_P0=5,recovery_min_meter=5,
        recovery_max_meter=5,reference_raw_need=1,actual_P=5,normal_contract_C=2,fault_firm_F=4,fault_raw_need=4)), "registered roles differ")
    qp = sum(row["objective"] == "economic" for row in schedule)
    require(qp == 16, "registered QP/LP split differs")
    require(len(selected) == 69 and len({json.dumps(s,sort_keys=True) for s in selected}) == 69, "selected network states differ")
    require(sum(bool(s["branches"]) for s in selected) == 37 and sum(bool(s["generators"]) for s in selected) == 32,
        "branch/generator state split differs")
    one_pass, journal = profile(role_sets,[1]*5), profile(role_sets)
    contract_hours = sorted({row["hour"] for row in schedule if row["role"] == "normal_contract_C"})
    require(contract_hours == [1,2], "contract frames differ")
    full_descriptions = sum(1+2*len(selected)+len(role_sets[hours.index(h)]) for h in contract_hours)
    worker = combine(one_pass,one_pass,journal,journal)
    phases = dict(
        registration_preparation=dict(selective=one_pass,full_calls=2,full_descriptions=full_descriptions,numeric_compile=0,imports=0,fingerprints=1,preserve=1),
        launcher_preflight=dict(selective=one_pass,full_calls=2,full_descriptions=full_descriptions,numeric_compile=0,imports=0,fingerprints=1,preserve=1),
        worker=dict(selective=worker,full_calls=4,full_descriptions=2*full_descriptions,numeric_compile=62,imports=31,fingerprints=65,preserve=3),
        point_children=dict(selective=profile(role_sets,[0]*5),full_calls=0,full_descriptions=0,numeric_compile=62,imports=31,fingerprints=62,preserve=0),
        fresh=dict(selective=journal,full_calls=0,full_descriptions=0,numeric_compile=0,imports=0,fingerprints=2,preserve=0))
    total = combine(*(v["selective"] for v in phases.values()))
    execution = combine(*(v["selective"] for name,v in phases.items() if name != "registration_preparation"))
    return dict(basis="conditional_all_ancestors_successful_no_policy_stop_not_executed",hours=hours,
        selective_descriptions_per_hour=list(map(len,role_sets)),single_journal=journal,phases=phases,
        selective_total_including_historical_registration=total,selective_execution_only=execution,
        full_calls_including_registration=sum(v["full_calls"] for v in phases.values()),
        full_descriptions_including_registration=sum(v["full_descriptions"] for v in phases.values()),
        full_calls_execution_only=6,full_descriptions_execution_only=3*full_descriptions,
        numeric_compile=124,pyomo_build=124,imports=62,qp_slots=qp,lp_slots=len(schedule)-qp,
        native_slots=31,reopens=2,logical_child_launches=33,physical_job_member_count=None,
        audit_execution_calls=dict(worker=35,fresh=17,total=52),audit_row_visits=135,
        audit_row_visits_per_hour=[9*(5-i) for i in range(5)],
        fingerprints_calls=sum(v["fingerprints"] for v in phases.values()),preserve_calls=sum(v["preserve"] for v in phases.values()),
        nested_numeric_audit_and_CAS_invocations_exhaustively_counted=False,native_measured=False,wall_estimate_seconds=None)


class Reader:
    """One bounded read pass plus complete byte bookend; no scientific imports."""
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.pins, self.operations, self.bytes, self.started = {},0,0,time.perf_counter()

    def read(self, name, expected=None):
        require(type(name) is str and "\\" not in name and ":" not in name and name != "" and
            not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts, "unsafe input path")
        path = self.root/name
        require(path.resolve(strict=True).is_relative_to(self.root), "input escaped root")
        for parent in (path,*path.parents):
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400, "linked input")
            if parent == self.root: break
        before = path.stat()
        size = before.st_size
        self.operations += 1; self.bytes += size
        require(stat.S_ISREG(path.stat().st_mode) and size <= 2*1024**2 and self.operations <= 1800 and
            self.bytes <= 12*1024**2 and time.perf_counter()-self.started <= 20, "metadata read cap")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            require(os.path.samestat(before,opened) and opened.st_size == size,"input replaced before read")
            raw = stream.read(size+1)
            closed = os.fstat(stream.fileno())
        require(os.path.samestat(opened,path.stat()) and closed.st_size == size,"input changed during read")
        pin = dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        require(len(raw) == size,"input size changed")
        if isinstance(expected,dict): require(pin == expected,"input pin differs")
        elif expected is not None: require(pin["sha256"] == expected,"input pin differs")
        require(name not in self.pins or self.pins[name] == pin, "input changed during read")
        self.pins[name] = pin
        require(time.perf_counter()-self.started <= 20,"metadata read cap")
        return raw

    def json(self,name,expected=None): return json.loads(self.read(name,expected))

    def bookend(self):
        for name,pin in list(self.pins.items()): self.read(name,pin)


def reconcile(root=ROOT):
    reader = Reader(root)
    for name in NEW_SOURCES: reader.read(name)
    native, saved, frames = reader.json(NATIVE,NATIVE_SHA),reader.json(COST,COST_SHA),reader.json(FRAMES,FRAMES_SHA)
    require(native["native_authorized"] is False and not (reader.root/Path(NATIVE).parent/"p1_01").exists(), "P1 must remain unexecuted")
    require(saved["combined_counts"] == [198,548] and saved["source_pins"] and saved["resource_admission"] is False, "saved observation scope differs")
    for name,pin in native["pins"]["sources"].items(): reader.read(name,pin)
    for name,identity in native["pins"]["runtime"]["sources"].items(): reader.read(name,identity)
    for name,pin in saved["source_pins"].items(): reader.read(name,pin)
    for name,pin in saved["result_files"].items(): reader.read(COST_BASE+name,pin)
    report = reader.json(COST_BASE+"cost_probe_01/report.json")
    worker_timing = reader.json(COST_BASE+"cost_probe_01/worker_timing.json")
    require(worker_timing["phases"][:-1] == report["phases"] and worker_timing["phases"][-1]["stage"] == "saved_report",
        "saved report timing phase differs")
    verification = reader.json(COST_BASE+"execution_observations_01/verification_v2.json")
    require(verification["all_files_hash_matched"] and verification["exact_core_and_controller_maps"]
        and verification["per_case_parent_and_fresh_roles_checked"], "saved independent readback missing")
    observations = {}
    for role in ("preparation","measurement"):
        target = "cost_preparation_01" if role == "preparation" else "cost_probe_01"
        capture = reader.json(COST_BASE+"execution_observations_01/"+role+"_01/capture.json")
        timing = reader.json(COST_BASE+target+"/controller_timings.json")
        monitor = reader.json(COST_BASE+target+"/launcher.json")
        require(capture["accepted_success"] and capture["exit_code"] == 0 and timing["accepted_success"]
            and monitor["job_quiet_confirmed"], "saved terminal observation differs")
        observations[role] = dict(external_wall_seconds=capture["external_wall_seconds"],controller=timing,
            guard_outer_seconds=monitor["outer_seconds"],sampled_worker_tree_peak_rss_bytes=monitor["sampled_tree_peak_rss_bytes"],
            peak_job_commit_bytes=monitor["peak_job_commit_bytes"],scope="saved_three_bus_two_hours_fixed_order_not_P1_or_public_cost")
    accounting = p1_accounting(native["schedule"],frames["selected"])
    reader.bookend()
    require(not (reader.root/Path(NATIVE).parent/"p1_01").exists(), "P1 appeared during metadata audit")
    return dict(authority="DRAFT_NONAUTHORITATIVE",scope="static_public_workflow_budget_reconciliation",input_pins=reader.pins,
        p1=accounting,public_request_caps=public_request_caps(len(frames["selected"])),
        saved_observations=observations,saved_group_seconds=worker_timing["group_seconds"],
        saved_group_timing_scope="final_worker_ledger_includes_saved_report_excludes_own_record_and_terminal_publication",
        saved_core_files=saved["core_files"],saved_terminal_files=saved["terminal_files"],saved_terminal_bytes=saved["terminal_bytes"],
        native_calls_in_this_audit=0,scientific_compiler_calls_in_this_audit=0,model_builds_in_this_audit=0,
        logical_input_reads=reader.operations,logical_input_bytes=reader.bytes,metadata_audit_wall_seconds=time.perf_counter()-reader.started,
        environment_revalidated=False,static_source_bytes_revalidated=True,source_and_artifact_bookends=True,
        metadata_interpreter=dict(python=sys.version,executable=sys.executable,no_user_site=sys.flags.no_user_site,
            dont_write_bytecode=sys.dont_write_bytecode,argv=list(sys.orig_argv)),
        p1_attempt_created=False,overall_performance_review_complete=False,resource_admission=False,formal_result=False,
        official_verdict=None,seal=None,receipt=None)


if __name__ == "__main__":
    require(not OUT.exists(),"metadata output already exists")
    result = reconcile()
    raw = (json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    require(len(raw) <= 512*1024,"metadata output cap")
    require(OUT.parent.resolve(strict=True).is_relative_to(ROOT.resolve()),"linked metadata output parent")
    OUT.mkdir(exist_ok=False)
    with (OUT/"audit.json").open("xb") as stream: stream.write(raw)
    print(json.dumps(dict(input_files=len(result["input_pins"]),input_reads=result["logical_input_reads"],input_bytes=result["logical_input_bytes"],
        static_selective=result["p1"]["selective_total_including_historical_registration"]["calls"],
        static_descriptions=result["p1"]["selective_total_including_historical_registration"]["descriptions"],
        native_calls_in_this_audit=0,resource_admission=False),sort_keys=True))
