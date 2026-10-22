"""Retained CAS closure is checked before adoption and across fresh replay."""
from dataclasses import replace
import json

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
from src import staged_rts24_journal_v2 as journal
from src.staged_rts24_evidence_store_v1 import EvidenceStore, parse, read_bytes, canonical


@pytest.fixture(autouse=True)
def no_solver_and_fixed_test_environment(monkeypatch):
    import pyomo.environ as pyo
    def denied(*args, **kwargs): pytest.fail("ordinary closure test requested solver")
    monkeypatch.setattr(pyo, "SolverFactory", denied)
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test": "fixed"})


def start(tmp_path, method="full_temporal"):
    return journal.create_session(tmp_path/"session", analytic_fixture(late=True), "on_time", "late", method)


def pending(session):
    item = journal.begin_step(session, analytic_hour(session.fixture, session.state))
    return item, analytic_actual(item.prepared, item.proposal)


def replay(session, binding=None):
    return journal.reopen(session.root, session.fixture, "on_time", "late", session.state.method,
                          journal.trusted_binding(session) if binding is None else binding)


def fixture_path(session):
    genesis = parse(read_bytes(session.root/"genesis.json"))
    return session.root/"objects"/(genesis["fixture_ref"]+".json")


@pytest.mark.parametrize("method", journal.c.METHODS)
def test_two_hour_scientific_state_unchanged_and_fresh_keyset_matches(tmp_path, method):
    session = start(tmp_path, method)
    for _ in range(2):
        item, actual = pending(session)
        prior = session
        session = journal.commit_step(session, item, actual)
        assert not session.closed and set(prior.cas_inventory) <= set(session.cas_inventory)
        assert EvidenceStore(session.root).inventory() == session.cas_inventory
    session = journal.finish(session)
    result = replay(session)
    assert result["state"] == session.state and result["scientific_outcome"] == "missing_input"
    assert result["summary"]["primary_right_censored"] and result["resume_permitted"] is False


def test_deleted_genesis_fixture_closes_before_planning(tmp_path):
    session = start(tmp_path)
    evidence = analytic_hour(session.fixture, session.state)
    fixture_path(session).unlink()
    with pytest.raises(journal.SessionClosed) as error: journal.begin_step(session, evidence)
    closed = error.value.session
    assert closed.closed and closed.state == session.state and closed.ordinal == 0
    with pytest.raises(ValueError, match="retained CAS missing"): replay(closed)


@pytest.mark.parametrize("field", ["payload_ref", "state_ref"])
def test_deleted_prior_hour_payload_or_state_cannot_be_adopted_over(tmp_path, field):
    session = start(tmp_path)
    item, actual = pending(session)
    session = journal.commit_step(session, item, actual)
    next_item, next_actual = pending(session)
    entry = parse(read_bytes(session.root/"entry_000001.json"))
    (session.root/"objects"/(entry[field]+".json")).unlink()
    closed = journal.commit_step(session, next_item, next_actual)
    assert closed.closed and closed.state == session.state and closed.ordinal == 1
    with pytest.raises(ValueError, match="retained CAS missing"): replay(closed)


@pytest.mark.parametrize("phase", ["cas", "entry"])
def test_old_object_deleted_during_append_never_adopts_candidate(tmp_path, phase):
    session = start(tmp_path)
    item, actual = pending(session)
    victim, deleted = fixture_path(session), False
    def fault(stage, path):
        nonlocal deleted
        wanted = path.parent.name == "objects" if phase == "cas" else path.name.startswith("entry_")
        if wanted and stage == "after_rename" and not deleted:
            victim.unlink()
            deleted = True
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert deleted and closed.closed and closed.state == session.state and closed.ordinal == 0
    assert closed.publication_outcome == ("not_published" if phase == "cas" else "unknown")
    with pytest.raises(ValueError, match="retained CAS missing"): replay(closed)


def test_forged_session_inventory_cannot_hide_a_deleted_object(tmp_path):
    session = start(tmp_path)
    victim = fixture_path(session)
    victim.unlink()
    forged = replace(session, cas_inventory={k: v for k, v in session.cas_inventory.items() if k != victim.name})
    with pytest.raises(journal.SessionClosed) as error: pending(forged)
    assert error.value.session.closed and error.value.session.state == session.state


def test_trusted_keyset_and_unknown_publication_bind_complete_closure(tmp_path):
    session = start(tmp_path)
    item, actual = pending(session)
    def fault(stage, path):
        if path.name.startswith("entry_") and stage == "after_rename": raise OSError("readback unknown")
    closed = journal.commit_step(session, item, actual, hook=fault)
    result = replay(closed)
    assert len(result["state"].records) == 1 and result["publication_outcome"] == "committed"
    binding = journal.trusted_binding(closed)
    binding["known_cas_keys"] = binding["known_cas_keys"][1:]
    with pytest.raises(ValueError, match="initial CAS binding"): replay(closed, binding)


def test_object_deleted_during_prepare_closes_without_returning_a_plan(tmp_path, monkeypatch):
    session = start(tmp_path)
    evidence = analytic_hour(session.fixture, session.state)
    original = journal.policy.prepare_hour
    def removed(*args, **kwargs):
        result = original(*args, **kwargs)
        fixture_path(session).unlink()
        return result
    monkeypatch.setattr(journal.policy, "prepare_hour", removed)
    with pytest.raises(journal.SessionClosed) as error: journal.begin_step(session, evidence)
    assert error.value.session.closed and error.value.session.state == session.state


@pytest.mark.parametrize("victim", ["genesis.json", "entry_000001.json"])
@pytest.mark.parametrize("phase", ["cas", "entry"])
def test_prior_root_deleted_during_append_never_adopts(tmp_path, victim, phase):
    session = start(tmp_path)
    item, actual = pending(session)
    session = journal.commit_step(session, item, actual)
    next_item, next_actual = pending(session)
    removed = False
    def fault(stage, path):
        nonlocal removed
        wanted = path.parent.name == "objects" if phase == "cas" else path.name == "entry_000002.json"
        if wanted and stage == "after_rename" and not removed:
            (session.root/victim).unlink()
            removed = True
    closed = journal.commit_step(session, next_item, next_actual, hook=fault)
    assert removed and closed.closed and closed.state == session.state and closed.ordinal == 1
    assert closed.publication_outcome == ("not_published" if phase == "cas" else "unknown")
    with pytest.raises((ValueError, FileNotFoundError)): replay(closed)


def test_extra_root_file_during_append_is_not_adopted(tmp_path):
    session = start(tmp_path)
    item, actual = pending(session)
    def fault(stage, path):
        if path.name == "entry_000001.json" and stage == "after_rename":
            (session.root/"unexpected.json").write_bytes(b'{}')
    closed = journal.commit_step(session, item, actual, hook=fault)
    assert closed.closed and closed.state == session.state
    with pytest.raises(ValueError, match="unknown journal filename"): replay(closed)


def test_forged_root_inventory_cannot_hide_a_changed_previous_entry(tmp_path):
    session = start(tmp_path)
    for _ in range(2):
        item, actual = pending(session)
        session = journal.commit_step(session, item, actual)
    path = session.root/"entry_000001.json"
    entry = parse(read_bytes(path))
    entry["before_state_sha"] = "0"*64
    raw = canonical(entry)
    path.write_bytes(raw)
    forged = replace(session, root_inventory={**session.root_inventory, path.name: journal.sha(raw)})
    with pytest.raises(journal.SessionClosed) as error: pending(forged)
    assert error.value.session.closed and error.value.session.state == session.state


@pytest.mark.parametrize("operation", ["genesis", "append"])
def test_runtime_drift_in_final_inventory_bookend_never_adopts(tmp_path, monkeypatch, operation):
    original = EvidenceStore.inventory
    drift = False
    def observed(store):
        nonlocal drift
        result = original(store)
        trigger = "genesis.json" if operation == "genesis" else "entry_000001.json"
        if (store.root/trigger).exists(): drift = True
        return result
    session = start(tmp_path) if operation == "append" else None
    item, actual = pending(session) if session else (None, None)
    monkeypatch.setattr(EvidenceStore, "inventory", observed)
    monkeypatch.setattr(journal, "runtime_identity", lambda: {"ordinary_test": "changed" if drift else "fixed"})
    if operation == "genesis":
        with pytest.raises(ValueError, match="dependency changed during genesis"): start(tmp_path)
    else:
        closed = journal.commit_step(session, item, actual)
        assert drift and closed.closed and closed.state == session.state and closed.ordinal == 0


@pytest.mark.parametrize("stage", ["reference", "actual"])
def test_v2_unresolved_attempt_binds_complete_objects_and_remains_unapplied(tmp_path, stage):
    session = start(tmp_path)
    if stage == "reference":
        with pytest.raises(journal.SessionClosed) as error: journal.begin_step(session, None)
        closed = error.value.session
    else:
        item, _ = pending(session)
        closed = journal.commit_step(session, item, None)
    assert closed.closed and closed.state == session.state
    result = replay(closed)
    assert result["scientific_outcome"] == stage+"_unresolved"
    assert result["terminal_entry_present"] is False and result["unaccepted_attempt"]["adopted"] is False


@pytest.mark.parametrize("phase", ["before_rename", "after_rename"])
def test_v2_terminal_pending_and_unknown_keep_state_without_arrival(tmp_path, phase):
    session = start(tmp_path)
    def fault(stage, path):
        if path.name.startswith("entry_") and stage == phase: raise OSError("terminal test")
    closed = journal.finish(session, hook=fault)
    result = replay(closed)
    assert closed.closed and result["state"] == session.state and result["unaccepted_attempt"] is None
    assert result["pending_terminal_checkpoint"] is not None if phase == "before_rename" else result["terminal_entry_present"]


def test_v2_known_actual_rejection_closes_with_unchanged_ledger(tmp_path):
    session = start(tmp_path)
    item, actual = pending(session)
    bad = replace(actual, point=replace(actual.point, flows_mw=((0, 0.), (1, 0.), (2, 0.))))
    rejected = journal.commit_step(session, item, bad)
    assert rejected.state.stopped and rejected.state.ledger == session.state.ledger
    closed = journal.finish(rejected)
    result = replay(closed)
    assert result["scientific_outcome"] == "known_rejection" and result["state"] == rejected.state
