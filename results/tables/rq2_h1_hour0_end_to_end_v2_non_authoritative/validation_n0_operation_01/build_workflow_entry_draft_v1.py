"""Build/refresh only the unsealed local workflow entry successor.

No production outer, lease or execution authority is created. Do not invoke
while any diagnostic using this draft is active. Each bounded attempt saves
its own exact tested bytes and manifest before importing project modules.
"""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
BASE=HERE.parent/'validation_path_optimization_01'
OLD=BASE/'entry_revision_07'
NEW=BASE/'entry_revision_08_non_authoritative'


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def pin(path):return sha256(path.read_bytes()).hexdigest()


if not NEW.exists():
    NEW.mkdir()
    for path in OLD.iterdir():
        if path.is_file() and path.name not in ('launch_validation.py','package_manifest_v1.json'):
            (NEW/path.name).write_bytes(path.read_bytes())
    (NEW/'entry07_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())

old_codes=json.loads((OLD/'code_allowlist_v3.json').read_bytes())
code_paths={Path(path) for path in old_codes['files_sha256']}
# Include the actual new functional-route dependencies, including retained
# kernel utilities. Existing scopes remain frozen; new files have new pins.
code_paths.update(path for path in (REPO/'experiments').glob('h1_*.py'))
codes={str(path):pin(path) for path in sorted(code_paths)}
save(NEW/'code_allowlist_v3.json',dict(schema='source_read_cache_allowlist_v3',
    purpose='unsealed workflow successor immutable code bytes only',
    files_sha256=codes,formal_result=False))
import re
vendor=(OLD/'vendor_code_policy.py').read_text(encoding='utf-8')
vendor=re.sub("REPOSITORY_ALLOWLIST_SHA='[0-9a-f]{64}'",
    "REPOSITORY_ALLOWLIST_SHA='"+pin(NEW/'code_allowlist_v3.json')+"'",vendor)
(NEW/'vendor_code_policy.py').write_text(vendor,encoding='utf-8')
old_tests=json.loads((OLD/'test_closure_v1.json').read_bytes())
test_paths={REPO/path for path in old_tests['files_sha256']}
test_paths.update((REPO/'tests').glob('*.py'))
save(NEW/'test_closure_v1.json',dict(schema='synthetic_test_closure_v1',formal_result=False,
    files_sha256={path.relative_to(REPO).as_posix():pin(path) for path in sorted(test_paths)}))
n=len(codes)
entry=(OLD/'validation_entry.py').read_text(encoding='utf-8')
entry=entry.replace('repository_code_files=149','repository_code_files='+str(n))
entry=entry.replace('code_lease_files=156','code_lease_files='+str(n+7))
entry=entry.replace('CanonicalPathLease(episode_store,[REPO])',
    "CanonicalPathLease(episode_store,[REPO,Path('D:/h1_wf08_'+label+'_non_authoritative')])")
entry=entry.replace('len(expected)!=149','len(expected)!='+str(n))
entry=entry.replace('149 repository plus seven',str(n)+' repository plus seven')
entry=entry.replace('exact 156-file','exact '+str(n+7)+'-file')
entry=entry.replace("schema='h1_configured_validation_entry_development_v1'",
    "schema='h1_configured_workflow_entry_draft_v1'")
allowed=(
    'tests/test_h1_selector_parent_controller_development_v3.py::test_actual_lifecycle_clears_each_external_boundary_and_binds_plain_receipts',
    'tests/test_h1_selector_parent_controller_development_v3.py',
    'tests/test_h1_selector_source_window_development_v1.py',
    'tests/test_h1_selector_parent_validation_operation_development_v3.py',
    'tests/test_h1_selector_post_negative_validation_development_v2.py',
    'tests/test_h1_common_validation_operation_development_v3.py',
    'tests/test_h1_selector_phase_handoff_development_v5.py',
    'tests/test_h1_repair_cap_normalization_operation_development_v1.py',
    'tests/test_h1_common_genesis_validation_operation_development_v1.py',
    'tests/test_h1_genesis_consumer_operation_development_v1.py',
    'tests/test_h1_genesis_consumer_operation_development_v1.py::test_three_actual_parents_commit_close_and_reopen_saved_phase',
)
begin=entry.index('    allowed={',entry.index('def pytest_tests():'))
end=entry.index('    if not targets',begin)
entry=entry[:begin]+'    allowed='+repr(allowed)+'\n'+entry[end:]
entry=entry.replace("basetemp=out/'pytest_temp_non_authoritative'",
    "basetemp=Path('D:/h1_wf08_'+label+'_non_authoritative')\n"
    "    if basetemp.exists():raise ValueError('unused short diagnostic root required')")
begin=entry.index('                    diagnostic=targets in (')
end=entry.index('                    selected_plugins=',begin)
entry=entry[:begin]+'                    diagnostic=True\n'+entry[end:]
entry=entry.replace('def lease_context(stack):\n',
    'normalization_reader=None\n\n\ndef lease_context(stack):\n')
entry=entry.replace('global path_lease,CanonicalPathLease',
    'global path_lease,CanonicalPathLease,normalization_reader')
entry=entry.replace('    return code,parsed\n',
    "    from experiments import h1_origin_grid_step_development_v1 as physical\n"
    "    from experiments import h1_repair_cap_normalization_operation_development_v1 as normalization\n"
    "    expected_physical=REPO/'experiments/h1_origin_grid_step_development_v1.py'\n"
    "    if (physical.__name__!='experiments.h1_origin_grid_step_development_v1'\n"
    "            or Path(physical.__file__)!=expected_physical\n"
    "            or physical.__spec__.origin!=str(expected_physical)\n"
    "            or physical.repair_mechanism_identity.__code__.co_filename!=str(expected_physical)):\n"
    "        raise ValueError('fixed physical normalization provenance required')\n"
    "    normalization_scope,normalization_reader=normalization.operation(physical)\n"
    "    stack.enter_context(normalization_scope)\n"
    "    result['normalization_scope_requires_process_exit']=True\n"
    "    return code,parsed\n",1)
entry=entry.replace("        save('call_counts.json',",
    "        if normalization_reader is not None:\n"
    "            normalized=normalization_reader()\n"
    "            save('repair_normalization_closed_receipt.json',normalized)\n"
    "            if (not normalized['all_normalization_cache_entries_cleared']\n"
    "                    or not normalized['original_alias_restored']\n"
    "                    or normalized['first_failure'] is not None or normalized['cleanup_error'] is not None):\n"
    "                raise ValueError('repair normalization did not close cleanly')\n"
    "            result['post_scope_consumer_reuse_allowed']=False\n"
    "        save('call_counts.json',")
# The ordinary lifecycle smoke is a zero-Job, zero-native unit test. Retain
# the original whole-invocation read, path, metadata and interpreter policies.
(NEW/'validation_entry.py').write_text(entry,encoding='utf-8')
failure_tests=(OLD/'test_validation_entry.py').read_text(encoding='utf-8')
failure_tests=failure_tests.replace('tests/test_h1_hour0_routing_development_v2.py',
    'tests/test_h1_selector_source_window_development_v1.py')
failure_tests=failure_tests.replace('            before=(sys.pycache_prefix',
    '            import_environment=(list(sys.meta_path),list(sys.path_hooks),dict(sys.path_importer_cache))\n'
    '            before=(sys.pycache_prefix')
failure_tests=failure_tests.replace('                sys.modules.update(modules)',
    '                sys.modules.update(modules)\n'
    '                sys.meta_path[:]=import_environment[0];sys.path_hooks[:]=import_environment[1]\n'
    '                sys.path_importer_cache.clear();sys.path_importer_cache.update(import_environment[2])')
(NEW/'test_validation_entry.py').write_text(failure_tests,encoding='utf-8')
members={path.name:pin(path) for path in sorted(NEW.iterdir())
    if path.is_file() and path.name not in ('launch_validation.py','package_manifest_v1.json')}
save(NEW/'package_manifest_v1.json',dict(schema='h1_configured_workflow_entry_draft_v1',
    files_sha256=members,status='DRAFT_NONAUTHORITATIVE',production_seal=False,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False))
launcher=(OLD/'launch_validation.py').read_text(encoding='utf-8')
old_pin=json.loads((OLD/'package_manifest_v1.json').read_bytes())
launcher=re.sub("MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'",launcher)
(NEW/'launch_validation.py').write_text(launcher,encoding='utf-8')
print(json.dumps(dict(entry=str(NEW),code_files=n,test_files=len(test_paths),
    package_sha256=pin(NEW/'package_manifest_v1.json'),production_seal=False)))
