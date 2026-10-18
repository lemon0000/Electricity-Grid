"""Read-only forensic closure of cold04's cap; never adopts journal suffixes."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
plan_path = HERE / 'fresh_n0_plan_04.json'
plan = json.loads(plan_path.read_bytes())
outer, inner, saved = (Path(plan[k]) for k in ('outer_output', 'inner_output', 'basetemp'))
out = HERE / 'fresh_n0_cap_postcheck_04_non_authoritative'
out.mkdir(exist_ok=False)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


terminal = json.loads((outer / 'terminal.json').read_bytes())
assert terminal['exit_code'] == 1 and terminal['stop_reason'] == 'wall'
assert terminal['source_unchanged'] and terminal['old_chain_unchanged'] and not terminal['errors']
assert terminal['observed_owned_processes_absent']
for row in terminal['observed_owned_processes']:
    try:
        process = psutil.Process(row['pid'])
        assert process.create_time() != row['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:
        pass
for path, pin in {**plan['source_sha256'], **plan['old_chain_sha256']}.items():
    assert digest(Path(path)) == pin
for name, pin in plan['source_sha256'].items():
    path = Path(name)
    relative = path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor') / path.relative_to(Path('D:/'))
    assert digest(outer / 'tested_bytes' / relative) == pin
for name in plan['code_lease_sha256']:
    with Path(name).open('r+b'):
        pass
pins = {str(p): digest(p) for p in saved.rglob('*') if p.is_file()}
locks = []
for path in sorted(saved.rglob('*.lock')):
    with path.open('r+b', buffering=0) as stream:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            locks.append(str(path))
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
assert len(locks) == 10
assert pins == {str(p): digest(p) for p in saved.rglob('*') if p.is_file()}
job_path, = saved.glob('nt_non_authoritative/episodes/*/controller_non_authoritative/job_000_non_authoritative/observation.json')
job = json.loads(job_path.read_bytes())
assert job['exit_code'] == 0 and job['whole_job_quiescent']
journals = {}
for label, pattern, count in (
        ('global', 'nt_non_authoritative/global_claims_non_authoritative', 3),
        ('bootstrap', 'nt_non_authoritative/episodes/*/bootstrap_non_authoritative', 5)):
    root, = saved.glob(pattern)
    rows = [json.loads(p.read_bytes()) for p in sorted(root.glob('[0-9]' * 20 + '.json'))]
    assert len(rows) == count
    journals[label] = dict(root=str(root), rows=count, last_persisted_record=rows[-1],
        rows_are_not_retained_head_credentials=True)
timing_path, = saved.glob('test_cold_owned_n0_registratio*/n0_timing.jsonl')
timing = [json.loads(line) for line in timing_path.read_text().splitlines()]
assert [r['stage'] for r in timing] == ['static_successor_imported', 'owner_open']
missing = ['n0_registry_execution_receipt.json', 'n0_retained_heads.json', 'n0_registration_report.json']
assert all(not list(saved.rglob(name)) for name in missing)
assert not (inner / 'terminal.json').exists() and not (inner / 'bounded_closed_receipt.json').exists()
value = dict(status='DRAFT_NONAUTHORITATIVE', postcheck_exit_code=0, cold_run_passed=False,
    plan_sha256=digest(plan_path), monitor_terminal_sha256=digest(outer / 'terminal.json'),
    postcheck_script_sha256=digest(Path(__file__)), sources_and_tested_bytes=len(plan['source_sha256']),
    old_chain_pins_unchanged=len(plan['old_chain_sha256']),
    code_paths_reopened_for_write_without_writing=len(plan['code_lease_sha256']),
    observed_owned_processes_absent=True, real_locks_reacquired_and_released=locks,
    preserved_files_sha256=pins, job_observation_path=str(job_path), job_observation=job,
    persisted_journals=journals, observed_test_timing=timing, missing_acceptance_artifacts=missing,
    graceful_inner_hook_restoration_not_observed=True,
    completed_n0_registration_and_oracle=False, full_hour0_chain_passed=False,
    whole_workflow_performance_review_complete=False, resource_admission=False,
    formal_result=False, native_execution_authorized=False)
with (out / 'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps({k: value[k] for k in ('postcheck_exit_code', 'cold_run_passed', 'sources_and_tested_bytes',
    'code_paths_reopened_for_write_without_writing', 'observed_owned_processes_absent',
    'completed_n0_registration_and_oracle')}))
