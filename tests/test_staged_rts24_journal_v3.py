"""Same-append snapshot/scan optimization, never a public numerical result."""
from copy import deepcopy
from dataclasses import replace

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
from src import staged_rts24_journal_v2 as old, staged_rts24_journal_v3 as journal
from src import staged_rts24_evidence_store_v1 as codec

REAL_IDENTITY = journal.runtime_identity


@pytest.fixture(autouse=True)
def no_solver_fixed_identity(monkeypatch):
    import pyomo.environ as pyo
    import highspy
    def denied(*a, **kw): pytest.fail("ordinary batch journal requested numerical factory")
    monkeypatch.setattr(pyo, "SolverFactory", denied)
    monkeypatch.setattr(highspy, "Highs", denied)
    monkeypatch.setattr(old, "runtime_identity", lambda: {"ordinary_test": "fixed"})
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test": "fixed"})


def start(path, module=journal, method="full_temporal"):
    return module.create_session(path, analytic_fixture(late=True), "on_time", "late", method)


def pending(session, module=journal):
    item = module.begin_step(session, analytic_hour(session.fixture, session.state))
    return item, analytic_actual(item.prepared, item.proposal)


def replay(session, module=journal):
    return module.reopen(session.root, session.fixture, "on_time", "late", session.state.method, module.trusted_binding(session))


@pytest.mark.parametrize("method", journal.c.METHODS)
def test_scientific_state_wire_and_replay_equal_v2(tmp_path, method):
    sessions = [start(tmp_path/name, module, method) for name, module in (("old", old), ("new", journal))]
    for _ in range(2):
        for i, module in enumerate((old, journal)):
            item, actual = pending(sessions[i], module)
            sessions[i] = module.commit_step(sessions[i], item, actual)
            assert not sessions[i].closed
        assert sessions[0].state == sessions[1].state
        assert sessions[0].cas_inventory == sessions[1].cas_inventory
        assert all((sessions[0].root/"objects"/n).read_bytes() == (sessions[1].root/"objects"/n).read_bytes()
                   for n in sessions[0].cas_inventory)
    results = []
    for i, module in enumerate((old, journal)):
        sessions[i] = module.finish(sessions[i])
        results.append(replay(sessions[i], module))
    assert sessions[0].cas_inventory == sessions[1].cas_inventory
    assert all((sessions[0].root/"objects"/n).read_bytes() == (sessions[1].root/"objects"/n).read_bytes()
               for n in sessions[0].cas_inventory)
    for name in ("state", "state_sha", "summary", "independent_audit", "scientific_outcome", "publication_outcome",
                 "state_certainty", "terminal_entry_present", "unaccepted_attempt", "pending_cas_objects"):
        assert results[0][name] == results[1][name]


@pytest.mark.parametrize("operation,expected", [("hour", (6, 2)), ("finish", (4, 2))])
def test_full_operation_inventory_and_pack_counts(tmp_path, monkeypatch, operation, expected):
    session = start(tmp_path/"new")
    counts = dict(inventory=0, pack=0)
    inventory, pack = codec.EvidenceStore.inventory, codec.pack
    def observed(store): counts["inventory"] += 1; return inventory(store)
    def encoded(value): counts["pack"] += 1; return pack(value)
    monkeypatch.setattr(codec.EvidenceStore, "inventory", observed)
    monkeypatch.setattr(codec, "pack", encoded)
    if operation == "hour":
        item, actual = pending(session)
        session = journal.commit_step(session, item, actual)
    else: session = journal.finish(session)
    assert counts == dict(inventory=expected[0], pack=expected[1])
    assert session.scientific_outcome != "persistence_failure"


@pytest.mark.parametrize("phase", ["before_open", "after_write", "after_fsync", "after_pending_readback", "before_rename", "after_rename", "after_final_readback"])
@pytest.mark.parametrize("target", ["cas", "entry"])
def test_publish_failures_keep_prefix_and_publication_certainty(tmp_path, phase, target):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    def fault(stage, path):
        wanted = path.parent.name == "objects" if target == "cas" else path.name == "entry_000001.json"
        if wanted and stage == phase: raise OSError("ordinary injected publication failure")
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.state == session.state and closed.ordinal == 0
    unknown = target == "entry" and phase in ("after_rename", "after_final_readback")
    assert closed.publication_outcome == ("unknown" if unknown else "not_published")
    result = replay(closed)
    assert len(result["state"].records) == (1 if unknown else 0)


@pytest.mark.parametrize("when", ["cas", "entry"])
@pytest.mark.parametrize("victim", ["fixture", "genesis"])
def test_deletion_during_publish_never_adopts_missing_closure(tmp_path, when, victim):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    genesis = codec.parse(codec.read_bytes(session.root/"genesis.json"))
    path = session.root/("objects/"+genesis["fixture_ref"]+".json" if victim == "fixture" else "genesis.json")
    removed = []
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000001.json"
        if wanted and stage == "after_rename" and not removed: path.unlink(); removed.append(True)
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert removed and closed.closed and closed.state == session.state and not path.exists()
    assert closed.publication_outcome == ("unknown" if when == "entry" else "not_published")
    with pytest.raises((ValueError, FileNotFoundError)): replay(closed)


@pytest.mark.parametrize("when", ["cas", "entry"])
def test_hook_mutation_of_input_has_frozen_failure_context(tmp_path, monkeypatch, when):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    accepted = journal.policy.accept_hour
    candidates = []
    def candidate(*a, **kw):
        value = accepted(*a, **kw); candidates.append(value); return value
    monkeypatch.setattr(journal.policy, "accept_hour", candidate)
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000001.json"
        if wanted and stage == "after_rename": candidates[0].records[-1]["mutated_test_field"] = True
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.ordinal == 0 and closed.state == session.state
    assert closed.publication_outcome == ("not_published" if when == "cas" else "unknown")
    result = replay(closed)
    assert len(result["state"].records) == (0 if when == "cas" else 1)
    if when == "entry": assert "mutated_test_field" not in result["state"].records[-1]


@pytest.mark.parametrize("when", ["cas", "entry"])
def test_mutating_previous_row_preserves_frozen_prefix_and_failure_witness(tmp_path, when):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    session = journal.commit_step(session, item, actual)
    prefix = deepcopy(session.state)
    item, actual = pending(session)
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000002.json"
        if wanted and stage == "after_rename": session.state.records[0]["mutated_old_row"] = True
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.ordinal == 1 and closed.state == prefix
    assert closed.failure["before_state_sha"] == journal.c.digest(prefix)
    result = replay(closed)
    assert len(result["state"].records) == (1 if when == "cas" else 2)
    assert "mutated_old_row" not in result["state"].records[0]


@pytest.mark.parametrize("field", ["head_sha", "ordinal", "root", "cas_inventory"])
@pytest.mark.parametrize("when", ["cas", "entry"])
def test_rebinding_session_fields_cannot_change_entry_or_failure_context(tmp_path, field, when):
    session = start(tmp_path/"new")
    initial = deepcopy(session)
    item, actual = pending(session)
    changed = []
    replacement = dict(head_sha="0"*64, ordinal=99, root=tmp_path/"other", cas_inventory={})
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000001.json"
        if wanted and stage == "after_rename" and not changed:
            object.__setattr__(session, field, replacement[field]); changed.append(True)
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert changed and closed.closed and closed.ordinal == 0 and closed.head_sha == initial.head_sha
    assert closed.root == initial.root and closed.cas_inventory == initial.cas_inventory and closed.state == initial.state
    result = replay(closed)
    assert len(result["state"].records) == (0 if when == "cas" else 1)


@pytest.mark.parametrize("phase", ["prepare", "external_wait"])
def test_no_cached_inventory_survives_prepare_or_external_wait(tmp_path, monkeypatch, phase):
    session = start(tmp_path/"new")
    genesis = codec.parse(codec.read_bytes(session.root/"genesis.json"))
    victim = session.root/"objects"/(genesis["fixture_ref"]+".json")
    if phase == "prepare":
        prepare = journal.policy.prepare_hour
        def fault(*a, **kw):
            result = prepare(*a, **kw); victim.unlink(); return result
        monkeypatch.setattr(journal.policy, "prepare_hour", fault)
        with pytest.raises(journal.SessionClosed) as error: pending(session)
        closed = error.value.session
    else:
        item, actual = pending(session)
        victim.unlink()
        # A forged in-memory map cannot hide the missing disk head closure.
        forged = replace(session, cas_inventory={k: v for k, v in session.cas_inventory.items() if k != victim.name})
        closed = journal.commit_step(forged, item, actual)
    assert closed.closed and closed.state == session.state and not victim.exists()
    with pytest.raises((ValueError, FileNotFoundError)): replay(closed)


@pytest.mark.parametrize("victim", ["entry_000001.json", "extra", "directory"])
@pytest.mark.parametrize("when", ["cas", "entry"])
def test_retained_root_and_directory_changes_prevent_adoption(tmp_path, victim, when):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    session = journal.commit_step(session, item, actual)
    item, actual = pending(session)
    changed = []
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000002.json"
        if wanted and stage == "after_rename" and not changed:
            if victim == "extra": (session.root/"unexpected.json").write_bytes(b"{}")
            elif victim == "directory":
                (session.root/"objects").rename(tmp_path/"retained_objects")
                (session.root/"objects").mkdir()
            else: (session.root/victim).unlink()
            changed.append(True)
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert changed and closed.closed and closed.ordinal == 1 and closed.state == session.state
    with pytest.raises((ValueError, FileNotFoundError)): replay(closed)


@pytest.mark.parametrize("when", ["cas", "entry"])
def test_runtime_drift_during_batch_or_entry_is_not_adopted(tmp_path, monkeypatch, when):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    drift = []
    def fault(stage, target):
        wanted = target.parent.name == "objects" if when == "cas" else target.name == "entry_000001.json"
        if wanted and stage == "after_rename": drift.append(True)
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test": "changed" if drift else "fixed"})
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert drift and closed.closed and closed.state == session.state
    with pytest.raises(ValueError, match="runtime"): replay(closed)
    # Restored dependencies let the independent reader decide the saved tail.
    drift.clear()
    assert len(replay(closed)["state"].records) == (0 if when == "cas" else 1)


@pytest.mark.parametrize("stage", ["reference", "actual", "audit"])
def test_unresolved_attempt_remains_unapplied_and_matches_v2(tmp_path, monkeypatch, stage):
    sessions = [start(tmp_path/name, module) for name, module in (("old", old), ("new", journal))]
    results = []
    for session, module in zip(sessions, (old, journal)):
        if stage == "reference":
            with pytest.raises(module.SessionClosed) as error: module.begin_step(session, None)
            closed = error.value.session
        else:
            item, actual = pending(session, module)
            original = module.audit_execution
            def candidate_only(fixture, state):
                if state.records: raise ValueError("ordinary injected audit failure")
                return original(fixture, state)
            with monkeypatch.context() as scoped:
                if stage == "audit": scoped.setattr(module, "audit_execution", candidate_only)
                closed = module.commit_step(session, item, None if stage == "actual" else actual)
                results.append(replay(closed, module))
        if stage == "reference": results.append(replay(closed, module))
        assert closed.closed and closed.state == session.state
    for name in ("state", "scientific_outcome", "unaccepted_attempt", "terminal_entry_present"):
        assert results[0][name] == results[1][name]
    assert results[1]["scientific_outcome"] == stage+"_unresolved"


@pytest.mark.parametrize("phase", ["before_rename", "after_rename"])
def test_terminal_pending_and_unknown_use_read_only_replay(tmp_path, monkeypatch, phase):
    session = start(tmp_path/"new")
    def fault(stage, target):
        if target.name == "entry_000001.json" and stage == phase: raise OSError("ordinary terminal failure")
    closed = journal.finish(session, hook=fault)
    def denied(*a, **kw): pytest.fail("read-only replay attempted generation or publication")
    monkeypatch.setattr(journal.c, "hour_requests", denied)
    monkeypatch.setattr(journal.c, "build_point_model", denied)
    monkeypatch.setattr(codec.EvidenceStore, "put", denied)
    monkeypatch.setattr(codec, "publish", denied)
    monkeypatch.setattr(journal, "publish", denied)
    result = replay(closed)
    assert result["state"] == session.state and result["unaccepted_attempt"] is None
    assert result["pending_terminal_checkpoint"] is not None if phase == "before_rename" else result["terminal_entry_present"]


def test_known_rejection_keeps_ledger_and_does_not_grant_resume(tmp_path):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    bad = replace(actual, point=replace(actual.point, flows_mw=((0, 0.), (1, 0.), (2, 0.))))
    rejected = journal.commit_step(session, item, bad)
    assert rejected.state.stopped and rejected.state.ledger == session.state.ledger
    closed = journal.finish(rejected)
    result = replay(closed)
    assert result["scientific_outcome"] == "known_rejection" and result["resume_permitted"] is False


@pytest.mark.parametrize("field", ["known_cas_keys", "known_head_sha", "failure"])
def test_fresh_reader_rejects_altered_external_binding_or_failure(tmp_path, field):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    def fault(stage, target):
        if target.name == "entry_000001.json" and stage == "after_rename": raise OSError("ordinary unknown")
    closed = journal.commit_step(session, item, actual, hook=fault)
    binding = journal.trusted_binding(closed)
    if field == "known_cas_keys": binding[field] = binding[field][1:]
    elif field == "known_head_sha": binding[field] = "0"*64
    else:
        path = closed.root/"failure.json"
        path.write_bytes(codec.read_bytes(path)+b" ")
    with pytest.raises(ValueError):
        journal.reopen(closed.root, closed.fixture, "on_time", "late", closed.state.method, binding)


def test_reader_bookend_detects_mutation_after_object_was_read(tmp_path, monkeypatch):
    session = start(tmp_path/"new")
    genesis = codec.parse(codec.read_bytes(session.root/"genesis.json"))
    victim = session.root/"objects"/(genesis["fixture_ref"]+".json")
    original, changed = codec.EvidenceReadView.get, []
    def get(reader, key):
        result = original(reader, key)
        if key == genesis["fixture_ref"] and not changed:
            victim.write_bytes(victim.read_bytes()+b" "); changed.append(True)
        return result
    monkeypatch.setattr(codec.EvidenceReadView, "get", get)
    with pytest.raises(ValueError): replay(session)
    assert changed


def test_failed_failure_witness_is_preserved_as_unreadable_completion(tmp_path, monkeypatch):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    original = journal.publish
    def publish(path, raw, hook=None):
        if path.name == "failure.json": raise OSError("ordinary unavailable failure witness")
        return original(path, raw, hook)
    monkeypatch.setattr(journal, "publish", publish)
    def fault(stage, target):
        if target.name == "entry_000001.json" and stage == "before_rename": raise OSError("ordinary pending")
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.state == session.state and closed.failure is not None
    assert not (closed.root/"failure.json").exists() and (closed.root/"entry_000001.json.pending").exists()
    with pytest.raises(ValueError, match="failure binding"): replay(closed)


def test_precreated_entry_remains_foreign_and_is_not_adopted(tmp_path):
    session = start(tmp_path/"new")
    item, actual = pending(session)
    target = session.root/"entry_000001.json"
    def fault(stage, path):
        if path.parent.name == "objects" and stage == "after_rename" and not target.exists(): target.write_bytes(b"{}")
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.ordinal == 0 and closed.state == session.state and target.read_bytes() == b"{}"
    with pytest.raises(ValueError): replay(closed)


def test_actual_runtime_pins_bind_both_successor_sources():
    pins = REAL_IDENTITY()
    assert len(pins["sources"]) == 29 and len(pins["external"]) == 10
    for name in ("src/staged_rts24_journal_v3.py", "src/staged_rts24_append_store_v1.py"):
        assert pins["sources"][name] == codec.sha(codec.read_bytes(journal.REPO/name))
