"""Tiny isolated orchestration checks; fake children, no scientific validation."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time

E = Path(__file__).resolve().parent
entry = E / 'supervise_completion.py'
spec = importlib.util.spec_from_file_location('synthetic_supervision_gate_check', entry)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def fixture(target, name, code):
    root = target / name
    evidence = root / 'results/tables/evidence'
    attempt = evidence / 'chain_01'
    attempt.mkdir(parents=True)
    source = root / 'source.py'
    source.write_bytes(b'# fixed fake input\n')
    pin = hashlib.sha256(source.read_bytes()).hexdigest()
    expected = {'source.py': pin}
    save(attempt / 'request.json', {'before': expected})
    save(attempt / 'started.json', {'pid': 0})
    save(attempt / 'terminal.json', {'exit_code': code, 'before': expected, 'after': expected})
    for name in ('stdout.log', 'stderr.log', 'timing.jsonl'):
        (attempt / name).write_bytes(b'FAKE FIXTURE ONLY\n')
    for name in ('run_postcheck.py', 'postcheck_complete.py', 'replay_saved_with_fixture_v1.py',
                 'write_complete_report.py', 'preservation_check_02.json'):
        (evidence / name).write_bytes(b'# fake fixture\n')
    manifest = root / 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json'
    save(manifest, {'synthetic_supervisor_fixture': True})
    m.ROOT, m.EVIDENCE = root, evidence
    return root, evidence, attempt


def main():
    start = time.perf_counter()
    utc = datetime.now(timezone.utc).isoformat()
    target = E / 'supervisor_gate_check_03'
    target.mkdir(exist_ok=False)
    before = hashlib.sha256(entry.read_bytes()).hexdigest()
    root, evidence, attempt = fixture(target, 'source_drift', 0)
    (root / 'source.py').write_bytes(b'# changed fake input\n')
    assert m.main('chain_01') == 1
    result = m.read(attempt / 'completion_supervision_01/terminal.json')
    assert 'active chain source already differs:' in result['error']
    assert result['stages'] == []
    root, evidence, attempt = fixture(target, 'invalid_request', 0)
    (attempt / 'request.json').write_bytes(b'INVALID JSON')
    assert m.main('chain_01') == 1
    assert m.read(attempt / 'completion_supervision_01/terminal.json')['stages'] == []
    root, evidence, attempt = fixture(target, 'failed_chain', 1)
    assert m.main('chain_01') == 1
    assert not (attempt / 'completion_supervision_01/postcheck.started.json').exists()
    root, evidence, attempt = fixture(target, 'failed_postcheck', 0)
    (evidence / 'run_postcheck.py').write_text('raise SystemExit(7)\n', encoding='utf-8')
    assert m.main('chain_01') == 1
    assert not (attempt / 'completion_supervision_01/report.started.json').exists()
    result = m.read(attempt / 'completion_supervision_01/terminal.json')
    assert result['stages'][0]['exit_code'] == 7
    for index, name in enumerate(('terminal.json', 'stdout.log', 'timing.jsonl', 'concurrent_validation_added.json')):
        root, evidence, attempt = fixture(target, 'closed_input_drift_' + str(index), 0)
        (evidence / 'run_postcheck.py').write_text(
            'from pathlib import Path\nimport sys\n'
            f'(Path(__file__).parent/sys.argv[1]/{name!r}).write_bytes(b"CHANGED")\n', encoding='utf-8')
        assert m.main('chain_01') == 1
        result = m.read(attempt / 'completion_supervision_01/terminal.json')
        assert 'pinned inputs changed during postcheck' in result['error']
        assert not (attempt / 'completion_supervision_01/report.started.json').exists()
    root, evidence, attempt = fixture(target, 'successful_orchestration', 0)
    (evidence / 'run_postcheck.py').write_text(
        'from pathlib import Path\nimport sys\n'
        'base=Path(__file__).parent/sys.argv[1]\n'
        'names=("postcheck_launch/terminal.json","postcheck/completed.json",'
        '"postcheck/postcheck_manifest.json","postcheck/chain_postcheck.json",'
        '"postcheck/fresh_process_replay/terminal.json","postcheck/fresh_process_replay/result.json")\n'
        'for name in names:\n p=base/name\n p.parent.mkdir(parents=True,exist_ok=True)\n'
        ' with p.open("x") as f:f.write("{\\"FAKE_FIXTURE\\":true}")\n', encoding='utf-8')
    (evidence / 'write_complete_report.py').write_text(
        'from pathlib import Path\nimport sys\n'
        'p=Path(__file__).parent/sys.argv[1]/"complete_integration_report.md"\n'
        'with p.open("x") as f:f.write("ISOLATED FAKE ORCHESTRATION FIXTURE ONLY")\n', encoding='utf-8')
    assert m.main('chain_01') == 0
    result = m.read(attempt / 'completion_supervision_01/terminal.json')
    assert [row['name'] for row in result['stages']] == ['postcheck', 'report']
    assert str(attempt / 'complete_integration_report.md') in result['outputs_sha256']
    assert str(attempt / 'completion_supervision_01/postcheck.stdout.log') in result['outputs_sha256']
    continuation = m.read(attempt / 'completion_supervision_01/continuation_inputs.json')
    assert str(attempt / 'terminal.json') in continuation['files_sha256']
    assert before == hashlib.sha256(entry.read_bytes()).hexdigest()
    summary = dict(checks_passed=9, scope='isolated fake orchestration children only',
        entry_sha256=before, elapsed_seconds=time.perf_counter()-start, start_utc=utc,
        end_utc=datetime.now(timezone.utc).isoformat(), exit_code=0, formal_result=False)
    save(target / 'result.json', summary)
    save(E / 'chain_04/concurrent_validation_supervisor_gates_03.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
