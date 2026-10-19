"""Build entry11 from byte-transport entry09; keep digest-cache branch separate."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = HERE.parent/'validation_path_optimization_01'
OLD = BASE/'entry_revision_09_non_authoritative'
NEW = BASE/'entry_revision_11_non_authoritative'


def pin(p): return sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, indent=2)+'\n', encoding='utf-8')


NEW.mkdir(exist_ok=True)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('launch_validation.py', 'package_manifest_v1.json'):
        (NEW/path.name).write_bytes(path.read_bytes())
(NEW/'entry09_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())
for name in ('pinned_distribution_resolver_v1.py', 'test_pinned_distribution_resolver_v1.py'):
    (NEW/name).write_bytes((HERE/name).read_bytes())

declaration = json.loads((OLD/'code_allowlist_v3.json').read_bytes())
paths = {Path(p) for p in declaration['files_sha256']} | set((REPO/'experiments').glob('h1_*.py'))
save(NEW/'code_allowlist_v3.json', dict(schema='source_read_cache_allowlist_v3',
    files_sha256={str(p): pin(p) for p in sorted(paths)}, formal_result=False))
old_count, new_count = len(declaration['files_sha256']), len(paths)
policy = re.sub("REPOSITORY_ALLOWLIST_SHA='[0-9a-f]{64}'",
    "REPOSITORY_ALLOWLIST_SHA='"+pin(NEW/'code_allowlist_v3.json')+"'",
    (OLD/'vendor_code_policy.py').read_text(encoding='utf-8'))
(NEW/'vendor_code_policy.py').write_text(policy, encoding='utf-8')
closure = json.loads((OLD/'test_closure_v1.json').read_bytes())
tests = {REPO/p for p in closure['files_sha256']} | set((REPO/'tests').glob('*.py'))
save(NEW/'test_closure_v1.json', dict(schema='synthetic_test_closure_v1', formal_result=False,
    files_sha256={p.relative_to(REPO).as_posix(): pin(p) for p in sorted(tests)}))

entry = (OLD/'validation_entry.py').read_text(encoding='utf-8')
entry = entry.replace('entry09 supports', 'entry11 supports').replace('h1_wf09_', 'h1_wf11_')
entry = entry.replace('h1_static_scientific_input_entry_draft_v2', 'h1_pinned_distribution_entry_draft_v1')
entry = entry.replace('global StaticScientificInputReadLease,', 'global DistributionOperation,StaticScientificInputReadLease,')
entry = entry.replace('    path_lease=None',
    "    DistributionOperation=load_module('performance.pinned_distribution_resolver_v1','pinned_distribution_resolver_v1.py').operation\n"
    '    path_lease=None')
entry = entry.replace("            raw_archive_or_source_rows_cached=False,",
    "            raw_archive_or_source_rows_cached=False,\n"
    "            distribution_discovery_cached=(kind=='pytest'),metadata_paths_cached=(kind=='pytest'),\n"
    "            distribution_instances_cached=False,per_call_distribution_discovery_preserved=False,\n"
    "            repair_identity_digest_cached=False,\n"
    "            distribution_helper_sha256=sha256(sources['pinned_distribution_resolver_v1.py']).hexdigest(),")
entry = entry.replace('repository_code_files='+str(old_count), 'repository_code_files='+str(new_count))
entry = entry.replace('code_lease_files='+str(old_count+7), 'code_lease_files='+str(new_count+7))
entry = entry.replace('len(expected)!='+str(old_count), 'len(expected)!='+str(new_count))
entry = entry.replace(str(old_count)+' repository plus seven', str(new_count)+' repository plus seven')
entry = entry.replace('exact 256-code plus two', 'exact '+str(new_count+7)+'-code plus two')
entry = entry.replace('normalization_reader=None', 'distribution_reader=None\nnormalization_reader=None', 1)
entry = entry.replace('global path_lease,CanonicalPathLease,normalization_reader,byte_lease',
    'global path_lease,CanonicalPathLease,normalization_reader,byte_lease,distribution_reader')
entry = entry.replace("    from experiments import h1_origin_grid_step_development_v1 as physical",
    "    distribution_scope,distribution_reader=DistributionOperation(parsed,metadata_expected)\n"
    "    stack.enter_context(distribution_scope)\n"
    "    from experiments import h1_origin_grid_step_development_v1 as physical", 1)
entry = entry.replace("'test_static_scientific_input_read_lease_v2.py'):",
    "'test_static_scientific_input_read_lease_v2.py','test_pinned_distribution_resolver_v1.py'):")
entry = entry.replace("    save('static_input_byte_lease_unit_evidence.json',",
    "    save('distribution_resolver_unit_evidence.json',sys.modules['performance.test_pinned_distribution_resolver_v1'].UNIT_EVIDENCE)\n"
    "    save('static_input_byte_lease_unit_evidence.json',")
entry = entry.replace("        save('call_counts.json',dict(rows=", 
    "        if distribution_reader is not None:\n"
    "            discovered=distribution_reader()\n"
    "            save('distribution_resolver_closed_receipt.json',discovered)\n"
    "            if (not discovered['original_alias_restored'] or not discovered['all_resolver_cached_paths_cleared']\n"
    "                    or discovered['first_failure'] is not None or discovered['cleanup_errors']\n"
    "                    or discovered['original_discovery_oracles']!={'entry':1,'exit':1}\n"
    "                    or set(discovered['selected'] or {})!={'Pyomo','highspy','numpy','scipy','PYPOWER','PyYAML','osqp','gurobipy'}\n"
    "                    or discovered['from_name_calls']!=discovered['fast_path_calls']+discovered['fallback_calls']\n"
    "                    or discovered['fast_path_calls']<=0\n"
    "                    or discovered['fresh_PathDistribution_instances']!=discovered['fast_path_calls']):\n"
    "                cleanup_failures.append(ValueError('distribution resolver did not close cleanly'))\n"
    "            result['distribution_resolver_fast_calls']=discovered['fast_path_calls']\n"
    "            result['distribution_resolver_fallback_calls']=discovered['fallback_calls']\n"
    "        save('call_counts.json',dict(rows=")
compile(entry, str(NEW/'validation_entry.py'), 'exec')
(NEW/'validation_entry.py').write_text(entry, encoding='utf-8')
failure_tests = (OLD/'test_validation_entry.py').read_text(encoding='utf-8')
failure_tests = failure_tests.replace("names=('static_scientific", "names=('pinned_distribution_resolver_v1.py','static_scientific")
(NEW/'test_validation_entry.py').write_text(failure_tests, encoding='utf-8')
old_tests = (OLD/'test_static_scientific_input_read_lease_v2.py').read_text(encoding='utf-8').replace('entry09', 'entry11')
(NEW/'test_static_scientific_input_read_lease_v2.py').write_text(old_tests, encoding='utf-8')
members = {p.name: pin(p) for p in sorted(NEW.iterdir())
           if p.is_file() and p.name not in ('launch_validation.py', 'package_manifest_v1.json')}
save(NEW/'package_manifest_v1.json', dict(schema='h1_pinned_distribution_entry_draft_v1',
    files_sha256=members, predecessor_entry09_manifest_sha256=pin(OLD/'package_manifest_v1.json'),
    unused_digest_cache_branch='entry10 not adopted: no full-parent improvement',
    status='DRAFT_NONAUTHORITATIVE', production_seal=False, formal_result=False,
    formal_execution_ready=False, resource_admission=False, native_execution_authorized=False))
launcher = re.sub("MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'",
                  (OLD/'launch_validation.py').read_text(encoding='utf-8'))
(NEW/'launch_validation.py').write_text(launcher, encoding='utf-8')
runner = (HERE/'run_workflow_entry_bounded_v3.py').read_text(encoding='utf-8')
runner = runner.replace('entry_revision_09_non_authoritative', 'entry_revision_11_non_authoritative').replace('h1_wf09_', 'h1_wf11_')
(HERE/'run_workflow_entry_bounded_v5.py').write_text(runner, encoding='utf-8')
print(json.dumps(dict(entry=str(NEW), code_files=new_count, test_files=len(tests),
    package_sha256=pin(NEW/'package_manifest_v1.json'), production_seal=False)))
