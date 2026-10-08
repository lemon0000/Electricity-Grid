from copy import copy, deepcopy
from dataclasses import replace
import json
from pathlib import Path
import pickle
import sqlite3
import subprocess
import sys

import pytest

from test_rq2_scale_selector_v1 import budget, args, REF, SPEC, ref_install
from src.rq2_joint_deliverability_boundary_v1 import scale_selector as scale
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_store as store


LIMIT = 2*1024*1024


def request():
    info, disclosure, before = args()
    b = budget()
    return store.SelectorRequest(info, disclosure, before,
        scale.reference.reference_input_identity(info, disclosure, before), REF, SPEC, b,
        scale.policy_identity(REF, SPEC, b))


def inspect(root, pin, limit=LIMIT):
    return store.inspect_scale_selector_store(root, expected_binding_identity=pin, max_record_bytes=limit)


def test_real_selector_archive_is_one_shot_and_inspectable(tmp_path):
    root = tmp_path/'selector_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        assert owned.inspection()['status'] == 'unused'
        result = owned.execute()
        assert result.status == 'selected'
        assert owned.inspection()['status'] == 'returned_unverified'
        with pytest.raises(ValueError):
            owned.execute()
    report = inspect(root, pin)
    assert report['result_present'] and report['planned_solver_calls'] == 3
    assert report['reported_solver_calls'] == report['reported_completed_solver_calls'] == 3
    assert not report['numerical_evidence_replayed'] and not report['executable_resume_available']
    with sqlite3.connect((root/'selector.sqlite3').as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        record = json.loads(db.execute('SELECT payload FROM result').fetchone()[0])
    assert record['result_identity'] == result.identity
    assert not result.durable_invocation_tracking  # wrapper does not relabel core evidence


@pytest.mark.parametrize('exception', [RuntimeError, KeyboardInterrupt])
def test_unreturned_invocation_stays_unknown_and_cannot_retry(tmp_path, monkeypatch, exception):
    root = tmp_path/'pending_non_authoritative'
    def fail(*args, **kwargs):
        raise exception()
    monkeypatch.setattr(scale, 'select_hour', fail)
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        with pytest.raises(exception):
            owned.execute()
        assert owned.inspection()['status'] == 'pending_unknown'
        with pytest.raises(ValueError, match='retry'):
            owned.execute()
    assert inspect(root, pin)['status'] == 'pending_unknown'


def test_result_commit_with_lost_ack_is_readable_but_not_reexecutable(tmp_path, monkeypatch):
    ref_install(monkeypatch)
    root = tmp_path/'result_ack_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        append = owned._append
        def lost(result=None):
            append(result)
            if result is not None:
                raise OSError('synthetic lost result acknowledgement')
        monkeypatch.setattr(owned, '_append', lost)
        with pytest.raises(OSError):
            owned.execute()
        with pytest.raises(ValueError, match='retry'):
            owned.execute()
    report = inspect(root, pin)
    assert report['status'] == 'returned_unverified' and report['reported_solver_calls'] == 3


def test_wrong_result_binding_never_publishes(tmp_path, monkeypatch):
    ref_install(monkeypatch)
    run = scale.select_hour
    def wrong(*args, **kwargs):
        result = run(*args, **kwargs)
        object.__setattr__(result, 'input_identity', 'b'*64)
        return result
    monkeypatch.setattr(scale, 'select_hour', wrong)
    root = tmp_path/'wrong_result_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        with pytest.raises(ValueError, match='binding'):
            owned.execute()
    report = inspect(root, pin)
    assert report['status'] == 'pending_unknown' and report['reported_solver_calls'] is None


def test_result_write_failure_keeps_committed_intent(tmp_path, monkeypatch):
    root = tmp_path/'write_failure_non_authoritative'
    ref_install(monkeypatch)
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        append = owned._append
        def fail(result=None):
            if result is not None:
                raise OSError('synthetic publication failure')
            append()
        monkeypatch.setattr(owned, '_append', fail)
        with pytest.raises(OSError):
            owned.execute()
    assert inspect(root, pin)['status'] == 'pending_unknown'


def test_intent_ack_failure_does_not_enter_selector(tmp_path, monkeypatch):
    root = tmp_path/'ack_failure_non_authoritative'
    def forbidden(*a, **kw):
        pytest.fail('numerical kernel entered after failed intent acknowledgement')
    monkeypatch.setattr(scale, 'select_hour', forbidden)
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        append = owned._append
        def fail(result=None):
            append(result)
            raise OSError('synthetic lost commit acknowledgement')
        monkeypatch.setattr(owned, '_append', fail)
        with pytest.raises(OSError):
            owned.execute()
    assert inspect(root, pin)['status'] == 'pending_unknown'


def test_small_record_limit_preserves_unresolved_intent(tmp_path, monkeypatch):
    ref_install(monkeypatch)
    root = tmp_path/'small_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=1) as owned:
        pin = owned.binding_identity
        with pytest.raises(ValueError, match='record limit'):
            owned.execute()
    assert inspect(root, pin, 1)['status'] == 'pending_unknown'


def test_exclusion_copy_and_active_inspection(tmp_path):
    root = tmp_path/'exclusive_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        for clone in (copy, deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                clone(owned)
        with pytest.raises(ValueError):
            inspect(root, owned.binding_identity)
        owned._guard.acquire()
        try:
            for operation in (owned.execute, owned.inspection, owned.close):
                with pytest.raises(ValueError):
                    operation()
        finally:
            owned._guard.release()


def test_wrong_external_binding_and_modified_payload_rejected(tmp_path, monkeypatch):
    ref_install(monkeypatch)
    root = tmp_path/'tamper_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        owned.execute()
    with pytest.raises(ValueError, match='binding'):
        inspect(root, 'b'*64)
    with sqlite3.connect(root/'selector.sqlite3') as db:
        db.execute("UPDATE result SET payload=?", (b'{}',))
    with pytest.raises(ValueError, match='digest'):
        inspect(root, pin)


def test_process_exit_after_intent_leaves_inspectable_unknown(tmp_path):
    root = tmp_path/'process_non_authoritative'
    code = '''
import os,sys
sys.path.insert(0, 'tests')
from test_rq2_scale_selector_store_v1 import request,LIMIT
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_store as store,scale_selector as scale
owned=store.DevelopmentScaleSelectorStore(sys.argv[1],request(),max_record_bytes=LIMIT)
print(owned.binding_identity,flush=True)
scale.select_hour=lambda *a,**kw: os._exit(17)
owned.execute()
'''
    process = subprocess.run([sys.executable, '-B', '-c', code, str(root)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
    assert process.returncode == 17, process.stderr
    pin = process.stdout.strip().splitlines()[-1]
    report = inspect(root, pin)
    assert report['status'] == 'pending_unknown'
    assert report['charged_solver_calls'] == report['charged_solver_seconds'] == 3
    assert report['reported_solver_calls'] is None


@pytest.mark.parametrize('target', ['intent', 'result'])
def test_insert_noop_fails_post_commit_readback(tmp_path, monkeypatch, target):
    calls = ref_install(monkeypatch)
    root = tmp_path/(target+'_noop_non_authoritative')
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        connect = store._connect
        class NoInsert:
            def __init__(self, db): self.db = db
            def execute(self, sql, *args):
                return self.db.execute('SELECT 1') if sql.startswith('INSERT INTO '+target+' ') else self.db.execute(sql, *args)
            def __enter__(self): self.db.__enter__(); return self
            def __exit__(self, *args): return self.db.__exit__(*args)
            def close(self): self.db.close()
        with monkeypatch.context() as patch:
            patch.setattr(store, '_connect', lambda path, readonly=False:
                connect(path, readonly) if readonly else NoInsert(connect(path, readonly)))
            with pytest.raises(ValueError, match='readback'):
                owned.execute()
        assert calls['solve'] == (0 if target == 'intent' else 3)
        with pytest.raises(ValueError, match='retry'):
            owned.execute()
    assert inspect(root, pin)['status'] == ('unused' if target == 'intent' else 'pending_unknown')


@pytest.mark.parametrize('status', ['pending_unknown', 'returned_unverified'])
def test_readback_error_poisoned_even_when_record_committed(tmp_path, monkeypatch, status):
    calls = ref_install(monkeypatch)
    root = tmp_path/'readback_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        read = store._read
        def fail(*args):
            result = read(*args)
            if result[0]['status'] == status:
                raise OSError('synthetic readback I/O failure')
            return result
        with monkeypatch.context() as patch:
            patch.setattr(store, '_read', fail)
            with pytest.raises(OSError):
                owned.execute()
        assert calls['solve'] == (0 if status == 'pending_unknown' else 3)
    assert inspect(root, pin)['status'] == status


def test_codec_source_drift_rejected_before_intent(tmp_path, monkeypatch):
    root = tmp_path/'codec_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        read = Path.read_bytes
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'read_bytes', lambda path: read(path)+(b'\n# drift' if path.name == 'continuous_grid_normal.py' else b''))
            with pytest.raises(ValueError):
                owned.execute()
    assert inspect(root, pin)['status'] == 'unused'


def test_early_stopped_return_still_charges_full_reservation(tmp_path, monkeypatch):
    ref_install(monkeypatch, fault='timeout', stage=0)
    root = tmp_path/'stopped_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        result = owned.execute()
        assert result.status == 'unresolved' and result.solver_calls == 1
    report = inspect(root, pin)
    assert report['reported_solver_calls'] == 1
    assert report['charged_solver_calls'] == report['charged_solver_seconds'] == 3


def test_relocated_copy_does_not_inherit_original_root_binding(tmp_path):
    import shutil
    root = tmp_path/'original_non_authoritative'
    with store.DevelopmentScaleSelectorStore(root, request(), max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
    copied = tmp_path/'copy_non_authoritative'
    shutil.copytree(root, copied)
    with pytest.raises(ValueError, match='root identity'):
        inspect(copied, pin)
    assert inspect(root, pin)['status'] == 'unused'
