"""Fake orchestration only: output handoff, membership and start failure gates."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def case(tmp_path):
    gate = load('old_gate_fixture', BASE / 'check_supervisor_gates.py')
    module = load('v2_gate_under_test', BASE / 'supervise_completion_v2.py')
    gate.m = module
    root, evidence, attempt = gate.fixture(tmp_path, 'fake', 0)
    artifact = root / 'saved_artifacts'
    artifact.mkdir()
    (artifact / 'report.json').write_text('{"FAKE_FIXTURE":true}', encoding='utf8')
    fake_post = '''from pathlib import Path
import hashlib,json,sys
base=Path(__file__).parent/sys.argv[1]
artifact=base.parents[3]/'saved_artifacts'
names=('postcheck_launch/terminal.json','postcheck/completed.json',
       'postcheck/postcheck_manifest.json','postcheck/chain_postcheck.json',
       'postcheck/fresh_process_replay/terminal.json','postcheck/fresh_process_replay/result.json')
for name in names:
    p=base/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('{"FAKE_FIXTURE":true}')
request=dict(artifact_root=str(artifact),artifact_files_sha256={
    'report.json':hashlib.sha256((artifact/'report.json').read_bytes()).hexdigest()})
(base/'postcheck/fresh_process_replay/request.json').write_text(json.dumps(request))
'''
    fake_report = '''from pathlib import Path
import sys
base=Path(__file__).parent/sys.argv[1]
(base/'complete_integration_report.md').write_text('FAKE ORCHESTRATION ONLY\n')
'''.replace('ONLY\n', 'ONLY\\n')
    (evidence / 'run_postcheck.py').write_text(fake_post, encoding='utf8')
    (evidence / 'write_complete_report.py').write_text(fake_report, encoding='utf8')
    return module, root, evidence, attempt, artifact


def result(case):
    return case[0].read(case[3] / 'completion_supervision_02/terminal.json')


def test_success_binds_full_postcheck_and_original_saved_inputs(case):
    module, root, evidence, attempt, artifact = case
    assert module.main('chain_01') == 0
    report_inputs = module.read(attempt / 'completion_supervision_02/report_inputs.json')
    assert len(report_inputs['postcheck_files_sha256']) == 7
    assert report_inputs['artifact_files_sha256'] == module.pins([artifact / 'report.json'])
    assert [stage['name'] for stage in result(case)['stages']] == ['postcheck', 'report']


@pytest.mark.parametrize('target', ['postcheck/completed.json', 'postcheck/fresh_process_replay/result.json',
                                    'postcheck/chain_postcheck.json', 'postcheck_launch/terminal.json',
                                    'postcheck/new_file.json', 'saved_artifact'])
@pytest.mark.parametrize('boundary', ['before_report', 'during_report'])
def test_persistent_output_or_saved_input_drift_cannot_pass(case, monkeypatch, target, boundary):
    module, root, evidence, attempt, artifact = case
    path = artifact / 'report.json' if target == 'saved_artifact' else attempt / target
    if boundary == 'before_report':
        original = module.save
        def save(destination, value):
            original(destination, value)
            if destination.name == 'report_inputs.json':
                path.write_bytes(b'ALTERED')
        monkeypatch.setattr(module, 'save', save)
    else:
        with (evidence / 'write_complete_report.py').open('a', encoding='utf8') as stream:
            stream.write(f'Path({str(path)!r}).write_bytes(b"ALTERED")\n')
    assert module.main('chain_01') == 1
    assert 'changed' in result(case)['error']
    if boundary == 'before_report':
        assert not (attempt / 'completion_supervision_02/report.started.json').exists()


def test_output_deletion_stops_before_report(case, monkeypatch):
    module, root, evidence, attempt, artifact = case
    original = module.save
    def save(path, value):
        original(path, value)
        if path.name == 'report_inputs.json':
            (attempt / 'postcheck/completed.json').unlink()
    monkeypatch.setattr(module, 'save', save)
    assert module.main('chain_01') == 1
    assert not (attempt / 'completion_supervision_02/report.started.json').exists()


@pytest.mark.parametrize('operation', ['add_artifact', 'delete_artifact', 'delete_postcheck'])
@pytest.mark.parametrize('boundary', ['before_report', 'during_report'])
def test_saved_tree_and_postcheck_membership_faults(case, monkeypatch, operation, boundary):
    module, root, evidence, attempt, artifact = case
    if operation == 'add_artifact':
        action = f'Path({str(artifact / "extra.bin")!r}).write_bytes(b"ADDED")'
    else:
        path = artifact / 'report.json' if operation == 'delete_artifact' else attempt / 'postcheck/completed.json'
        action = f'Path({str(path)!r}).unlink()'
    if boundary == 'before_report':
        original = module.save
        def save(path, value):
            original(path, value)
            if path.name == 'report_inputs.json':
                exec(action, {'Path': Path})
        monkeypatch.setattr(module, 'save', save)
    else:
        with (evidence / 'write_complete_report.py').open('a', encoding='utf8') as stream:
            stream.write(action + '\n')
    assert module.main('chain_01') == 1
    if boundary == 'before_report':
        assert not (attempt / 'completion_supervision_02/report.started.json').exists()


def test_existing_supervisor_directory_is_not_adopted_or_overwritten(case):
    module, root, evidence, attempt, artifact = case
    out = attempt / 'completion_supervision_02'
    out.mkdir()
    sentinel = out / 'request.json'
    sentinel.write_bytes(b'EXISTING OWNER')
    assert module.main('chain_01') == 1
    assert sentinel.read_bytes() == b'EXISTING OWNER'
    assert list(out.iterdir()) == [sentinel]
    failures = list(attempt.glob('completion_supervision_02_start_failure_*.json'))
    assert len(failures) == 1
    assert module.read(failures[0])['status'] == 'START_FAILED'


@pytest.mark.parametrize('fault', ['source', 'request', 'chain', 'postcheck', 'closed_log', 'closed_membership'])
def test_existing_upstream_failure_gates_remain(case, fault):
    module, root, evidence, attempt, artifact = case
    if fault == 'source':
        (root / 'source.py').write_bytes(b'CHANGED')
    elif fault == 'request':
        (attempt / 'request.json').write_bytes(b'INVALID JSON')
    elif fault == 'chain':
        terminal = module.read(attempt / 'terminal.json')
        terminal['exit_code'] = 1
        (attempt / 'terminal.json').write_text(json.dumps(terminal), encoding='utf8')
    elif fault == 'postcheck':
        (evidence / 'run_postcheck.py').write_text('raise SystemExit(7)\n', encoding='utf8')
    else:
        name = 'stdout.log' if fault == 'closed_log' else 'concurrent_validation_added.json'
        with (evidence / 'run_postcheck.py').open('a', encoding='utf8') as stream:
            stream.write(f'(base/{name!r}).write_bytes(b"CHANGED")\n')
    assert module.main('chain_01') == 1
    assert not (attempt / 'completion_supervision_02/report.started.json').exists()
