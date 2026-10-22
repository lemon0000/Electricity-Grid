"""Temporary-directory development checks; no solver or writable reopen."""
from dataclasses import replace
from fractions import Fraction as Q
import math
import os

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
from src import staged_rts24_development_v1 as c
from src import staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_journal_v1 as journal

REAL_IDENTITY = journal.runtime_identity


@pytest.fixture(autouse=True)
def bounded_ordinary_test(monkeypatch):
    import pyomo.environ as pyo
    def denied(*args, **kwargs): pytest.fail("ordinary journal test requested solver")
    monkeypatch.setattr(pyo, "SolverFactory", denied)
    # This fixture tests journal semantics. The registered integration probe checks real pins.
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test_only": "fixed"})


def store_at(tmp_path):
    (tmp_path/"objects").mkdir()
    return codec.EvidenceStore(tmp_path)


def start(tmp_path, method="full_temporal"):
    fixture = analytic_fixture(late=True)
    return journal.create_session(tmp_path/"session", fixture, "on_time", "late", method)


def pending(session):
    item = journal.begin_step(session, analytic_hour(session.fixture, session.state))
    return item, analytic_actual(item.prepared, item.proposal)


def replay(session):
    return journal.reopen(session.root, session.fixture, session.state.plan, session.state.clean_path,
                          session.state.method, journal.trusted_binding(session))


def test_lossless_codec_and_deduplicated_full_frames(tmp_path):
    store = store_at(tmp_path)
    fixture = analytic_fixture()
    state = journal.policy.initialize_execution(fixture, "on_time", "early", "full_temporal")
    evidence = analytic_hour(fixture, state)
    value = dict(fixture=fixture, evidence=evidence, numbers=(Q(1, 3), -0., 5e-324), sequence=[1, True, None])
    identity = store.put(value)
    reopened = store.get(identity)
    assert reopened == value and c.digest(reopened) == c.digest(value)
    assert math.copysign(1., reopened["numbers"][1]) == -1 and reopened["numbers"][2].hex() == (5e-324).hex()
    inventory = store.inventory()
    assert sum(codec.parse(codec.read_bytes(store.objects/name))["kind"] == "Rts24Data" for name in inventory) == 1
    assert store.put(value) == identity and store.inventory() == inventory


@pytest.mark.parametrize("value", [float("nan"), float("inf"), c.Outage(12), c.Outage("bad", [1])])
def test_nonfinite_or_wrong_dataclass_types_do_not_publish(tmp_path, value):
    store = store_at(tmp_path)
    with pytest.raises(ValueError): store.put(value)
    assert store.inventory() == {}


def test_complexity_and_publication_budget_precede_writes(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    cycle = []; cycle.append(cycle)
    with pytest.raises(ValueError, match="cyclic"): store.put(cycle)
    monkeypatch.setattr(codec, "MAX_TOTAL", 8)
    with pytest.raises(ValueError, match="budget"): store.put("too large")
    assert list(store.objects.iterdir()) == []
    with pytest.raises(ValueError, match="JSON complexity"): codec.parse(b"["*257+b"0"+b"]"*257)
    with pytest.raises(ValueError, match="duplicate"): codec.parse(b'{"x":1,"x":2}')


def test_noncanonical_wire_and_unknown_classes_are_rejected(tmp_path):
    store = store_at(tmp_path)
    identity = store.put(c.Outage("normal"))
    for wire in (["ref", identity], ["class", "Outage", [["name", 2], ["branches", ["tuple", []]], ["generators", ["tuple", []]]]],
                 ["class", "ArbitraryImport", []]):
        data = codec.canonical(dict(schema=codec.SCHEMA, kind="Outage", payload=wire))
        key = codec.sha(data)
        codec.publish(store.objects/(key+".json"), data)
        with pytest.raises(ValueError): store.get(key)


def test_final_pending_conflict_and_replaced_directory_are_rejected(tmp_path):
    store = store_at(tmp_path)
    identity = store.put("item")
    data = codec.read_bytes(store.objects/(identity+".json"))
    (store.objects/(identity+".json.pending")).write_bytes(data)
    with pytest.raises(ValueError, match="conflict"): store.inventory()
    with pytest.raises(ValueError): store.put("item")
    store.objects.rename(tmp_path/"old_objects")
    store.objects.mkdir()
    with pytest.raises(ValueError, match="directory identity"): store.inventory()


@pytest.mark.parametrize("method", c.METHODS)
def test_continuous_three_method_save_close_and_replay(tmp_path, method, monkeypatch):
    session = start(tmp_path, method)
    for _ in range(5):
        item, actual = pending(session)
        session = journal.commit_step(session, item, actual)
        assert not session.closed
    session = journal.finish(session)
    assert session.closed and session.scientific_outcome == "complete"
    def denied(*args, **kwargs): pytest.fail("saved replay generated new evidence or full contract queries")
    monkeypatch.setattr(c, "hour_requests", denied)
    result = replay(session)
    assert result["state"] == session.state and result["summary"] == journal.policy.execution_summary(session.fixture, session.state)
    assert result["publication_outcome"] == "committed" and result["state_certainty"] == "known"
    assert result["terminal_entry_present"] and result["resume_permitted"] is False
    assert result["summary"]["actual_accepted_hours"] == (5 if method == "full_temporal" else 0)
    if method == "full_temporal": assert result["summary"]["observed_primary_deadline_miss"] == 40


def test_missing_next_input_is_closed_and_right_censors_only_existing_tasks(tmp_path):
    session = start(tmp_path)
    for _ in range(2):
        item, actual = pending(session)
        session = journal.commit_step(session, item, actual)
    session = journal.finish(session)
    result = replay(session)
    assert result["scientific_outcome"] == "missing_input" and result["summary"]["primary_right_censored"]
    assert result["summary"]["method_conditions_satisfied"] is None
    assert len(result["summary"]["tasks"]) == 2 and result["state"].ledger.debt == 40


@pytest.mark.parametrize("stage", ["reference", "actual"])
def test_missing_required_evidence_saves_unaccepted_observation_without_advancing(tmp_path, stage):
    session = start(tmp_path)
    initial = session.state
    if stage == "reference":
        with pytest.raises(journal.SessionClosed) as error: journal.begin_step(session, None)
        closed = error.value.session
    else:
        item, _ = pending(session)
        closed = journal.commit_step(session, item, None)
    assert closed.closed and closed.state == initial
    result = replay(closed)
    assert result["scientific_outcome"] == stage+"_unresolved"
    assert result["state"] == initial and result["summary"]["tasks"] == ()
    assert result["unaccepted_attempt"]["observation"].workload == 100
    assert result["unaccepted_attempt"]["adopted"] is False
    assert result["terminal_entry_present"] is False and result["closed_entry_present"] is True


def test_known_actual_rejection_is_journaled_without_advancing_ledger(tmp_path):
    session = start(tmp_path)
    item, actual = pending(session)
    bad = replace(actual, point=replace(actual.point, flows_mw=((0, 0.), (1, 0.), (2, 0.))))
    rejected = journal.commit_step(session, item, bad)
    assert rejected.state.stopped and rejected.state.ledger == session.state.ledger
    closed = journal.finish(rejected)
    result = replay(closed)
    assert result["scientific_outcome"] == "known_rejection"
    assert not result["state"].records[-1]["actual_accepted"] and result["summary"]["unapplied_attempts"]


@pytest.mark.parametrize("phase", ["before_rename", "after_rename"])
def test_prepublish_and_publication_unknown_are_decided_from_final_bytes(tmp_path, phase):
    session = start(tmp_path)
    item, actual = pending(session)
    def fail(name, path):
        if path.name.startswith("entry_") and name == phase: raise OSError("injected publish failure")
    closed = journal.commit_step(session, item, actual, hook=fail)
    assert closed.closed and closed.state == session.state
    assert closed.publication_outcome == ("unknown" if phase == "after_rename" else "not_published")
    result = replay(closed)
    assert result["resume_permitted"] is False
    assert len(result["state"].records) == (1 if phase == "after_rename" else 0)
    assert result["publication_outcome"] == ("committed" if phase == "after_rename" else "not_published")
    if phase == "before_rename": assert result["unaccepted_attempt"]["status"] == "observed_pending_unaccepted"


def test_unknown_without_final_or_pending_remains_unresolved(tmp_path):
    session = start(tmp_path)
    item, actual = pending(session)
    def fail(name, path):
        if path.name.startswith("entry_") and name == "after_rename":
            path.rename(tmp_path/"hidden_final")
            raise OSError("lost final visibility")
    closed = journal.commit_step(session, item, actual, hook=fail)
    result = replay(closed)
    assert result["state"] == session.state and result["publication_outcome"] == "unknown"
    assert result["state_certainty"] == "unresolved"


def test_trusted_bindings_runtime_and_file_tampering_are_rejected(tmp_path, monkeypatch):
    session = start(tmp_path)
    binding = journal.trusted_binding(session)
    with pytest.raises(ValueError, match="genesis"): journal.reopen(session.root, session.fixture, "on_time", "late", "full_temporal", {**binding, "genesis_sha": "0"*64})
    with pytest.raises(ValueError, match="context"): journal.reopen(session.root, replace(session.fixture, observation_end=6), "on_time", "late", "full_temporal", binding)
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"changed": True})
    with pytest.raises(ValueError, match="runtime"): replay(session)
    with pytest.raises(ValueError, match="runtime"): pending(session)


def test_actual_runtime_identity_binds_new_and_transitive_sources():
    pins = REAL_IDENTITY()
    assert len(pins["sources"]) == 28 and len(pins["external"]) == 10
    assert "src/staged_rts24_causal_v1.py" in pins["sources"] and "highspy" in pins["versions"]
    assert pins["executable_sha256"] and pins["sources"]["src/staged_rts24_journal_v1.py"]


@pytest.mark.parametrize("target", ["entry_000001.json", "entry_000002.json"])
def test_trusted_head_detects_deleted_hour_or_terminal_tail(tmp_path, target):
    session = start(tmp_path)
    item, actual = pending(session)
    session = journal.finish(journal.commit_step(session, item, actual))
    binding = journal.trusted_binding(session)
    (session.root/target).rename(tmp_path/"removed_tail")
    with pytest.raises(ValueError): journal.reopen(session.root, session.fixture, "on_time", "late", "full_temporal", binding)


@pytest.mark.parametrize("action", ["delete", "flip_may", "flip_outcome"])
def test_trusted_failure_presence_and_bytes_cannot_be_changed(tmp_path, action):
    session = start(tmp_path)
    item, actual = pending(session)
    def fail(name, path):
        if path.name.startswith("entry_") and name == "after_rename": raise OSError("unknown")
    closed = journal.commit_step(session, item, actual, hook=fail)
    binding = journal.trusted_binding(closed)
    path = session.root/"failure.json"
    if action == "delete": path.rename(tmp_path/"removed_failure")
    else:
        value = codec.parse(codec.read_bytes(path))
        value["may_have_published" if action == "flip_may" else "publication_outcome"] = False if action == "flip_may" else "not_published"
        path.write_bytes(codec.canonical(value))
    with pytest.raises(ValueError, match="failure binding"):
        journal.reopen(closed.root, closed.fixture, "on_time", "late", "full_temporal", binding)


@pytest.mark.parametrize("phase", ["before_rename", "after_rename"])
def test_terminal_failure_does_not_create_an_unaccepted_arrival(tmp_path, phase):
    session = start(tmp_path)
    def fail(name, path):
        if path.name.startswith("entry_") and name == phase: raise OSError("terminal publication")
    closed = journal.finish(session, hook=fail)
    result = replay(closed)
    assert result["state"] == session.state and result["unaccepted_attempt"] is None
    assert result["pending_terminal_checkpoint"] is not None if phase == "before_rename" else result["terminal_entry_present"]
    assert result["summary"]["tasks"] == ()


@pytest.mark.parametrize("phase", ["before_open", "after_write", "after_fsync", "after_pending_readback", "before_rename", "after_rename", "after_final_readback"])
def test_CAS_publication_failure_retains_orphans_without_adopting_hour(tmp_path, phase):
    session = start(tmp_path)
    item, actual = pending(session)
    def fail(name, path):
        if path.parent.name == "objects" and name == phase: raise OSError("CAS publication")
    closed = journal.commit_step(session, item, actual, hook=fail)
    result = replay(closed)
    assert result["state"] == session.state and result["publication_outcome"] == "not_published"
    assert result["state_certainty"] == "known" and result["unaccepted_attempt"] is None
    if phase != "before_open": assert result["pending_cas_objects"] or result["unreferenced_final_cas_objects"]


def test_read_view_rechecks_cached_object_bytes_at_bookend(tmp_path):
    store = store_at(tmp_path)
    identity = store.put("trusted")
    view = codec.EvidenceReadView(store)
    assert view.get(identity) == "trusted"
    path = store.objects/(identity+".json")
    path.write_bytes(codec.read_bytes(path).replace(b"trusted", b"changed"))
    assert view.get(identity) == "trusted"
    with pytest.raises(ValueError, match="changed during decode"): view.bookend()


def test_changed_fixture_with_same_source_identity_is_rejected_by_writer(tmp_path):
    session = start(tmp_path)
    forged = replace(session, fixture=replace(session.fixture, observation_end=6))
    with pytest.raises(ValueError, match="session fixture"): pending(forged)


def test_watchdog_scan_tolerates_pending_rename(tmp_path, monkeypatch):
    from experiments import staged_rts24_journal_launcher_v1 as launcher
    from pathlib import Path
    pending = tmp_path/"item.pending"
    pending.write_bytes(b"abc")
    original = Path.stat
    def vanished(path, *args, **kwargs):
        if path == pending: raise FileNotFoundError("renamed by writer")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", vanished)
    assert launcher.scan_output(tmp_path) == (0, 0)


def test_watchdog_exception_kills_owned_process_waits_and_saves_terminal(tmp_path, monkeypatch):
    from experiments import staged_rts24_journal_launcher_v1 as launcher
    class FakeProcess:
        pid, killed, waited = 123, False, False
        def poll(self): return -9 if self.killed else None
        def kill(self): self.killed = True
        def wait(self, timeout):
            assert self.killed
            self.waited = True
            return -9
    process = FakeProcess()
    monkeypatch.setattr(launcher, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(launcher.psutil, "Process", lambda *a: (_ for _ in ()).throw(OSError("resource observation failed")))
    monkeypatch.setattr(launcher, "kill_tree", lambda p: p.kill())
    assert launcher.main() == 1 and process.killed and process.waited
    import json
    report = json.loads((launcher.OUTPUT/"launcher.json").read_text())
    assert report["stop_reason"] == "launcher_exception" and report["child_running_after_cleanup"] is False


@pytest.mark.parametrize("limit", ["storage", "wall"])
def test_watchdog_checks_final_limits_even_when_child_exits_between_samples(tmp_path, monkeypatch, limit):
    from experiments import staged_rts24_journal_launcher_v1 as launcher
    class FinishedProcess:
        pid = 123
        def poll(self): return 0
        def wait(self, timeout): return 0
    monkeypatch.setattr(launcher, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: FinishedProcess())
    if limit == "storage": monkeypatch.setattr(launcher, "scan_output", lambda *a: (launcher.LIMITS["output_bytes"]+1, 2))
    else: monkeypatch.setattr(launcher, "LIMITS", {**launcher.LIMITS, "wall_seconds": -1})
    assert launcher.main() == 1
    import json
    report = json.loads((launcher.OUTPUT/"launcher.json").read_text())
    assert report["exit_code"] == 0 and report["stop_reason"] == "terminal_"+limit+"_limit"


def test_saved_process_snapshot_omits_private_arguments(monkeypatch):
    from experiments import staged_rts24_journal_diagnostic_v1 as diagnostic
    from types import SimpleNamespace
    import psutil
    import json
    sample = SimpleNamespace(info=dict(pid=7, name="python.exe", cmdline=[str(diagnostic.ROOT/"script.py"), "--token", "pretend-token-only"]))
    monkeypatch.setattr(psutil, "process_iter", lambda *a: [sample])
    snapshot = diagnostic.process_snapshot()
    assert len(snapshot) == 1 and snapshot[0]["mentions_repository"] is True
    assert set(snapshot[0]) == {"pid", "name", "argv_sha256", "mentions_repository"}
    assert "pretend-token-only" not in json.dumps(snapshot) and "--token" not in json.dumps(snapshot)
