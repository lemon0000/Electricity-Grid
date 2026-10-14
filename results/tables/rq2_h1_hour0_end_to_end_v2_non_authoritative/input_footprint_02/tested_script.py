"""Read-only diagnostic of existing loader inputs; never a live cache credential."""
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from experiments import h1_outage_registry_development_v1 as registry
from experiments import h1_phase_historical_controller_development_v1 as historical

FILE_CAP=512*1024**2
TOTAL_CAP=2*1024**3


def observation(path):
    before=path.stat()
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if before.st_size>FILE_CAP:raise ValueError('diagnostic file cap')
    digest=hashlib.sha256();count=0
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno())
        # Match the existing verifier contract: Windows path/fd ctime bases differ.
        if identity(opened)[:4]!=identity(before)[:4]:raise ValueError('changed before open')
        while count<=before.st_size:
            raw=stream.read(min(65536,before.st_size-count+1))
            if not raw:break
            count+=len(raw);digest.update(raw)
        if count!=before.st_size or identity(os.fstat(stream.fileno()))!=identity(opened):
            raise ValueError('changed while reading')
    if identity(path.stat())!=identity(before):raise ValueError('changed after reading')
    return dict(sha256=digest.hexdigest(),identity=identity(before),bytes=count)


def main(output):
    start=time.perf_counter()
    files={};roles={};directories=set()
    def add(path,role):
        path=Path(path).absolute()
        key=os.path.normcase(str(path))
        files[key]=path;roles.setdefault(key,set()).add(role)
        return path
    def document(path,role):
        return json.loads(add(path,role).read_bytes())
    def package(root,role):
        directories.add(root)
        members=document(root/'SHA256SUMS.json',role+' manifest')
        for name in members:add(root/name,role+' member')
        return members
    authority=document(registry.AUTHORITY,'registry authority')
    add(ROOT/authority['proposal_path'],'registry proposal')
    table=document(ROOT/authority['cap_table_path'],'registry cap table')
    add(ROOT/table['source_gen_path'],'registry source generators')
    config=registry.frozen.yaml.safe_load(add(registry.frozen.CONFIG,'registry config').read_bytes())
    package_root=ROOT/config['output']['directory']
    members=package(package_root,'power')
    assert 'summary.json' in members
    grid=ROOT/config['source']['grid_root'];directories.add(grid)
    grid_manifest=add(grid/'SHA256SUMS','grid manifest')
    for line in grid_manifest.read_text(encoding='ascii').splitlines():
        _,name=line.split('  ',1);add(grid/name,'grid member')
    package(ROOT/config['source']['cfe_package'],'CFE')
    manifest=document(registry.ARCHIVE/'manifest.json','registry split manifest')
    directories.add(registry.ARCHIVE)
    add(ROOT/manifest['source_member_path'],'registry source member')
    for split in ('training','holdout'):
        add(registry.ARCHIVE/manifest['members'][split]['path'],split+' split archive')
    add(ROOT/registry.catalog.CATALOG,'registry catalog')
    add(registry.frozen.GAPS,'registry gaps')
    modules=(registry,registry.old,registry.old.source,registry.old.source.audit,
        registry.events,registry.frozen,registry.frozen.chronology,registry.frozen.builder,
        registry.rts_gmlc,registry.extractor,registry.catalog)
    for module in modules:add(module.__file__,'registry implementation')
    source_config=Path(registry.old.source.audit.DEFAULT_CONFIG)
    declaration=dict(config_path=str(source_config),upstream_root=str(grid),
        origin=dict(config_sha256=hashlib.sha256(source_config.read_bytes()).hexdigest()))
    normal_files,normal_directories=historical._source_paths(declaration)
    for path in normal_files:add(path,'normal/current source enumeration')
    directories.update(normal_directories)
    add(Path(__file__),'diagnostic script')
    before={key:observation(path) for key,path in files.items()}
    if sum(row['bytes'] for row in before.values())>TOTAL_CAP:raise ValueError('diagnostic total cap')
    names_before={str(p):sorted(x.name for x in p.iterdir()) for p in directories}
    active=None;captured={split:set() for split in ('training','holdout')}
    def audit(event,args):
        if active is None or event!='open':return
        name,mode,flags=args
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise ValueError('loader attempted write')
        if isinstance(name,(str,bytes,os.PathLike)):
            captured[active].add(os.path.normcase(str(Path(os.fsdecode(name)).absolute())))
    sys.addaudithook(audit)
    loads=[]
    # This guard forbids solver calls; existing loaders only read local source files.
    with historical.history.replay.guard.solver_calls_forbidden():
        for split in ('training','holdout'):
            begin=time.perf_counter();active=split
            try:context=registry._load(split)
            finally:active=None
            loads.append(dict(split=split,elapsed_seconds=time.perf_counter()-begin,
                identity=context['identity'],source_seed_count=len(context['rows'])))
            del context
    after={key:observation(path) for key,path in files.items()}
    names_after={str(p):sorted(x.name for x in p.iterdir()) for p in directories}
    assert before==after and names_before==names_after
    missing={split:sorted(paths-files.keys()) for split,paths in captured.items()}
    result=dict(scope='read-only input-footprint diagnostic; no fast validator implemented',
        formal_result=False,live_owner_credential=False,fast_full_equivalence_proved=False,
        transaction_boundary_change=False,real_native_calls=0,
        exact_read_path_coverage={split:not paths for split,paths in missing.items()},
        unenumerated_reads=missing,captured_read_paths={k:sorted(v) for k,v in captured.items()},
        file_observations=before,file_roles={k:sorted(v) for k,v in roles.items()},
        directory_names=names_before,input_bytes_and_identities_unchanged=True,
        namespace_unchanged=True,python_version=platform.python_version(),
        yaml_version=registry.frozen.yaml.__version__,registry_loads=loads,
        normal_source_coverage='static enumeration only; normal loader not executed here',
        transient_ABA_covered=False,containment_policy_changed=False,
        elapsed_seconds=time.perf_counter()-start)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(files=len(files),bytes=sum(r['bytes'] for r in before.values()),
        missing=missing,elapsed_seconds=result['elapsed_seconds'])),flush=True)


if __name__=='__main__':main(Path(sys.argv[1]))
