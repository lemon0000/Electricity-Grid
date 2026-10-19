"""Build a fresh non-authoritative entry13 from entry11 and current pinned code."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
BASE=HERE.parent/'validation_path_optimization_01'
OLD=BASE/'entry_revision_11_non_authoritative'
NEW=BASE/'entry_revision_13_non_authoritative'


def pin(path):return sha256(path.read_bytes()).hexdigest()
def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


resuming=sys.argv[1:]==['--resume-incomplete']
if sys.argv[1:] and not resuming:raise ValueError('explicit incomplete-build resume only')
if NEW.exists():
    if not resuming or (NEW/'package_manifest_v1.json').exists() or (NEW/'launch_validation.py').exists():
        raise ValueError('preserve an existing completed candidate')
    expected={p.name for p in OLD.iterdir() if p.is_file()}|{
        'profile_code_counter_v1.py','test_profile_code_counter_v1.py','entry11_predecessor_package_manifest.json'}
    if any(not p.is_file() or p.name not in expected for p in NEW.iterdir()):
        raise ValueError('unexpected incomplete candidate inventory')
for name,key in (('vendor_code_allowlist_v1.json','files_sha256'),
        ('metadata_allowlist_v1.json','files_sha256')):
    for path,expected in json.loads((OLD/name).read_bytes())[key].items():
        if pin(Path(path))!=expected:raise ValueError('environment binding drift: '+path)
science=json.loads((OLD/'scientific_input_allowlist_v1.json').read_bytes())['files']
for path,row in science.items():
    if pin(Path(path))!=row['sha256']:raise ValueError('scientific input binding drift: '+path)

NEW.mkdir(exist_ok=resuming)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('launch_validation.py','package_manifest_v1.json'):
        (NEW/path.name).write_bytes(path.read_bytes())
for name in ('profile_code_counter_v1.py','test_profile_code_counter_v1.py'):
    (NEW/name).write_bytes((HERE/name).read_bytes())
(NEW/'entry11_predecessor_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())
declaration=json.loads((OLD/'code_allowlist_v3.json').read_bytes())
paths={Path(p) for p in declaration['files_sha256']}|set((REPO/'experiments').glob('h1_*.py'))
old_count,new_count=len(declaration['files_sha256']),len(paths)
save(NEW/'code_allowlist_v3.json',dict(schema='source_read_cache_allowlist_v3',
    files_sha256={str(p):pin(p) for p in sorted(paths)},formal_result=False))
policy=re.sub("REPOSITORY_ALLOWLIST_SHA='[0-9a-f]{64}'",
    "REPOSITORY_ALLOWLIST_SHA='"+pin(NEW/'code_allowlist_v3.json')+"'",
    (OLD/'vendor_code_policy.py').read_text(encoding='utf-8'))
(NEW/'vendor_code_policy.py').write_text(policy,encoding='utf-8')
old_tests=json.loads((OLD/'test_closure_v1.json').read_bytes())['files_sha256']
tests={REPO/p for p in old_tests}|set((REPO/'tests').glob('*.py'))
save(NEW/'test_closure_v1.json',dict(schema='synthetic_test_closure_v1',formal_result=False,
    files_sha256={p.relative_to(REPO).as_posix():pin(p) for p in sorted(tests)}))

entry=(OLD/'validation_entry.py').read_text(encoding='utf-8')
entry=entry.replace('entry11','entry13').replace('h1_wf11_','h1_wf13_')
entry=entry.replace('h1_pinned_distribution_entry_draft_v1','h1_shared_reference_workflow_entry_draft_v1')
for before,after in ((f'repository_code_files={old_count}',f'repository_code_files={new_count}'),
        (f'code_lease_files={old_count+7}',f'code_lease_files={new_count+7}'),
        (f'len(expected)!={old_count}',f'len(expected)!={new_count}'),
        (f'{old_count} repository plus seven',f'{new_count} repository plus seven'),
        (f'exact {old_count+7}-code plus two',f'exact {new_count+7}-code plus two')):
    if before not in entry:raise ValueError('entry layout changed: '+before)
    entry=entry.replace(before,after)
routes={
 'h1_selector_source_window_development_v1':'h1_selector_source_window_development_v2',
 'h1_selector_parent_validation_operation_development_v3':'h1_selector_parent_validation_operation_development_v4',
 'h1_selector_post_negative_validation_development_v2':'h1_selector_post_negative_validation_development_v3',
 'h1_common_validation_operation_development_v3':'h1_common_validation_operation_development_v4',
 'h1_selector_phase_handoff_development_v5':'h1_selector_phase_handoff_development_v6',
 'h1_common_genesis_validation_operation_development_v1':'h1_common_genesis_validation_operation_development_v2',
 'h1_genesis_consumer_operation_development_v1':'h1_genesis_consumer_operation_development_v2'}
for before,after in routes.items():entry=entry.replace(before,after)
extra=(
 'tests/test_h1_reference_sequence_window_development_v1.py',
 'tests/test_h1_reference_validation_window_development_v1.py',
 'tests/test_h1_validation_runtime_closure_development_v1.py',
 'tests/test_h1_parent_guard_cleanup_development_v1.py',
 'tests/test_h1_handoff_bundle_cleanup_development_v6.py',
 'tests/test_h1_handoff_runtime_anchor_development_v6.py')
line=next(line for line in entry.splitlines() if line.startswith('    allowed='))
entry=entry.replace(line,line+' + '+repr(extra))
entry=entry.replace("    load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py')",
    "    load_module('performance.profile_code_counter_v1','profile_code_counter_v1.py')\n"
    "    load_module('performance.pytest_lease_plugin','pytest_lease_plugin.py')",1)
entry=entry.replace("'test_pinned_distribution_resolver_v1.py'):",
    "'test_pinned_distribution_resolver_v1.py','test_profile_code_counter_v1.py'):")
start=entry.index('    counted_names=')
end=entry.index('    try:\n',start)
counted=('h1_selector_parent_controller_development_v4.py','h1_selector_phase_handoff_development_v6.py',
    'h1_selector_parent_validation_operation_development_v4.py','h1_selector_post_negative_validation_development_v3.py',
    'h1_reference_sequence_window_development_v1.py','h1_reference_validation_window_development_v1.py',
    'h1_validation_runtime_closure_development_v1.py','h1_common_validation_operation_development_v4.py',
    'h1_common_genesis_validation_operation_development_v2.py','h1_common_owner_genesis_development_v2.py',
    'h1_group_n0_common_input_binding_development_v2.py')
entry=entry[:start]+('    counted_names='+repr(counted)+'\n'
    "    counted_files={os.path.normcase(str(REPO/'experiments'/name)) for name in counted_names}\n"
    "    CounterType=load_module('performance.profile_code_counter_v1','profile_code_counter_v1.py').CodeCallCounter\n"
    '    count_calls=CounterType(counted_files,call_counts,max_codes=100000)\n')+entry[end:]
entry=entry.replace('\n        sys.setprofile(previous_profile)\n',
    "\n        sys.setprofile(previous_profile)\n"
    "        save('profile_code_counter_closed_receipt.json',count_calls.close())\n",1)
compile(entry,str(NEW/'validation_entry.py'),'exec')
(NEW/'validation_entry.py').write_text(entry,encoding='utf-8')
for name in ('test_validation_entry.py','test_static_scientific_input_read_lease_v2.py'):
    text=(NEW/name).read_text(encoding='utf-8').replace('entry11','entry13')
    for before,after in routes.items():text=text.replace(before,after)
    if name=='test_validation_entry.py':
        text=text.replace("names=('pinned_distribution", "names=('profile_code_counter_v1.py','pinned_distribution")
    (NEW/name).write_text(text,encoding='utf-8')
members={p.name:pin(p) for p in sorted(NEW.iterdir()) if p.is_file()}
save(NEW/'package_manifest_v1.json',dict(schema='h1_shared_reference_workflow_entry_draft_v1',
    files_sha256=members,predecessor_entry11_manifest_sha256=pin(OLD/'package_manifest_v1.json'),
    repository_code_files=new_count,test_closure_files=len(tests),
    validation_graph='Parent4/Source2/reference-lifecycle1/shared-reference1/ParentVal4/Post3/Handoff6/Common4/GenesisOp2',
    profile_code_metadata_cache=True,scientific_value_profile_cache=False,
    status='DRAFT_NONAUTHORITATIVE',production_seal=False,official_review=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False))
launcher=re.sub("MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'",
    (OLD/'launch_validation.py').read_text(encoding='utf-8'))
(NEW/'launch_validation.py').write_text(launcher,encoding='utf-8')
runner=(HERE/'run_workflow_entry_bounded_v5.py').read_text(encoding='utf-8')
runner=runner.replace('entry_revision_11_non_authoritative','entry_revision_13_non_authoritative').replace('h1_wf11_','h1_wf13_')
for before,after in routes.items():runner=runner.replace(before,after)
runner=runner.replace('if kind==\'unit\':', 'allowed.update('+repr(extra)+")\nif kind=='unit':",1)
runner=runner.replace("    save('terminal.json', result)",
    "    result['request_sha256']=sha256((out/'request.json').read_bytes()).hexdigest() if (out/'request.json').exists() else None\n"
    "    result['started_sha256']=sha256((out/'started.json').read_bytes()).hexdigest() if (out/'started.json').exists() else None\n"
    "    result['runner_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()\n"
    "    save('terminal.json', result)")
compile(runner,str(HERE/'run_workflow_entry_bounded_v7.py'),'exec')
with (HERE/'run_workflow_entry_bounded_v7.py').open('x',encoding='utf-8') as stream:stream.write(runner)
print(json.dumps(dict(entry=str(NEW),code_files=new_count,test_files=len(tests),
    package_sha256=pin(NEW/'package_manifest_v1.json'),production_seal=False)))
