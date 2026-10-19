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
discovery_context=dict(entry_sys_path=list(sys.path),test_sys_path=[]);resolver_receipts=[]
with ExitStack() as stack:
    code_lease=stack.enter_context(load('code_read_lease').CodeReadLease(expected,root=Path('D:/')))
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
            finally:resolver_receipts.append(dict(nodeid=item.nodeid,receipt=reader()))
    code=pytest.main(['-q','--disable-warnings','--maxfail=1','--import-mode=importlib','-p','no:cacheprovider',*sys.argv[1:]],plugins=[Windows()])
    parse_receipt=parsed.receipt();read_receipt=code_lease.receipt()
discovery_context['exit_sys_path']=list(sys.path)
for row in resolver_receipts:
    receipt=row['receipt']
    assert receipt['original_alias_restored'] and receipt['all_resolver_cached_paths_cleared']
    assert not receipt['cleanup_errors']
    if code==0:assert receipt['first_failure'] is None
    assert receipt['original_discovery_oracles']=={'entry':1,'exit':1}
    assert receipt['fresh_PathDistribution_instances']==receipt['fast_path_calls']
    assert receipt['from_name_calls']==receipt['fast_path_calls']+receipt['fallback_calls']
assert not parsed._handles and parsed._state=='closed'
read_receipt.update(all_code_handles_closed=not code_lease._handles,
    original_read_alias_restored=Path.read_bytes is code_lease._restore_read,
    metadata_parse_receipt=parse_receipt,all_metadata_handles_closed=not parsed._handles,
    original_metadata_version_alias_restored=parsed._original is sys.modules['importlib.metadata'].Distribution.version,
    distribution_resolver_receipts=resolver_receipts,discovery_context=discovery_context,formal_result=False,resource_admission=False)
assert read_receipt['all_code_handles_closed'] and read_receipt['original_read_alias_restored']
assert read_receipt['original_metadata_version_alias_restored']
base.mkdir(exist_ok=True)
with (base/'unit_code_read_lease_closed.json').open('x',encoding='utf-8') as stream:json.dump(read_receipt,stream,indent=2)
print(json.dumps(dict(ordinary_unit_immutable_code_files=read_receipt['file_count'],
    code_read_hits=read_receipt['code_read_hits'],all_code_handles_closed=True,original_read_alias_restored=True,
    all_metadata_handles_closed=True,original_metadata_version_alias_restored=True,
    distribution_fast_calls=sum(row['receipt']['fast_path_calls'] for row in resolver_receipts),
    distribution_fallback_calls=sum(row['receipt']['fallback_calls'] for row in resolver_receipts),
    metadata_parse_hits=parse_receipt['hits'],metadata_parse_misses=parse_receipt['misses'],
    per_call_distribution_discovery_preserved=False,formal_result=False)),flush=True)
sys.exit(code)
