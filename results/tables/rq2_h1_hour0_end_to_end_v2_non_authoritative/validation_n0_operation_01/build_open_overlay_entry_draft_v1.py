"""Build isolated entry12: Path.open overlay around entry11's sole byte owner."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'validation_path_optimization_01'
OLD, NEW = BASE/'entry_revision_11_non_authoritative', BASE/'entry_revision_12_non_authoritative'


def pin(path): return sha256(path.read_bytes()).hexdigest()
def save(path, value): path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def replace_once(text, old, new):
    if text.count(old) != 1: raise ValueError('exact entry insertion point required: '+old)
    return text.replace(old, new, 1)


NEW.mkdir(exist_ok=True)
for path in OLD.iterdir():
    if path.is_file() and path.name not in ('launch_validation.py', 'package_manifest_v1.json'):
        (NEW/path.name).write_bytes(path.read_bytes())
(NEW/'entry11_package_manifest.json').write_bytes((OLD/'package_manifest_v1.json').read_bytes())
for name in ('bounded_stable_read_overlay_v1.py', 'test_bounded_stable_read_overlay_v1.py'):
    (NEW/name).write_bytes((HERE/name).read_bytes())
entry = (OLD/'validation_entry.py').read_text(encoding='utf-8').replace('entry11', 'entry12').replace('h1_wf11_', 'h1_wf12_')
entry = entry.replace('h1_pinned_distribution_entry_draft_v1', 'h1_bounded_open_overlay_entry_draft_v1')
entry = replace_once(entry, 'global DistributionOperation,', 'global open_overlay,open_install,DistributionOperation,')
entry = replace_once(entry,
    "    StaticScientificInputReadLease=load_module('performance.static_scientific_input_read_lease_v2',",
    "    OpenOverlay=load_module('performance.bounded_stable_read_overlay_v1','bounded_stable_read_overlay_v1.py').operation\n"
    "    if kind=='pytest':\n"
    "        open_overlay=OpenOverlay(root=REPO)\n"
    "        open_install=open_overlay.install()\n"
    "        open_install.__enter__()\n"
    "    StaticScientificInputReadLease=load_module('performance.static_scientific_input_read_lease_v2',")
entry = replace_once(entry, 'distribution_reader=None', 'open_overlay=None\nopen_install=None\nentry_error=None\ndistribution_reader=None')
entry = replace_once(entry, "            distribution_helper_sha256=sha256(sources['pinned_distribution_resolver_v1.py']).hexdigest(),",
    "            distribution_helper_sha256=sha256(sources['pinned_distribution_resolver_v1.py']).hexdigest(),\n"
    "            bounded_open_overlay_enabled=(kind=='pytest'),\n"
    "            bounded_open_overlay_helper_sha256=sha256(sources['bounded_stable_read_overlay_v1.py']).hexdigest(),\n"
    "            bounded_open_raw_source_sha256='df59ba543655307f0aae369bebf85e46d5ed94a3525f1a7f72f718fe744b598a',\n"
    "            bounded_open_scope='global Path.open wrapper; exact canonical raw caller only',\n"
    "            bounded_open_read_length='cap+1 -> observed_before_size+1',\n"
    "            bounded_open_preserves_fresh_stat_open_fstat_read_fstat_path_observations=True,\n"
    "            bounded_open_creates_second_byte_owner=False,\n"
    "            bounded_open_tracks_transient_original_streams=True,\n"
    "            bounded_open_audit_hook_transparency_proven=False,\n"
    "            bounded_open_per_site_IO_failure_order_preserved=False,")
entry = replace_once(entry, '    code=stack.enter_context(byte_lease) if byte_lease is not None else None',
    '    if open_overlay is not None:open_overlay.adopt(byte_lease)\n'
    '    code=stack.enter_context(byte_lease) if byte_lease is not None else None\n'
    '    if open_overlay is not None:stack.enter_context(open_overlay.bind(code))')
entry = replace_once(entry, "'test_pinned_distribution_resolver_v1.py'):",
    "'test_pinned_distribution_resolver_v1.py','test_bounded_stable_read_overlay_v1.py'):")
entry = replace_once(entry, "    save('distribution_resolver_unit_evidence.json',",
    "    save('bounded_open_overlay_unit_evidence.json',sys.modules['performance.test_bounded_stable_read_overlay_v1'].UNIT_EVIDENCE)\n"
    "    save('distribution_resolver_unit_evidence.json',")
entry = replace_once(entry, "except BaseException:\n    result.update(exit_code=1,error=traceback.format_exc())",
    "except BaseException as error:\n    entry_error=error\n    result.update(exit_code=1,error=traceback.format_exc())")
# -I has not admitted repository imports at the original helper-load point.
# Configure the existing path policy and snapshot code first; then preload raw
# and install open before the static module captures its definition-time hooks.
start = entry.index("    OpenOverlay=load_module(")
end = entry.index("    path_lease=None", start)
module_block = entry[start:end]
entry = entry[:start]+entry[end:]
entry = replace_once(entry, '    interpreter_policy.configure()\n',
    '    interpreter_policy.configure()\n'+module_block)
entry = replace_once(entry, "    result['elapsed_seconds']=perf_counter()-start",
    "    if open_install is not None:\n"
    "        try:\n"
    "            open_install.__exit__(type(entry_error) if entry_error is not None else None,entry_error,\n"
    "                entry_error.__traceback__ if entry_error is not None else None)\n"
    "        except BaseException:result.update(exit_code=1,open_overlay_error=traceback.format_exc())\n"
    "        try:\n"
    "            opened=open_overlay.closed_receipt()\n"
    "            save('bounded_open_overlay_closed_receipt.json',opened)\n"
    "            if (opened['first_failure'] is not None or opened['cleanup_errors']\n"
    "                    or not opened['eligible_for_canonical_entry_clean'] or not opened['canonical_IO_dependencies']\n"
    "                    or opened['schema']!='h1_bounded_stable_read_overlay_draft_v1'\n"
    "                    or opened['implementation']!=sha256(sources['bounded_stable_read_overlay_v1.py']).hexdigest()\n"
    "                    or opened['raw_source_sha256']!='df59ba543655307f0aae369bebf85e46d5ed94a3525f1a7f72f718fe744b598a'\n"
    "                    or opened['raw_source_path']!=str(REPO/'experiments/h1_raw_ingress_development_v1.py')\n"
    "                    or opened['original_read_calls']!=opened['bounded_read_calls']\n"
    "                    or not opened['original_open_restored'] or not opened['original_read_bytes_restored']\n"
    "                    or opened['remaining_streams'] or opened['bounded_read_calls']<=0):\n"
    "                result.update(exit_code=1,open_overlay_clean=False)\n"
    "            else:result['open_overlay_clean']=True\n"
    "            result['bounded_open_observation']=dict(helper_sha256=opened['implementation'],\n"
    "                raw_source_sha256=opened['raw_source_sha256'],calls=opened['original_read_calls'],\n"
    "                hits=opened['bounded_read_calls'],raw_fallback=opened['raw_fallback_opens'],\n"
    "                requested_bytes=opened['original_requested_bytes'],bounded_requested_bytes=opened['bounded_requested_bytes'])\n"
    "        except BaseException:result.update(exit_code=1,open_overlay_receipt_error=traceback.format_exc())\n"
    "    result['elapsed_seconds']=perf_counter()-start")
# Restore the outer hook before any final report/hash/settings operation can
# fail. All byte/static-runtime consumers have already closed in pytest_tests.
close_start = entry.index('    if open_install is not None:\n', entry.index('finally:\n    if interpreter_policy'))
close_end = entry.index("    result['elapsed_seconds']=", close_start)
close_block = entry[close_start:close_end]
entry = entry[:close_start]+entry[close_end:]
entry = replace_once(entry, 'finally:\n    if interpreter_policy is not None:',
    'finally:\n'+close_block+'    if interpreter_policy is not None:')
compile(entry, str(NEW/'validation_entry.py'), 'exec')
(NEW/'validation_entry.py').write_text(entry, encoding='utf-8')
failure = (OLD/'test_validation_entry.py').read_text(encoding='utf-8')
failure = replace_once(failure, "names=('pinned_distribution_resolver_v1.py',",
    "names=('bounded_stable_read_overlay_v1.py','test_bounded_stable_read_overlay_v1.py','pinned_distribution_resolver_v1.py',")
failure = replace_once(failure, "            sys.argv=['entry',kind,mode,'failure',*targets]",
    "            for key in modules:sys.modules.pop(key,None)\n"
    "            sys.argv=['entry',kind,mode,'failure',*targets]")
(NEW/'test_validation_entry.py').write_text(failure, encoding='utf-8')
for filename in ('test_static_scientific_input_read_lease_v2.py',):
    (NEW/filename).write_text((NEW/filename).read_text(encoding='utf-8').replace('entry11','entry12'), encoding='utf-8')
members = {p.name: pin(p) for p in sorted(NEW.iterdir()) if p.is_file() and p.name not in ('launch_validation.py','package_manifest_v1.json')}
save(NEW/'package_manifest_v1.json',dict(schema='h1_bounded_open_overlay_entry_draft_v1',files_sha256=members,
    predecessor_entry11_manifest_sha256=pin(OLD/'package_manifest_v1.json'),status='DRAFT_NONAUTHORITATIVE',
    production_seal=False,formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False))
launcher = re.sub("MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+pin(NEW/'package_manifest_v1.json')+"'",
    (OLD/'launch_validation.py').read_text(encoding='utf-8'))
(NEW/'launch_validation.py').write_text(launcher,encoding='utf-8')
runner = (HERE/'run_workflow_entry_bounded_v5.py').read_text(encoding='utf-8').replace('entry_revision_11_non_authoritative','entry_revision_12_non_authoritative').replace('h1_wf11_','h1_wf12_')
(HERE/'run_workflow_entry_bounded_v6.py').write_text(runner,encoding='utf-8')
print(json.dumps(dict(entry=str(NEW),manifest_sha256=pin(NEW/'package_manifest_v1.json'),production_seal=False)))
