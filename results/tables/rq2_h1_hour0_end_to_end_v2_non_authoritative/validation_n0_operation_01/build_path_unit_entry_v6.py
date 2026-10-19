"""Compose entry4 with the unchanged canonical path helper; no fixture scopes."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE/'run_unit_entry_v4.py').read_text(encoding='utf-8')
source = source.replace("base=Path(sys.argv[sys.argv.index('--basetemp')+1])", """base=Path(sys.argv[sys.argv.index('--basetemp')+1])
path_roots=[REPO,base]
if '--canonical-path-root' in sys.argv:
    index=sys.argv.index('--canonical-path-root')
    extra=Path(sys.argv[index+1])
    if (not extra.is_absolute() or '..' in extra.parts or not extra.name.endswith('_non_authoritative')):
        raise ValueError('explicit absolute non-authoritative path root required')
    path_roots.append(extra)
    del sys.argv[index:index+2]
from experiments import h1_canonical_path_lease_development_v1 as canonical
from src.rq2_joint_deliverability_boundary_v1 import episode_store as store
original_path=store._path
""")
source = source.replace("    parsed=stack.enter_context", "    path_lease=stack.enter_context(canonical.CanonicalPathLease(store,path_roots))\n    parsed=stack.enter_context", 1)
source = source.replace("            finally:resolver_receipts.append(dict(nodeid=item.nodeid,receipt=reader()))", """            finally:
                row=dict(nodeid=item.nodeid,receipt=None,reader_error=None)
                try:row['receipt']=reader()
                except BaseException as error:row['reader_error']=repr(error)
                resolver_receipts.append(row)""")
assert "finally:resolver_receipts.append" not in source
source = source.replace("    parse_receipt=parsed.receipt();read_receipt=code_lease.receipt()", "    path_receipt=path_lease.receipt()\n    parse_receipt=parsed.receipt();read_receipt=code_lease.receipt()")
first = source.index('for row in resolver_receipts:\n')
last = source.index("assert not parsed._handles and parsed._state=='closed'", first)
source = source[:first]+"""validation_errors=[]
for row in resolver_receipts:
    receipt=row['receipt']
    if receipt is None:
        validation_errors.append(dict(nodeid=row['nodeid'],reason='resolver receipt unavailable',error=row['reader_error']))
        continue
    if not receipt['original_alias_restored'] or not receipt['all_resolver_cached_paths_cleared']:
        validation_errors.append(dict(nodeid=row['nodeid'],reason='resolver alias/cache not restored'))
    if receipt['cleanup_errors'] or receipt['first_failure'] is not None:
        validation_errors.append(dict(nodeid=row['nodeid'],reason='resolver failure',error=receipt['first_failure'],errors=receipt['cleanup_errors']))
    if receipt['original_discovery_oracles']!={'entry':1,'exit':1}:
        validation_errors.append(dict(nodeid=row['nodeid'],reason='incomplete discovery bookends'))
    if (receipt['fresh_PathDistribution_instances']!=receipt['fast_path_calls']
            or receipt['from_name_calls']!=receipt['fast_path_calls']+receipt['fallback_calls']):
        validation_errors.append(dict(nodeid=row['nodeid'],reason='resolver count mismatch'))
"""+source[last:]
source = source.replace("distribution_resolver_receipts=resolver_receipts,discovery_context=discovery_context,formal_result=False,resource_admission=False)",
    "distribution_resolver_receipts=resolver_receipts,discovery_context=discovery_context,\n"
    "    diagnostic_validation_errors=validation_errors,canonical_path_receipt=path_receipt,\n"
    "    canonical_path_alias_restored=store._path is original_path,\n"
    "    all_path_handles_closed=not path_lease._directories,canonical_path_state=path_lease._state,\n"
    "    canonical_paths_cleared=not path_lease._paths,formal_result=False,resource_admission=False)")
source = source.replace("assert read_receipt['original_metadata_version_alias_restored']", "assert read_receipt['original_metadata_version_alias_restored']\nassert read_receipt['canonical_path_alias_restored'] and read_receipt['all_path_handles_closed']\nassert read_receipt['canonical_path_state']=='closed' and read_receipt['canonical_paths_cleared']")
source = source.replace("sum(row['receipt']['fast_path_calls'] for row in resolver_receipts)", "sum(row['receipt']['fast_path_calls'] for row in resolver_receipts if row['receipt'] is not None)")
source = source.replace("sum(row['receipt']['fallback_calls'] for row in resolver_receipts)", "sum(row['receipt']['fallback_calls'] for row in resolver_receipts if row['receipt'] is not None)")
source = source.replace('sys.exit(code)', 'sys.exit(code if code else 1 if validation_errors else 0)')
compile(source, str(HERE/'run_unit_entry_v6.py'), 'exec')
with (HERE/'run_unit_entry_v6.py').open('x', encoding='utf-8', newline='\n') as stream:stream.write(source)
monitor = (HERE/'run_unit_bounded_v17.py').read_text(encoding='utf-8')
monitor = monitor.replace('run_unit_entry_v4.py','run_unit_entry_v6.py')
with (HERE/'run_unit_bounded_v19.py').open('x', encoding='utf-8', newline='\n') as stream:stream.write(monitor)
print('Created non-authoritative entry6 and monitor19; original helper and entry4 unchanged.')
