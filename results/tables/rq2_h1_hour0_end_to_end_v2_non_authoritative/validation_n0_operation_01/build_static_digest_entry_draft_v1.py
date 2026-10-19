"""Build entry10 draft for the explicit static repair-identity borrow.

Do not run while this candidate is active. No production seal, authority,
preflight or native execution is created.
"""
from hashlib import sha256
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = HERE.parent/'validation_path_optimization_01'
OLD = BASE/'entry_revision_09_non_authoritative'
NEW = BASE/'entry_revision_10_non_authoritative'


def pin(path): return sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


NEW.mkdir(exist_ok=True)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('launch_validation.py', 'package_manifest_v1.json'):
        (NEW/path.name).write_bytes(path.read_bytes())
(NEW/'entry09_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())
for name in ('static_input_capability_v1.py', 'test_static_repair_identity_operation_v2.py'):
    (NEW/name).write_bytes((HERE/name).read_bytes())
declaration = json.loads((OLD/'code_allowlist_v3.json').read_bytes())
code_paths = {Path(p) for p in declaration['files_sha256']} | set((REPO/'experiments').glob('h1_*.py'))
codes = {str(p): pin(p) for p in sorted(code_paths)}
save(NEW/'code_allowlist_v3.json', dict(schema='source_read_cache_allowlist_v3',
    purpose='draft code bytes, explicit static input borrow and repair-identity digest reuse',
    files_sha256=codes, formal_result=False))
old_count = len(declaration['files_sha256']); new_count = len(codes)
vendor = (OLD/'vendor_code_policy.py').read_text(encoding='utf-8')
vendor = re.sub("REPOSITORY_ALLOWLIST_SHA='[0-9a-f]{64}'",
    "REPOSITORY_ALLOWLIST_SHA='"+pin(NEW/'code_allowlist_v3.json')+"'", vendor)
(NEW/'vendor_code_policy.py').write_text(vendor, encoding='utf-8')
closure = json.loads((OLD/'test_closure_v1.json').read_bytes())
test_paths = {REPO/p for p in closure['files_sha256']} | set((REPO/'tests').glob('*.py'))
save(NEW/'test_closure_v1.json', dict(schema='synthetic_test_closure_v1', formal_result=False,
    files_sha256={p.relative_to(REPO).as_posix(): pin(p) for p in sorted(test_paths)}))

entry = (OLD/'validation_entry.py').read_text(encoding='utf-8')
entry = entry.replace('entry09 supports', 'entry10 supports').replace('h1_wf09_', 'h1_wf10_')
entry = entry.replace('h1_static_scientific_input_entry_draft_v2', 'h1_static_repair_identity_entry_draft_v1')
entry = entry.replace('global StaticScientificInputReadLease,', 'global CapabilityByteLease,StaticScientificInputReadLease,')
entry = entry.replace("    scientific_expected=json.loads(",
    "    CapabilityByteLease=load_module('performance.static_input_capability_v1','static_input_capability_v1.py').CapabilityByteLease\n"
    "    scientific_expected=json.loads(")
entry = entry.replace('byte_lease=StaticScientificInputReadLease(', 'byte_lease=CapabilityByteLease(')
entry = entry.replace('h1_repair_cap_normalization_operation_development_v1 as normalization',
    'h1_repair_cap_normalization_operation_development_v2 as normalization')
entry = entry.replace('normalization.operation(physical)', 'normalization.operation(physical,byte_lease)')
entry = entry.replace("            raw_archive_or_source_rows_cached=False,",
    "            raw_archive_or_source_rows_cached=False,\n"
    "            repair_identity_digest_cached=(kind=='pytest'),\n"
    "            per_call_pin_sha_digest_preserved=False,failure_timing_preserved=False,\n"
    "            capability_helper_sha256=sha256(sources['static_input_capability_v1.py']).hexdigest(),\n"
    "            normalization_source_sha256=sha256((REPO/'experiments/h1_repair_cap_normalization_operation_development_v2.py').read_bytes()).hexdigest(),")
entry = entry.replace('repository_code_files='+str(old_count), 'repository_code_files='+str(new_count))
entry = entry.replace('code_lease_files='+str(old_count+7), 'code_lease_files='+str(new_count+7))
entry = entry.replace('len(expected)!='+str(old_count), 'len(expected)!='+str(new_count))
entry = entry.replace(str(old_count)+' repository plus seven', str(new_count)+' repository plus seven')
entry = entry.replace('exact 256-code plus two', 'exact '+str(new_count+7)+'-code plus two')
entry = entry.replace("'test_static_scientific_input_read_lease_v2.py'):",
    "'test_static_scientific_input_read_lease_v2.py','test_static_repair_identity_operation_v2.py'):")
entry = entry.replace("    save('static_input_byte_lease_unit_evidence.json',",
    "    save('static_repair_identity_unit_evidence.json',sys.modules['performance.test_static_repair_identity_operation_v2'].UNIT_EVIDENCE)\n"
    "    save('static_input_byte_lease_unit_evidence.json',")
entry = entry.replace("normalized['cleanup_error'] is not None", "bool(normalized['cleanup_errors'])")
entry = entry.replace('    call_counts=Counter()', '    status=None\n    call_counts=Counter()')
entry = entry.replace("minimum_pin_reads=normalized['adapter_pin_reads']+(oracles['entry']+oracles['exit'])*normalized['oracle_pin_reads_per_successful_invocation']",
    "minimum_pin_reads=normalized['original_pin_reads_in_successful_oracles']")
entry = entry.replace("                save('scientific_input_caller_execution.json',dict(",
    "                if (not normalized['capability_released'] or closed['borrow_active']\n"
    "                        or closed['borrow_releases']!=1\n"
    "                        or normalized['per_route_capability_checks']!=2*normalized['calls']):\n"
    "                    cleanup_failures.append(ValueError('repair identity capability lifecycle or route counts differ'))\n"
    "                try:\n"
    "                    joint=sys.modules['performance.static_input_capability_v1'].compose_closed_receipts(\n"
    "                        normalized,closed,execution_success=(status==0 and not cleanup_failures and primary_error is None))\n"
    "                    joint['entry_code_allowlist_sha256']=sha256(sources['code_allowlist_v3.json']).hexdigest()\n"
    "                    joint['entry_scientific_allowlist_sha256']=sha256(sources['scientific_input_allowlist_v1.json']).hexdigest()\n"
    "                    if joint['normalization_implementation']!=sha256((REPO/'experiments/h1_repair_cap_normalization_operation_development_v2.py').read_bytes()).hexdigest():\n"
    "                        raise ValueError('normalization implementation differs from entry binding')\n"
    "                    save('static_repair_joint_closed_evidence.json',joint)\n"
    "                except BaseException as error: cleanup_failures.append(error)\n"
    "                save('scientific_input_caller_execution.json',dict(")
entry = entry.replace('scope=\'normalizer original pin body and minimum counts; other caller counts not attributed\'',
    "scope='entry/exit original pin oracle counts; routed pin/SHA/digest calls are zero; other callers not attributed'")
entry = entry.replace("start=perf_counter();result=dict(kind=kind,mode=mode,formal_result=False,full_chain_passed=False)",
    "start=perf_counter();result=dict(kind=kind,mode=mode,formal_result=False,full_chain_passed=False,\n"
    "    runtime_validation_schedule='light_on_code_hit; full_on_scientific_hit_and_lifecycle_checkpoint',\n"
    "    repair_identity_digest_cached=(kind=='pytest'),per_call_pin_sha_digest_preserved=False,failure_timing_preserved=False)")
compile(entry, str(NEW/'validation_entry.py'), 'exec')
(NEW/'validation_entry.py').write_text(entry, encoding='utf-8')
failure_tests = (OLD/'test_validation_entry.py').read_text(encoding='utf-8')
failure_tests = failure_tests.replace("names=('static_scientific", "names=('static_input_capability_v1.py','static_scientific")
(NEW/'test_validation_entry.py').write_text(failure_tests, encoding='utf-8')
old_tests = (OLD/'test_static_scientific_input_read_lease_v2.py').read_text(encoding='utf-8').replace('entry09', 'entry10')
(NEW/'test_static_scientific_input_read_lease_v2.py').write_text(old_tests, encoding='utf-8')
members = {p.name: pin(p) for p in sorted(NEW.iterdir())
           if p.is_file() and p.name not in ('launch_validation.py', 'package_manifest_v1.json')}
save(NEW/'package_manifest_v1.json', dict(schema='h1_static_repair_identity_entry_draft_v1',
    files_sha256=members, predecessor_entry09_manifest_sha256=pin(OLD/'package_manifest_v1.json'),
    status='DRAFT_NONAUTHORITATIVE', production_seal=False, formal_result=False,
    formal_execution_ready=False, resource_admission=False,native_execution_authorized=False))
launcher = re.sub("MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'",
                  (OLD/'launch_validation.py').read_text(encoding='utf-8'))
(NEW/'launch_validation.py').write_text(launcher, encoding='utf-8')
runner = (HERE/'run_workflow_entry_bounded_v3.py').read_text(encoding='utf-8')
runner = runner.replace('entry_revision_09_non_authoritative', 'entry_revision_10_non_authoritative').replace('h1_wf09_', 'h1_wf10_')
(HERE/'run_workflow_entry_bounded_v4.py').write_text(runner, encoding='utf-8')
print(json.dumps(dict(entry=str(NEW),code_files=new_count,test_files=len(test_paths),
    package_sha256=pin(NEW/'package_manifest_v1.json'), production_seal=False)))
