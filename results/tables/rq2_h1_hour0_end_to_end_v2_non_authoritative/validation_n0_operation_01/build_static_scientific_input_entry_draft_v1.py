"""Build entry09 draft; retain entry08 and each attempt's immutable evidence."""
from hashlib import sha256
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = HERE.parent/'validation_path_optimization_01'
OLD = BASE/'entry_revision_08_non_authoritative'
NEW = BASE/'entry_revision_09_non_authoritative'


def pin(path):
    return sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


NEW.mkdir(exist_ok=True)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('launch_validation.py', 'package_manifest_v1.json'):
        (NEW/path.name).write_bytes(path.read_bytes())
(NEW/'entry08_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())
for name in ('static_scientific_input_read_lease_v2.py', 'test_static_scientific_input_read_lease_v2.py'):
    (NEW/name).write_bytes((HERE/name).read_bytes())

inputs = {}
for relative, expected, size in (
    ('results/tables/rq2_h1_outage_registry_v1_non_authoritative/scientific_development_authority.json',
     '45710f18fcf98113d53c50cd74e0dfc311ad3e03cfb8ab8f75b01dc2720de0a8', 888),
    ('results/tables/rq2_h1_outage_origin_replay_v1_non_authoritative/repair_cap_proposal.json',
     '6435c85b6cc99d243077bd014b1f52cc90427270a4c50cb26a67fb7e34edf031', 23475),
):
    path = REPO/relative
    if pin(path) != expected or path.stat().st_size != size:
        raise ValueError('fixed scientific input differs: '+str(path))
    inputs[str(path)] = dict(sha256=expected, size_bytes=size)
save(NEW/'scientific_input_allowlist_v1.json', dict(
    schema='h1_static_scientific_input_byte_allowlist_draft_v1',
    files=inputs, static_scientific_input_bytes_cached=True,
    repair_cap_table_bytes_cached=True, formal_result=False))

entry = (OLD/'validation_entry.py').read_text(encoding='utf-8')
entry = entry.replace("'h1_configured_workflow_entry_draft_v1'", "'h1_static_scientific_input_entry_draft_v2'")
entry = entry.replace('h1_wf08_', 'h1_wf09_')
entry = entry.replace('import json\n', 'import json\nimport marshal\n', 1)
entry = entry.replace("assert kind in ('arm','phase','unit','pytest') and mode in ('plain','leased','parse','parse_path')",
    "if (kind,mode) not in (('unit','parse'),('pytest','parse_path')):\n"
    "    raise ValueError('entry09 supports only unit/parse or pytest/parse_path')")
entry = entry.replace('global CodeReadLease,', 'global StaticScientificInputReadLease,scientific_expected,CodeReadLease,')
entry = entry.replace('            stock_metadata_finder_unchanged=True,',
    "            static_scientific_input_bytes_cached=(kind=='pytest' and mode=='parse_path'),\n"
    "            repair_cap_table_bytes_cached=(kind=='pytest' and mode=='parse_path'),\n"
    "            byte_cache_scope='whole pytest invocation' if kind=='pytest' else 'explicit unit-case leases only',\n"
    "            runtime_validation_schedule='light_on_code_hit; full_on_scientific_hit_and_lifecycle_checkpoint',\n"
    "            raw_archive_or_source_rows_cached=False,\n"
    "            static_input_byte_lease_sha256=sha256(sources['static_scientific_input_read_lease_v2.py']).hexdigest(),\n"
    "            static_input_allowlist_sha256=sha256(sources['scientific_input_allowlist_v1.json']).hexdigest(),\n"
    "            scientific_inputs=json.loads(sources['scientific_input_allowlist_v1.json'])['files'],\n"
    "            stock_metadata_finder_unchanged=True,")
entry = entry.replace("    MetadataParseLease=load_module(",
    "    StaticScientificInputReadLease=load_module('performance.static_scientific_input_read_lease_v2',\n"
    "        'static_scientific_input_read_lease_v2.py').StaticScientificInputReadLease\n"
    "    scientific_expected=json.loads(sources['scientific_input_allowlist_v1.json'],object_pairs_hook=no_duplicate_keys)['files']\n"
    "    if scientific_expected!=load_module_scientific_inputs(REPO):raise ValueError('exact scientific input allowlist required')\n"
    "    MetadataParseLease=load_module(")
# The helper is already a pinned package member, not imported from working code.
entry = entry.replace("    if scientific_expected!=load_module_scientific_inputs(REPO):",
    "    if scientific_expected!=sys.modules['performance.static_scientific_input_read_lease_v2'].scientific_inputs(REPO):")
entry = entry.replace('normalization_reader=None', 'normalization_reader=None\nbyte_lease=None')
entry = entry.replace('global path_lease,CanonicalPathLease,normalization_reader',
    'global path_lease,CanonicalPathLease,normalization_reader,byte_lease')
entry = entry.replace("    code=stack.enter_context(CodeReadLease(expected,root=Path('D:/'))) if mode!='plain' else None",
    "    byte_lease=StaticScientificInputReadLease(expected,scientific_expected,root=REPO,code_root=Path('D:/')) if mode!='plain' else None\n"
    "    code=stack.enter_context(byte_lease) if byte_lease is not None else None", 1)
entry = entry.replace("        if receipt['files_sha256']!={str(path):pin for path,pin in expected.items()}:",
    "        expected_byte_pins={str(path):pin for path,pin in expected.items()}\n"
    "        expected_byte_pins.update({p:row['sha256'] for p,row in scientific_expected.items()})\n"
    "        if receipt['files_sha256']!=expected_byte_pins:")
entry = entry.replace('exact 256-file code lease receipt', 'exact 256-code plus two scientific input byte lease receipt')
entry = entry.replace("'test_vendor_code_policy.py'):",
    "'test_vendor_code_policy.py','test_static_scientific_input_read_lease_v2.py'):")
entry = entry.replace('    normalization_scope,normalization_reader=normalization.operation(physical)',
    "    registry=physical.registry\n"
    "    registry_path=REPO/'experiments/h1_outage_registry_development_v1.py'\n"
    "    original_pin=registry._pin\n"
    "    original_code=next(c for c in compile(registry_path.read_bytes(),str(registry_path),'exec').co_consts\n"
    "        if isinstance(c,type(original_pin.__code__)) and c.co_name=='_pin')\n"
    "    if (registry.__name__!='experiments.h1_outage_registry_development_v1'\n"
    "            or registry.__file__!=str(registry_path) or registry.__spec__.origin!=str(registry_path)\n"
    "            or registry.ROOT!=REPO or original_pin.__globals__ is not vars(registry)\n"
    "            or original_pin.__defaults__ is not None or original_pin.__kwdefaults__ is not None\n"
    "            or original_pin.__closure__ is not None\n"
    "            or marshal.dumps(original_pin.__code__)!=marshal.dumps(original_code)):\n"
    "        raise ValueError('canonical registry and source-authored original _pin required')\n"
    "    authority_path=REPO/'results/tables/rq2_h1_outage_registry_v1_non_authoritative/scientific_development_authority.json'\n"
    "    if registry.AUTHORITY!=authority_path:raise ValueError('canonical authority path required')\n"
    "    authority=json.loads(original_pin(authority_path,registry.AUTHORITY_SHA))\n"
    "    table_path=REPO/authority['cap_table_path']\n"
    "    actual_inputs={str(authority_path):dict(sha256=registry.AUTHORITY_SHA,size_bytes=len(authority_path.read_bytes())),\n"
    "        str(table_path):dict(sha256=authority['cap_table_sha256'],size_bytes=len(original_pin(table_path,authority['cap_table_sha256'])))}\n"
    "    if actual_inputs!=scientific_expected:raise ValueError('canonical two-input registry cross-link required')\n"
    "    result['scientific_input_caller_binding']=dict(registry_path=str(registry_path),\n"
    "        original_pin_code_sha256=sha256(marshal.dumps(original_code)).hexdigest(),\n"
    "        registry_implementation_identity=registry.implementation_identity(),\n"
    "        static_input_paths_bound=True,source_authored_pin_hash_body_verified=True)\n"
    "    normalization_scope,normalization_reader=normalization.operation(physical)")
entry = entry.replace("        receipt['vendor_module_origins']=",
    "        if any(receipt['hits_by_path'].get(os.path.normcase(p),0)<=0 for p in scientific_expected):\n"
    "            raise ValueError('both canonical scientific inputs must actually use held bytes')\n"
    "        receipt['vendor_module_origins']=")
entry = entry.replace('    result.update(tests_run=run.testsRun,',
    "    save('static_input_byte_lease_unit_evidence.json',sys.modules['performance.test_static_scientific_input_read_lease_v2'].UNIT_EVIDENCE)\n"
    "    result.update(tests_run=run.testsRun,")
entry = entry.replace("        if normalization_reader is not None:",
    "        if byte_lease is not None:\n"
    "            closed=byte_lease.closed_receipt()\n"
    "            save('static_input_byte_lease_closed_receipt.json',closed)\n"
    "            if (not closed['all_handles_closed'] or not closed['original_alias_restored']\n"
    "                    or not closed['exit_files_and_ancestors_verified']\n"
    "                    or closed['first_failure'] is not None or closed['cleanup_errors']):\n"
    "                cleanup_failures.append(ValueError('static scientific input byte lease did not close cleanly'))\n"
    "        if normalization_reader is not None:")
entry = entry.replace('    finally:\n        sys.setprofile(previous_profile)\n',
    '    finally:\n        primary_error=sys.exc_info()[1]\n        cleanup_failures=[]\n        sys.setprofile(previous_profile)\n')
entry = entry.replace("                raise ValueError('repair normalization did not close cleanly')",
    "                cleanup_failures.append(ValueError('repair normalization did not close cleanly'))")
entry = entry.replace("            result['post_scope_consumer_reuse_allowed']=False",
    "            if byte_lease is not None:\n"
    "                closed=byte_lease.closed_receipt()\n"
    "                oracles=normalized['original_oracle_invocations']\n"
    "                minimum_pin_reads=normalized['adapter_pin_reads']+(oracles['entry']+oracles['exit'])*normalized['oracle_pin_reads_per_successful_invocation']\n"
    "                if (minimum_pin_reads%2 or any(closed['hits_by_path'].get(os.path.normcase(p),0)<minimum_pin_reads//2\n"
    "                        for p in scientific_expected)):\n"
    "                    cleanup_failures.append(ValueError('held input hits do not cover verified normalizer pin schedule'))\n"
    "                save('scientific_input_caller_execution.json',dict(\n"
    "                    **result.get('scientific_input_caller_binding',{}),\n"
    "                    normalizer_calls=normalized['calls'],normalizer_original_pin_reads=minimum_pin_reads,\n"
    "                    static_input_hits=closed['scientific_input_read_hits'],\n"
    "                    scope='normalizer original pin body and minimum counts; other caller counts not attributed',\n"
    "                    bytes_transport_identity_separate_from_scientific_identity=True,formal_result=False))\n"
    "            result['post_scope_consumer_reuse_allowed']=False")
entry = entry.replace("        result['pytest_environment_restored']=all(os.environ.get(k)==v for k,v in previous_pytest_environment.items())",
    "        result['pytest_environment_restored']=all(os.environ.get(k)==v for k,v in previous_pytest_environment.items())\n"
    "        if cleanup_failures:\n"
    "            if primary_error is not None:\n"
    "                for failure in cleanup_failures:primary_error.add_note(repr(failure))\n"
    "            else:raise cleanup_failures[0]")
entry = entry.replace("original common._arm; original numerical and fresh source checks",
    "original common._arm and numerical checks; two named immutable scientific inputs use held bytes")
begin = entry.index('def saved_arm():')
end = entry.index('def unit_tests():', begin)
entry = entry[:begin]+entry[end:]
entry = entry.replace("    if kind in ('arm','phase'):saved_arm();result['exit_code']=0\n    elif kind=='unit':",
    "    if kind=='unit':")
(NEW/'validation_entry.py').write_text(entry, encoding='utf-8')
tests = (OLD/'test_validation_entry.py').read_text(encoding='utf-8')
tests = tests.replace("names=('validation_entry.py',", "names=('static_scientific_input_read_lease_v2.py','scientific_input_allowlist_v1.json','validation_entry.py',")
tests = tests.replace("mode='plain'", 'mode=None')
tests = tests.replace('        with tempfile.TemporaryDirectory',
    "        if mode is None:mode='parse_path' if kind=='pytest' else 'parse'\n"
    '        with tempfile.TemporaryDirectory', 1)
tests = tests.replace("kind='pytest',mode='parse'", "kind='pytest',mode='parse_path'")
(NEW/'test_validation_entry.py').write_text(tests, encoding='utf-8')

members = {p.name: pin(p) for p in sorted(NEW.iterdir())
           if p.is_file() and p.name not in ('launch_validation.py', 'package_manifest_v1.json')}
save(NEW/'package_manifest_v1.json', dict(
    schema='h1_static_scientific_input_entry_draft_v2', files_sha256=members,
    predecessor_entry08_manifest_sha256=pin(OLD/'package_manifest_v1.json'),
    static_scientific_input_allowlist_sha256=pin(NEW/'scientific_input_allowlist_v1.json'),
    status='DRAFT_NONAUTHORITATIVE', production_seal=False, formal_result=False,
    formal_execution_ready=False, native_execution_authorized=False, resource_admission=False))
launcher = (OLD/'launch_validation.py').read_text(encoding='utf-8')
launcher = re.sub("MANIFEST_SHA='[0-9a-f]{64}'",
                  "MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'", launcher)
(NEW/'launch_validation.py').write_text(launcher, encoding='utf-8')
runner = (HERE/'run_workflow_entry_bounded_v2.py').read_text(encoding='utf-8')
runner = runner.replace('entry_revision_08_non_authoritative', 'entry_revision_09_non_authoritative').replace('h1_wf08_', 'h1_wf09_')
runner = runner.replace('    vendor_manifest=entry/',
    "    sources.update(Path(name) for name in json.loads((entry/'scientific_input_allowlist_v1.json').read_bytes())['files'])\n"
    "    vendor_manifest=entry/")
(HERE/'run_workflow_entry_bounded_v3.py').write_text(runner, encoding='utf-8')
print(json.dumps(dict(entry=str(NEW), package_sha256=pin(NEW/'package_manifest_v1.json'),
                      scientific_inputs=inputs, production_seal=False)))
