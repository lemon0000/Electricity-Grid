"""Private append batching in pytest temp; old codec wire stays authoritative."""
from copy import deepcopy
from fractions import Fraction as Q
import math

import pytest

from src import staged_rts24_append_store_v1 as batch, staged_rts24_evidence_store_v1 as codec
from experiments.staged_rts24_causal_examples_v1 import analytic_fixture


def store_at(root):
    (root/"objects").mkdir()
    return codec.EvidenceStore(root)


def test_shared_closure_published_once_with_unchanged_wire_and_root_ids(tmp_path, monkeypatch):
    store = store_at(tmp_path)
    fixture = analytic_fixture()
    left = dict(fixture=fixture, numbers=(Q(1, 3), -0., 5e-324))
    right = dict(again=deepcopy(fixture), same=fixture)
    wanted = [codec.pack(v) for v in (left, right)]
    calls = []
    original = codec.publish
    def publish(path, raw, hook=None): calls.append(path.name); return original(path, raw, hook)
    monkeypatch.setattr(codec, "publish", publish)
    roots, expected = batch.publish_roots(store, (left, right), store.inventory())
    assert roots == tuple(w[0] for w in wanted) and expected == store.inventory()
    assert len(calls) == len(set(calls)) == len(set(wanted[0][1]) | set(wanted[1][1]))
    assert store.get(roots[0]) == left and store.get(roots[1]) == right
    assert math.copysign(1., store.get(roots[0])["numbers"][1]) == -1
    for _, blobs in wanted:
        assert all(codec.read_bytes(store.objects/(key+".json")) == data for key, data in blobs.items())


@pytest.mark.parametrize("limits", [dict(MAX_OBJECTS=1), dict(MAX_TOTAL=110)])
def test_separately_valid_roots_exceed_combined_budget_before_any_write(tmp_path, monkeypatch, limits):
    store = store_at(tmp_path)
    values = ({"a": 1}, {"b": 2})
    for name, value in limits.items(): monkeypatch.setattr(codec, name, value)
    assert all(codec.pack(v) for v in values)
    with pytest.raises(ValueError, match="batch CAS publication budget"):
        batch.publish_roots(store, values, {})
    assert list(store.objects.iterdir()) == []


@pytest.mark.parametrize("kind", ["key", "root", "conflict"])
def test_invalid_packed_closure_is_rejected_before_write(tmp_path, monkeypatch, kind):
    store = store_at(tmp_path)
    data = codec.canonical(dict(schema=codec.SCHEMA, kind="dict", payload=["dict", []]))
    key = codec.sha(data)
    n = [0]
    def invalid(value):
        n[0] += 1
        if kind == "key": return "0"*64, {"0"*64: data}
        if kind == "root": return "0"*64, {key: data}
        if n[0] == 1: return key, {key: data}
        # Exercise conflict even under a deliberately collided fake hash.
        monkeypatch.setattr(codec, "sha", lambda value: key)
        return key, {key: data+b" "}
    monkeypatch.setattr(codec, "pack", invalid)
    with pytest.raises(ValueError): batch.publish_roots(store, ({}, {}), {})
    assert list(store.objects.iterdir()) == []


def test_retained_key_disappearing_is_not_republished(tmp_path):
    store = store_at(tmp_path)
    value = dict(v=1)
    root = store.put(value)
    before = store.inventory()
    (store.objects/(root+".json")).unlink()
    with pytest.raises(FileNotFoundError): batch.publish_roots(store, (value,), before)
    assert not (store.objects/(root+".json")).exists()


def test_unexpected_precreated_new_key_does_not_become_existing_success(tmp_path):
    store = store_at(tmp_path)
    value = dict(v=1)
    root, blobs = codec.pack(value)
    codec.publish(store.objects/(root+".json"), blobs[root])
    with pytest.raises(ValueError, match="immutable target"):
        batch.publish_roots(store, (value,), {})


def test_overlapping_retained_key_deleted_after_budget_is_not_healed(tmp_path):
    store = store_at(tmp_path)
    retained = dict(retained=True)
    identity = store.put(retained)
    before = store.inventory()
    victim = store.objects/(identity+".json")
    removed = []
    def fault(stage, path):
        if stage == "after_rename" and not removed:
            victim.unlink(); removed.append(True)
    store.hook = fault
    with pytest.raises(FileNotFoundError):
        batch.publish_roots(store, (dict(new=True), retained), before)
    assert removed and not victim.exists()


def test_new_target_racing_after_pending_write_is_never_overwritten(tmp_path):
    store = store_at(tmp_path)
    foreign = b"foreign writer's retained bytes"
    targets = []
    def fault(stage, path):
        if stage == "before_rename":
            path.write_bytes(foreign); targets.append(path)
    store.hook = fault
    with pytest.raises(codec.PublicationError): batch.publish_roots(store, (dict(new=True),), {})
    assert targets[0].read_bytes() == foreign
    assert targets[0].with_name(targets[0].name+".pending").exists()


@pytest.mark.parametrize("left,right", [(0, 0.), (True, 1), (-0., 0.), ((1,), [1]), ({"a": 1}, {"a": 1.})])
def test_typed_comparison_rejects_python_equal_wire_differences(left, right):
    assert not batch.typed_equal(left, right)


def test_snapshot_comparison_preserves_fraction_dataclasses_and_shared_values():
    fixture = analytic_fixture()
    value = (dict(first=fixture, again=fixture), Q(2, 3), 5e-324, -0.)
    assert batch.typed_equal(value, deepcopy(value))
