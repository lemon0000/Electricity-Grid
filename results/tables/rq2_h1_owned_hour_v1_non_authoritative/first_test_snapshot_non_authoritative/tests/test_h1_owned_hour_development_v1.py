import json
import shutil

import pytest

from experiments import h1_owned_hour_development_v1 as api
from tests.test_h1_stage_completion_development_v1 import SyntheticDirect
from tests.test_h1_native_raw_science_development_v1 import LIMITS
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec


def install(monkeypatch, root, saved, *, fail_stage=None):
    solvers = []
    monkeypatch.setattr(api.stage.capture, 'GurobiDirect', SyntheticDirect)
    def factory(specification):
        index = len(solvers)
        solver = SyntheticDirect(None, None, None, root/'stages'/f'{index:03d}',
                                 'close' if index == fail_stage else None)
        solver.report = json.loads(saved[1][index])
        solvers.append(solver)
        return solver, api.stage.capture.old.audit.solver_options(specification)
    monkeypatch.setattr(api.stage.capture.old.provenance.adapter, 'create_solver', factory)
    return solvers


@pytest.fixture(scope='module')
def completed(tmp_path_factory, saved):
    root = tmp_path_factory.mktemp('owned_hour')/'hour'
    with pytest.MonkeyPatch.context() as mp:
        no_solver.__wrapped__(mp)
        solvers = install(mp, root, saved)
        owner = api.OwnedHour(root, packet(), spec(), LIMITS)
        result = owner.run()
        assert [s.apply_calls for s in solvers] == [1, 1, 1]
        assert [s.close_calls for s in solvers] == [1, 1, 1]
        return owner, result


def replay(root, receipt, context=None):
    return api.inspect(root, *(context or (packet(), spec(), LIMITS)),
        expected_terminal_sha=receipt.terminal_sha256, expected_implementation=receipt.implementation)


def test_complete_three_stage_hour_matches_old_science_values(completed, saved):
    owner, receipt = completed
    assert type(receipt) is api.HourCompletion and owner.complete and not owner.poisoned
    result = replay(owner.root, receipt)
    assert result['canonical_locks'] == (20., 1., 20.)
    assert not result['owned_run_return_observed'] and not result['whole_job_quiescence_checked']
    assert not any(dict(receipt.authority_flags).values())
    old = api.prior.replay_stream(packet(), spec(), LIMITS, saved[1],
        expected_key=api.prior.request_key(packet(), spec(), LIMITS))
    payload = json.loads(receipt.projection_payload)
    assert payload['value'] == json.loads(old.projection_payload)
    assert payload['before_identity'] == old.before_identity
    assert len([p for p in owner.root.rglob('*') if p.is_file()]) == 18*3+3
    with pytest.raises(TypeError): api.HourCompletion(owner.root, 'a'*64, 'b'*64, 'c'*64, b'{}')
    with pytest.raises(ValueError): owner.run()


@pytest.mark.parametrize('fault', ['stage', 'fresh', 'commit_before', 'commit_after'])
def test_failed_stage_or_commit_stops_before_next_stage(tmp_path, saved, monkeypatch, fault):
    root = tmp_path/'hour'; solvers = install(monkeypatch, root, saved, fail_stage=0 if fault == 'stage' else None)
    owner = api.OwnedHour(root, packet(), spec(), LIMITS)
    write = api.io.write_metadata
    def fail(path, doc):
        if path == root/'commits/000.json':
            if fault == 'commit_after': write(path, doc)
            raise OSError('commit confirmation failed')
        return write(path, doc)
    if fault.startswith('commit'): monkeypatch.setattr(api.io, 'write_metadata', fail)
    if fault == 'fresh':
        original = api.stage.inspect
        calls = []
        def reject(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2: raise ValueError('hour fresh stage inspection failed')
            return original(*args, **kwargs)
        monkeypatch.setattr(api.stage, 'inspect', reject)
    with pytest.raises((OSError, ValueError, RuntimeError)): owner.run()
    assert owner.poisoned and not owner.complete and len(solvers) == 1
    assert not (root/'stages/001').exists()
    assert not (root/'projection.bin').exists() and not (root/'terminal.json').exists()
    assert (root/'commits/000.json').exists() == (fault == 'commit_after')
    with pytest.raises(ValueError): owner.run()
    assert len(solvers) == 1


@pytest.mark.parametrize('name', ['projection.bin', 'terminal.json'])
@pytest.mark.parametrize('after_write', [False, True])
def test_publication_failure_does_not_return_hour(tmp_path, saved, monkeypatch, name, after_write):
    root = tmp_path/'hour'; solvers = install(monkeypatch, root, saved)
    owner = api.OwnedHour(root, packet(), spec(), LIMITS)
    original = api.io.write_new
    def fail(path, raw):
        if path == root/name:
            if after_write: original(path, raw)
            raise OSError('hour publication confirmation failed')
        return original(path, raw)
    monkeypatch.setattr(api.io, 'write_new', fail)
    returned = []
    with pytest.raises(OSError): returned.append(owner.run())
    assert returned == [] and owner.poisoned and not owner.complete
    assert len(solvers) == 3 and len(list((root/'commits').iterdir())) == 3
    assert (root/name).exists() == after_write
    with pytest.raises(ValueError): owner.run()
    assert len(solvers) == 3


@pytest.mark.parametrize('fault', ['previous', 'prefix', 'pins', 'stage_request', 'foreign_child', 'missing', 'extra'])
def test_hour_commit_and_topology_corruption_rejected(tmp_path, completed, fault):
    original, receipt = completed
    # Science binds absolute native paths, so operate on the original test root
    # and restore exact bytes after each fault. No repository artifact is edited.
    root = original.root
    path = root/'commits/001.json'; before = path.read_bytes()
    try:
        if fault == 'missing': path.rename(root/'retained_commit.json')
        elif fault == 'extra': (root/'stages/extra').mkdir()
        else:
            doc = json.loads(before)
            if fault == 'previous': doc['previous_sha256'] = 'a'*64
            elif fault == 'prefix': doc['prefix_sha256'] = 'a'*64
            elif fault == 'pins': doc['science_terminal_sha256'] = json.loads((root/'commits/000.json').read_bytes())['science_terminal_sha256']
            elif fault == 'stage_request': doc['stage_request_sha256'] = 'a'*64
            else: doc['child'] = 'foreign'
            path.write_bytes(api.io.encode(doc))
        with pytest.raises(ValueError): replay(root, receipt)
    finally:
        if fault == 'missing': (root/'retained_commit.json').rename(path)
        elif fault == 'extra': (root/'stages/extra').rmdir()
        else: path.write_bytes(before)


@pytest.mark.parametrize('name', ['commits/000.json', 'stages/000/complete.json', 'projection.bin', 'terminal.json'])
def test_mid_replay_byte_drift_with_restored_mtime_rejects(completed, monkeypatch, name):
    import os
    owner, receipt = completed; path = owner.root/name; before = path.read_bytes()
    original = api._projection
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        stamp = path.stat()
        path.write_bytes(before.replace(b'false', b' true', 1))
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        return result
    monkeypatch.setattr(api, '_projection', mutate)
    try:
        with pytest.raises(ValueError): replay(owner.root, receipt)
    finally: path.write_bytes(before)


def test_hour_owner_reentry_and_context_gate(tmp_path):
    owner = api.OwnedHour(tmp_path/'hour', packet(), spec(), LIMITS)
    owner.guard.acquire()
    try:
        with pytest.raises(ValueError): owner.run()
        assert not owner.started and not owner.poisoned
    finally: owner.guard.release()
    owner.owner = (-1, -1)
    with pytest.raises(ValueError): owner.run()
    assert owner.poisoned


def test_pinned_rts_declares_full_232_stage_hour_without_running(tmp_path):
    from tests.test_h1_native_export_guard_development_v1 import saved_origin
    _, p, _ = saved_origin.__wrapped__()
    owner = api.OwnedHour(tmp_path/'hour', p, spec(), LIMITS)
    assert owner.count == 232 and not owner.started
    assert not list((owner.root/'stages').iterdir())


def test_dependency_drift_during_hour_replay_rejects(completed, monkeypatch):
    owner, receipt = completed
    original = api._projection
    def drift(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr(api, 'implementation_identity', lambda: 'f'*64)
        return result
    monkeypatch.setattr(api, '_projection', drift)
    with pytest.raises(ValueError): replay(owner.root, receipt)
