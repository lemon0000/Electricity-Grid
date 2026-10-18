"""Close exact sampler-entry bytes and its completed short invocations."""
from hashlib import sha256
import json
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P = HERE.parent/'validation_path_optimization_01'
ENTRY = P/'entry_revision_06'


def read(path): return json.loads(path.read_bytes())
def digest(path): return sha256(path.read_bytes()).hexdigest()


pins = {}


def bind(path):
    pins[path.relative_to(REPO).as_posix()] = digest(path)


assert digest(ENTRY/'package_manifest_v1.json') == '6c0db76dd3bbcfb8281e69d7ad70cc18caaf7adef4d120c0aebb30bbcedef03d'
for name,pin in read(ENTRY/'package_manifest_v1.json')['files_sha256'].items():
    assert digest(ENTRY/name) == pin
    bind(ENTRY/name)
for name in ('launch_validation.py', 'package_manifest_v1.json'):
    bind(ENTRY/name)
observations = {}
for label,outer_name in (('unit_checks_05','configured_entry_06_unit_monitor_02'),
                         ('sampler_smoke_02','configured_entry_06_sampler_smoke_monitor_02')):
    root = P/outer_name
    request,terminal = read(root/'request.json'),read(root/'terminal.json')
    assert terminal['exit_code'] == 0 and terminal['stop_reason'] is None
    assert terminal['source_unchanged'] and terminal['source_snapshot_complete']
    assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
    assert not terminal['storage_read_errors'] and terminal['final_storage_observation_complete']
    assert not terminal['complete_process_tree_absence_proven']
    assert terminal['observed_storage_bytes'] == sum(path.stat().st_size
        for name in request['storage_roots'] for path in Path(name).rglob('*') if path.is_file())
    for name,pin in request['source_sha256'].items():
        path = Path(name)
        assert digest(path) == pin
        assert digest(root/'tested_bytes'/path.relative_to(REPO)) == pin
    for row in terminal['observed_owned_processes']:
        try:
            process = psutil.Process(row['pid'])
            assert process.create_time() != row['creation_time'] or not process.is_running()
        except psutil.NoSuchProcess:
            pass
    inner = read(ENTRY/label/'terminal.json')
    assert inner['exit_code'] == 0 and inner['candidate_bytes_unchanged']
    assert inner['repository_test_closure_unchanged'] and inner['repository_code_unchanged']
    assert inner['interpreter_settings_restored']
    assert inner['repository_code_file_count'] == 149
    assert inner['repository_test_closure_file_count'] == 614
    if label == 'unit_checks_05':
        assert inner['tests_run'] == 78 and inner['skipped'] == 1
        assert inner['failures'] == inner['errors'] == 0
    else:
        assert inner['pytest_tests_collected'] == 13 and inner['pytest_tests_failed'] == 0
        assert inner['diagnostic_pytest_flags'] == ['-p','no:faulthandler']
        assert inner['diagnostic_faulthandler_plugin_absent']
        assert inner['diagnostic_fatal_handler_enabled_at_configure'] is False
        assert inner['pytest_environment_restored']
        assert len(inner['pytest_test_calls']) == 13
        assert all(row['scope_entered'] and row['scope_exited'] for row in inner['pytest_test_calls'])
    for path in (root/'request.json',root/'terminal.json',root/'started.json',
                 ENTRY/label/'request.json',ENTRY/label/'terminal.json'):
        bind(path)
    observations[label] = dict(outer=terminal,inner_exit_code=0,inner_elapsed_seconds=inner['elapsed_seconds'])

# The monitor's only later change was fresh labels. Retain the tested control flow.
old_monitor = (P/'run_bounded_configured_entry_v5.py').read_text(encoding='utf-8')
new_monitor = (P/'run_bounded_configured_entry_v6.py').read_text(encoding='utf-8')
assert new_monitor == old_monitor.replace('unit_checks_04','unit_checks_05').replace('sampler_smoke_01','sampler_smoke_02')
monitor_test = HERE/'slice_monitor_unit_05'
assert read(monitor_test/'terminal.json')['exit_code'] == 0
assert '15 passed' in (monitor_test/'stdout.log').read_text(encoding='utf-8')
for name,pin in read(monitor_test/'request.json')['source_sha256'].items():
    path = Path(name)
    snapshot = monitor_test/'tested_bytes'/path.relative_to(REPO)
    assert digest(snapshot) == pin
    # The later IO-test seam correction is pinned by the configured smoke.
    if path.name != 'test_h1_gil_stack_observer_development_v1.py':
        assert digest(path) == pin

for path in (Path(__file__), HERE/'python_sampler_entry_plan_02.json',
    HERE/'stack_sampler_churn_pair_01/postcheck_and_erratum_02.json',
    HERE/'common_slice_crash_01/postcheck.json',
    P/'run_bounded_configured_entry_v5.py',P/'run_bounded_configured_entry_v6.py',
    REPO/'tests/h1_gil_stack_observer_development_v1.py',
    REPO/'tests/test_h1_gil_stack_observer_development_v1.py',
    REPO/'tests/test_h1_guarded_common_slice_development_v2.py',
    REPO/'tests/test_h1_common_slice_monitor_development_v2.py',
    monitor_test/'request.json',monitor_test/'terminal.json',monitor_test/'stdout.log',
    ENTRY/'sampler_smoke_02/pytest.log',
    ENTRY/'sampler_smoke_01/terminal.json',ENTRY/'sampler_smoke_01/pytest.log'):
    bind(path)
old = read(HERE.parent/'chain_07/request.json')['before']
assert all(digest(Path(name)) == pin for name,pin in old.items())
assert not Path('D:/h1_cs02_non_authoritative').exists()
result = dict(status='SCOPED_PYTHON_SAMPLER_ENTRY_CHECKS_COMPLETE_PENDING_PRESEAL_REVIEW',
    observations=observations, configured_helper_tests_passed=77,permission_skips=1,
    configured_sampler_tests_passed=13,monitor_tests_passed=15,
    monitor_v6_diff_only_two_fresh_attempt_labels=True,old_chain_inputs_unchanged=len(old),
    failed_smoke_preserved='sampler_smoke_01: output fault injected process-wide Path.open; narrowed to observer-only output constructor',
    source_code_and_test_closure_current=True,
    actual_fresh_numerical_slice_started=False,full_hour0_chain_passed=False,
    full_chain_performance_review_complete=False, official_review_verdict=None,
    formal_execution_ready=False,formal_result=False,resource_admission=False,
    native_execution_authorized=False,files_sha256=pins)
with (HERE/'python_sampler_entry_checks_01.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(dict(output=str(HERE/'python_sampler_entry_checks_01.json'),pins=len(pins),
    configured_helper_passed=77,configured_sampler_passed=13,monitor_passed=15)),flush=True)
