"""Continue this synthetic validation after success; never start/restart its chain."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import uuid

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[2]


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def pins(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def postcheck_files(attempt):
    return sorted(p for name in ('postcheck', 'postcheck_launch')
                  for p in (attempt / name).rglob('*') if p.is_file())


def main(label):
    if not re.fullmatch(r'chain_[0-9]+', label):
        raise ValueError('exact local chain label required')
    attempt = EVIDENCE / label
    out = attempt / 'completion_supervision_02'
    try:
        out.mkdir(exist_ok=False)
    except OSError:
        # Never adopt an existing observer directory or overwrite its records.
        failure = attempt / ('completion_supervision_02_start_failure_' + uuid.uuid4().hex + '.json')
        result = dict(status='START_FAILED', error=traceback.format_exc(),
                      pid=os.getpid(), stages=[], formal_result=False,
                      chain_restarted=False, native_execution_authorized=False)
        save(failure, result)
        print(json.dumps(result), flush=True)
        return 1
    started = time.perf_counter()
    stages = []
    status = 'FAILED'
    error = None
    outputs = {}
    try:
        request_raw = (attempt / 'request.json').read_bytes()
        request = json.loads(request_raw)
        paths = [ROOT / name for name in request['before']]
        paths += [Path(__file__).resolve(), EVIDENCE / 'run_postcheck.py',
                  EVIDENCE / 'postcheck_complete.py', EVIDENCE / 'replay_saved_with_fixture_v1.py',
                  EVIDENCE / 'write_complete_report.py', EVIDENCE / 'preservation_check_02.json',
                  ROOT / 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json',
                  attempt / 'request.json', attempt / 'started.json']
        expected = pins(paths)
        expected[str(attempt / 'request.json')] = hashlib.sha256(request_raw).hexdigest()
        save(out / 'request.json', dict(chain=label, pid=os.getpid(), files_sha256=expected,
            scope='synthetic development postcheck and report only', formal_result=False))
        if pins(paths) != expected:
            raise ValueError('inputs changed during initial observation')
        for name, pin in request['before'].items():
            if expected[str(ROOT / name)] != pin:
                raise ValueError('active chain source already differs: ' + name)
        # A bounded observer has no authority to interrupt, resume or relaunch
        # the existing chain. Its timeout is not a chain failure verdict.
        while not (attempt / 'terminal.json').exists():
            if time.perf_counter() - started > 72 * 3600:
                raise TimeoutError('observer deadline; chain left untouched')
            time.sleep(2)
        # The launcher writes a small JSON once. Allow its write to close.
        for trial in range(30):
            try:
                terminal_raw = (attempt / 'terminal.json').read_bytes()
                terminal = json.loads(terminal_raw)
                break
            except json.JSONDecodeError:
                if trial == 29:
                    raise
                time.sleep(1)
        if terminal['exit_code'] != 0:
            raise ValueError('chain did not succeed; no postcheck launched')
        if terminal['before'] != request['before'] or terminal['after'] != request['before']:
            raise ValueError('chain terminal source pins differ')
        paths.append(attempt / 'terminal.json')
        expected[str(attempt / 'terminal.json')] = hashlib.sha256(terminal_raw).hexdigest()
        concurrent = sorted(attempt.glob('concurrent_validation*.json'))
        closed_logs = [attempt / name for name in ('stdout.log', 'stderr.log', 'timing.jsonl')]
        closed_logs += concurrent
        paths += closed_logs
        expected.update(pins(closed_logs))
        save(out / 'continuation_inputs.json', dict(files_sha256=expected,
            initial_request_sha256=pins([out / 'request.json'])[str(out / 'request.json')]))
        post_files = None
        artifact_root = None
        artifact_files = None
        for name, command in (
            ('postcheck', [sys.executable, '-B', str(EVIDENCE / 'run_postcheck.py'), label]),
            ('report', [sys.executable, '-B', str(EVIDENCE / 'write_complete_report.py'), label]),
        ):
            if pins(paths) != expected or sorted(attempt.glob('concurrent_validation*.json')) != concurrent:
                raise ValueError('pinned inputs changed before ' + name)
            if post_files is not None and postcheck_files(attempt) != post_files:
                raise ValueError('postcheck output membership changed before ' + name)
            if artifact_root is not None and sorted(p for p in artifact_root.rglob('*') if p.is_file()) != artifact_files:
                raise ValueError('saved artifact membership changed before ' + name)
            stage_start = time.perf_counter()
            with (out / (name + '.stdout.log')).open('xb') as stdout, \
                    (out / (name + '.stderr.log')).open('xb') as stderr:
                child = subprocess.Popen(command, cwd=ROOT,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdout=stdout, stderr=stderr)
                save(out / (name + '.started.json'), dict(command=command, pid=child.pid))
                code = child.wait()
            stage = dict(name=name, pid=child.pid, exit_code=code,
                         elapsed_seconds=time.perf_counter() - stage_start)
            stages.append(stage)
            save(out / (name + '.terminal.json'), stage)
            if code != 0:
                raise ValueError(name + ' failed; downstream stopped')
            if pins(paths) != expected or sorted(attempt.glob('concurrent_validation*.json')) != concurrent:
                raise ValueError('pinned inputs changed during ' + name)
            if post_files is not None and postcheck_files(attempt) != post_files:
                raise ValueError('postcheck output membership changed during ' + name)
            if artifact_root is not None and sorted(p for p in artifact_root.rglob('*') if p.is_file()) != artifact_files:
                raise ValueError('saved artifact membership changed during ' + name)
            if name == 'postcheck':
                # Freeze the completed postcheck before the reporter reads it.
                post_files = postcheck_files(attempt)
                post_pins = pins(post_files)
                raw = (attempt / 'postcheck/fresh_process_replay/request.json').read_bytes()
                if hashlib.sha256(raw).hexdigest() != post_pins[str(attempt / 'postcheck/fresh_process_replay/request.json')]:
                    raise ValueError('saved replay request changed during capture')
                saved_request = json.loads(raw)
                artifact_root = Path(saved_request['artifact_root'])
                artifact_files = sorted(artifact_root / path for path in saved_request['artifact_files_sha256'])
                artifact_pins = {str(artifact_root / path): pin
                                 for path, pin in saved_request['artifact_files_sha256'].items()}
                if pins(artifact_files) != artifact_pins:
                    raise ValueError('saved artifacts changed after postcheck')
                paths += post_files + artifact_files
                expected.update(post_pins)
                expected.update(artifact_pins)
                receipt = out / 'report_inputs.json'
                save(receipt, dict(postcheck_files_sha256=post_pins,
                    artifact_files_sha256=artifact_pins, formal_result=False))
                paths.append(receipt)
                expected.update(pins([receipt]))
        outputs = pins([attempt / name for name in (
            'complete_integration_report.md', 'postcheck_launch/terminal.json',
            'postcheck/completed.json', 'postcheck/postcheck_manifest.json',
            'postcheck/chain_postcheck.json', 'postcheck/fresh_process_replay/terminal.json',
            'postcheck/fresh_process_replay/result.json')])
        status = 'SYNTHETIC_POSTCHECK_AND_REPORT_COMPLETED'
    except BaseException:
        error = traceback.format_exc()
    finally:
        outputs.update(pins([p for p in out.iterdir() if p.is_file()]))
        result = dict(status=status, elapsed_seconds=time.perf_counter() - started,
                      stages=stages, error=error, outputs_sha256=outputs, formal_result=False,
                      chain_restarted=False, native_execution_authorized=False)
        save(out / 'terminal.json', result)
        print(json.dumps(result), flush=True)
    return 0 if error is None else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
