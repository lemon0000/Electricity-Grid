"""Create-only, saved-input v2/v3 cost diagnostic; never a native entry point."""
import time
BOOT = time.perf_counter()
import argparse
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT/"results/tables/staged_rts24_append_cost_v1_non_authoritative"
PREP, OUTPUT, REGISTRATION = BASE/"cost_preparation_01", BASE/"cost_probe_01", BASE/"cost_registration_v1.json"
OLD = ROOT/"results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01"
METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
KINDS = ("unknown", "deletion", "reference_unresolved")
DIRECT = ("experiments/staged_rts24_append_cost_probe_v1.py", "experiments/staged_rts24_append_cost_observer_v1.py",
    "tests/test_staged_rts24_append_cost_probe_v1.py", "docs/plan/staged_deliverability_c_append_cost_probe_contract_v1.md",
    "results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/launch_capture.ps1",
    "src/staged_rts24_process_guard_v1.py", "src/rq2_joint_deliverability_boundary_v1/normal_process.py",
    "experiments/staged_rts24_native_probe_v1.py")
OLD_TREES = (OLD, ROOT/"results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01",
    ROOT/"results/tables/staged_rts24_append_batch_v1_non_authoritative/development_checks_01",
    ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/development_checks_01")
P1 = ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/registration_v1.json"
P1_SHA = "23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2"
LIMITS = dict(wall_seconds=300, no_progress_seconds=30, rss_bytes=1024**3, output_bytes=16*1024**2, files=3000)
FRESH_LIMITS = {**LIMITS, "wall_seconds": 10, "no_progress_seconds": 10}
PREP_LIMITS = {**LIMITS, "wall_seconds": 30, "no_progress_seconds": 20, "output_bytes": 4*1024**2, "files": 200}
GROUPS = dict(pre=25, parent=110, fresh=110, post=20, report=5)
CASES = tuple(dict(name=version+"_"+method, version=version, method=method, kind="success")
    for method in METHODS for version in ("v2", "v3")) + tuple(
    dict(name=version+"_"+kind, version=version, method="full_temporal", kind=kind)
    for version in ("v2", "v3") for kind in KINDS)


def require(value, message):
    if not value: raise ValueError(message)


def stamp(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64*1024**2, "pin file limit")
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def load(path, expected_sha=None):
    raw = Path(path).read_bytes()
    require(len(raw) <= 2*1024**2 and (expected_sha is None or sha256(raw).hexdigest() == expected_sha), "JSON pin/size differs")
    return json.loads(raw)


def write(path, value):
    path = Path(path)
    relative = path.absolute().relative_to(BASE.absolute())
    require(relative.parts[0] in (PREP.name, OUTPUT.name, REGISTRATION.name), "output outside new diagnostic")
    require(path.parent.resolve().is_relative_to(BASE.resolve()), "linked output parent")
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)+"\n").encode()
    require(len(raw) <= 2*1024**2, "diagnostic artifact limit")
    with path.open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def event(root, stage):
    with (root/"events.jsonl").open("ab") as stream:
        stream.write((json.dumps(dict(stage=stage, elapsed=time.perf_counter()-BOOT))+"\n").encode()); stream.flush()


def system():
    return dict(platform=platform.platform(), cpu_count=os.cpu_count(), pid=os.getpid(), parent_pid=os.getppid(),
        python=sys.version, executable=sys.executable, no_user_site=sys.flags.no_user_site,
        dont_write_bytecode=sys.dont_write_bytecode, argv=list(sys.orig_argv), process_cpu_seconds=time.process_time(),
        epoch=time.time(), clock=vars(time.get_clock_info("perf_counter")))


def tree_pins():
    result, pending, entries, total = {}, list(OLD_TREES), 0, 0
    while pending:
        directory = pending.pop()
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and not getattr(info, "st_file_attributes", 0)&0x400, "linked historical directory")
        with os.scandir(directory) as children:
            for child in children:
                entries += 1
                require(entries <= 1500, "historical tree entry cap")
                path, info = Path(child.path), child.stat(follow_symlinks=False)
                require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0)&0x400, "linked historical tree")
                if stat.S_ISDIR(info.st_mode): pending.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode), "nonregular historical file")
                    total += info.st_size
                    require(total <= 8*1024**2, "historical tree byte cap")
                    result[path.relative_to(ROOT).as_posix()] = stamp(path)
    return result


def pins(m):
    from src.staged_rts24_process_guard_v1 import controlled_environment
    from experiments import staged_rts24_native_probe_v1 as historical
    historical.require_compute()
    require(sys.flags.no_user_site and sys.dont_write_bytecode, "controlled -B -s interpreter required")
    require(stamp(P1)["sha256"] == P1_SHA and not historical.OUTPUT.exists(), "P1 must remain unexecuted")
    native = load(OLD_TREES[-1]/"development_checks.json")
    batch = load(OLD_TREES[-2]/"development_checks.json")
    for record, directory in ((native, OLD_TREES[-1]), (batch, OLD_TREES[-2])):
        require(all(stamp(ROOT/name) == pin for name, pin in record["source_pins"].items()), "historical source pin differs")
        require(all(stamp(directory/name) == pin for name, pin in record["artifacts"].items()), "historical artifact pin differs")
    preserved = historical.preserve()  # No request_schedule/registration/P1 entry.
    require(preserved == native["preserved_after"], "historical preservation differs")
    require(m["v3"].runtime_identity() == load(OLD_TREES[-2]/"runtime_identity.json"), "batch runtime differs")
    return dict(direct={name: stamp(ROOT/name) for name in DIRECT}, historical_trees=tree_pins(),
        v2=m["v2"].runtime_identity(), v3=m["v3"].runtime_identity(), preserved=preserved,
        p1_registration=stamp(P1), p1_sources=load(P1)["pins"]["sources"],
        executable=stamp(sys.executable), environment=controlled_environment(),
        package_entries={name: stamp(ROOT/name) if (ROOT/name).exists() else None for name in ("experiments/__init__.py",)},
        observer_clock=vars(time.get_clock_info("perf_counter")))


def packet(method, m):
    require(method in METHODS, "unregistered method")
    codec, c = m["codec"], m["c"]
    root = OLD/method/"journal"
    names = ("genesis.json", "entry_000001.json", "entry_000002.json")
    raw_roots = [codec.read_bytes(root/name) for name in names]
    root_shas = [codec.sha(raw) for raw in raw_roots]
    genesis, *entries = map(codec.parse, raw_roots)
    view = codec.EvidenceReadView(codec.EvidenceStore(root))
    fixture, initial = view.get(genesis["fixture_ref"]), view.get(genesis["state_ref"])
    payloads = [view.get(e["payload_ref"]) for e in entries]
    states = [view.get(e["state_ref"]) for e in entries]
    require(fixture.observation_end == 5 and states[-1].next_hour == 2 and len(states[-1].records) == 2, "frozen prefix scope differs")
    source_refs = [genesis["fixture_ref"], genesis["state_ref"], *(e["payload_ref"] for e in entries), *(e["state_ref"] for e in entries)]
    values = [fixture, initial, *payloads, *states]
    require([codec.pack(v)[0] for v in values] == source_refs, "typed source identity differs")
    view.bookend()
    require([codec.sha(codec.read_bytes(root/name)) for name in names] == root_shas, "source roots changed during decode")
    return dict(fixture=fixture, initial=initial, payloads=payloads, states=states, view=view,
        method=method, root_shas=root_shas, source_refs=source_refs, values=values, evidence=[p["row"]["prepared"].evidence for p in payloads],
        actual=[p["row"]["actual"] for p in payloads])


def packet_bookend(p, m):
    # Compare every originally used byte plus the complete inventory/roots and
    # retained directory identity. Never reopen the closed decoding operation.
    codec, view = m["codec"], p["view"]
    view.store._check_directories()
    require(all(codec.read_bytes(view.store.objects/(key+".json")) == raw for key, raw in view.used.items())
        and view.store.inventory() == view.before, "frozen packet CAS source changed")
    require([codec.sha(codec.read_bytes(view.store.root/name)) for name in
        ("genesis.json", "entry_000001.json", "entry_000002.json")] == p["root_shas"], "frozen packet roots changed")
    require([m["codec"].pack(v)[0] for v in p["values"]] == p["source_refs"], "input packet mutated")


def baseline(p, m):
    c, codec, policy = m["c"], m["codec"], m["policy"]
    state = p["states"][-1]
    summary, audit = policy.execution_summary(p["fixture"], state), m["audit"].audit_execution(p["fixture"], state)
    terminal = dict(checkpoint_state=state, summary=summary, independent_audit=audit,
        scientific_outcome="missing_input", next_input="not_observed", resume_permitted=False)
    blobs = {}
    for value in [*p["values"], terminal]:
        for key, data in codec.pack(value)[1].items():
            require(key not in blobs or blobs[key] == data, "baseline wire conflict")
            blobs[key] = data
    packet_bookend(p, m)
    return dict(state=c.plain(state), state_sha=c.digest(state), state_ref=codec.pack(state)[0],
        summary=c.plain(summary), independent_audit=c.plain(audit), source_refs=p["source_refs"], root_shas=p["root_shas"],
        terminal_ref=codec.pack(terminal)[0], cas_keys=sorted(key+".json" for key in blobs),
        wire={key: data.decode("utf-8") for key, data in blobs.items()},
        cas_bytes=sum(map(len, blobs.values())), scientific_outcome="missing_input", publication_outcome="committed",
        state_certainty="known", terminal_entry_present=True, final_entries=3, resume_permitted=False)


def check_counts(counts, calls, descriptions, roles=None):
    require(counts.get("forbidden_calls", 0) == 0, "forbidden entry was requested")
    require(counts.get("selective.started", 0) == counts.get("selective.returned", 0) == calls
        and counts.get("descriptions", 0) == descriptions, "selective accounting differs")
    if roles is not None: require({k[5:]: v for k, v in counts.items() if k.startswith("role.")} == roles, "role accounting differs")


def expected_counts(case, *, fresh):
    if case["kind"] == "success": return 13, 18 if case["method"] == "instantaneous" else 44
    return {"unknown": ((5, 15) if fresh else (3, 9)), "deletion": ((0, 0) if fresh else (3, 9)),
            "reference_unresolved": (2, 6)}[case["kind"]]


def verify_request(expected_sha, m, *, full):
    from src.staged_rts24_process_guard_v1 import controlled_environment
    request = load(PREP/"request.json", expected_sha)
    require(request["schema"] == "saved_append_cost_preparation_v1" and request["authority"] == "DRAFT_NONAUTHORITATIVE"
        and request["cases"] == list(CASES) and request["limits"] == PREP_LIMITS and request["native_authorized"] is False
        and set(request) == {"schema", "authority", "pins", "cases", "limits", "system", "native_authorized"}, "preparation scope differs")
    bound = request["pins"]
    require(all(stamp(ROOT/name) == pin for name, pin in bound["direct"].items()), "diagnostic direct bytes differ")
    require(stamp(sys.executable) == bound["executable"] and sys.flags.no_user_site and sys.dont_write_bytecode,
            "diagnostic interpreter differs")
    require(all((stamp(ROOT/name) if (ROOT/name).exists() else None) == pin for name, pin in bound["package_entries"].items()), "package entry changed")
    require(controlled_environment() == bound["environment"], "registered environment differs")
    require(m["v2"].runtime_identity() == bound["v2"] and m["v3"].runtime_identity() == bound["v3"], "runtime differs")
    if full: require(pins(m) == bound, "registered dependencies or historical trees differ")
    return request


def verify_registration(expected_sha, m, *, full):
    record = load(REGISTRATION, expected_sha)
    require(record["schema"] == "saved_append_cost_registration_v1" and record["authority"] == "DRAFT_NONAUTHORITATIVE"
        and record["limits"] == LIMITS and record["fresh_limits"] == FRESH_LIMITS and record["groups"] == GROUPS
        and record["cases"] == list(CASES) and record["native_authorized"] is False and record["solver_calls_allowed"] == 0
        and record["expected_preparation"] == dict(calls=12, descriptions=34)
        and record["expected_measurement"] == dict(calls=186, descriptions=514)
        and set(record) == {"schema", "authority", "request_sha", "preparation_artifacts", "cases", "limits", "fresh_limits", "groups",
            "native_authorized", "solver_calls_allowed", "expected_preparation", "expected_measurement"}, "registration scope differs")
    verify_request(record["request_sha"], m, full=full)
    for name, pin in record["preparation_artifacts"].items(): require(stamp(PREP/name) == pin, "prepared result differs")
    late = load(PREP/"controller_timings.json")
    require(late["accepted_success"] is True and late["registration_sha"] == expected_sha, "preparation controller result differs")
    return record


def verify_role(role, expected_sha):
    expected = [sys.executable, "-B", "-s", str(Path(__file__).resolve()), role, "--registration-sha", expected_sha]
    require(sys.orig_argv == expected, "owned role exact argv differs")


def accepted_monitor(record):
    witness = record.get("quiescence_witness") or {}
    require(record["exit_code"] == 0 and record["stop_reason"] is None and record["job_quiet_confirmed"]
        and witness.get("all_handles_signaled") and witness.get("complete_inventory")
        and witness.get("total_processes") == witness.get("observed_unique_member_handles")
        and witness.get("active_processes") == 0 and witness.get("final_pids") == [], "owned process not successfully quiet")


def prepare_worker(expected_sha, obs):
    verify_role("--prepare-worker", expected_sha)
    request = verify_request(expected_sha, obs.m, full=True)
    event(PREP, "bound_inputs")
    result = {}
    for method in METHODS:
        result[method] = baseline(packet(method, obs.m), obs.m)
        event(PREP, "baseline_"+method)
        require(time.perf_counter()-BOOT <= 20, "preparation work cap")
    require(pins(obs.m) == request["pins"], "preparation end pins differ")
    require(time.perf_counter()-BOOT <= 20, "preparation end work cap")
    check_counts(obs.counts, 12, 34, dict(reference_base_P0=12, reference_raw_need=6, recovery_min_meter=8, recovery_max_meter=8))
    write(PREP/"baseline.json", result)
    event(PREP, "prepared_baseline")


class Budget:
    def __init__(self, root, obs):
        self.root, self.obs, self.spent, self.phases = root, obs, Counter(), []
        self.spent["pre"] = time.perf_counter()-BOOT
        self.last = time.perf_counter()

    def check(self):
        now = time.perf_counter()
        self.spent["parent"] += now-self.last
        self.last = now
        require(time.perf_counter()-BOOT <= 270 and all(self.spent[g] <= cap for g, cap in GROUPS.items()), "diagnostic group budget")
        self.obs.check()

    def phase(self, group, name, action):
        self.check()
        before, started, cpu = self.obs.snapshot(), time.perf_counter(), time.process_time()
        outcome = "returned"
        try: return action()
        except BaseException: outcome = "raised"; raise
        finally:
            elapsed = time.perf_counter()-started
            self.spent[group] += elapsed
            self.last = time.perf_counter()
            after = self.obs.snapshot()
            self.phases.append(dict(group=group, stage=name, outcome=outcome, wall_seconds=elapsed,
                cpu_seconds=time.process_time()-cpu, counts={key: value-before["counts"].get(key, 0) for key, value in after["counts"].items()
                    if value != before["counts"].get(key, 0)}, inclusive_seconds={key: value-before["inclusive_seconds"].get(key, 0)
                    for key, value in after["inclusive_seconds"].items() if value != before["inclusive_seconds"].get(key, 0)}))
            event(self.root, name)
            self.check()

    def reserve_fresh(self):
        self.check()
        require(self.spent["fresh"]+15 <= GROUPS["fresh"] and time.perf_counter()-BOOT+15 <= 270, "fresh cleanup reservation unavailable")


def metrics(result, m):
    c, codec = m["c"], m["codec"]
    return dict(state=c.plain(result["state"]), state_sha=result["state_sha"], state_ref=codec.pack(result["state"])[0],
        **{key: c.plain(result[key]) for key in ("summary", "independent_audit", "scientific_outcome", "publication_outcome",
            "state_certainty", "terminal_entry_present", "final_entries", "resume_permitted")},
        pending_cas=list(result["pending_cas_objects"]), orphan_cas=list(result["unreferenced_final_cas_objects"]),
        failure=c.plain(result["failure"]), unaccepted_attempt=c.plain(result["unaccepted_attempt"]))


def registered_packet(p):
    expected = load(PREP/"baseline.json")[p["method"]]
    require(p["source_refs"] == expected["source_refs"] and p["root_shas"] == expected["root_shas"], "registered method inputs differ")
    return expected


def fresh_intent(case, case_sha, registration_sha):
    from src.staged_rts24_process_guard_v1 import controlled_environment
    root = OUTPUT/case["name"]
    argv = [sys.executable, "-B", "-s", str(Path(__file__).resolve()), "--fresh", case["name"],
        "--case-sha", case_sha, "--registration-sha", registration_sha]
    return dict(schema="saved_append_fresh_intent_v1", case=case, case_sha=case_sha, registration_sha=registration_sha,
        argv_without_intent_sha=argv, append_arguments=["--intent-sha", "sha256_this_intent_file"],
        executable=stamp(sys.executable), environment=controlled_environment(), limits=FRESH_LIMITS,
        output=str(OUTPUT), progress=str(root/"events.jsonl"), expected_action="read_only_reopen_then_publish_diagnostic_output")


def verify_fresh_intent(expected_sha, case, case_sha, registration_sha):
    root = OUTPUT/case["name"]
    intent = load(root/"fresh_intent.json", expected_sha)
    require(intent == fresh_intent(case, case_sha, registration_sha), "fresh intent differs")
    require(sys.orig_argv == intent["argv_without_intent_sha"]+["--intent-sha", expected_sha], "fresh exact argv differs")
    return intent


def inspect_failure(case, p, m, binding):
    """Independently check the deterministic post-rename/attempt disk shape."""
    codec, c, journal = m["codec"], m["c"], m[case["version"]]
    root = OUTPUT/case["name"]
    disk = root/"journal"
    raw_genesis, raw_entry = (codec.read_bytes(disk/name) for name in ("genesis.json", "entry_000001.json"))
    genesis, entry = codec.parse(raw_genesis), codec.parse(raw_entry)
    gen_sha, entry_sha = codec.sha(raw_genesis), codec.sha(raw_entry)
    require(genesis["fixture_ref"] == p["source_refs"][0] and genesis["state_ref"] == p["source_refs"][1], "failure genesis source differs")
    blobs = {}
    for value in (p["fixture"], p["initial"]): blobs.update(codec.pack(value)[1])
    initial_keys = sorted(key+".json" for key in blobs)
    failure = None
    if case["kind"] == "reference_unresolved":
        reader = codec.EvidenceReadView(codec.EvidenceStore(disk))
        payload = reader.get(entry["payload_ref"])
        reader.bookend()
        require(payload["stage"] == "reference" and payload["evidence"] is None and payload["prepared"] is None
            and payload["proposal"] is None and payload["actual"] is None and payload["adopted"] is False
            and payload["mathematical_infeasibility_inferred"] is False and payload["after_state_sha"] is None,
            "reference attempt shape differs")
        blobs.update(codec.pack(payload)[1])
        after_state, state_ref, kind = None, None, "attempt"
        head, ordinal, outcome, publication = entry_sha, 1, "reference_unresolved", "committed"
    else:
        for value in (p["payloads"][0], p["states"][0]): blobs.update(codec.pack(value)[1])
        after_state, state_ref, kind = c.digest(p["states"][0]), p["source_refs"][4], "hour"
        require(entry["payload_ref"] == p["source_refs"][2], "failure hour payload wire differs")
        observation = p["payloads"][0]["row"]["prepared"].observation
        unknown = case["kind"] == "unknown"
        failure = dict(schema=journal.SCHEMA, kind="failure", operation="hour", ordinal=1,
            previous_sha=gen_sha, before_state_sha=c.digest(p["initial"]), expected_after_state_sha=after_state,
            target="entry_000001.json", failed_target="entry_000001.json" if unknown else None,
            expected_file_sha=entry_sha, phase="after_rename" if unknown else "validation_or_bookend",
            publication_outcome="unknown", may_have_published=True, error_type="PublicationError" if unknown else "ValueError",
            error="after_rename: OSError: registered append cost readback unknown" if unknown else "retained CAS closure changed before adoption",
            observed_hour=observation.hour, reported_unaccepted_workload=str(observation.workload),
            observed_scope="writer_diagnostic_only_not_an_accepted_arrival", resume_permitted=False)
        require(codec.read_bytes(disk/"failure.json") == codec.canonical(failure), "complete failure witness differs")
        head, ordinal, outcome, publication = gen_sha, 0, "persistence_failure", "unknown"
    expected_entry = dict(after_cas_keys=sorted(key+".json" for key in blobs), schema=journal.SCHEMA,
        kind=kind, ordinal=1, previous_sha=gen_sha, before_state_sha=c.digest(p["initial"]),
        after_state_sha=after_state, payload_ref=entry["payload_ref"], state_ref=state_ref)
    require(raw_entry == codec.canonical(expected_entry), "complete failure entry differs")
    actual_blobs = dict(blobs)
    removed = None
    if case["kind"] == "deletion":
        removed = actual_blobs.pop(p["source_refs"][0])
        require((root/"removed_object.json").read_bytes() == removed and not (disk/"objects"/(p["source_refs"][0]+".json")).exists(), "removed fixture evidence differs")
    store = codec.EvidenceStore(disk)
    actual = store.inventory()
    require(sorted(actual) == sorted(key+".json" for key in actual_blobs) and all(
        codec.read_bytes(store.objects/(key+".json")) == raw for key, raw in actual_blobs.items()), "failure complete CAS wire differs")
    require({path.name for path in disk.iterdir()} == {"objects", "genesis.json", "entry_000001.json", *(["failure.json"] if failure else [])}, "failure pending/terminal/root shape differs")
    expected_binding = dict(genesis_sha=gen_sha, known_head_sha=head, known_entries=ordinal,
        known_state_sha=c.digest(p["initial"]), closed=True, scientific_outcome=outcome, publication_outcome=publication,
        failure_sha=codec.sha(codec.canonical(failure)) if failure else None,
        known_cas_keys=initial_keys if failure else sorted(actual))
    require(binding == expected_binding, "failure trusted prefix differs")
    return dict(accepted_state_sha=c.digest(p["initial"]), accepted_rows=0, writer_ordinal=ordinal,
        publication_outcome=publication, terminal_present=False, pending_cas=[],
        additional_final_cas=sorted(set(actual)-set(binding["known_cas_keys"])), cas_keys=sorted(actual),
        removed_object_sha=codec.sha(removed) if removed is not None else None,
        normalized_failure={key: value for key, value in (failure or {}).items() if key not in ("schema", "previous_sha", "expected_file_sha")})


def fresh_worker(expected_sha, case, case_sha, intent_sha, obs):
    verify_fresh_intent(intent_sha, case, case_sha, expected_sha)
    verify_registration(expected_sha, obs.m, full=False)
    m, root = obs.m, OUTPUT/case["name"]
    p = packet(case["method"], m)
    registered_packet(p)
    binding = load(root/"trusted_binding.json")
    require(binding == load(root/"case.json", case_sha)["trusted_binding"], "external fresh binding differs")
    journal = m[case["version"]]
    inspection = inspect_failure(case, p, m, binding) if case["kind"] != "success" else None
    event(root, "fresh_bound_inputs")
    try: result = journal.reopen(root/"journal", p["fixture"], "on_time", "late", case["method"], binding)
    except ValueError as error:
        require(case["kind"] == "deletion" and "retained CAS missing" in str(error), "unexpected reader refusal")
        report = dict(reader_refused_missing_closure=True, error=str(error), state_adopted=False)
    else:
        require(case["kind"] != "deletion", "deleted retained closure was accepted")
        report = metrics(result, m)
        wanted = p["states"][-1 if case["kind"] == "success" else 0] if case["kind"] != "reference_unresolved" else p["initial"]
        require(result["state"] == wanted and report["state_ref"] == m["codec"].pack(wanted)[0], "fresh complete state differs")
        if case["kind"] == "success":
            expected = load(PREP/"baseline.json")[case["method"]]
            require(all(report[key] == expected[key] for key in expected if key not in ("source_refs", "root_shas", "terminal_ref", "cas_keys", "cas_bytes", "wire")), "fresh baseline differs")
            store = m["codec"].EvidenceStore(root/"journal")
            require(sorted(store.inventory()) == expected["cas_keys"] and all(
                m["codec"].read_bytes(store.objects/(key+".json")) == data.encode("utf-8")
                for key, data in expected["wire"].items()), "fresh full CAS wire differs")
        elif case["kind"] == "unknown":
            require(report["final_entries"] == 1 and report["publication_outcome"] == "committed"
                and not report["terminal_entry_present"] and report["scientific_outcome"] == "incomplete_journal", "unknown adjudication differs")
        else:
            require(report["final_entries"] == 1 and report["scientific_outcome"] == "reference_unresolved"
                and report["unaccepted_attempt"]["adopted"] is False and not report["terminal_entry_present"], "unresolved attempt differs")
        require(report["pending_cas"] == [] and report["orphan_cas"] == [], "unexpected fresh pending/orphan CAS")
    if inspection is not None: report["writer_inspection"] = inspection
    packet_bookend(p, m)
    check_counts(obs.counts, *expected_counts(case, fresh=True))
    write(root/"fresh_result.json", report)
    event(root, "fresh_adjudicated")


def remove_fixture(session, case_root, codec):
    codec.directory_chain(OUTPUT)
    require(case_root.resolve(strict=True).is_relative_to(OUTPUT.resolve(strict=True)), "fault case outside new output")
    genesis = codec.parse(codec.read_bytes(session.root/"genesis.json"))
    victim = session.root/"objects"/(genesis["fixture_ref"]+".json")
    require(victim.resolve(strict=True).is_relative_to((case_root/"journal").resolve(strict=True)), "fault target outside new case")
    raw = codec.read_bytes(victim)
    require(codec.sha(raw) == genesis["fixture_ref"], "fault object SHA differs")
    with (case_root/"removed_object.json").open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    victim.unlink()
    return dict(path=victim.relative_to(OUTPUT).as_posix(), bytes=len(raw), sha256=codec.sha(raw))


def run_case(case, expected_sha, budget):
    m, root = budget.obs.m, OUTPUT/case["name"]
    root.mkdir(exist_ok=False)
    journal, codec, c = m[case["version"]], m["codec"], m["c"]
    p = budget.phase("parent", case["name"]+"_input", lambda: packet(case["method"], m))
    registered_packet(p)
    initial_counts = Counter(budget.obs.counts)
    session = budget.phase("parent", case["name"]+"_create", lambda: journal.create_session(root/"journal", p["fixture"], "on_time", "late", case["method"]))
    initial, fault_observation = session, []
    if case["kind"] == "success":
        for hour in range(2):
            def step():
                pending = journal.begin_step(session, p["evidence"][hour])
                return journal.commit_step(session, pending, p["actual"][hour])
            session = budget.phase("parent", case["name"]+"_hour_"+str(hour), step)
            require(not session.closed and session.state == p["states"][hour]
                and codec.pack(session.state)[0] == p["source_refs"][4+hour], "writer full prefix differs")
        session = budget.phase("parent", case["name"]+"_finish", lambda: journal.finish(session))
        expected = load(PREP/"baseline.json")[case["method"]]
        def wire_check():
            store = codec.EvidenceStore(session.root)
            actual = store.inventory()
            require(sorted(actual) == expected["cas_keys"] and session.closed and session.scientific_outcome == "missing_input", "terminal CAS/outcome differs")
            for hour in (1, 2):
                entry = codec.parse(codec.read_bytes(session.root/f"entry_{hour:06d}.json"))
                require(entry["payload_ref"] == p["source_refs"][1+hour] and entry["state_ref"] == p["source_refs"][3+hour], "source payload/state wire differs")
            terminal = codec.parse(codec.read_bytes(session.root/"entry_000003.json"))
            require(terminal["payload_ref"] == expected["terminal_ref"], "terminal typed wire differs")
            require(all(codec.read_bytes(store.objects/(key+".json")) == data.encode("utf-8")
                        for key, data in expected["wire"].items()), "source/terminal CAS bytes differ")
            return dict(cas=actual, bytes=sum((store.objects/name).stat().st_size for name in actual))
        wire = budget.phase("parent", case["name"]+"_wire_check", wire_check)
        require(wire["bytes"] == expected["cas_bytes"], "CAS wire bytes differ")
    elif case["kind"] == "reference_unresolved":
        def unresolved():
            try: journal.begin_step(session, None)
            except journal.SessionClosed as error: return error.session
            raise ValueError("missing evidence was accepted")
        session = budget.phase("parent", case["name"]+"_attempt", unresolved)
        require(session.closed and session.ordinal == 1 and session.state == initial.state
            and session.scientific_outcome == "reference_unresolved" and session.publication_outcome == "committed", "unresolved writer differs")
    else:
        def injected():
            pending = journal.begin_step(session, p["evidence"][0])
            def fault(stage, path):
                if path == session.root/"entry_000001.json" and stage == "after_rename":
                    require(not fault_observation, "duplicate registered fault")
                    entry = codec.parse(codec.read_bytes(path))
                    require(entry["ordinal"] == 1 and entry["previous_sha"] == initial.head_sha and entry["kind"] == "hour", "fault publication identity differs")
                    fault_observation.append(dict(stage=stage, path=path.relative_to(OUTPUT).as_posix(), pin=stamp(path)))
                    if case["kind"] == "deletion": fault_observation[0]["removed"] = remove_fixture(session, root, codec)
                    else: raise OSError("registered append cost readback unknown")
            return journal.commit_step(session, pending, p["actual"][0], hook=fault)
        session = budget.phase("parent", case["name"]+"_fault", injected)
        require(len(fault_observation) == 1 and session.closed and session.ordinal == 0 and session.head_sha == initial.head_sha
            and session.state == initial.state and session.publication_outcome == "unknown" and session.failure["may_have_published"], "failed writer adopted or misclassified")
    check_counts(Counter(budget.obs.counts)-initial_counts, *expected_counts(case, fresh=False))
    packet_bookend(p, m)
    binding = journal.trusted_binding(session)
    inspection = inspect_failure(case, p, m, binding) if case["kind"] != "success" else None
    write(root/"trusted_binding.json", binding)
    write(root/"case.json", dict(case=case, trusted_binding=binding, fault=fault_observation,
        writer_state_sha=c.digest(session.state), writer_state_ref=codec.pack(session.state)[0],
        writer_ordinal=session.ordinal, writer_closed=session.closed, publication_outcome=session.publication_outcome,
        failure=c.plain(session.failure), logical_inputs=p["source_refs"], writer_inspection=inspection))
    budget.reserve_fresh()
    from src.staged_rts24_process_guard_v1 import supervise
    intent = fresh_intent(case, stamp(root/"case.json")["sha256"], expected_sha)
    write(root/"fresh_intent.json", intent)
    intent_sha = stamp(root/"fresh_intent.json")["sha256"]
    argv = intent["argv_without_intent_sha"]+["--intent-sha", intent_sha]
    monitor = budget.phase("fresh", case["name"]+"_fresh_quiet", lambda: supervise(argv, cwd=ROOT, output=OUTPUT,
        progress=root/"events.jsonl", limits=FRESH_LIMITS))
    write(root/"fresh_launch.json", dict(argv=argv, intent_sha=intent_sha, monitor=monitor))
    accepted_monitor(monitor)  # First read of scientific child outputs follows complete Job quiet.
    fresh, observed = load(root/"fresh_result.json"), load(root/"fresh_observations.json")
    require(observed["bindings_valid"] and observed["complete"], "fresh observations missing or invalid")
    check_counts(observed["counts"], *expected_counts(case, fresh=True))
    require(case["kind"] == "success" or fresh["writer_inspection"] == inspection, "fresh/writer failure inspection differs")
    return dict(case=case, writer=binding, writer_inspection=inspection, fresh=fresh, observations=observed,
        storage=dict(files=sum(p.is_file() for p in root.rglob("*")), bytes=sum(p.stat().st_size for p in root.rglob("*") if p.is_file())))


def worker(expected_sha, obs):
    verify_role("--worker", expected_sha)
    budget = Budget(OUTPUT, obs)
    record = budget.phase("pre", "full_registration", lambda: verify_registration(expected_sha, obs.m, full=True))
    before_system = system()
    results = [run_case(case, expected_sha, budget) for case in CASES]
    for method in METHODS:
        left, right = (OUTPUT/(version+"_"+method)/"journal/objects" for version in ("v2", "v3"))
        require({p.name: p.read_bytes() for p in left.iterdir()} == {p.name: p.read_bytes() for p in right.iterdir()}, "v2/v3 complete CAS bytes differ")
    for kind in KINDS:
        pair = [next(result for result in results if result["case"]["name"] == version+"_"+kind) for version in ("v2", "v3")]
        require(pair[0]["writer_inspection"] == pair[1]["writer_inspection"], "v2/v3 failure semantics differ")
        for key in ("state", "state_sha", "state_ref", "summary", "independent_audit", "scientific_outcome", "publication_outcome",
                    "state_certainty", "terminal_entry_present", "final_entries", "pending_cas", "orphan_cas", "unaccepted_attempt"):
            require(pair[0]["fresh"].get(key) == pair[1]["fresh"].get(key), "v2/v3 fresh failure semantics differ: "+key)
    budget.phase("post", "historical_end_bookend", lambda: verify_registration(expected_sha, obs.m, full=True))
    check_counts(obs.counts, 94, 260, dict(reference_base_P0=94, reference_raw_need=30, recovery_min_meter=68, recovery_max_meter=68))
    combined = Counter(obs.counts)
    for result in results: combined.update(result["observations"]["counts"])
    check_counts(combined, 186, 514, dict(reference_base_P0=186, reference_raw_need=60, recovery_min_meter=134, recovery_max_meter=134))
    prep_counts = load(PREP/"prepare_observations.json")["counts"]
    combined.update(prep_counts)
    check_counts(combined, 198, 548, dict(reference_base_P0=198, reference_raw_need=66, recovery_min_meter=142, recovery_max_meter=142))
    def report():
        write(OUTPUT/"report.json", dict(authority="DRAFT_NONAUTHORITATIVE", registration_sha=expected_sha,
            system_before=before_system, system_after=system(), cases=results, phases=budget.phases,
            group_seconds=dict(budget.spent), combined_counts=dict(combined), measured_counts_including_fresh=dict(Counter(combined)-Counter(prep_counts)),
            preparation_measured_separately=True, fixed_order_single_descriptive_observation=True,
            preparation_controller_timings=load(PREP/"controller_timings.json"),
            overall_performance_review_complete=False, public_numeric_results=False, native_authorized=False, resource_admission=False))
    budget.phase("report", "saved_report", report)
    write(OUTPUT/"worker_timing.json", dict(phases=budget.phases, group_seconds=dict(budget.spent),
        elapsed=time.perf_counter()-BOOT, excludes="this_record_observations_and_terminal_manifest_publication"))


def complete_core():
    excluded = {"completion.json", "launcher.json", "launcher.stdout.log", "launcher.stderr.log", "worker.stdout.log", "worker.stderr.log"}
    files = {p.relative_to(OUTPUT).as_posix(): stamp(p) for p in sorted(OUTPUT.rglob("*"))
             if p.is_file() and p.relative_to(OUTPUT).as_posix() not in excluded}
    write(OUTPUT/"completion.json", dict(authority="DRAFT_NONAUTHORITATIVE", files=files,
        count=len(files), bytes=sum(pin["bytes"] for pin in files.values()), official_verdict=None, seal=None, receipt=None))


def output_pins():
    from src.staged_rts24_process_guard_v1 import scan_output
    size, files = scan_output(OUTPUT, LIMITS["output_bytes"], LIMITS["files"])
    require(size <= LIMITS["output_bytes"] and files <= LIMITS["files"], "controller output limit")
    return {path.relative_to(OUTPUT).as_posix(): stamp(path) for path in sorted(OUTPUT.rglob("*")) if path.is_file()}


def controller_readback(expected_sha, m):
    """Called only after complete outer Job quiet; cover late logs as well."""
    started = time.perf_counter()
    before = output_pins()
    completion = load(OUTPUT/"completion.json")
    excluded = {"completion.json", "launcher.json", "launcher.stdout.log", "launcher.stderr.log", "worker.stdout.log", "worker.stderr.log"}
    expected_core = {name: pin for name, pin in before.items() if name not in excluded}
    require(completion["authority"] == "DRAFT_NONAUTHORITATIVE" and completion["files"] == expected_core
        and completion["count"] == len(expected_core) and completion["bytes"] == sum(pin["bytes"] for pin in expected_core.values())
        and all(completion[key] is None for key in ("official_verdict", "seal", "receipt")), "core completion/readback differs")
    report, observed = load(OUTPUT/"report.json"), load(OUTPUT/"worker_observations.json")
    require(report["authority"] == "DRAFT_NONAUTHORITATIVE" and report["registration_sha"] == expected_sha
        and report["fixed_order_single_descriptive_observation"] is True
        and all(report[key] is False for key in ("overall_performance_review_complete", "public_numeric_results", "native_authorized", "resource_admission")), "report scope differs")
    require(observed["bindings_valid"] and observed["complete"], "worker observations invalid")
    require([result["case"] for result in report["cases"]] == list(CASES), "completed case set/order differs")
    combined = Counter(observed["counts"])
    check_counts(observed["counts"], 94, 260)
    for case, result in zip(CASES, report["cases"]):
        require(time.perf_counter()-started <= 45, "controller readback budget")
        root = OUTPUT/case["name"]
        case_data, launch = load(root/"case.json"), load(root/"fresh_launch.json")
        require(case_data["case"] == case and result["writer"] == case_data["trusted_binding"], "case/trusted writer readback differs")
        intent_sha = stamp(root/"fresh_intent.json")["sha256"]
        intent = load(root/"fresh_intent.json")
        require(launch["intent_sha"] == intent_sha and launch["argv"] == intent["argv_without_intent_sha"]+["--intent-sha", intent_sha], "fresh intent/launch readback differs")
        accepted_monitor(launch["monitor"])
        fresh, child = load(root/"fresh_result.json"), load(root/"fresh_observations.json")
        require(fresh == result["fresh"] and child == result["observations"] and child["bindings_valid"] and child["complete"], "fresh report/readback differs")
        check_counts(child["counts"], *expected_counts(case, fresh=True))
        p = packet(case["method"], m)
        expected = registered_packet(p)
        if case["kind"] == "success":
            require(all(fresh[key] == expected[key] for key in expected if key not in ("source_refs", "root_shas", "terminal_ref", "cas_keys", "cas_bytes", "wire")), "controller full success differs")
        else: require(inspect_failure(case, p, m, case_data["trusted_binding"]) == result["writer_inspection"] == fresh["writer_inspection"], "controller failure inspection differs")
        packet_bookend(p, m)
        combined.update(child["counts"])
    check_counts(combined, 186, 514)
    require(dict(combined) == report["measured_counts_including_fresh"], "measured aggregate readback differs")
    combined.update(load(PREP/"prepare_observations.json")["counts"])
    check_counts(combined, 198, 548)
    require(dict(combined) == report["combined_counts"], "total aggregate readback differs")
    verify_registration(expected_sha, m, full=True)
    require(before == output_pins(), "output changed during controller readback")
    verification = dict(authority="DRAFT_NONAUTHORITATIVE", registration_sha=expected_sha,
        files=before, all_core_and_late_files_read_back=True, cases=12, selective_calls=198, descriptions=548,
        measured_selective_calls=186, measured_descriptions=514, native_calls=0, numerical_factories=0,
        source_and_old_trees_unchanged=True, readback_seconds=time.perf_counter()-started,
        launcher_wall_through_readback=time.perf_counter()-BOOT,
        timing_excludes="this_verification_publication_final_scan_and_console_exit",
        official_verdict=None, seal=None, receipt=None)
    final_bytes = len((json.dumps(verification, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)+"\n").encode())
    require(sum(pin["bytes"] for pin in before.values())+final_bytes <= LIMITS["output_bytes"]
        and len(before)+1 <= LIMITS["files"] and time.perf_counter()-started <= 45, "controller terminal budget")
    write(OUTPUT/"controller_verification.json", verification)
    require(output_pins() == {**before, "controller_verification.json": stamp(OUTPUT/"controller_verification.json")}, "controller terminal tree differs")


def launch_core(*, preparation, expected_sha, timings):
    from experiments.staged_rts24_append_cost_observer_v1 import Observation
    from src.staged_rts24_process_guard_v1 import supervise
    if preparation:
        with Observation() as obs:
            bound = pins(obs.m)
        PREP.mkdir(parents=True, exist_ok=False)
        timings["_owns_target"] = True
        write(PREP/"request.json", dict(schema="saved_append_cost_preparation_v1", authority="DRAFT_NONAUTHORITATIVE",
            pins=bound, cases=CASES, limits=PREP_LIMITS, system=system(), native_authorized=False))
        expected_sha = stamp(PREP/"request.json")["sha256"]
        target, role, limits = PREP, "--prepare-worker", PREP_LIMITS
    else:
        with Observation() as obs: verify_registration(expected_sha, obs.m, full=True)
        OUTPUT.mkdir(parents=True, exist_ok=False)
        timings["_owns_target"] = True
        target, role, limits = OUTPUT, "--worker", LIMITS
    argv = [sys.executable, "-B", "-s", str(Path(__file__).resolve()), role, "--registration-sha", expected_sha]
    write(target/"launcher_start.json", dict(authority="DRAFT_NONAUTHORITATIVE", argv=argv, limits=limits,
        registration_or_request_sha=expected_sha, system=system()))
    with (target/"launcher.stdout.log").open("x", encoding="utf-8") as out, (target/"launcher.stderr.log").open("x", encoding="utf-8") as err:
        with redirect_stdout(out), redirect_stderr(err):
            timings["controller_preflight_seconds"] = time.perf_counter()-timings["started"]
            monitor_start = time.perf_counter()
            monitor = supervise(argv, cwd=ROOT, output=target, progress=target/"events.jsonl", limits=limits)
            timings["owned_monitor_seconds"] = time.perf_counter()-monitor_start
            timings["post_quiet_started"] = time.perf_counter()
            timings["job_quiet_confirmed"] = monitor["job_quiet_confirmed"]
            write(target/"launcher.json", monitor)
    accepted_monitor(monitor)
    if preparation:
        with Observation() as obs: verify_request(expected_sha, obs.m, full=True)
        prepared = load(PREP/"prepare_observations.json")
        require(prepared["bindings_valid"] and prepared["complete"], "preparation observations invalid")
        check_counts(prepared["counts"], 12, 34)
        require(set(load(PREP/"baseline.json")) == set(METHODS), "baseline method set differs")
        artifacts = {p.relative_to(PREP).as_posix(): stamp(p) for p in sorted(PREP.rglob("*")) if p.is_file()}
        write(REGISTRATION, dict(schema="saved_append_cost_registration_v1", authority="DRAFT_NONAUTHORITATIVE",
            request_sha=expected_sha, preparation_artifacts=artifacts, cases=CASES, limits=LIMITS,
            fresh_limits=FRESH_LIMITS, groups=GROUPS, native_authorized=False, solver_calls_allowed=0,
            expected_preparation=dict(calls=12, descriptions=34), expected_measurement=dict(calls=186, descriptions=514)))
    else:
        try:
            with Observation() as obs: controller_readback(expected_sha, obs.m)
        except BaseException as error:
            write(OUTPUT/"controller_failure.json", dict(accepted_success=False, error=type(error).__name__+": "+str(error),
                owned_worker_monitor=monitor, requires_successor=True))
            raise
    return dict(role="preparation" if preparation else "measurement", monitor=monitor,
        registration_sha=stamp(REGISTRATION)["sha256"])


def launch(*, preparation, expected_sha=None):
    target = PREP if preparation else OUTPUT
    timings = dict(authority="DRAFT_NONAUTHORITATIVE", started=time.perf_counter(),
        controller_preflight_seconds=None, owned_monitor_seconds=None, post_quiet_readback_seconds=None,
        accepted_success=False, error=None, timing_scope="launch_entry_through_last_record_excludes_own_publication_console_and_process_exit")
    result = None
    try:
        result = launch_core(preparation=preparation, expected_sha=expected_sha, timings=timings)
        timings["accepted_success"] = True
    except BaseException as error:
        timings["error"] = type(error).__name__+": "+str(error)
        raise
    finally:
        now = time.perf_counter()
        owns_target = timings.pop("_owns_target", False)
        timings["launcher_total_seconds"] = now-timings["started"]
        if timings.get("post_quiet_started") is not None:
            post = now-timings.pop("post_quiet_started")
            timings["post_monitor_processing_seconds"] = post
            if timings.get("job_quiet_confirmed"): timings["post_quiet_readback_seconds"] = post
        if timings["controller_preflight_seconds"] is None: timings["controller_preflight_seconds"] = timings["launcher_total_seconds"]
        if result is not None: timings["registration_sha"] = result["registration_sha"]
        if owns_target:
            raw_size = len((json.dumps(timings, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)+"\n").encode())
            from src.staged_rts24_process_guard_v1 import scan_output
            limits = PREP_LIMITS if preparation else LIMITS
            size, files = scan_output(target, limits["output_bytes"], limits["files"])
            require(size+raw_size <= limits["output_bytes"] and files+1 <= limits["files"], "late controller observation budget")
            write(target/"controller_timings.json", timings)
    print(json.dumps({**result, "controller_timings": timings, "launcher_wall_before_final_stdout": time.perf_counter()-BOOT}, sort_keys=True))


def cli():
    parser = argparse.ArgumentParser(description="Only the fixed saved-input cost diagnostic; no native/solver entry.")
    roles = parser.add_mutually_exclusive_group(required=True)
    roles.add_argument("--prepare-registration", action="store_true")
    roles.add_argument("--launch", action="store_true")
    roles.add_argument("--prepare-worker", action="store_true")
    roles.add_argument("--worker", action="store_true")
    roles.add_argument("--fresh", choices=[case["name"] for case in CASES])
    parser.add_argument("--registration-sha")
    parser.add_argument("--case-sha")
    parser.add_argument("--intent-sha")
    args = parser.parse_args()
    if not args.prepare_registration: require(args.registration_sha is not None, "external exact SHA required")
    if args.fresh: require(args.case_sha is not None and args.intent_sha is not None, "external exact case/intent SHAs required")
    if args.prepare_registration or args.launch:
        launch(preparation=args.prepare_registration, expected_sha=args.registration_sha)
        return
    target, prefix = (PREP, "prepare") if args.prepare_worker else ((OUTPUT/args.fresh, "fresh") if args.fresh else (OUTPUT, "worker"))
    from experiments.staged_rts24_append_cost_observer_v1 import Observation
    with (target/(prefix+".stdout.log")).open("x", encoding="utf-8") as out, (target/(prefix+".stderr.log")).open("x", encoding="utf-8") as err:
        with redirect_stdout(out), redirect_stderr(err):
            obs = None
            try:
                with Observation(readonly=bool(args.fresh)) as obs:
                    if args.prepare_worker: prepare_worker(args.registration_sha, obs)
                    elif args.fresh: fresh_worker(args.registration_sha, next(case for case in CASES if case["name"] == args.fresh), args.case_sha, args.intent_sha, obs)
                    else: worker(args.registration_sha, obs)
                    observed = dict(**obs.snapshot(), bindings_valid=True, complete=True, process=system())
                    write(target/(prefix+"_observations.json"), observed)
                if args.worker: complete_core()
                require(time.perf_counter()-BOOT <= (20 if args.prepare_worker else 270 if args.worker else 10), "terminal process budget")
            except BaseException as error:
                import traceback
                traceback.print_exc(file=err); err.flush()
                if obs is not None and not (target/(prefix+"_observations.json")).exists():
                    try: write(target/(prefix+"_observations.json"), dict(counts=dict(obs.counts), inclusive_seconds=dict(obs.seconds),
                        bindings_valid=False, complete=False, error=type(error).__name__+": "+str(error)))
                    except BaseException: traceback.print_exc(file=err); err.flush()
                raise


if __name__ == "__main__": cli()
