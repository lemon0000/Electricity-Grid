"""Explicit P1 worker/point/fresh modes. Importing this module never starts work."""
import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
import hashlib
import importlib
from importlib.metadata import Distribution, distribution, version
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/p1_01"
REGISTRATION = OUTPUT.parent/"registration_v1.json"
COMPUTE = Path("D:/Miniconda3/envs/compute/python.exe")
COMPUTE_SHA = "4a7d81f72d979c088c653b1da12c2f2d81da66bdf8074753c6a9b154d9c86116"
NUMERIC_CHECKS_SHA = "87e7ad75eb3309e6ec5a58e486719462d6d3ed681e82e960ebcf47e6db191eeb"
METHOD, PLAN, CLEAN = "full_temporal", "on_time", "early"
MAX_CALLS = 31
LIMITS = dict(wall_seconds=300, no_progress_seconds=30, rss_bytes=1024**3, output_bytes=64*1024**2, files=5000)
POINT_LIMITS = {**LIMITS, "wall_seconds": 10, "no_progress_seconds": 10}
FRESH_LIMITS = {**LIMITS, "wall_seconds": 20, "no_progress_seconds": 20}
SOURCES = ("AGENTS.md", "agent.md", "docs/plan/staged_deliverability_c_public_numeric_package_plan_v1.md",
    "src/staged_rts24_highs_backend_v1.py", "src/staged_rts24_process_guard_v1.py",
    "src/staged_rts24_numeric_interface_v1.py", "src/rq2_joint_deliverability_boundary_v1/normal_process.py",
    "experiments/staged_rts24_native_probe_v1.py", "experiments/staged_rts24_native_launcher_v1.py",
    "tests/test_staged_rts24_highs_backend_v1.py", "tests/test_staged_rts24_process_guard_v1.py",
    "tests/test_staged_rts24_native_probe_v1.py", "docs/plan/staged_deliverability_c_native_p1_contract_v1.md")
OLD_CORES = {
    "results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01": "dbb0200384c5706bc43001981f943308c5f612f5402ac51e623944718a6f3620",
    "results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01": "2826a634b43be911b3911c1666e295d98edc07d7185e0a5fcd08ad9e71fac6ae",
}


def modules():
    from src import staged_rts24_development_v1 as c, staged_rts24_evidence_store_v1 as codec
    return c, codec


def write(path, value):
    _, codec = modules()
    return codec.publish(Path(path), codec.canonical(value))


def load(path):
    _, codec = modules()
    return codec.parse(codec.read_bytes(path))


def stamp(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink(): raise ValueError("ordinary source required")
    h, size = hashlib.sha256(), 0
    with path.open("rb") as f:
        while data := f.read(1024**2): h.update(data); size += len(data)
    return dict(bytes=size, sha256=h.hexdigest())


def fingerprints():
    from src import staged_rts24_journal_v2 as journal
    from src.staged_rts24_highs_backend_v1 import VERSION, OPTIONS
    from src.staged_rts24_process_guard_v1 import controlled_environment
    c, _ = modules()
    c.require(version("highspy") == VERSION, "registered highspy package version differs")
    native = {}
    for name in ("highspy", "numpy", "pyomo"):
        dist = distribution(name)
        for item in dist.files or ():
            rel = str(item).replace("\\", "/")
            metadata = rel.endswith((".dist-info/METADATA", ".dist-info/RECORD", ".dist-info/WHEEL"))
            selected_binary = name in ("highspy", "numpy") and rel.endswith((".pyd", ".dll"))
            selected_source = name == "highspy" and rel.endswith((".py", ".pyi"))
            if metadata or selected_binary or selected_source:
                path = Path(dist.locate_file(item)).resolve(strict=True)
                native["distribution/"+name+"/"+rel] = stamp(path)
    for name in ("pyomo.repn.standard_repn", "pyomo.core.expr.numeric_expr", "pyomo.core.expr.numvalue",
                 "pyomo.core.expr.relational_expr", "pyomo.core.base.var", "pyomo.core.base.constraint",
                 "pyomo.core.base.objective"):
        path = Path(importlib.import_module(name).__file__).resolve(strict=True)
        native["module/"+name] = stamp(path)
    for name in ("python312.dll", "vcruntime140.dll", "vcruntime140_1.dll", "zlib.dll"):
        path = Path(sys.executable).parent/name
        c.require(path.is_file(), "registered Python runtime component missing")
        native["runtime/"+name] = stamp(path)
    return dict(runtime=journal.runtime_identity(), sources={p: stamp(ROOT/p) for p in SOURCES},
        selected_application_files=native, options=OPTIONS, python=sys.version, executable=str(Path(sys.executable).absolute()),
        controlled_environment_sha=c.digest(controlled_environment()),
        host_windows=list(sys.getwindowsversion()) if os.name == "nt" else None,
        boundary="selected_application_files_and_dist_records_not_full_stdlib_or_resolved_OS_closure")


def preserve():
    c, _ = modules()
    # Verify retained bytes directly. Importing historical diagnostic programs
    # would load their optional user-site psutil, absent in the controlled child.
    def saved(path):
        _, codec = modules()
        return json.loads(codec.read_bytes(path))
    audit_path = ROOT/"results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01/audit.json"
    c.require(stamp(audit_path)["sha256"] == "9a04b13e1778614ecefac1890c0f68ab30d81dd5990b7be2cf6c745763ff6e90", "old audit anchor differs")
    audit = saved(audit_path)
    overlap = set(audit["saved_files"]) & set(audit["repository_pins"])
    c.require(all(audit["saved_files"][p] == audit["repository_pins"][p] for p in overlap), "old pin overlap differs")
    files = {**audit["saved_files"], **audit["repository_pins"]}
    c.require(all(stamp(ROOT/p) == pin for p, pin in files.items()), "B1-B3 source or artifact differs")
    b3 = saved(ROOT/"results/tables/staged_deliverability_b3_v1_non_authoritative/attempt_01/report.json")["fingerprints"]
    external = {name: stamp(item["path"]) for name, item in b3["external_selected"].items()}
    c.require(external == audit["selected_external"], "old selected external bytes differ")
    import site
    # Metadata discovery does not enable/import user-site packages. Preserve the
    # historical version check while keeping that optional module unimported.
    matches = [d for d in Distribution.discover(name="psutil", path=[site.getusersitepackages()])
               if d.version == b3["versions"]["psutil"]]
    c.require(len(matches) == 1, "unique historical psutil distribution required")
    dist = matches[0]
    historical_metadata = {str(item): stamp(dist.locate_file(item)) for item in dist.files or ()
        if str(item).replace("\\", "/").endswith((".dist-info/METADATA", ".dist-info/RECORD", ".dist-info/WHEEL"))}
    c.require({Path(p).name for p in historical_metadata} == {"METADATA", "RECORD", "WHEEL"}, "historical psutil metadata unavailable")
    def dependency(name): return dist.version if name.lower() == "psutil" else version(name)
    c.require(all(dependency(name) == expected for name, expected in b3["versions"].items()), "old dependency version differs")
    build = ROOT/"results/tables/staged_deliverability_rts24_v1_non_authoritative/build_01"
    build_pins = saved(build/"report.json")["fingerprints"]
    build_sources = ("configs/staged_deliverability_rts24_v1.DRAFT.yaml", "src/staged_rts24_development_v1.py",
        "src/staged_rts24_audit_v1.py", "experiments/staged_rts24_analytic_examples_v1.py",
        "experiments/staged_rts24_build_diagnostic_v1.py", "tests/test_staged_rts24_development_v1.py",
        "docs/model_spec/staged_deliverability_rts24_development_v1.md",
        "docs/plan/staged_deliverability_c_rts24_build_contract_v1.md")
    current = dict(repository={p: stamp(ROOT/p) for p in build_sources}, prior_audit=stamp(audit_path),
        public_case=stamp(importlib.import_module("pypower.case24_ieee_rts").__file__),
        versions={name: dependency(name) for name in ("PYPOWER", "Pyomo", "PyYAML", "numpy", "scipy", "psutil")},
        python=sys.version, executable=sys.executable)
    c.require(current == build_pins, "old build dependency differs")
    c.require(stamp(build/"completion.json")["bytes"] <= 4*1024**2, "old build completion too large")
    completion = saved(build/"completion.json")
    supplements = {"completion.json", "launcher.json", "postcheck.py", "verification.json", "preseal_findings.json", "validation_report.md"}
    paths = tuple(build.iterdir())
    c.require(all(p.is_file() and not p.is_symlink() for p in paths), "nonregular old build artifact")
    actual = {p.name: stamp(p) for p in paths if p.name not in supplements}
    c.require(completion["status"] == "build_only_diagnostic_completed" and completion["authority"] == "DRAFT_NONAUTHORITATIVE"
              and set(actual) == {"start.json", "network_frames.json", "query_dag.json", "analytic_points.json",
                  "model_shapes.json", "report.json", "events.jsonl"}
              and actual == completion["inventory"] and not (build/"failure.json").exists(), "old build completion differs")
    causal = saved(ROOT/"results/tables/staged_rts24_causal_v1_non_authoritative/development_checks_01/verification.json")
    c.require(all(stamp(ROOT/p) == pin for p, pin in causal["new_bound_sources"].items()), "old causal source differs")
    old_c = saved(audit_path.with_name("start.json"))["bindings"]
    c.require(all(stamp(ROOT/p) == pin for p, pin in old_c.items()), "old C source differs")
    result = dict(prior=dict(b1_b3_files=len(audit["saved_files"]), repository_pins=len(audit["repository_pins"]),
        unique=len(files), selected_external=external, old_c_bindings=old_c, public_build_checked=True,
        causal_sources=len(causal["new_bound_sources"])), cores={}, historical_psutil_metadata=historical_metadata)
    for name, expected in OLD_CORES.items():
        root = ROOT/name
        c.require(stamp(root/"completion.json")["sha256"] == expected, "old completion anchor differs")
        manifest = load(root/"completion.json")
        c.require(all(stamp(root/p) == pin for p, pin in manifest["files"].items()), "old core differs")
        result["cores"][name] = expected
    checks = ROOT/"results/tables/staged_rts24_numeric_interface_v1_non_authoritative/development_checks.json"
    _, codec = modules()
    raw = codec.read_bytes(checks)
    c.require(hashlib.sha256(raw).hexdigest() == NUMERIC_CHECKS_SHA, "historical numeric checks bytes differ")
    # Historical report is pretty JSON. Do not rewrite it to the live protocol's
    # canonical format; its existing exact bytes are the trust anchor.
    previous = json.loads(raw)
    c.require(all(stamp(ROOT/p) == pin for p, pin in previous["source_pins"].items()), "numeric source bytes changed")
    result["numeric_interface_checks"] = dict(bytes=len(raw), sha256=NUMERIC_CHECKS_SHA)
    return result


def require_compute():
    c, _ = modules()
    c.require(Path(sys.executable).resolve() == COMPUTE.resolve()
              and stamp(sys.executable)["sha256"] == COMPUTE_SHA, "exact registered compute interpreter required")


def registration_record():
    """Read-only preparation; no attempt directory, native object or solve."""
    require_compute()
    c, _ = modules()
    schedule = request_schedule(c.load_fixture())
    return dict(schema="staged_rts24_native_registration_v1", authority="DRAFT_NONAUTHORITATIVE",
        native_authorized=False, output=str(OUTPUT), limits=LIMITS, point_limits=POINT_LIMITS,
        fresh_limits=FRESH_LIMITS, max_point_attempts=MAX_CALLS, schedule=schedule,
        schedule_sha=c.digest(schedule), pins=fingerprints(), preserved=preserve(),
        authorization="separate_explicit_user_instruction_required_not_granted_by_this_file")


def verify_registration(expected_sha, *, full=True):
    require_compute()
    c, _ = modules()
    c.require(type(expected_sha) is str and len(expected_sha) == 64
              and stamp(REGISTRATION)["sha256"] == expected_sha, "registration SHA differs")
    record = load(REGISTRATION)
    expected = dict(schema="staged_rts24_native_registration_v1", authority="DRAFT_NONAUTHORITATIVE",
        native_authorized=False, output=str(OUTPUT), limits=LIMITS, point_limits=POINT_LIMITS,
        fresh_limits=FRESH_LIMITS, max_point_attempts=MAX_CALLS,
        authorization="separate_explicit_user_instruction_required_not_granted_by_this_file")
    c.require(set(record) == {*expected, "schedule", "schedule_sha", "pins", "preserved"}
              and all(record.get(k) == v for k, v in expected.items()), "registration scope differs")
    c.require(record["schedule_sha"] == c.digest(record["schedule"]), "registration schedule digest differs")
    if full:
        schedule = request_schedule(c.load_fixture())
        c.require(record["schedule_sha"] == c.digest(schedule)
                  and record["pins"] == fingerprints(), "registered schedule or dependencies differ")
    return record


def install_observers(*, allow_native, api=None):
    """Selected inclusive timings/counters; CLI-only, not a total I/O profiler."""
    from src import staged_rts24_journal_v2 as journal, staged_rts24_causal_v2 as policy
    from src import staged_rts24_causal_audit_v2 as audit, staged_rts24_reference_queries_v1 as selective
    from src import staged_rts24_numeric_interface_v1 as numeric
    from src import staged_rts24_highs_backend_v1 as backend
    import pyomo.environ as pyo
    c, codec = modules()
    counts, seconds, stack = Counter(), Counter(), []

    def measured(label, function, result_hook=None):
        def wrapped(*a, **kw):
            counts[label+"_attempts"] += 1
            in_replay = "journal_reopen" in stack
            if in_replay:
                counts["replay/"+label+"_attempts"] += 1
                if label in ("numeric_compile", "pyomo_build", "native_call", "native_model", "cas_put", "publication"):
                    raise TransportUnresolved("new evidence or publication during read-only replay")
            if label == "numeric_compile": counts["importer_recompile" if "numeric_import" in stack else "explicit_compile"] += 1
            started = time.perf_counter()
            stack.append(label)
            try:
                result = function(*a, **kw)
                counts[label+"_returned"] += 1
                if result_hook is not None: result_hook(result)
                return result
            except BaseException:
                counts[label+"_raised"] += 1
                raise
            finally:
                stack.pop()
                seconds[label] += time.perf_counter()-started
        return wrapped

    def descriptions(label):
        def record(value):
            counts[label+"_descriptions"] += len(value["requests"])
            counts.update(label+"_role_"+q.role for q in value["requests"])
        return record
    c.hour_requests = measured("full_compile", c.hour_requests, descriptions("full"))
    selected = measured("selective_compile", selective.reference_requests, descriptions("selective"))
    selective.reference_requests = policy.reference_requests = audit.reference_requests = journal.reference_requests = selected
    c.build_point_model = measured("pyomo_build", c.build_point_model)
    c.bind = measured("query_bind", c.bind)
    numeric.compile_problem = measured("numeric_compile", numeric.compile_problem)
    numeric.import_snapshot = measured("numeric_import", numeric.import_snapshot)
    for name in ("call_highs", "make_model", "snapshot_from_raw", "hessian_columns"):
        label = {"call_highs": "native_call", "make_model": "native_model"}.get(name, name)
        setattr(backend, name, measured(label, getattr(backend, name)))
    for name in ("create_session", "begin_step", "commit_step", "finish", "reopen", "trusted_binding", "runtime_identity"):
        setattr(journal, name, measured("journal_"+name, getattr(journal, name)))
    for name in ("prepare_hour", "propose_hour", "accept_hour", "execution_summary"):
        setattr(policy, name, measured(name, getattr(policy, name)))
    audit.audit_execution = journal.audit_execution = measured("audit_execution", audit.audit_execution)
    for name in ("put", "get"):
        setattr(codec.EvidenceStore, name, measured("cas_"+name, getattr(codec.EvidenceStore, name)))
    c.digest = measured("semantic_digest", c.digest)
    codec.pack = journal.pack = measured("cas_pack", codec.pack)
    def read_count(raw): counts["bounded_read_bytes"] += len(raw)
    codec.read_bytes = journal.read_bytes = measured("bounded_read", codec.read_bytes, read_count)
    publication = codec.publish
    def publish(path, raw, hook=None):
        counts["publication_requested_bytes"] += len(raw)
        return publication(path, raw, hook)
    codec.publish = journal.publish = measured("publication", publish)
    global fingerprints
    fingerprints = measured("fingerprints", fingerprints)

    def forbidden(*a, **kw):
        counts["forbidden_factory_requests"] += 1
        raise TransportUnresolved("alternate numeric factory prohibited")
    pyo.SolverFactory = forbidden
    for name in ("src.grid.dc_opf", "src.grid.network_grid_need", "src.grid.scopf"):
        importlib.import_module(name).SolverFactory = forbidden
    importlib.import_module("src.grid.rts_gmlc_scuc").Highs = forbidden
    if api is None: api = importlib.import_module("highspy")
    constructor = api.Highs
    def native_factory(*a, **kw):
        counts["native_factory_requested"] += 1
        if not allow_native or counts["native_factory_requested"] > 1:
            raise TransportUnresolved("native factory outside one registered point")
        return constructor(*a, **kw)
    api.Highs = native_factory
    return lambda: dict(counts=dict(counts), inclusive_seconds=dict(seconds),
        scope="selected_inclusive_calls_not_additive_wall_or_total_OS_IO_excludes_observation_write_and_terminal_manifest_scan_and_completion_publication",
        missing_process_observations="unknown_not_zero", allow_native=allow_native)


class Events:
    def __init__(self, root): self.root, self.seq, self.start = Path(root), 0, time.monotonic()
    def __call__(self, stage, **meta):
        _, codec = modules()
        self.seq += 1
        with (self.root/"events.jsonl").open("ab") as f:
            f.write(codec.canonical(dict(sequence=self.seq, stage=stage, elapsed=time.monotonic()-self.start, **meta))+b"\n")
            f.flush()


class TransportUnresolved(RuntimeError):
    """Do not append/finish/fresh after unknown transport or ownership."""


class NumericUnresolved(RuntimeError):
    """Quiet child saved a bound, explicitly unsuccessful numeric result."""


def child_path(root, relative):
    c, codec = modules()
    c.require(type(relative) is str and relative, "relative child path required")
    path = (Path(root)/relative).absolute()
    c.require(path.resolve().is_relative_to(Path(root).resolve()), "child path outside attempt")
    codec.directory_chain(path)
    return path


def point_worker(root, relative, expected_request_sha, registration_sha=None):
    from src.staged_rts24_numeric_interface_v1 import compile_problem, import_snapshot, UnresolvedNumeric
    from src.staged_rts24_highs_backend_v1 import call_highs, snapshot_from_raw, BackendFailure
    c, codec = modules()
    point = child_path(root, relative)
    request = load(point/"request.json")
    c.require(stamp(point/"request.json")["sha256"] == expected_request_sha, "point request changed")
    c.require(request.get("registration_sha") == registration_sha, "point registration differs")
    if registration_sha is not None:
        c.require(request["pins_sha"] == c.digest(load(REGISTRATION)["pins"]), "point registered pins differ")
    pins = fingerprints()
    c.require(c.digest(pins) == request["pins_sha"], "point dependency identity differs")
    store = codec.EvidenceStore(point/"cas")
    query = store.get(request["query_ref"])
    problem = compile_problem(query)
    c.require(query.identity == request["query_sha"] and problem.identity == request["problem_sha"], "point model changed")
    status, error, evidence_ref = "transport_unresolved", None, None
    try:
        try: raw = call_highs(problem, point/"native.log")
        except BackendFailure as failure: raw = failure.record
        write(point/"native.json", raw)
        c.require(fingerprints() == pins and stamp(point/"request.json")["sha256"] == expected_request_sha,
                  "point dependency drift before publication")
        c.require((point/"native.log").is_file() and raw.get("log_pin") == stamp(point/"native.log"), "native log not retained")
        try: evidence = import_snapshot(query, problem, snapshot_from_raw(problem, raw))
        except UnresolvedNumeric as exc:
            status = "numeric_unresolved"
            error = dict(type=type(exc).__name__, message=str(exc))
        else:
            evidence_ref = store.put(evidence)
            status = "imported"
    except (Exception,) as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    write(point/"result.json", dict(status=status, error=error, evidence_ref=evidence_ref,
        raw_pin=stamp(point/"native.json") if (point/"native.json").is_file() else None, request_sha=expected_request_sha,
        query_sha=query.identity, problem_sha=problem.identity, infeasibility_inferred=False))
    return 0 if status == "imported" else 2


class PointClient:
    def __init__(self, root, pins, events, monitor=None, schedule=None, registration_sha=None):
        from src.staged_rts24_process_guard_v1 import supervise
        self.root, self.pins, self.events, self.monitor = Path(root), pins, events, monitor or supervise
        self.reserved = self.imported = self.run_invoked = self.run_returned = 0
        self.schedule = schedule
        self.registration_sha = registration_sha

    def __call__(self, query):
        from src.staged_rts24_numeric_interface_v1 import compile_problem, import_snapshot, UnresolvedNumeric
        from src.staged_rts24_highs_backend_v1 import snapshot_from_raw
        c, codec = modules()
        c.require(self.reserved < MAX_CALLS, "P1 call cap reached")
        if self.schedule is not None:
            slot = self.schedule[self.reserved]
            q = query.request
            c.require((q.role, q.hour, q.plan, q.clean_path, q.method, asdict(q.outages), q.objective, q.anchor_id) ==
                      (slot["role"], slot["hour"], PLAN, CLEAN, METHOD, slot["outage"], slot["objective"],
                       slot["parent_request_sha"]), "query outside registered schedule")
            c.require(slot["request_sha"] is None or q.identity == slot["request_sha"], "scheduled request identity differs")
        self.reserved += 1  # Never refunded, even if directory/spawn fails.
        relative = f"points/point_{self.reserved:04d}"
        point = self.root/relative
        point.mkdir(parents=True, exist_ok=False)
        (point/"cas").mkdir()
        (point/"cas/objects").mkdir()
        store = codec.EvidenceStore(point/"cas")
        problem = compile_problem(query)
        req = dict(ordinal=self.reserved, query_ref=store.put(query), query_sha=query.identity, problem_sha=problem.identity,
                   pins_sha=c.digest(self.pins), role=query.request.role, hour=query.request.hour,
                   registration_sha=self.registration_sha)
        request_sha = write(point/"request.json", req)
        self.events("point_reserved", ordinal=self.reserved, role=query.request.role, hour=query.request.hour)
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--point", relative,
            "--request-sha", request_sha, "--root", str(self.root)]
        if self.registration_sha is not None: argv += ["--registration-sha", self.registration_sha]
        record = self.monitor(argv, cwd=ROOT, output=self.root,
            progress=self.root/"events.jsonl", limits=POINT_LIMITS)
        write(point/"process.json", record)
        if not record["job_quiet_confirmed"]: raise TransportUnresolved("point Job quiescence unknown")
        if (point/"native.json").is_file():
            raw = load(point/"native.json")
            if raw.get("problem_sha") != problem.identity: raise TransportUnresolved("failed raw identity differs")
            self.run_invoked += int(raw.get("run_invoked") is True)
            self.run_returned += int(raw.get("run_returned") is True)
        else: raise TransportUnresolved("native raw record missing")
        if record["stop_reason"] not in (None, "child_exit_nonzero"):
            raise TransportUnresolved("point resource/transport stop: "+str(record["stop_reason"]))
        if not (point/"result.json").is_file(): raise TransportUnresolved("point result missing")
        result = load(point/"result.json")
        c.require(result["request_sha"] == request_sha
                  and result["query_sha"] == query.identity and result["problem_sha"] == problem.identity
                  and stamp(point/"request.json")["sha256"] == request_sha, "point return binding differs")
        if fingerprints() != self.pins: raise TransportUnresolved("point dependency drift")
        if result.get("raw_pin") != stamp(point/"native.json"): raise TransportUnresolved("point raw changed")
        if not (point/"native.log").is_file() or raw.get("log_pin") != stamp(point/"native.log"):
            raise TransportUnresolved("point native log missing or changed")
        if record["exit_code"] == 2 and result["status"] == "numeric_unresolved" and result["error"]:
            try: import_snapshot(query, problem, snapshot_from_raw(problem, raw))
            except UnresolvedNumeric as exc: raise NumericUnresolved(str(exc)) from exc
            raise TransportUnresolved("numeric failure witness did not reproduce")
        if record["exit_code"] != 0 or record["stop_reason"] is not None or result["status"] != "imported":
            raise TransportUnresolved("point protocol incomplete")
        evidence = store.get(result["evidence_ref"])
        fresh = import_snapshot(query, problem, snapshot_from_raw(problem, raw))
        c.require(evidence == fresh and fingerprints() == self.pins, "parent point audit or dependency differs")
        self.imported += 1
        self.events("point_imported", ordinal=self.reserved)
        return fresh


def hour_evidence(fixture, state, point):
    from src.staged_rts24_reference_queries_v1 import reference_requests
    from src.staged_rts24_causal_v1 import HourEvidence
    c, _ = modules()
    h = reference_requests(fixture, state.plan, state.clean_path, state.method, state.next_hour)
    roles = {r.role: r for r in h["requests"]}
    c.require(h["reference_connection_shortfall_mw"] == 0, "reference connection shortfall")
    root = point(c.bind(roles["reference_base_P0"]))
    def child(role):
        return None if role not in roles else point(c.bind(roles[role], root.query, root.point, root.economic))
    return HourEvidence(root, child("reference_raw_need"), child("recovery_min_meter"), child("recovery_max_meter"))


def request_schedule(fixture):
    """Fixed requests and dynamic actual slots; no invented future bound identities."""
    from src.staged_rts24_reference_queries_v1 import reference_requests
    c, _ = modules()
    rows = []
    def add(request, *, dynamic=False):
        rows.append(dict(ordinal=len(rows)+1, hour=request.hour, role=request.role, objective=request.objective,
            outage=asdict(request.outages), request_sha=None if dynamic else request.identity,
            parent_request_sha=request.anchor_id, bound_query_sha=None,
            dynamic_reason="policy_power_and_parent_point" if dynamic else "bound_parent_point" if request.anchor_id else None))
    for hour in range(fixture.first_hour, 3):
        h = reference_requests(fixture, PLAN, CLEAN, METHOD, hour)
        for q in h["requests"]: add(q)
        base = h["requests"][0]
        add(replace(base, role="actual_P", outages=h["actual_outage"], anchor_id=base.identity), dynamic=True)
    branch = min((o for o in fixture.selected if o.branches), key=lambda o: o.branches)
    generator = min((o for o in fixture.selected if o.generators), key=lambda o: o.generators)
    for hour in (1, 2):
        h = c.hour_requests(fixture, PLAN, CLEAN, METHOD, hour)
        add(h["requests"][0])
        for outage in (branch, generator):
            for q in h["requests"]:
                if q.outages == outage and q.role in ("fault_firm_F", "fault_raw_need"): add(q)
    c.require(len(rows) == MAX_CALLS and sum(r["objective"] == "economic" for r in rows) == 16,
              "P1 registered shape differs")
    return rows


def actual_query(pending):
    c, _ = modules()
    root = pending.prepared.evidence.reference
    request = replace(root.query.request, role="actual_P", meter_min=pending.proposal.power_mw,
        meter_max=pending.proposal.power_mw, outages=pending.prepared.actual_outage, anchor_id=root.query.request.identity)
    return c.bind(request, root.query, root.point, root.economic)


def actual_prefix(fixture, root, point, events):
    from src import staged_rts24_journal_v2 as journal
    c, _ = modules()
    session = journal.create_session(root, fixture, PLAN, CLEAN, METHOD)
    prefixes = Path(root).parent/"trusted_prefixes"
    prefixes.mkdir(exist_ok=False)
    def checkpoint():
        write(prefixes/f"prefix_{session.ordinal:06d}.json", journal.trusted_binding(session))
    checkpoint()
    while session.state.next_hour <= 2 and not session.state.stopped:
        try:
            evidence = hour_evidence(fixture, session.state, point)
        except NumericUnresolved as exc:
            # Record the exact already accepted prefix; no artificial partial
            # HourEvidence, no placeholder point and no business refusal.
            return session, dict(stage="reference_numeric", type=type(exc).__name__, message=str(exc),
                current_observation=c.plain(c.observe(fixture, PLAN, CLEAN, session.state.next_hour)),
                unaccepted_status="numeric_unresolved_observed_current_inputs", candidate_adopted=False)
        try: pending = journal.begin_step(session, evidence)
        except journal.SessionClosed as exc:
            write(Path(root).parent/"writer_closed_binding.json", journal.trusted_binding(exc.session))
            raise TransportUnresolved("journal closed while preparing") from exc
        excluded = any(code.startswith("network_projection_") or code == "connection_capacity" for code in pending.proposal.violations)
        try: actual = None if excluded else point(actual_query(pending))
        except NumericUnresolved as exc:
            # Preserve observed evidence as the existing unresolved actual attempt.
            session = journal.commit_step(session, pending, None)
            write(Path(root).parent/"writer_closed_binding.json", journal.trusted_binding(session))
            if session.scientific_outcome != "actual_unresolved" or session.publication_outcome != "committed":
                raise TransportUnresolved("numeric attempt publication unresolved")
            return session, dict(stage="actual_numeric", type=type(exc).__name__, message=str(exc))
        session = journal.commit_step(session, pending, actual)
        if not session.closed: checkpoint()
        events("hour_adopted" if not session.closed else "hour_closed", next_hour=session.state.next_hour)
        if session.closed:
            write(Path(root).parent/"writer_closed_binding.json", journal.trusted_binding(session))
            raise TransportUnresolved("journal publication or audit unresolved")
    return session, None


def representative_contracts(fixture, point, events, rows=None):
    from src.staged_rts24_audit_v1 import audit_legal_x, audit_point
    c, _ = modules()
    branch = min((o for o in fixture.selected if o.branches), key=lambda o: o.branches)
    generator = min((o for o in fixture.selected if o.generators), key=lambda o: o.generators)
    rows = [] if rows is None else rows
    for hour in (1, 2):
        h = c.hour_requests(fixture, PLAN, CLEAN, METHOD, hour)
        root = point(c.bind(h["requests"][0]))
        for outage in (branch, generator):
            requests = [q for q in h["requests"] if q.outages == outage and q.role in ("fault_firm_F", "fault_raw_need")]
            c.require([q.role for q in requests] == ["fault_firm_F", "fault_raw_need"], "representative contract roles differ")
            firm, raw = (point(c.bind(q, root.query, root.point, root.economic)) for q in requests)
            rows.append(dict(hour=hour, outage=asdict(outage), normal_query=root.query.identity,
                firm_query=firm.query.identity, raw_query=raw.query.identity, raw_curtailment_mw=raw.point.curtailment_mw,
                firm_audit=audit_point(firm.query, firm.point), legal_X=audit_legal_x(raw.query, raw.point, *raw.query.request.rights)))
        events("representative_contracts", hour=hour)
    return rows


def metrics(result):
    c, codec = modules()
    return dict(state_sha=c.digest(result["state"]), state_cas_sha=codec.pack(result["state"])[0],
        summary=c.plain(result["summary"]), independent_audit=c.plain(result["independent_audit"]),
        scientific_outcome=result["scientific_outcome"], publication_outcome=result["publication_outcome"],
        terminal_entry_present=result["terminal_entry_present"],
        **{k: c.plain(result[k]) for k in ("state_certainty", "closed_entry_present", "unaccepted_attempt", "failure",
            "pending_terminal_checkpoint", "pending_cas_objects", "unreferenced_final_cas_objects",
            "genesis_sha", "head_sha", "final_entries", "saved_objects", "resume_permitted")})


def fresh_worker(root):
    from src import staged_rts24_journal_v2 as journal
    c, _ = modules()
    # Fingerprints may import class definitions; no backend call/construction.
    before = fingerprints()
    c.require(before == load(root/"start.json")["pins"], "fresh dependency differs")
    expected = load(root/"trusted_binding.json")
    result = journal.reopen(root/"journal", c.load_fixture(), PLAN, CLEAN, METHOD, expected)
    c.require(fingerprints() == before, "fresh dependency changed")
    write(root/"fresh.json", dict(metrics=metrics(result), solver_calls=0))
    return 0


def worker(root, registration_sha):
    from src import staged_rts24_journal_v2 as journal
    from src.staged_rts24_process_guard_v1 import supervise
    c, codec = modules()
    c.require(Path(root).resolve() == OUTPUT.resolve(), "registered P1 output required")
    launcher = load(root/"launcher_start.json")
    c.require(launcher["limits"] == LIMITS and launcher["package"] == "staged_rts24_P1_v1"
              and launcher["registration_sha"] == registration_sha, "launcher scope differs")
    pins, old = fingerprints(), preserve()
    registered = load(REGISTRATION)
    c.require(registered["pins"] == pins and registered["preserved"] == old, "registered initial bytes differ")
    write(root/"start.json", dict(authority="DRAFT_NONAUTHORITATIVE", pins=pins, preserved=old,
        max_point_attempts=MAX_CALLS, plan=PLAN, clean=CLEAN, method=METHOD, first_hour=-2, last_included_hour=2,
        expected_full_observation_end=8, registration_sha=registration_sha,
        native_user_authority="external_explicit_user_instruction_not_inferred_from_files"))
    events = Events(root)
    events("start")
    fixture = c.load_fixture()
    schedule = request_schedule(fixture)
    c.require(c.digest(schedule) == registered["schedule_sha"], "worker registered schedule differs")
    write(root/"request_schedule.json", schedule)
    point = PointClient(root, pins, events, schedule=schedule, registration_sha=registration_sha)
    session, failure = actual_prefix(fixture, root/"journal", point, events)
    contracts = []
    if failure is None and not session.state.stopped:
        try: representative_contracts(session.fixture, point, events, rows=contracts)
        except NumericUnresolved as exc: failure = dict(stage="contract_numeric", type=type(exc).__name__, message=str(exc))
    if fingerprints() != pins or preserve() != old: raise TransportUnresolved("dependency or prior drift before finish")
    # Numeric reference failure has no fabricated HourEvidence/attempt. Its raw
    # point files remain separate from the trusted accepted scientific prefix.
    if not session.closed:
        session = journal.finish(session)
        if not session.closed or session.publication_outcome != "committed" or session.scientific_outcome not in (
                "known_rejection", "missing_input", "right_censored", "complete"):
            write(root/"writer_closed_binding.json", journal.trusted_binding(session))
            raise TransportUnresolved("journal finish publication unresolved")
    write(root/"contract_rows.json", contracts)
    write(root/"trusted_binding.json", journal.trusted_binding(session))
    if failure is not None: write(root/"numeric_failure.json", dict(**failure, infeasibility_inferred=False))
    events("fresh_reserved")
    fresh_record = supervise([sys.executable, "-B", str(Path(__file__).resolve()), "--fresh", "--root", str(root),
        "--registration-sha", registration_sha],
        cwd=ROOT, output=root, progress=root/"events.jsonl", limits=FRESH_LIMITS)
    write(root/"fresh_process.json", fresh_record)
    c.require(fresh_record["job_quiet_confirmed"] and fresh_record["stop_reason"] is None
              and fresh_record["exit_code"] == 0, "fresh process unresolved")
    events("fresh_returned")
    result = journal.reopen(root/"journal", session.fixture, PLAN, CLEAN, METHOD, journal.trusted_binding(session))
    c.require(load(root/"fresh.json")["metrics"] == metrics(result), "fresh scientific replay differs")
    c.require(fingerprints() == pins and preserve() == old, "source or prior bytes changed")
    complete = failure is None and not session.state.stopped and point.reserved == point.imported == MAX_CALLS
    write(root/"report.json", dict(authority="DRAFT_NONAUTHORITATIVE", package_complete=complete, failure=failure,
        point_attempts_reserved=point.reserved, native_run_invoked_observed=point.run_invoked,
        native_run_returned_observed=point.run_returned, points_imported=point.imported, fresh_launches=1,
        metrics=metrics(result), representative_contracts=contracts, resource_admission=False,
        overall_performance_review_complete=False, full_139_executed=False, fx_temporal_backing=False, formal_result=False))
    events("report", package_complete=complete)
    return 0 if complete else 2


def complete_core(root):
    """Publish only after the CLI saved worker observations successfully."""
    manifest = {p.relative_to(root).as_posix(): stamp(p) for p in root.rglob("*") if p.is_file()
        and p.name not in ("completion.json", "launcher.json", "launcher.stdout.log", "launcher.stderr.log",
            "worker.stdout.log", "worker.stderr.log")}
    write(root/"completion.json", dict(files=manifest, manifest_files=len(manifest), logical_bytes=sum(p["bytes"] for p in manifest.values())))


def cli():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--worker", action="store_true")
    group.add_argument("--point")
    group.add_argument("--fresh", action="store_true")
    p.add_argument("--root", required=True)
    p.add_argument("--request-sha")
    p.add_argument("--registration-sha", required=True)
    args = p.parse_args()
    root = Path(args.root).absolute()
    c, codec = modules()
    c.require(root.resolve() == OUTPUT.resolve() and root.is_dir(), "registered attempt root required")
    logdir = child_path(root, args.point) if args.point else root
    prefix = "point" if args.point else "fresh" if args.fresh else "worker"
    with (logdir/(prefix+".stdout.log")).open("x", encoding="utf-8") as out, (logdir/(prefix+".stderr.log")).open("x", encoding="utf-8") as err:
        with redirect_stdout(out), redirect_stderr(err):
            observations = None
            try:
                observations = install_observers(allow_native=bool(args.point))
                verify_registration(args.registration_sha, full=False)
                if args.point: code = point_worker(root, args.point, args.request_sha, args.registration_sha)
                elif args.fresh: code = fresh_worker(root)
                else: code = worker(root, args.registration_sha)
                write(logdir/(prefix+"_observations.json"), observations())
                if args.worker: complete_core(root)
                return code
            except BaseException as exc:
                import traceback
                traceback.print_exc(file=err)
                err.flush()
                try:
                    write(logdir/(prefix+"_failure.json"), dict(type=type(exc).__name__, message=str(exc),
                        ownership_or_transport_unknown=True, no_new_journal_terminal_or_resume=True))
                    if observations is not None and not (logdir/(prefix+"_observations.json")).exists():
                        write(logdir/(prefix+"_observations.json"), observations())
                except BaseException:
                    traceback.print_exc(file=err)
                    err.flush()
                return 3


if __name__ == "__main__": sys.exit(cli())
