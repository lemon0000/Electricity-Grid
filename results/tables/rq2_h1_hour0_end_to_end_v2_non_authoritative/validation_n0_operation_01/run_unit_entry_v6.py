"""Non-authoritative diagnostic units composing the already reviewed metadata resolver."""
from contextlib import ExitStack
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
BASE=HERE.parent/'validation_path_optimization_01'
ENTRY=BASE/'entry_revision_07';RESOLVER=BASE/'entry_revision_14_non_authoritative'
sys.path[:0]=[str(REPO),str(REPO/'tests')]
package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package


def load(name,root=ENTRY):
    qualified='performance.'+name
    if qualified in sys.modules:return sys.modules[qualified]
    spec=importlib.util.spec_from_file_location(qualified,root/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[qualified]=module;spec.loader.exec_module(module)
    return module


expected={Path(k):v for k,v in json.loads((ENTRY/'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
expected.update(load('vendor_code_policy').vendor_files((ENTRY/'code_allowlist_v3.json').read_bytes(),
    (ENTRY/'vendor_code_allowlist_v1.json').read_bytes()))
for path in (REPO/'experiments').glob('h1_*.py'):expected[path]=sha256(path.read_bytes()).hexdigest()
for path in (Path(__file__),ENTRY/'code_read_lease.py',ENTRY/'metadata_parse_lease.py',RESOLVER/'pinned_distribution_resolver_v1.py'):
    expected[path]=sha256(path.read_bytes()).hexdigest()
metadata={Path(k):v for k,v in json.loads((ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
base=Path(sys.argv[sys.argv.index('--basetemp')+1])
path_roots=[REPO,base]
if '--canonical-path-root' in sys.argv:
    index=sys.argv.index('--canonical-path-root')
    if sys.argv.count('--canonical-path-root')!=1 or index+1>=len(sys.argv):
        raise ValueError('one canonical-path-root value required')
    extra=Path(sys.argv[index+1])
    if (not extra.is_absolute() or '..' in extra.parts or not extra.name.endswith('_non_authoritative')):
        raise ValueError('explicit absolute non-authoritative path root required')
    path_roots.append(extra)
    del sys.argv[index:index+2]
from experiments import h1_canonical_path_lease_development_v1 as canonical
from src.rq2_joint_deliverability_boundary_v1 import episode_store as store
original_path=store._path
retry_path_cleanup=canonical._RELEASE

discovery_context=dict(entry_sys_path=list(sys.path),test_sys_path=[]);resolver_receipts=[]
code_lease=path_lease=parsed=None
code=1;entry_error=None;path_retry=[]
path_receipt=parse_receipt=None
read_receipt=dict(file_count=0,code_read_hits=0)

def describe(error):
    try:return repr(error)
    except BaseException:return '<exception repr failed>'

try:
    with ExitStack() as stack:
        code_lease=stack.enter_context(load('code_read_lease').CodeReadLease(expected,root=Path('D:/')))
        path_lease=stack.enter_context(canonical.CanonicalPathLease(store,path_roots))
        parsed=stack.enter_context(load('metadata_parse_lease').MetadataParseLease(metadata))
        distribution_operation=load('pinned_distribution_resolver_v1',RESOLVER).operation
        import pytest
        class Windows:
            @pytest.hookimpl(tryfirst=True,hookwrapper=True)
            def pytest_runtest_call(self,item):
                discovery_context['test_sys_path'].append(list(sys.path));parsed.begin_discovery_window()
                distribution_scope,reader=distribution_operation(parsed,metadata)
                try:
                    with distribution_scope:
                        outcome=yield
                        outcome.get_result()
                finally:
                    row=dict(nodeid=item.nodeid,receipt=None,reader_error=None)
                    try:row['receipt']=reader()
                    except BaseException as error:row['reader_error']=describe(error)
                    resolver_receipts.append(row)
        code=pytest.main(['-q','--disable-warnings','--maxfail=1','--import-mode=importlib','-p','no:cacheprovider',*sys.argv[1:]],plugins=[Windows()])
        path_receipt=path_lease.receipt()
        parse_receipt=parsed.receipt();read_receipt=code_lease.receipt()
except BaseException as error:
    entry_error=describe(error)
    # ExitStack has attempted every registered exit. Retry only the original
    # path cleanup capsule once; preserve a failed terminal even if it succeeds.
    if path_lease is not None and path_lease._directories:
        row=dict(pending_before=len(path_lease._directories),error=None)
        try:retry_path_cleanup(path_lease)
        except BaseException as retry_error:row['error']=describe(retry_error)
        row['pending_after']=len(path_lease._directories);path_retry.append(row)
discovery_context['exit_sys_path']=list(sys.path)
validation_errors=[]
if entry_error is not None:validation_errors.append(dict(reason='entry or cleanup failure',error=entry_error))
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
read_receipt.update(all_code_handles_closed=code_lease is not None and not code_lease._handles,
    original_read_alias_restored=code_lease is not None and Path.read_bytes is code_lease._restore_read,
    metadata_parse_receipt=parse_receipt,all_metadata_handles_closed=parsed is not None and not parsed._handles,
    original_metadata_version_alias_restored=parsed is not None and parsed._original is sys.modules['importlib.metadata'].Distribution.version,
    distribution_resolver_receipts=resolver_receipts,discovery_context=discovery_context,
    diagnostic_validation_errors=validation_errors,canonical_path_receipt=path_receipt,
    canonical_path_alias_restored=store._path is original_path,
    all_path_handles_closed=path_lease is not None and not path_lease._directories,
    canonical_path_state=None if path_lease is None else path_lease._state,
    canonical_paths_cleared=path_lease is not None and not path_lease._paths,
    canonical_path_roots=list(map(str,path_roots)),entry_error=entry_error,path_cleanup_retry=path_retry,
    pending_path_handles=None if path_lease is None else len(path_lease._directories),
    diagnostic_state_observations=True,formal_result=False,resource_admission=False)
for key in ('all_code_handles_closed','original_read_alias_restored','all_metadata_handles_closed',
        'original_metadata_version_alias_restored','canonical_path_alias_restored',
        'all_path_handles_closed','canonical_paths_cleared'):
    if not read_receipt[key]:validation_errors.append(dict(reason=key+' not proven'))
if read_receipt['canonical_path_state']!='closed':validation_errors.append(dict(reason='path state not closed'))
base.mkdir(exist_ok=True)
with (base/'unit_code_read_lease_closed.json').open('x',encoding='utf-8') as stream:json.dump(read_receipt,stream,indent=2)
print(json.dumps(dict(ordinary_unit_immutable_code_files=read_receipt['file_count'],
    code_read_hits=read_receipt['code_read_hits'],all_code_handles_closed=read_receipt['all_code_handles_closed'],
    original_read_alias_restored=read_receipt['original_read_alias_restored'],
    all_metadata_handles_closed=read_receipt['all_metadata_handles_closed'],
    original_metadata_version_alias_restored=read_receipt['original_metadata_version_alias_restored'],
    distribution_fast_calls=sum(row['receipt']['fast_path_calls'] for row in resolver_receipts if row['receipt'] is not None),
    distribution_fallback_calls=sum(row['receipt']['fallback_calls'] for row in resolver_receipts if row['receipt'] is not None),
    metadata_parse_hits=None if parse_receipt is None else parse_receipt['hits'],
    metadata_parse_misses=None if parse_receipt is None else parse_receipt['misses'],
    per_call_distribution_discovery_preserved=False,formal_result=False)),flush=True)
sys.exit(code if code else 1 if validation_errors else 0)
