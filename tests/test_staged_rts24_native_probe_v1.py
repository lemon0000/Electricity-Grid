"""P1 orchestration in pytest temp dirs, using explicit analytic/fake evidence."""
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pytest

from experiments import staged_rts24_native_probe_v1 as probe
from experiments.staged_rts24_causal_examples_v1 import (
    analytic_fixture, analytic_point, analytic_economic, analytic_child,
)
from src import staged_rts24_development_v1 as c, staged_rts24_journal_v2 as journal
from src import staged_rts24_evidence_store_v1 as codec, staged_rts24_highs_backend_v1 as backend
from src.staged_rts24_causal_v1 import PointEvidence
from test_staged_rts24_numeric_interface_v1 import frame, raw_snapshot
from test_staged_rts24_highs_backend_v1 import FakeApi


@pytest.fixture(autouse=True)
def fixed_test_context(monkeypatch):
    import pyomo.environ as pyo
    def denied(*a, **k): pytest.fail("real numeric backend requested by ordinary runner test")
    monkeypatch.setattr(pyo, "SolverFactory", denied)
    monkeypatch.setattr(backend, "call_highs", denied)
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test": True})
    monkeypatch.setattr(probe, "fingerprints", lambda: {"ordinary_test": True})


def analytic_provider(query):
    role = query.request.role
    if role == "reference_base_P0":
        point = analytic_point(query, query.request.meter_min)
        return PointEvidence(query, point, economic=analytic_economic(query, point))
    if role == "actual_P": return PointEvidence(query, analytic_point(query, query.request.meter_min))
    return analytic_child(query)


def test_public_request_schedule_is_31_with_unresolved_future_identities():
    fixture = c.load_fixture()
    schedule = probe.request_schedule(fixture)
    assert len(schedule) == 31
    assert [r["ordinal"] for r in schedule] == list(range(1, 32))
    assert sum(r["objective"] == "economic" for r in schedule) == 16
    assert [r["hour"] for r in schedule if r["role"] == "actual_P"] == [-2, -1, 0, 1, 2]
    assert all(r["bound_query_sha"] is None for r in schedule)
    assert all(r["request_sha"] is None for r in schedule if r["role"] == "actual_P")
    assert [(r["hour"], r["role"]) for r in schedule[-10:]] == [
        (1, "normal_contract_C"), (1, "fault_firm_F"), (1, "fault_raw_need"),
        (1, "fault_firm_F"), (1, "fault_raw_need"), (2, "normal_contract_C"),
        (2, "fault_firm_F"), (2, "fault_raw_need"), (2, "fault_firm_F"), (2, "fault_raw_need")]
    assert schedule[-9]["outage"]["branches"] == (0,) and schedule[-7]["outage"]["generators"] == (0,)


def test_analytic_prefix_runs_fixed_policy_and_keeps_original_horizon(tmp_path):
    fixture = analytic_fixture()
    calls = []
    def point(q): calls.append(q.request.role); return analytic_provider(q)
    session, failure = probe.actual_prefix(fixture, tmp_path/"journal", point, lambda *a, **k: None)
    assert failure is None and len(session.state.records) == 3 and calls.count("actual_P") == 3
    assert len(calls) == 13 and session.fixture.observation_end == 5
    session = journal.finish(session)
    reopened = journal.reopen(session.root, fixture, probe.PLAN, probe.CLEAN, probe.METHOD, journal.trusted_binding(session))
    assert reopened["state"] == session.state and reopened["scientific_outcome"] == "missing_input"


def test_reference_failure_retains_observed_inputs_without_fake_hour(tmp_path):
    calls = []
    def point(q):
        calls.append(q.request.role)
        if len(calls) == 2: raise probe.NumericUnresolved("fake numeric unresolved")
        return analytic_provider(q)
    session, failure = probe.actual_prefix(analytic_fixture(), tmp_path/"journal", point, lambda *a, **k: None)
    assert not session.state.records and not session.closed
    assert failure["stage"] == "reference_numeric" and failure["current_observation"]["hour"] == 0
    assert failure["unaccepted_status"] == "numeric_unresolved_observed_current_inputs"
    assert failure["candidate_adopted"] is False and len(calls) == 2


def test_actual_failure_saves_existing_unresolved_attempt_not_new_ledger(tmp_path):
    def point(q):
        if q.request.role == "actual_P": raise probe.NumericUnresolved("fake actual unresolved")
        return analytic_provider(q)
    session, failure = probe.actual_prefix(analytic_fixture(), tmp_path/"journal", point, lambda *a, **k: None)
    assert session.closed and not session.state.records and failure["stage"] == "actual_numeric"
    result = journal.reopen(session.root, session.fixture, probe.PLAN, probe.CLEAN, probe.METHOD, journal.trusted_binding(session))
    assert result["scientific_outcome"] == "actual_unresolved" and result["unaccepted_attempt"]


def test_point_parent_child_protocol_reaudits_analytic_raw(tmp_path, monkeypatch):
    item = frame().reference
    problem, raw = raw_snapshot(item)
    # Capture the real transport function before replacing the forbidden entry.
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("ordinary_backend_copy", Path(backend.__file__))
    copied = module_from_spec(spec); spec.loader.exec_module(copied)
    monkeypatch.setattr(backend, "call_highs", lambda p, log: copied.call_highs(p, log, api=FakeApi(raw)))

    def monitor(argv, **kwargs):
        relative, request_sha = argv[argv.index("--point")+1], argv[argv.index("--request-sha")+1]
        code = probe.point_worker(tmp_path, relative, request_sha)
        return dict(job_quiet_confirmed=True, stop_reason=None, exit_code=code)
    client = probe.PointClient(tmp_path, {"ordinary_test": True}, lambda *a, **k: None, monitor=monitor)
    assert client(item.query) == item
    assert (client.reserved, client.imported, client.run_invoked, client.run_returned) == (1, 1, 1, 1)
    assert probe.load(tmp_path/"points/point_0001/result.json")["status"] == "imported"


@pytest.mark.parametrize("failure", ["spawn", "unknown_cleanup", "nonzero"])
def test_failed_point_reservation_is_consumed_and_never_retried(tmp_path, failure):
    def monitor(*a, **kw):
        if failure == "spawn": raise OSError("fake spawn failure")
        return dict(job_quiet_confirmed=failure != "unknown_cleanup", stop_reason=None, exit_code=7)
    client = probe.PointClient(tmp_path, {}, lambda *a, **k: None, monitor=monitor)
    with pytest.raises((ValueError, OSError, probe.TransportUnresolved)): client(frame().reference.query)
    assert client.reserved == 1 and client.imported == 0
    assert (tmp_path/"points/point_0001/request.json").is_file()
    assert not (tmp_path/"points/point_0002").exists()


def test_call_cap_is_checked_before_directory_or_backend(tmp_path):
    client = probe.PointClient(tmp_path, {}, lambda *a, **k: None)
    client.reserved = 31
    with pytest.raises(ValueError, match="call cap"): client(frame().reference.query)
    assert not (tmp_path/"points").exists()


def test_wrong_schedule_role_is_rejected_before_reserve(tmp_path):
    client = probe.PointClient(tmp_path, {}, lambda *a, **k: None, schedule=probe.request_schedule(c.load_fixture()))
    with pytest.raises(ValueError, match="schedule"): client(frame().reference.query)
    assert client.reserved == 0


@pytest.mark.parametrize("change", [dict(objective="min_meter"), dict(anchor_id="0"*64)])
def test_dynamic_slot_objective_and_parent_identity_are_not_dynamic(tmp_path, change):
    item = frame().reference
    request = replace(item.query.request, role="actual_P", anchor_id=item.query.request.identity)
    query = replace(item.query, request=request)
    slot = dict(role=request.role, hour=request.hour, outage=probe.asdict(request.outages),
        objective=request.objective, parent_request_sha=request.anchor_id, request_sha=None)
    client = probe.PointClient(tmp_path, {}, lambda *a, **kw: None, schedule=[slot])
    # Alter declared slot metadata; constructing an actual request with another
    # objective is already rejected by the frozen PointRequest invariant.
    if "objective" in change: slot["objective"] = change["objective"]
    else: slot["parent_request_sha"] = change["anchor_id"]
    with pytest.raises(ValueError, match="schedule"): client(query)
    assert client.reserved == 0 and not (tmp_path/"points").exists()


def test_fresh_is_read_only_and_never_calls_backend(tmp_path, monkeypatch):
    fixture = analytic_fixture()
    session, error = probe.actual_prefix(fixture, tmp_path/"journal", analytic_provider, lambda *a, **k: None)
    assert error is None
    session = journal.finish(session)
    probe.write(tmp_path/"trusted_binding.json", journal.trusted_binding(session))
    probe.write(tmp_path/"start.json", dict(pins={"ordinary_test": True}))
    monkeypatch.setattr(c, "load_fixture", lambda: fixture)
    before = {p.relative_to(session.root): p.read_bytes() for p in session.root.rglob("*") if p.is_file()}
    assert probe.fresh_worker(tmp_path) == 0
    assert probe.load(tmp_path/"fresh.json")["solver_calls"] == 0
    assert before == {p.relative_to(session.root): p.read_bytes() for p in session.root.rglob("*") if p.is_file()}


def test_child_path_cannot_escape_attempt(tmp_path):
    with pytest.raises(ValueError, match="outside"): probe.child_path(tmp_path, "../")


def test_launcher_default_cli_does_not_start_or_create_attempt():
    path = Path(probe.__file__).with_name("staged_rts24_native_launcher_v1.py")
    existed = probe.OUTPUT.exists()
    result = subprocess.run([sys.executable, "-B", str(path)], capture_output=True, timeout=5)
    assert result.returncode != 0 and b"--execute-p1" in result.stderr
    assert probe.OUTPUT.exists() == existed


def install_fake_backend(monkeypatch, transform=None):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("ordinary_fake_transport", Path(backend.__file__))
    copied = module_from_spec(spec); spec.loader.exec_module(copied)
    _, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected)
    def call(problem, path):
        try: raw = copied.call_highs(problem, path, api=api)
        except copied.BackendFailure as exc: raise backend.BackendFailure(exc.record, exc) from exc
        if transform: transform(raw, path)
        return raw
    monkeypatch.setattr(backend, "call_highs", call)
    return api


@pytest.mark.parametrize("failure", ["fingerprint", "store", "log", "raw_publish"])
def test_point_post_run_dependency_or_publication_failure_is_transport(tmp_path, monkeypatch, failure):
    install_fake_backend(monkeypatch, (lambda raw, p: p.unlink()) if failure == "log" else None)
    def monitor(argv, **kw):
        if failure == "fingerprint":
            n = [0]
            def changing_pins():
                n[0] += 1
                return {"ordinary_test": True} if n[0] == 1 else {"drift": True}
            monkeypatch.setattr(probe, "fingerprints", changing_pins)
        if failure == "store":
            original = codec.EvidenceStore.put
            def put(self, value):
                if type(value) is PointEvidence: raise OSError("fake point CAS publication")
                return original(self, value)
            monkeypatch.setattr(codec.EvidenceStore, "put", put)
        if failure == "raw_publish":
            original = probe.write
            def write(path, value):
                if Path(path).name == "native.json": raise OSError("fake raw publication")
                return original(path, value)
            monkeypatch.setattr(probe, "write", write)
        code = probe.point_worker(tmp_path, argv[argv.index("--point")+1], argv[argv.index("--request-sha")+1])
        return dict(job_quiet_confirmed=True, stop_reason="child_exit_nonzero", exit_code=code)
    client = probe.PointClient(tmp_path, {"ordinary_test": True}, lambda *a, **k: None, monitor=monitor)
    with pytest.raises(probe.TransportUnresolved): client(frame().reference.query)
    saved = probe.load(tmp_path/"points/point_0001/result.json")
    assert saved["status"] == "transport_unresolved" and client.imported == 0 and client.reserved == 1


@pytest.mark.parametrize("mode", ["nonoptimal", "warning"])
def test_failed_numeric_exit_still_reads_raw_counts_and_reproduces_witness(tmp_path, monkeypatch, mode):
    api = install_fake_backend(monkeypatch)
    if mode == "nonoptimal": api.model_status = "kTimeLimit"
    else: api.fail_at = "run"
    def monitor(argv, **kw):
        code = probe.point_worker(tmp_path, argv[argv.index("--point")+1], argv[argv.index("--request-sha")+1])
        assert code == 2
        return dict(job_quiet_confirmed=True, stop_reason="child_exit_nonzero", exit_code=code)
    client = probe.PointClient(tmp_path, {"ordinary_test": True}, lambda *a, **k: None, monitor=monitor)
    with pytest.raises(probe.NumericUnresolved): client(frame().reference.query)
    assert (client.reserved, client.imported, client.run_invoked, client.run_returned) == (1, 0, 1, 1)
    assert probe.load(tmp_path/"points/point_0001/result.json")["status"] == "numeric_unresolved"


@pytest.mark.parametrize("getter", ["getInfo", "getRunTime"])
def test_incomplete_getter_diagnostics_remain_transport_even_with_nonoptimal_status(tmp_path, monkeypatch, getter):
    api = install_fake_backend(monkeypatch)
    api.model_status = "kTimeLimit"
    monkeypatch.setattr(api, getter, lambda: (_ for _ in ()).throw(OSError("fake getter failure")))
    def monitor(argv, **kw):
        code = probe.point_worker(tmp_path, argv[argv.index("--point")+1], argv[argv.index("--request-sha")+1])
        return dict(job_quiet_confirmed=True, stop_reason="child_exit_nonzero", exit_code=code)
    client = probe.PointClient(tmp_path, {"ordinary_test": True}, lambda *a, **k: None, monitor=monitor)
    with pytest.raises(probe.TransportUnresolved): client(frame().reference.query)
    assert probe.load(tmp_path/"points/point_0001/native.json")["extraction_errors"]
    assert probe.load(tmp_path/"points/point_0001/result.json")["status"] == "transport_unresolved"


@pytest.mark.parametrize("stage", ["reference", "actual"])
def test_transport_unknown_keeps_prefix_without_artificial_terminal(tmp_path, stage):
    calls = [0]
    def point(query):
        calls[0] += 1
        if (stage == "reference" and calls[0] == 2) or (stage == "actual" and query.request.role == "actual_P"):
            raise probe.TransportUnresolved("fake killed child")
        return analytic_provider(query)
    with pytest.raises(probe.TransportUnresolved):
        probe.actual_prefix(analytic_fixture(), tmp_path/"journal", point, lambda *a, **k: None)
    assert (tmp_path/"trusted_prefixes/prefix_000000.json").is_file()
    assert not (tmp_path/"fresh.json").exists()
    assert not list((tmp_path/"journal").glob("entry_*.json"))


@pytest.mark.parametrize("stage", ["actual", "contract", "finish"])
def test_worker_unknown_failure_never_finishes_or_launches_fresh(tmp_path, monkeypatch, stage):
    fixture = analytic_fixture()
    monkeypatch.setattr(probe, "OUTPUT", tmp_path)
    monkeypatch.setattr(c, "load_fixture", lambda: fixture)
    monkeypatch.setattr(probe, "preserve", lambda: {})
    monkeypatch.setattr(probe, "request_schedule", lambda f: [])
    monkeypatch.setattr(probe, "REGISTRATION", tmp_path/"registration.json")
    probe.write(probe.REGISTRATION, dict(pins={"ordinary_test": True}, preserved={}, schedule_sha=c.digest([])))
    probe.write(tmp_path/"launcher_start.json", dict(limits=probe.LIMITS, package="staged_rts24_P1_v1", registration_sha="test"))
    def point(query):
        if stage == "actual" and query.request.role == "actual_P": raise probe.TransportUnresolved("fake transport")
        return analytic_provider(query)
    monkeypatch.setattr(probe, "PointClient", lambda *a, **kw: point)
    def contracts(*a, **kw):
        if stage == "contract": raise probe.TransportUnresolved("fake contract transport")
    monkeypatch.setattr(probe, "representative_contracts", contracts)
    if stage == "finish":
        def failed_finish(session):
            return replace(session, closed=True, scientific_outcome="persistence_failure", publication_outcome="unresolved")
        monkeypatch.setattr(journal, "finish", failed_finish)
    else:
        monkeypatch.setattr(journal, "finish", lambda *a, **kw: pytest.fail("finish after transport failure"))
    from src import staged_rts24_process_guard_v1 as guard
    monkeypatch.setattr(guard, "supervise", lambda *a, **kw: pytest.fail("fresh after transport failure"))
    with pytest.raises(probe.TransportUnresolved): probe.worker(tmp_path, "test")
    assert (tmp_path/"trusted_prefixes/prefix_000000.json").is_file()
    assert not (tmp_path/"trusted_binding.json").exists() and not (tmp_path/"fresh_process.json").exists()


def test_registration_light_check_avoids_recompilation_and_checks_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "REGISTRATION", tmp_path/"registration.json")
    monkeypatch.setattr(probe, "require_compute", lambda: None)
    value = dict(schema="staged_rts24_native_registration_v1", authority="DRAFT_NONAUTHORITATIVE",
        native_authorized=False, output=str(probe.OUTPUT), limits=probe.LIMITS, point_limits=probe.POINT_LIMITS,
        fresh_limits=probe.FRESH_LIMITS, max_point_attempts=31, pins={"ordinary_test": True}, schedule=[], schedule_sha=c.digest([]),
        preserved={}, authorization="separate_explicit_user_instruction_required_not_granted_by_this_file")
    sha = probe.write(probe.REGISTRATION, value)
    monkeypatch.setattr(probe, "request_schedule", lambda *a: pytest.fail("light child rebuilt schedule"))
    assert probe.verify_registration(sha, full=False) == value
    with pytest.raises(ValueError, match="SHA"): probe.verify_registration("0"*64, full=False)
    for modified in ({**value, "lease": "extra"}, {**value, "authorization": "changed"}):
        probe.REGISTRATION.write_bytes(codec.canonical(modified))
        with pytest.raises(ValueError, match="scope"): probe.verify_registration(probe.stamp(probe.REGISTRATION)["sha256"], full=False)
    monkeypatch.setattr(probe, "require_compute", lambda: (_ for _ in ()).throw(ValueError("interpreter")))
    with pytest.raises(ValueError, match="interpreter"): probe.verify_registration(sha, full=False)


def test_launcher_verification_failure_creates_no_attempt(tmp_path, monkeypatch):
    from experiments import staged_rts24_native_launcher_v1 as launcher
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"p1")
    monkeypatch.setattr(probe, "verify_registration", lambda *a: (_ for _ in ()).throw(ValueError("invalid registration")))
    with pytest.raises(ValueError): launcher.execute("0"*64)
    assert not probe.OUTPUT.exists()


@pytest.mark.parametrize("mode", ["--worker", "--fresh"])
def test_cli_failure_is_saved_in_stderr_and_diagnostic(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(probe, "OUTPUT", tmp_path)
    monkeypatch.setattr(probe, "install_observers", lambda **kw: lambda: {})
    monkeypatch.setattr(probe, "verify_registration", lambda *a, **kw: (_ for _ in ()).throw(ValueError("fake bootstrap")))
    monkeypatch.setattr(sys, "argv", ["probe", mode, "--root", str(tmp_path), "--registration-sha", "0"*64])
    assert probe.cli() == 3
    prefix = "worker" if mode == "--worker" else "fresh"
    assert "fake bootstrap" in (tmp_path/(prefix+".stderr.log")).read_text()
    assert probe.load(tmp_path/(prefix+"_failure.json"))["ownership_or_transport_unknown"]
    assert (tmp_path/(prefix+"_observations.json")).is_file()


def test_fresh_inner_cap_leaves_outer_no_progress_margin():
    assert probe.FRESH_LIMITS["wall_seconds"] == 20 < probe.LIMITS["no_progress_seconds"] == 30


def test_observers_count_recompilation_replay_and_deny_parent_native(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from src import staged_rts24_numeric_interface_v1 as numeric, staged_rts24_reference_queries_v1 as selective
    from src import staged_rts24_causal_v2 as policy, staged_rts24_causal_audit_v2 as audit
    import importlib
    import pyomo.environ as pyo
    # Register undo before CLI-style installation changes cached module aliases.
    names = [(c, ("hour_requests", "bind", "build_point_model", "digest")),
        (numeric, ("compile_problem", "import_snapshot")),
        (backend, ("call_highs", "make_model", "snapshot_from_raw", "hessian_columns")),
        (selective, ("reference_requests",)),
        (policy, ("reference_requests", "prepare_hour", "propose_hour", "accept_hour", "execution_summary")),
        (audit, ("reference_requests", "audit_execution")),
        (journal, ("reference_requests", "create_session", "begin_step", "commit_step", "finish", "reopen", "trusted_binding",
            "runtime_identity", "audit_execution", "pack", "read_bytes", "publish")),
        (codec, ("pack", "read_bytes", "publish")), (codec.EvidenceStore, ("put", "get")),
        (probe, ("fingerprints",)), (pyo, ("SolverFactory",))]
    for name in ("src.grid.dc_opf", "src.grid.network_grid_need", "src.grid.scopf"):
        names.append((importlib.import_module(name), ("SolverFactory",)))
    names.append((importlib.import_module("src.grid.rts_gmlc_scuc"), ("Highs",)))
    for module, attributes in names:
        for attribute in attributes: monkeypatch.setattr(module, attribute, getattr(module, attribute))
    api = SimpleNamespace(Highs=lambda: pytest.fail("parent native constructor escaped guard"))
    observe = probe.install_observers(allow_native=False, api=api)
    item = frame().reference
    problem, raw = raw_snapshot(item)
    assert numeric.import_snapshot(item.query, problem, raw) == item
    counts = observe()["counts"]
    assert counts["importer_recompile"] == 1 and counts["numeric_import_returned"] == 1
    session, failure = probe.actual_prefix(analytic_fixture(), tmp_path/"journal", analytic_provider, lambda *a, **kw: None)
    assert failure is None
    session = journal.finish(session)
    before = observe()["counts"].get("pyomo_build_attempts", 0)
    journal.reopen(session.root, session.fixture, probe.PLAN, probe.CLEAN, probe.METHOD, journal.trusted_binding(session))
    assert observe()["counts"].get("pyomo_build_attempts", 0) == before
    assert observe()["counts"]["journal_reopen_returned"] == 1
    with pytest.raises(probe.TransportUnresolved): api.Highs()
    assert observe()["counts"]["native_factory_requested"] == 1


def test_observation_publication_failure_cannot_publish_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "OUTPUT", tmp_path)
    monkeypatch.setattr(probe, "install_observers", lambda **kw: lambda: {})
    monkeypatch.setattr(probe, "verify_registration", lambda *a, **kw: {})
    monkeypatch.setattr(probe, "worker", lambda *a: 0)
    original = probe.write
    def write(path, value):
        if Path(path).name == "worker_observations.json": raise OSError("fake observations publication")
        return original(path, value)
    monkeypatch.setattr(probe, "write", write)
    monkeypatch.setattr(sys, "argv", ["probe", "--worker", "--root", str(tmp_path), "--registration-sha", "0"*64])
    assert probe.cli() == 3
    assert (tmp_path/"worker_failure.json").is_file() and not (tmp_path/"completion.json").exists()
    assert "fake observations publication" in (tmp_path/"worker.stderr.log").read_text()


def test_launcher_terminal_write_failure_is_logged_not_success(tmp_path, monkeypatch):
    from experiments import staged_rts24_native_launcher_v1 as launcher
    from src import staged_rts24_process_guard_v1 as guard
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"attempt")
    monkeypatch.setattr(probe, "verify_registration", lambda *a: {"preserved": {}})
    monkeypatch.setattr(probe, "preserve", lambda: {})
    monkeypatch.setattr(guard, "supervise", lambda *a, **kw: dict(job_quiet_confirmed=True, stop_reason=None, exit_code=0))
    original = probe.write
    def write(path, value):
        if Path(path).name == "launcher.json": raise OSError("fake terminal publication")
        return original(path, value)
    monkeypatch.setattr(probe, "write", write)
    assert launcher.execute("0"*64) == 3
    saved = probe.load(probe.OUTPUT/"launcher_failure.json")
    assert not saved["accepted_success"] and saved["process_observation"]["job_quiet_confirmed"]
    assert "fake terminal publication" in (probe.OUTPUT/"launcher.stderr.log").read_text()


def test_preservation_reuses_historical_pretty_json_bytes_without_rewriting():
    result = probe.preserve()
    assert result["numeric_interface_checks"]["sha256"] == probe.NUMERIC_CHECKS_SHA
    assert result["prior"]["b1_b3_files"] == 118 and len(result["cores"]) == 2


def test_clean_interpreter_preservation_matches_legacy_without_importing_psutil():
    code = ("import json,sys; from experiments import staged_rts24_native_probe_v1 as p; "
        "old=p.load(p.OUTPUT.parent/'development_checks_01/preservation_before.json'); new=p.preserve(); "
        "assert all(new[k]==old[k] for k in ('prior','cores','numeric_interface_checks')); "
        "assert 'psutil' not in sys.modules; assert not p.OUTPUT.exists(); print('clean_preservation_equal')")
    result = subprocess.run([sys.executable, "-B", "-s", "-c", code], cwd=probe.ROOT,
        capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert b"clean_preservation_equal" in result.stdout


def test_preservation_rejects_b1_source_drift(monkeypatch):
    original = probe.stamp
    def stamp(path):
        value = original(path)
        if Path(path) == probe.ROOT/"src/staged_deliverability_development_v1.py": return {**value, "sha256": "0"*64}
        return value
    monkeypatch.setattr(probe, "stamp", stamp)
    with pytest.raises(ValueError, match="B1-B3"): probe.preserve()


def test_preservation_rejects_self_described_build_source_omission(monkeypatch):
    original = codec.read_bytes
    def read(path, **kw):
        raw = original(path, **kw)
        if str(path).replace("\\", "/").endswith("staged_deliverability_rts24_v1_non_authoritative/build_01/report.json"):
            import json
            value = json.loads(raw)
            value["fingerprints"]["repository"].pop("experiments/staged_rts24_build_diagnostic_v1.py")
            return json.dumps(value).encode()
        return raw
    monkeypatch.setattr(codec, "read_bytes", read)
    with pytest.raises(ValueError, match="build dependency"): probe.preserve()
