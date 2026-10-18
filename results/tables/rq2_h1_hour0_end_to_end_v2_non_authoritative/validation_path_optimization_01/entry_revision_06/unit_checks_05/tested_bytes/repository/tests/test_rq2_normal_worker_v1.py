"""Development subprocess transport with explicitly stubbed public-source boundary."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from test_rq2_source_normal_execution_v1 import supplied, options
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as api


def budget():
    return api.NormalWorkerBudget(30, 1024**3, 2*1024**3, 16*1024**2, 16*1024**2, 3)


def launch(tmp_path, supplied, monkeypatch, *, mode='normal', limits=None):
    assembly, declaration, report, _ = supplied
    original = api._worker_argv

    def command(*args):
        argv = original(*args)
        script = ('import sys; sys.path.insert(0, '+repr(str(api.ROOT))+'); '
                  'from src.rq2_joint_deliverability_boundary_v1 import normal_worker as w; '
                  'w.journal.execution.binding.bind_pair_normal = lambda *a, **k: '+repr(report)+'; ')
        if mode == 'before_intent':
            script += 'w.journal.DevelopmentNormalStore.execute = lambda self: w.os._exit(17); '
        elif mode in ('after_intent', 'after_result'):
            script += '\noriginal = w.journal.DevelopmentNormalStore._append\ndef append(self, raw=None):\n original(self, raw)\n'
            script += ' if '+('raw is None' if mode == 'after_intent' else 'raw is not None')+': w.os._exit(18)\n'
            script += 'w.journal.DevelopmentNormalStore._append = append\n'
        elif mode == 'timeout':
            script += 'import time; time.sleep(20); '
        elif mode == 'false_zero':
            script += 'raise SystemExit(0); '
        elif mode == 'environment_drift':
            script += 'w.os.environ["UNDECLARED_WORKER_SETTING"] = "changed"; '
        elif mode == 'argv_drift':
            script += 'w.sys.orig_argv = ["different command"]; '
        elif mode == 'duplicate_claim':
            script += 'w.main(); '
        script += '\ntry: w.main()\nexcept BaseException:\n import traceback\n from pathlib import Path\n Path(sys.argv[1]).with_name("bootstrap_error.txt").write_text(traceback.format_exc())\n raise\n'
        argv[4] = script
        return argv

    monkeypatch.setattr(api, '_worker_argv', command)
    kw = options(assembly, declaration, report)
    limits = limits or budget()
    env = api.development_environment()
    identity = api.supervision_identity(kw['expected_source_execution_identity'], limits, env)
    root = tmp_path/'attempt_non_authoritative'
    observed = api.supervise_normal(root, assembly, 'unused', declaration, worker_budget=limits,
        environment=env, expected_supervision_identity=identity, **kw)
    return root, observed


def test_owned_worker_tiny_native_once_and_parent_readback(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch)
    errors = (root/'worker_error.json').read_text() if (root/'worker_error.json').exists() else ''
    if (root/'bootstrap_error.txt').exists():
        errors += (root/'bootstrap_error.txt').read_text()
    assert observed.status == 'returned_record_unreplayed', (observed, errors)
    assert observed.process.exit_code == 0 and observed.whole_job_quiescent
    assert observed.store.result_present and observed.store.intent_present
    assert not observed.numerical_evidence_replayed and not observed.native_execution_authenticated
    assert not observed.formal_result
    with sqlite3.connect(root/'normal_non_authoritative'/'normal.sqlite3') as connection:
        raw = connection.execute('SELECT payload FROM result').fetchone()[0]
        record = api.journal._decoded(raw)
        result = dict(record['encoded_result'][1])
        assert result['solver_calls'] == 1 and result['call_count_complete'] is True
        assert result['source_bound_normal_accepted'] is True
    assert api.journal._decoded((root/'observation.json').read_bytes())['request_sha256'] == observed.request_sha256
    launch_raw = (root/'launch.json').read_bytes()
    assert api.sha256(launch_raw).hexdigest() == observed.launch_sha256
    assert 'bind_pair_normal = lambda' in api.journal._decoded(launch_raw)['argv'][4]
    with pytest.raises(FileExistsError):
        launch(tmp_path, supplied, monkeypatch)


@pytest.mark.parametrize('mode, intent, result', [
    ('before_intent', False, False), ('after_intent', True, False), ('after_result', True, True),
    ('false_zero', False, False)])
def test_worker_crash_windows_never_promote_or_retry(tmp_path, supplied, monkeypatch, mode, intent, result):
    root, observed = launch(tmp_path, supplied, monkeypatch, mode=mode)
    assert observed.status == 'unresolved_worker_attempt'
    assert observed.whole_job_quiescent
    assert observed.store.intent_present is intent
    assert observed.store.result_present is result
    with pytest.raises(FileExistsError):
        launch(tmp_path, supplied, monkeypatch, mode=mode)


def test_timeout_without_normal_intent_is_unresolved(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch, mode='timeout',
                            limits=replace(budget(), max_child_seconds=.1))
    assert observed.process.reason == 'deadline_termination'
    assert observed.status == 'unresolved_worker_attempt'
    assert not observed.store.intent_present


def test_full_record_cap_failure_keeps_intent(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch, limits=replace(budget(), max_record_bytes=1))
    assert observed.status == 'unresolved_worker_attempt'
    assert observed.store.status == 'unresolved_intent'
    assert 'exceeds byte budget' in (root/'worker_error.json').read_text()


def test_input_roundtrip_preserves_exact_identity(supplied):
    assembly, declaration, report, _ = supplied
    original = (assembly, declaration, options(assembly, declaration, report))
    encoded = api._encode(original)
    decoded = api._decode(json.loads(json.dumps(encoded)))
    assert api.kernel._digest(original) == api.kernel._digest(decoded)
    assert type(decoded[0]) is api.SourceNormalAssembly
    assert decoded[0].inputs.request.completed_periods == frozenset()


@pytest.mark.parametrize('value', [
    ['SourceNormalExecutionResult', []], ['NormalAssignmentWitness', []],
    ['__import__', 'os'], ['float', 'inf'], ['mapping', [[1, 1], [True, 2]]],
    ['NormalExecutionBudget', []], ['set', [1, 1]]])
def test_codec_rejects_owned_or_ambiguous_types(value):
    with pytest.raises((ValueError, TypeError)):
        api._decode(value)


def test_request_hash_size_and_canonical_bytes(tmp_path):
    path = tmp_path/'request.json'
    path.write_bytes(b'{}')
    digest = api.sha256(b'{}').hexdigest()
    assert api._read_request(path, digest, 2) == {}
    with pytest.raises(ValueError):
        api._read_request(path, digest, 1)
    with pytest.raises(ValueError):
        api._read_request(path, '0'*64, 2)
    path.write_bytes(b'{ }')
    with pytest.raises(ValueError, match='canonical'):
        api._read_request(path, api.sha256(b'{ }').hexdigest(), 3)


def test_environment_is_explicit_and_excludes_parent_secret(monkeypatch):
    monkeypatch.setenv('NORMAL_TEST_SECRET', 'test-only')
    env = api.development_environment()
    assert 'NORMAL_TEST_SECRET' not in env
    api._environment(env)
    with pytest.raises(ValueError):
        api._environment(dict(env, NORMAL_TEST_SECRET='test-only'))


def test_external_identity_refusal_before_files(tmp_path, supplied):
    assembly, declaration, report, _ = supplied
    root = tmp_path/'attempt_non_authoritative'
    with pytest.raises(ValueError, match='identity'):
        api.supervise_normal(root, assembly, 'unused', declaration, worker_budget=budget(),
            environment=api.development_environment(), expected_supervision_identity='0'*64,
            **options(assembly, declaration, report))
    assert not root.exists()


def test_actual_worker_entry_rejects_missing_public_source(tmp_path, supplied):
    # Fixed production-of-draft argv, with no source stub inside the child.
    assembly, declaration, report, _ = supplied
    kw = options(assembly, declaration, report)
    limits, env = budget(), api.development_environment()
    identity = api.supervision_identity(kw['expected_source_execution_identity'], limits, env)
    root = tmp_path/'missing_source_non_authoritative'
    observed = api.supervise_normal(root, assembly, str(tmp_path/'missing'), declaration,
        worker_budget=limits, environment=env, expected_supervision_identity=identity, **kw)
    assert observed.process.exit_code != 0
    assert observed.store.status == 'unresolved_intent'
    assert observed.status == 'unresolved_worker_attempt'
    assert (root/'worker_error.json').exists()


def test_quiescence_failure_prevents_parent_result_read(tmp_path, supplied, monkeypatch):
    original_inspect = api.journal.DevelopmentNormalStore.inspect
    reads = []
    def inspect(self):
        reads.append(True)
        return original_inspect(self)
    def fail(self, **kwargs):
        raise TimeoutError('injected nonquiet Job')
    monkeypatch.setattr(api.journal.DevelopmentNormalStore, 'inspect', inspect)
    monkeypatch.setattr(api.process.DevelopmentNormalChild, 'quiesce', fail)
    with pytest.raises(TimeoutError):
        launch(tmp_path, supplied, monkeypatch, mode='false_zero')
    assert len(reads) == 1  # Only parent pre-launch genesis inspection.
    assert not (tmp_path/'attempt_non_authoritative'/'observation.json').exists()


def test_oversize_request_prevents_process_creation(tmp_path, supplied, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('no child allowed')
    monkeypatch.setattr(api.process, 'DevelopmentNormalChild', forbidden)
    with pytest.raises(ValueError, match='request exceeds'):
        launch(tmp_path, supplied, monkeypatch, limits=replace(budget(), max_request_bytes=1))


def test_worker_environment_drift_rejected_before_claim(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch, mode='environment_drift')
    assert observed.status == 'unresolved_worker_attempt'
    assert not observed.store.intent_present
    assert not (root/'worker_claim.json').exists()
    assert 'environment differs' in (root/'bootstrap_error.txt').read_text()


def test_duplicate_worker_claim_cannot_invoke_again(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch, mode='duplicate_claim')
    assert observed.status == 'unresolved_worker_attempt' and observed.store.result_present
    assert observed.process.exit_code != 0
    assert 'FileExistsError' in (root/'bootstrap_error.txt').read_text()
    with sqlite3.connect(root/'normal_non_authoritative'/'normal.sqlite3') as connection:
        assert connection.execute('SELECT COUNT(*) FROM intent').fetchone() == (1,)
        assert connection.execute('SELECT COUNT(*) FROM result').fetchone() == (1,)


def test_worker_actual_argv_mismatch_rejected_before_claim(tmp_path, supplied, monkeypatch):
    root, observed = launch(tmp_path, supplied, monkeypatch, mode='argv_drift')
    assert observed.status == 'unresolved_worker_attempt'
    assert not observed.store.intent_present
    assert not (root/'worker_claim.json').exists()
    assert 'launch identity mismatch' in (root/'bootstrap_error.txt').read_text()


def test_parent_death_after_worker_intent_preserves_unresolved_store(tmp_path, supplied):
    assembly, declaration, report, _ = supplied
    input_path = tmp_path/'test_inputs.json'
    input_path.write_bytes(api.journal._bytes(api._encode((assembly, declaration, report))))
    root = tmp_path/'death_non_authoritative'
    ready = tmp_path/'worker_waiting'
    worker_script = (
        'import sys,time; sys.path.insert(0, '+repr(str(api.ROOT))+'); '
        'from pathlib import Path; from src.rq2_joint_deliverability_boundary_v1 import normal_worker as w; '
        'w.journal.execution.binding.bind_pair_normal=lambda *a,**k: '+repr(report)+'\n'
        'original=w.journal.DevelopmentNormalStore._append\n'
        'def append(self,raw=None):\n original(self,raw)\n if raw is None:\n'
        '  Path('+repr(str(ready))+').write_text("intent committed")\n  time.sleep(20)\n'
        'w.journal.DevelopmentNormalStore._append=append\nw.main()')
    parent_script = f"""
import sys
sys.path.insert(0, {str(api.ROOT)!r})
sys.path.insert(0, {str(api.ROOT/'tests')!r})
from pathlib import Path
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as w
from test_rq2_source_normal_execution_v1 import options
assembly, declaration, report = w._decode(w.journal._decoded(Path({str(input_path)!r}).read_bytes()))
original = w._worker_argv
def argv(*args):
    result = original(*args)
    result[4] = {worker_script!r}
    return result
w._worker_argv = argv
kw = options(assembly, declaration, report)
budget = w.NormalWorkerBudget(**{api.asdict(budget())!r})
env = w.development_environment()
identity = w.supervision_identity(kw['expected_source_execution_identity'], budget, env)
w.supervise_normal({str(root)!r}, assembly, 'unused', declaration, worker_budget=budget,
    environment=env, expected_supervision_identity=identity, **kw)
"""
    parent = subprocess.Popen([sys.executable, '-B', '-c', parent_script], cwd=api.ROOT,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    k, handle = api.process._api(), None
    k.OpenProcess.argtypes = [api.process.DWORD, api.process.w.BOOL, api.process.DWORD]
    k.OpenProcess.restype = api.process.HANDLE
    try:
        deadline = time.monotonic()+15
        while not ready.exists():
            assert parent.poll() is None
            assert time.monotonic() < deadline
            time.sleep(.02)
        launch = api.journal._decoded((root/'launch.json').read_bytes())
        handle = api.process._check(k.OpenProcess(0x100000, False, launch['pid']))
        assert k.WaitForSingleObject(handle, 0) == 258
        parent.kill()
        parent.wait(timeout=5)
        assert k.WaitForSingleObject(handle, 5000) == 0
        packet = api.journal._decoded((root/'request.json').read_bytes())
        assert not (root/'observation.json').exists()
        with api.journal.DevelopmentNormalStore(root/'normal_non_authoritative', assembly, 'unused', declaration,
                create=False, expected_head=packet['genesis'], max_record_bytes=budget().max_record_bytes,
                **options(assembly, declaration, report)) as store:
            assert store.inspect().status == 'unresolved_intent'
            with pytest.raises(ValueError, match='cannot retry'):
                store.execute()
        with pytest.raises(FileExistsError):
            api.supervise_normal(root, assembly, 'unused', declaration, worker_budget=budget(),
                environment=packet['environment'], expected_supervision_identity=packet['supervision_identity'],
                **options(assembly, declaration, report))
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if handle:
            k.CloseHandle(handle)
