"""Read-only postcheck after the one fixed Python-sampler slice terminates."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import msvcrt
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P = HERE.parent/'validation_path_optimization_01'
OUTER = P/'configured_entry_06_common_slice_monitor_01'
INNER = P/'entry_revision_06/common_slice_02'
SHORT = Path('D:/h1_cs02_non_authoritative')


def digest(path): return sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())


# Refuse to postcheck or create an outcome while the attempt has no terminal.
terminal = read(OUTER/'terminal.json')
request = read(OUTER/'request.json')
assert terminal['source_snapshot_complete'] and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert terminal['final_storage_observation_complete'] and not terminal['storage_read_errors']
assert not terminal['complete_process_tree_absence_proven']
for name,pin in request['source_sha256'].items():
    path = Path(name)
    assert digest(path) == pin
    assert digest(OUTER/'tested_bytes'/path.relative_to(REPO)) == pin
for row in terminal['observed_owned_processes']:
    try:
        process = psutil.Process(row['pid'])
        assert process.create_time() != row['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:
        pass
storage = sum(path.stat().st_size for name in request['storage_roots']
              for path in Path(name).rglob('*') if path.is_file())
assert storage == terminal['observed_storage_bytes']

saved_before = {path.relative_to(SHORT).as_posix():digest(path)
    for path in SHORT.rglob('*') if path.is_file()}
locks = []
for path in sorted(SHORT.rglob('*.lock')):
    if not path.is_file():
        continue
    raw = path.read_bytes()
    assert raw, 'empty lock file cannot be checked without changing its bytes'
    with path.open('r+b') as stream:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            locks.append(dict(path=path.relative_to(SHORT).as_posix(),sha256=sha256(raw).hexdigest(),bytes_hex=raw.hex()))
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
assert saved_before == {path.relative_to(SHORT).as_posix():digest(path)
    for path in SHORT.rglob('*') if path.is_file()}

timings = [json.loads(line) for line in (INNER/'timing.jsonl').read_text().splitlines()]
sample_lines = (SHORT/'stack_samples.jsonl').read_text().splitlines()
samples, sample_parse_errors = [], []
for index,line in enumerate(sample_lines):
    try:
        samples.append(json.loads(line))
    except json.JSONDecodeError as error:
        # A killed diagnostic may leave only its final write partial. Preserve
        # it verbatim; never infer a complete sample from that partial line.
        if terminal['stop_reason'] is None or index != len(sample_lines)-1:
            raise
        sample_parse_errors.append(dict(line=index+1,error=str(error)))
assert all(not row.get('truncated') or len(row['frames']) == 128 for row in samples)
assert all(len(row['frames']) <= 128 for row in samples)
sampled_frames = [dict(elapsed_seconds=row['elapsed_seconds'],frames=row['frames'][:10],
    truncated=row['truncated']) for row in samples]
inner = read(INNER/'terminal.json') if (INNER/'terminal.json').exists() else None
reports = list(SHORT.rglob('guarded_common_slice_report.json'))
report = read(reports[0]) if len(reports) == 1 else None
success = terminal['exit_code'] == 0 and terminal['stop_reason'] is None
if success:
    assert inner is not None and inner['exit_code'] == 0
    assert inner['repository_code_unchanged'] and inner['repository_test_closure_unchanged']
    assert inner['candidate_bytes_unchanged'] and inner['interpreter_settings_restored']
    assert inner['diagnostic_faulthandler_plugin_absent']
    assert inner['diagnostic_fatal_handler_enabled_at_configure'] is False
    assert inner['pytest_tests_failed'] == 0 and report is not None
    assert report['full_chain_passed'] is False and report['formal_result'] is False

observed_jobs = []
for path in sorted(SHORT.rglob('observation.json')):
    try:
        value = read(path)
    except json.JSONDecodeError as error:
        observed_jobs.append(dict(path=path.relative_to(SHORT).as_posix(),sha256=digest(path),
            parse_error=str(error),terminal_state='unresolved partial artifact'))
        continue
    observed_jobs.append(dict(path=path.relative_to(SHORT).as_posix(),
        exit_code=value.get('exit_code'),whole_job_quiescent=value.get('whole_job_quiescent'),
        sha256=digest(path)))
chain = HERE.parent/'chain_07'
old = read(chain/'request.json')['before']
assert all(digest(Path(name)) == pin for name,pin in old.items())
old_processes = []
for pid in (43640,27888,42184):
    try:
        process = psutil.Process(pid)
        old_processes.append(dict(pid=pid,creation_time=process.create_time(),command=process.cmdline(),
            cpu_seconds=sum(process.cpu_times()[:2]),rss_bytes=process.memory_info().rss))
    except psutil.NoSuchProcess:
        old_processes.append(dict(pid=pid,present=False))

out = HERE/'common_slice_outcome_02'
out.mkdir(exist_ok=False)
for source,name in ((INNER/'timing.jsonl','timing.jsonl'),(INNER/'pytest.log','pytest.log'),
                     (SHORT/'stack_samples.jsonl','stack_samples.jsonl')):
    (out/name).write_bytes(source.read_bytes())
status = ('SLICE_PASSED' if success else 'STOPPED_BUDGET' if terminal['stop_reason'] is not None
          else 'FAILED_DIAGNOSTIC')
result = dict(status=status,observed_utc=datetime.now(timezone.utc).isoformat(),
    source_files_and_tested_copies_unchanged=len(request['source_sha256']),
    outer_terminal=terminal,inner_terminal_present=inner is not None,
    inner_exit_code=inner['exit_code'] if inner else None,
    observed_owned_processes_absent=True,complete_process_tree_absence_proven=False,
    final_three_root_storage_bytes=storage,
    short_root_files_unchanged_by_postcheck=len(saved_before),
    lock_files_reacquired_and_released=locks,
    completed_stage_timings=timings,
    completed_N0_stage_markers=[row for row in timings if row['label'].startswith('slice_arm_') and row['label'].endswith('_N0')],
    stack_samples=len(samples),stack_sample_parse_errors=sample_parse_errors,
    sampled_project_frames=sampled_frames,
    zero_native_synthetic_job_observations=observed_jobs,
    slice_success_report_present=report is not None, report=report,
    old_chain_inputs_unchanged=len(old),old_chain_process_observation=old_processes,
    old_chain_terminal_present=(chain/'terminal.json').exists(),
    full_hour0_chain_passed=False,full_192_hour_verified=False,
    full_chain_performance_review_complete=False,official_review_verdict=None,
    formal_execution_ready=False,formal_result=False,resource_admission=False,
    native_execution_authorized=False,
    files_sha256={path.relative_to(REPO).as_posix():digest(path) for path in (
        Path(__file__),OUTER/'request.json',OUTER/'started.json',OUTER/'terminal.json',
        HERE/'common_slice_plan_04.json',HERE/'python_sampler_entry_preseal_summary_01.json',
        out/'timing.jsonl',out/'pytest.log',out/'stack_samples.jsonl')})
with (out/'postcheck.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(dict(output=str(out/'postcheck.json'),status=status,
    child_exit_code=terminal['exit_code'],stop_reason=terminal['stop_reason'],
    stage_labels=[row['label'] for row in timings],stack_samples=len(samples),
    source_files=len(request['source_sha256']),lock_files=len(locks))),flush=True)
