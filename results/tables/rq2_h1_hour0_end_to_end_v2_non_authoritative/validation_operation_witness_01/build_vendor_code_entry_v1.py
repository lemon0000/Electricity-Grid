"""Add seven immutable vendor files to the existing diagnostic code lease."""
from hashlib import sha256
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
from types import ModuleType
import re

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
P=HERE.parent/'validation_path_optimization_01'
prior=P/'entry_revision_06';target=P/'entry_revision_07'
raw=(prior/'package_manifest_v1.json').read_bytes()
assert sha256(raw).hexdigest()=='6c0db76dd3bbcfb8281e69d7ad70cc18caaf7adef4d120c0aebb30bbcedef03d'
members=json.loads(raw)['files_sha256']
assert all(sha256((prior/name).read_bytes()).hexdigest()==pin for name,pin in members.items())
vendor_root=Path('D:/Miniconda3/envs/compute/Lib/site-packages/pyomo')
names=('solvers/plugins/solvers/GUROBI.py','solvers/plugins/solvers/gurobi_direct.py',
    'solvers/plugins/solvers/direct_solver.py','solvers/plugins/solvers/direct_or_persistent_solver.py',
    'opt/results/results_.py','opt/results/solution.py','opt/results/solver.py')
vendor={str(vendor_root/name):sha256((vendor_root/name).read_bytes()).hexdigest() for name in names}
micro=json.loads((HERE/'vendor_code_identity_pair_01/1_vendor7_non_authoritative/result.json').read_bytes())
assert {key:value for key,value in micro['code_lease_receipt']['files_sha256'].items()
    if Path(key).is_relative_to(vendor_root)}==vendor


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)


target.mkdir(exist_ok=False)
for name in (*members,'launch_validation.py'):(target/name).write_bytes((prior/name).read_bytes())
(target/'entry06_predecessor_package_manifest.json').write_bytes(raw)
manifest=dict(schema='h1_fixed_vendor_code_allowlist_development_v1',
    root=str(vendor_root),files_sha256=vendor)
(target/'vendor_code_allowlist_v1.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
policy='''"""Fixed extension of the predecessor code allowlist; no discovery/result cache."""
from hashlib import sha256
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
from types import ModuleType

REPOSITORY_ALLOWLIST_SHA=__REPO_SHA__
VENDOR_ROOT=Path('D:/Miniconda3/envs/compute/Lib/site-packages/pyomo')
VENDOR_PINS=__VENDOR_PINS__
MODULE_PATHS={
    'pyomo.solvers.plugins.solvers.GUROBI':'solvers/plugins/solvers/GUROBI.py',
    'pyomo.solvers.plugins.solvers.gurobi_direct':'solvers/plugins/solvers/gurobi_direct.py',
    'pyomo.solvers.plugins.solvers.direct_solver':'solvers/plugins/solvers/direct_solver.py',
    'pyomo.solvers.plugins.solvers.direct_or_persistent_solver':'solvers/plugins/solvers/direct_or_persistent_solver.py',
    'pyomo.opt.results.results_':'opt/results/results_.py',
    'pyomo.opt.results.solution':'opt/results/solution.py',
    'pyomo.opt.results.solver':'opt/results/solver.py'}


def no_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate vendor JSON key')
        result[key]=value
    return result


def vendor_files(repository_raw,vendor_raw):
    if sha256(repository_raw).hexdigest()!=REPOSITORY_ALLOWLIST_SHA:
        raise ValueError('exact predecessor repository allowlist required')
    declaration=json.loads(vendor_raw,object_pairs_hook=no_duplicates)
    expected=dict(schema='h1_fixed_vendor_code_allowlist_development_v1',
        root=str(VENDOR_ROOT),files_sha256=VENDOR_PINS)
    if declaration!=expected:raise ValueError('exact seven vendor paths and pins required')
    return {Path(name):pin for name,pin in declaration['files_sha256'].items()}


def assert_unloaded(modules):
    if any(name in modules for name in MODULE_PATHS):
        raise ValueError('vendor modules must not precede union code lease')


def origins(modules,*,required=False):
    result={}
    for name,relative in MODULE_PATHS.items():
        module=modules.get(name)
        if module is None:
            if required:raise ValueError('required vendor module absent: '+name)
            continue
        expected=str(VENDOR_ROOT/relative)
        spec=getattr(module,'__spec__',None)
        loader=getattr(module,'__loader__',None);inner=loader
        owner=modules.get('pyomo.common.dependencies')
        if owner is not None and type(loader) is getattr(owner,'DeferredImportCallbackLoader',None):
            inner=loader._loader
        if (not isinstance(module,ModuleType) or getattr(module,'__file__',None)!=expected
                or spec is None or getattr(spec,'origin',None)!=expected or spec.name!=name
                or spec.loader is not loader or type(inner) is not SourceFileLoader
                or inner.name!=name or inner.path!=expected):
            raise ValueError('fixed vendor module origin differs: '+name)
        result[name]=expected
    return result
'''
policy=policy.replace('__REPO_SHA__',repr(members['code_allowlist_v3.json'])).replace('__VENDOR_PINS__',repr(vendor))
(target/'vendor_code_policy.py').write_text(policy,encoding='utf-8',newline='\n')
entry=(target/'validation_entry.py').read_text(encoding='utf-8')
entry=change(entry,'repository_pins,repository_code_pins\n','repository_pins,repository_code_pins,vendor_policy,vendor_expected\n')
entry=change(entry,"            stock_metadata_finder_unchanged=True),",'''            stock_metadata_finder_unchanged=True,
            repository_code_manifest_sha256=sha256(sources['code_allowlist_v3.json']).hexdigest(),
            vendor_code_manifest_sha256=sha256(sources['vendor_code_allowlist_v1.json']).hexdigest(),
            repository_code_files=149,vendor_code_files=7,code_lease_files=156,
            code_lease_root='D:/',vendor_origin_manifest=sources['vendor_code_allowlist_v1.json'].decode() ),''')
anchor="    metadata_expected=unique_paths(json.loads(sources['metadata_allowlist_v1.json'],object_pairs_hook=no_duplicate_keys)['files_sha256'])"
entry=change(entry,anchor,anchor+'''
    vendor_policy=load_module('performance.vendor_code_policy','vendor_code_policy.py')
    vendor_policy.assert_unloaded(sys.modules)
    vendor_expected=vendor_policy.vendor_files(sources['code_allowlist_v3.json'],sources['vendor_code_allowlist_v1.json'])
    if len(expected)!=149 or len(vendor_expected)!=7 or expected.keys()&vendor_expected.keys():
        raise ValueError('149 repository plus seven disjoint vendor code files required')''')
anchor="        repository_code_pins[str(path)]=pin\n"
entry=change(entry,anchor,anchor+'''    for path,pin in vendor_expected.items():
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=pin:raise ValueError('vendor source pin differs: '+str(path))
        destination=tested/'vendor_code/pyomo'/path.relative_to(vendor_policy.VENDOR_ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
        vendor_code_pins[str(path)]=pin
    expected={**expected,**vendor_expected}
''')
entry=change(entry,'CodeReadLease(expected,root=REPO)','CodeReadLease(expected,root=Path(\'D:/\'))')
entry=change(entry,"    CanonicalPathLease=load_module('experiments.h1_canonical_path_lease_development_v1','canonical_path_lease.py').CanonicalPathLease\n",'')
entry=change(entry,'    global path_lease\n','    global path_lease,CanonicalPathLease\n    vendor_policy.assert_unloaded(sys.modules)\n')
entry=change(entry,"    if mode=='parse_path':\n        from src.rq2_joint_deliverability_boundary_v1 import episode_store",
    "    if mode=='parse_path':\n        CanonicalPathLease=load_module('experiments.h1_canonical_path_lease_development_v1','canonical_path_lease.py').CanonicalPathLease\n        from src.rq2_joint_deliverability_boundary_v1 import episode_store")
start=entry.index('def saved_arm():\n');end=entry.index('def unit_tests():\n',start)
arm=entry[start:end]
arm=change(arm,'def saved_arm():\n','def _saved_arm_leased(code):\n')
arm=change(arm,'        with ExitStack() as stack:\n            code,parsed=lease_context(stack);begin=perf_counter()\n',
    "        with ExitStack() as metadata_stack:\n            parsed=metadata_stack.enter_context(MetadataParseLease(metadata_expected)) if mode in ('parse','parse_path') else None\n            begin=perf_counter()\n")
entry=entry[:start]+'''def saved_arm():
    with ExitStack() as stack:
        vendor_policy.assert_unloaded(sys.modules)
        code=stack.enter_context(CodeReadLease(expected,root=Path('D:/'))) if mode!='plain' else None
        _saved_arm_leased(code)


'''+arm+entry[end:]
entry=change(entry,"    if code:save(name+'lease_receipt.json',dict(code.receipt(),test_nodeid=nodeid))",'''    if code:
        receipt=code.receipt()
        if receipt['files_sha256']!={str(path):pin for path,pin in expected.items()}:
            raise ValueError('exact 156-file code lease receipt required')
        receipt['vendor_module_origins']=vendor_policy.origins(sys.modules,required=kind in ('arm','phase'))
        save(name+'lease_receipt.json',dict(receipt,test_nodeid=nodeid))''')
entry=change(entry,"'test_pytest_admission_plugin.py'):","'test_pytest_admission_plugin.py','test_vendor_code_policy.py'):")
entry=entry.replace('h1_cs02_non_authoritative','h1_cs03_non_authoritative')
entry=change(entry,'repository_code_pins={}\ninterpreter_policy=None','repository_code_pins={}\nvendor_code_pins={}\ninterpreter_policy=None\nvendor_policy=None')
anchor="    result['candidate_bytes_unchanged']=after==code_pins"
entry=change(entry,anchor,'''    vendor_after={};vendor_errors={}
    for path in vendor_code_pins:
        try:vendor_after[path]=sha256(Path(path).read_bytes()).hexdigest()
        except BaseException as error:vendor_errors[path]=repr(error)
    save('vendor_code_pins_after.json',dict(files_sha256=vendor_after,read_errors=vendor_errors))
    result['vendor_code_file_count']=len(vendor_code_pins)
    result['vendor_code_unchanged']=vendor_after==vendor_code_pins and not vendor_errors
    if vendor_policy is not None:
        try:result['vendor_module_origins_at_exit']=vendor_policy.origins(sys.modules,required=kind in ('arm','phase'))
        except BaseException:result.update(exit_code=1,vendor_origin_error=traceback.format_exc())
    if vendor_after!=vendor_code_pins or vendor_errors:
        result.update(exit_code=1,error='vendor code changed during measurement')
'''+anchor)
(target/'validation_entry.py').write_text(entry,encoding='utf-8',newline='\n')
test_entry=(target/'test_validation_entry.py').read_text(encoding='utf-8')
test_entry=change(test_entry,"'code_allowlist_v3.json','metadata_allowlist_v1.json'",
    "'vendor_code_policy.py','vendor_code_allowlist_v1.json','code_allowlist_v3.json','metadata_allowlist_v1.json'")
(target/'test_validation_entry.py').write_text(test_entry,encoding='utf-8',newline='\n')
tests='''"""Admission faults for the exact vendor extension and fresh module origins."""
import copy
from importlib.machinery import SourceFileLoader,ModuleSpec
import json
from pathlib import Path
from types import ModuleType
import unittest
from performance import vendor_code_policy as policy

HERE=Path(__file__).resolve().parent


class VendorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.repo=(HERE/'code_allowlist_v3.json').read_bytes()
        self.vendor=json.loads((HERE/'vendor_code_allowlist_v1.json').read_bytes())

    def reject(self,change):
        value=copy.deepcopy(self.vendor);change(value)
        with self.assertRaises(ValueError):policy.vendor_files(self.repo,json.dumps(value).encode())

    def test_exact_predecessor_and_seven_paths(self):
        actual=policy.vendor_files(self.repo,json.dumps(self.vendor).encode())
        self.assertEqual({str(path):pin for path,pin in actual.items()},policy.VENDOR_PINS)
        self.assertEqual(len(actual),7)

    def test_repository_subset_rejected(self):
        value=json.loads(self.repo);value['files_sha256'].pop(next(iter(value['files_sha256'])))
        with self.assertRaisesRegex(ValueError,'exact predecessor'):
            policy.vendor_files(json.dumps(value).encode(),json.dumps(self.vendor).encode())

    def test_missing_vendor_rejected(self):
        self.reject(lambda value:value['files_sha256'].pop(next(iter(value['files_sha256']))))

    def test_extra_vendor_rejected(self):
        self.reject(lambda value:value['files_sha256'].update({'D:/unlisted.py':'a'*64}))

    def test_wrong_sha_rejected(self):
        self.reject(lambda value:value['files_sha256'].update({next(iter(value['files_sha256'])):'a'*64}))

    def test_same_name_c_support_file_rejected(self):
        def change(value):
            path=next(iter(value['files_sha256']));pin=value['files_sha256'].pop(path)
            value['files_sha256']['C:/support/pyomo/'+Path(path).name]=pin
        self.reject(change)

    def test_path_alias_rejected(self):
        def change(value):
            path=next(iter(value['files_sha256']));pin=value['files_sha256'].pop(path)
            value['files_sha256'][path.lower()]=pin
        self.reject(change)

    def test_extra_schema_field_rejected(self):self.reject(lambda value:value.update(cache_all=True))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate vendor'):
            policy.vendor_files(self.repo,b'{"root":"D:/","root":"D:/"}')

    def modules(self):
        modules={}
        for name,relative in policy.MODULE_PATHS.items():
            path=str(policy.VENDOR_ROOT/relative);loader=SourceFileLoader(name,path)
            module=ModuleType(name);module.__file__=path;module.__loader__=loader
            module.__spec__=ModuleSpec(name,loader,origin=path);modules[name]=module
        return modules

    def test_preloaded_vendor_rejected_before_lease(self):
        policy.assert_unloaded({})
        for name in policy.MODULE_PATHS:
            with self.assertRaisesRegex(ValueError,'must not precede'):policy.assert_unloaded({name:None})

    def test_origins_bound_to_d_compute(self):
        self.assertEqual(len(policy.origins(self.modules(),required=True)),7)

    def test_required_missing_module_rejected(self):
        with self.assertRaisesRegex(ValueError,'absent'):policy.origins({},required=True)
        self.assertEqual(policy.origins({}),{})

    def test_module_file_origin_drift_rejected(self):
        modules=self.modules();next(iter(modules.values())).__file__='C:/support/GUROBI.py'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_spec_origin_drift_rejected(self):
        modules=self.modules();next(iter(modules.values())).__spec__.origin='C:/support/GUROBI.py'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_loader_mismatch_rejected(self):
        modules=self.modules();next(iter(modules.values())).__loader__=object()
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_name_mismatch_rejected(self):
        modules=self.modules();next(iter(modules.values())).__spec__.name='pyomo.wrong'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)
'''
(target/'test_vendor_code_policy.py').write_text(tests,encoding='utf-8',newline='\n')
monitor=(P/'run_bounded_configured_entry_v6.py').read_text(encoding='utf-8')
assert sha256((P/'run_bounded_configured_entry_v6.py').read_bytes()).hexdigest()=='830f68ecc6db3d9b721ec2de5733ea6f4cb2f15fa53fd1b5e55d536e313f2a8a'
monitor=monitor.replace('entry_revision_06','entry_revision_07').replace('unit_checks_05','unit_checks_06')
monitor=monitor.replace('sampler_smoke_02','sampler_smoke_03').replace('common_slice_02','common_slice_03').replace('h1_cs02_non_authoritative','h1_cs03_non_authoritative')
monitor=change(monitor,"if launcher!=entry/'launch_validation.py' or not arguments[4].replace('_','').isalnum():",'''baseline=(HERE/'entry_revision_06').resolve(strict=True)
if launcher==baseline/'launch_validation.py':entry=baseline
if launcher!=entry/'launch_validation.py' or not arguments[4].replace('_','').isalnum():''')
monitor=change(monitor,"if kind=='unit':",'''if entry==baseline and not (kind=='arm' and mode=='parse' and child_label=='vendor_saved_arm_01' and not targets):
    raise ValueError('predecessor allowed only for the fixed saved-arm comparison')
if kind=='arm':
    if mode!='parse' or targets or child_label!='vendor_saved_arm_01' or limit>120 or ram>512*1024**2 or storage_cap>64*1024**2:
        raise ValueError('exact bounded saved-arm role required')
elif kind=='unit':''')
monitor=change(monitor,"    source_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}",'''    vendor_manifest=HERE/'entry_revision_07/vendor_code_allowlist_v1.json'
    sources.add(vendor_manifest)
    sources.update(Path(name) for name in json.loads(vendor_manifest.read_bytes())['files_sha256'])
    source_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}''')
monitor=change(monitor,"        destination = out / 'tested_bytes' / path.relative_to(REPO)",'''        destination = (out/'tested_bytes'/path.relative_to(REPO) if path.is_relative_to(REPO)
            else out/'tested_bytes/external'/path.drive[:1]/Path(*path.parts[1:]))''')
(P/'run_bounded_configured_entry_v7.py').write_text(monitor,encoding='utf-8',newline='\n')
newnames=(*members,'entry06_predecessor_package_manifest.json','vendor_code_allowlist_v1.json',
    'vendor_code_policy.py','test_vendor_code_policy.py')
for name in newnames:
    if name.endswith('.py'):compile((target/name).read_bytes(),str(target/name),'exec')
new_members={name:sha256((target/name).read_bytes()).hexdigest() for name in newnames}
package=(json.dumps(dict(schema='h1_configured_validation_package_development_v1',files_sha256=new_members,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False),indent=2)+'\n').encode()
(target/'package_manifest_v1.json').write_bytes(package)
pin=sha256(package).hexdigest()
launch,n=re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+pin+"'",(target/'launch_validation.py').read_text(encoding='utf-8'))
assert n==1
(target/'launch_validation.py').write_text(launch,encoding='utf-8',newline='\n')
plan=dict(status='DRAFT_NONAUTHORITATIVE',question='Does exact seven-file vendor code reuse reduce a saved real arm validation with identical science and audit?',
    package_manifest_sha256=pin,predecessor_package_manifest_sha256=sha256(raw).hexdigest(),
    unchanged_code_read_lease_sha256=members['code_read_lease.py'],repository_files=149,test_closure_files=614,vendor_files=7,
    vendor_bytes=sum((vendor_root/name).stat().st_size for name in names),code_lease_root='D:/',
    monitor='run_bounded_configured_entry_v7.py',monitor_sha256=sha256((P/'run_bounded_configured_entry_v7.py').read_bytes()).hexdigest(),
    unit_role=['unit','parse','unit_checks_06'],unit_limits=dict(count=1,wall_seconds=120,sampled_rss_mib=512,storage_mib=64),
    saved_arm_roles=[dict(entry=name,kind='arm',mode='parse',label='vendor_saved_arm_01') for name in ('entry_revision_06','entry_revision_07')],
    saved_arm_limits=dict(count_per_entry=1,wall_seconds_per_entry=120,sampled_rss_mib=512,storage_mib=64,concurrency=1),
    stop='first failed/capped stage; no automatic retry; all source/saved inputs must remain unchanged',
    original_identity_functions_unchanged=True,stock_metadata_discovery_unchanged=True,
    unknown_reads='original Path.read_bytes fallback; no result/input caching',
    scientific_oracle='saved original common._arm scientific payload and projected audit, plus direct two-entry differential',
    full_chain_speedup_measured=False,full_hour0_chain_passed=False,full_chain_launch_admitted=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'vendor_code_entry_plan_01.json').open('x',encoding='utf-8',newline='\n') as stream:json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=pin,members=len(new_members),monitor_sha256=plan['monitor_sha256'])),flush=True)
