"""Fixed local numerical routes for the one-shot Genesis observation adapter."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import FunctionType

SCHEMA='h1_common_genesis_validation_routes_development_v1'
ROUTES=(
    ('h1_operation_historical_witness_development_v5','254658ab10ff6a100ac90972e1d5b8824fc25592a4031a2832951f87f54e3384'),
    ('h1_phase_exact_source_current_development_v6','e73df62d5acc2306f13369d7fed1c74c9ec2db108d43e23d3f0216f050686ba9'),
    ('h1_group_n0_common_input_binding_development_v6','74daa4a9f293703433bdd798f9522151a79f82727497162045cc36a6014b945a'))


def _state(fn):
    return (fn.__code__,repr(fn.__defaults__),repr(fn.__kwdefaults__),
        tuple(id(c.cell_contents) for c in fn.__closure__ or ())) if type(fn) is FunctionType else None


def implementation_identity():
    return sha256(json.dumps([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),ROUTES],
        sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()


def load(bridge):
    """Load once before consumers; rollback only routes created by this call."""
    package=sys.modules['experiments'];root=Path(__file__).parent;created=[]
    if any('experiments.'+name in sys.modules or hasattr(package,name) for name,_ in ROUTES):
        raise ValueError('local Genesis routes must not be preloaded')
    raw=[]
    for name,pin in ROUTES:
        path=root/(name+'.py');data=path.read_bytes()
        if sha256(data).hexdigest()!=pin:raise ValueError('local Genesis route source changed')
        raw.append((name,path,pin,data))
    try:
        for name,path,pin,data in raw:
            qualified='experiments.'+name
            spec=importlib.util.spec_from_file_location(qualified,path)
            module=importlib.util.module_from_spec(spec);created.append((name,module,spec))
            sys.modules[qualified]=module;setattr(package,name,module)
            exec(compile(data,str(path),'exec'),vars(module))
        witness,source,common=(m for _,m,_ in created)
        if (witness.operation_bridge is not bridge or source.witness is not witness
                or common.witness is not witness or common.source is not source):
            raise ValueError('local Genesis route graph differs')
        observations=[]
        for module in (witness,source,common):
            for name,value in vars(module).items():
                if type(value) is FunctionType or isinstance(value,type):
                    observations.append((module,name,value,_state(value)))
                    if isinstance(value,type) and value.__module__==module.__name__:
                        observations.extend((value,n,v,_state(v)) for n,v in vars(value).items()
                            if callable(v) or isinstance(v,(property,staticmethod,classmethod)))
        fixed=tuple(observations);own=implementation_identity()
        def check():
            if implementation_identity()!=own:raise ValueError('local Genesis route manifest changed')
            for (name,module,spec),(_,path,pin,_) in zip(created,raw,strict=True):
                if (sys.modules.get('experiments.'+name) is not module or getattr(package,name,None) is not module
                        or module.__spec__ is not spec or module.__loader__ is not spec.loader
                        or module.__file__!=str(path) or sha256(path.read_bytes()).hexdigest()!=pin):
                    raise ValueError('local Genesis module provenance changed')
            if any(vars(obj).get(name) is not value or _state(value)!=state for obj,name,value,state in fixed):
                raise ValueError('local Genesis runtime route changed')
        check()
        return dict(check=check,session_type=witness.GroupWitnessSession,
            source_type=source.CommonSourceBundle,common_type=common.PreparedCommonInput,
            source_entry=source.prepare_common_bundle,common_entry=common.prepare,
            manifest=dict(schema=SCHEMA,implementation=own,sources=[dict(module='experiments.'+n,
                path=str(p),sha256=pin) for n,p,pin,_ in raw]))
    except BaseException as error:
        for name,module,_ in reversed(created):
            try:
                if vars(package).get(name) is module:delattr(package,name)
                if sys.modules.get('experiments.'+name) is module:del sys.modules['experiments.'+name]
            except BaseException as cleanup:error.add_note('local Genesis route rollback: '+repr(cleanup))
        raise
