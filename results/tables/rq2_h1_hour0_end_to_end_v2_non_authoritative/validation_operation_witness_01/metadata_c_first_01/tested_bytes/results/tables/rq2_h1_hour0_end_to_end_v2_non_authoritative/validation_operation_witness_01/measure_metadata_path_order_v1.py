"""One 4000-lookup stock-discovery probe; no repo model, solver or saved input."""
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType

HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'validation_path_optimization_01/entry_revision_03'
mode,supplied=sys.argv[1:]
if mode not in ('c_first','d_first'):raise ValueError('two explicit path vectors only')
out=Path(supplied)
if (not out.is_absolute() or str(out)!=str(out.resolve(strict=False)) or out.parent.parent!=HERE
        or out.name!='attempt_non_authoritative' or not out.parent.name.startswith('metadata_'+mode+'_')):
    raise ValueError('owned monitor output child required')
out.mkdir(exist_ok=False)
prefix=out/'empty_pycache';prefix.mkdir();sys.pycache_prefix=str(prefix)
if not sys.flags.isolated or not sys.flags.dont_write_bytecode or not sys.dont_write_bytecode:
    raise ValueError('fixed -I -B interpreter required')
NAMES=('Pyomo','highspy','numpy','scipy','PYPOWER','PyYAML','osqp','gurobipy')


def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def load(name,filename,members):
    path=PACKAGE/filename;raw=path.read_bytes()
    if sha256(raw).hexdigest()!=members[filename]:raise ValueError('fixed helper byte mismatch')
    module=ModuleType(name);module.__file__=str(path);module.__package__='performance';sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),vars(module));return module


start=perf_counter();source_pins={};metadata_pins={};policy=None;result=dict(mode=mode,formal_result=False,
    resource_admission=False,full_chain_passed=False,native_execution_authorized=False,
    stock_distribution_discovery_cached=False,scope='stock metadata lookup only; no scientific performance claim')
try:
    raw=(PACKAGE/'package_manifest_v1.json').read_bytes()
    if sha256(raw).hexdigest()!='e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139':
        raise ValueError('fixed package differs')
    members=json.loads(raw)['files_sha256']
    source_pins={str(PACKAGE/name):pin for name,pin in members.items()}
    source_pins.update({str(PACKAGE/'package_manifest_v1.json'):sha256(raw).hexdigest(),
        str(Path(__file__).resolve()):sha256(Path(__file__).read_bytes()).hexdigest(),
        str(Path(metadata.__file__)):sha256(Path(metadata.__file__).read_bytes()).hexdigest()})
    if any(sha256(Path(name).read_bytes()).hexdigest()!=h for name,h in source_pins.items()):
        raise ValueError('helper/stdlib/source beforepin mismatch')
    package=ModuleType('performance');package.__path__=[str(PACKAGE)];sys.modules['performance']=package
    load('performance.code_read_lease','code_read_lease.py',members)
    parsed=load('performance.metadata_parse_lease','metadata_parse_lease.py',members)
    interpreter=load('performance.interpreter_path_policy','interpreter_path_policy.py',members)
    declaration=json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes())
    old_paths=tuple(declaration['configured_paths'])
    if mode=='d_first':
        paths=declaration['configured_paths']
        if not paths[-1].startswith('D:') or not paths[-2].startswith('C:'):
            raise ValueError('only the fixed last two site roots may be swapped')
        paths[-2],paths[-1]=paths[-1],paths[-2]
    policy=interpreter.InterpreterPathPolicy(declaration);policy.configure()
    metadata_pins=json.loads((PACKAGE/'metadata_allowlist_v1.json').read_bytes())['files_sha256']
    if any(sha256(Path(name).read_bytes()).hexdigest()!=h for name,h in metadata_pins.items()):
        raise ValueError('METADATA beforepin mismatch')
    original_version,original_distribution=metadata.version,metadata.distribution
    def selected():
        rows={}
        for name in NAMES:
            dist=original_distribution(name)
            if type(dist) is not metadata.PathDistribution:raise ValueError('exact stock PathDistribution required')
            path=dist._path/'METADATA'
            if str(path) not in metadata_pins:raise ValueError('selected distribution is outside fixed D pins')
            rows[name]=dict(version=dist.version,metadata=str(path),sha256=metadata_pins[str(path)])
        return rows
    save('request.json',dict(mode=mode,repetitions=500,lookups=4000,names=NAMES,source_sha256=source_pins,
        metadata_sha256=metadata_pins,configured_paths=list(sys.path),predecessor_paths=old_paths,
        policy_sha256=sha256(json.dumps(declaration,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        distribution_discovery_cached=False,selected_locked_metadata_version_value_cached=True,
        warmup='one stock selection per name before one measured window',formal_result=False))
    with parsed.MetadataParseLease(metadata_pins) as lease:
        before=selected();lease.begin_discovery_window();begin=perf_counter()
        observed=None
        for _ in range(500):
            observed=tuple(metadata.version(name) for name in NAMES)
            if observed!=tuple(before[name]['version'] for name in NAMES):raise ValueError('stock version selection changed')
        elapsed=perf_counter()-begin
        after=selected()
        if before!=after or metadata.version is not original_version or metadata.distribution is not original_distribution:
            raise ValueError('stock selection/dispatch changed')
        save('metadata_receipt.json',lease.receipt());policy.admit('after_lookup_probe')
        result.update(exit_code=0,lookup_seconds=elapsed,lookups=4000,selected=before,
            scientific_outputs_executed=False,real_native_calls=0,stock_version_and_distribution_functions_unchanged=True)
except BaseException:result.update(exit_code=1,error=traceback.format_exc())
finally:
    errors=[]
    for label,pins in (('source',source_pins),('metadata',metadata_pins)):
        try:
            unchanged=bool(pins) and all(sha256(Path(name).read_bytes()).hexdigest()==h for name,h in pins.items())
            result[label+'_unchanged']=unchanged
            if not unchanged:result['exit_code']=1
        except BaseException:errors.append(dict(stage=label,error=traceback.format_exc()))
    if policy is not None:
        try:save('interpreter_receipt.json',policy.receipt())
        except BaseException:errors.append(dict(stage='policy_receipt',error=traceback.format_exc()))
    if errors:result.update(exit_code=1,finalization_errors=errors)
    result['elapsed_seconds']=perf_counter()-start
    save('terminal.json',result)
    print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
