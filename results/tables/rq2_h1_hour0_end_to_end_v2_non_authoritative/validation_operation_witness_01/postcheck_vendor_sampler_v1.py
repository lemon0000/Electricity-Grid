"""Close actual configured pytest routing for the current vendor-code entry."""
from hashlib import sha256
import json
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
P=HERE.parent/'validation_path_optimization_01';ENTRY=P/'entry_revision_07'
OUT=P/'configured_entry_07_sampler_smoke_monitor_01';INNER=ENTRY/'sampler_smoke_03'
def read(path):return json.loads(path.read_bytes())
def digest(path):return sha256(path.read_bytes()).hexdigest()
request,outer,inner=read(OUT/'request.json'),read(OUT/'terminal.json'),read(INNER/'terminal.json')
assert digest(ENTRY/'package_manifest_v1.json')=='ab0ad89e7efa04c57185dca779a822ea5ae70fc07c0fbb2cd92f2e03360f1925'
assert outer['exit_code']==inner['exit_code']==0 and outer['stop_reason'] is None
assert inner['pytest_tests_collected']==13 and inner['pytest_tests_failed']==0
assert len(inner['pytest_test_calls'])==13 and all(row['scope_entered'] and row['scope_exited'] for row in inner['pytest_test_calls'])
assert inner['diagnostic_pytest_flags']==['-p','no:faulthandler'] and inner['diagnostic_faulthandler_plugin_absent']
assert inner['diagnostic_fatal_handler_enabled_at_configure'] is False
assert all(inner[key] for key in ('candidate_bytes_unchanged','repository_code_unchanged',
    'repository_test_closure_unchanged','vendor_code_unchanged','interpreter_settings_restored','pytest_environment_restored'))
assert inner['repository_code_file_count']==149 and inner['repository_test_closure_file_count']==614 and inner['vendor_code_file_count']==7
assert outer['source_unchanged'] and outer['source_snapshot_complete'] and outer['observed_owned_processes_absent']
assert outer['final_storage_observation_complete'] and not outer['storage_read_errors'] and not outer['cleanup_errors']
assert outer['elapsed_seconds']<60 and outer['peak_observed_process_tree_rss']<512*1024**2
assert outer['observed_storage_bytes']==sum(path.stat().st_size for name in request['storage_roots'] for path in Path(name).rglob('*') if path.is_file())<64*1024**2
for name,pin in request['source_sha256'].items():
    path=Path(name);snapshot=(OUT/'tested_bytes'/path.relative_to(REPO) if path.is_relative_to(REPO)
        else OUT/'tested_bytes/external'/path.drive[:1]/Path(*path.parts[1:]))
    assert digest(path)==pin and digest(snapshot)==pin
for row in outer['observed_owned_processes']:
    try:
        process=psutil.Process(row['pid']);assert process.create_time()!=row['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:pass
receipts=list(INNER.glob('*lease_receipt.json'));assert len(receipts)==14
for path in receipts:
    receipt=read(path);assert receipt['file_count']==156 and len(receipt['vendor_module_origins'])==7
    assert receipt['vendor_module_origins']==inner['vendor_module_origins_at_exit']
old=read(HERE.parent/'chain_07/request.json')['before'];assert all(digest(Path(name))==pin for name,pin in old.items())
paths=[Path(__file__),OUT/'request.json',OUT/'terminal.json',INNER/'request.json',INNER/'terminal.json',
    INNER/'pytest.log',ENTRY/'package_manifest_v1.json',HERE/'vendor_configured_sampler_check_plan_01.json',*receipts]
output=dict(status='CURRENT_ENTRY_CONFIGURED_SAMPLER_UNIT_ROUTING_COMPLETE',tests_passed=13,
    source_and_tested_copies_unchanged=len(request['source_sha256']),observed_owned_processes_absent=True,
    complete_process_tree_absence_proven=False,outer_elapsed_seconds=outer['elapsed_seconds'],
    final_storage_bytes=outer['observed_storage_bytes'],old_chain_inputs_unchanged=36,
    files_sha256={str(path):digest(path) for path in paths},full_hour0_chain_passed=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'vendor_configured_sampler_checks_01.json').open('x',encoding='utf-8') as stream:json.dump(output,stream,indent=2)
print(json.dumps(dict(tests_passed=13,source_and_tested_copies_unchanged=output['source_and_tested_copies_unchanged'],receipts=len(receipts),outer_elapsed_seconds=outer['elapsed_seconds'])),flush=True)
