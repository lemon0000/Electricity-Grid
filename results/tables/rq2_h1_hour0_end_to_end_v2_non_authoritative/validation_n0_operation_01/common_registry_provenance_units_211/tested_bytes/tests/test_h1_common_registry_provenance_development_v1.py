"""Pinned loader protocol with isolated synthetic modules; no Bootstrap scope."""
import gc
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from threading import Thread
from types import FunctionType,SimpleNamespace
from weakref import ref

import experiments
import pytest

from experiments import h1_common_registry_provenance_development_v1 as m


BRIDGE='''import sys
_register=_register
_activate=_activate
_deactivate=_deactivate
_LOADER_READY=False
_DEACTIVATE_FAILURE=False
def _build():
    def verify(lease):return True
    def route(action,actor,frame):
        if not verify(None):raise ValueError('private lease failed')
        if action=='activate' and not _LOADER_READY:raise ValueError('loader not complete')
        if action=='deactivate' and _DEACTIVATE_FAILURE:raise OSError('deactivate primary')
    return verify,route
_VERIFY_LEASE,_VERIFY_REGISTRY_ROUTE=_build()
def _install_runtime():
    def check():return None
    return check
_RUNTIME=_install_runtime()
def load(ready=True):
    global _LOADER_READY
    _LOADER_READY=ready
    _activate(sys.modules[__name__])
def unload():_deactivate(sys.modules[__name__])
_register(sys.modules[__name__])
'''
WITNESS='''import sys
_register=_register
from experiments import protocol_bridge_non_authoritative as operation_bridge
class Session:
    def check(self):return None
def _install_runtime():
    def check():return None
    return check
_runtime_check=_install_runtime()
_register(sys.modules[__name__])
'''
COMMON='''import sys
_register=_register
from experiments import protocol_witness_non_authoritative as witness
def prepare(session):return None
def _install_runtime():
    def check():return None
    return check
_FIXED=_install_runtime()
_register(sys.modules[__name__])
'''


@pytest.fixture
def case(tmp_path,monkeypatch):
    root=tmp_path/'protocol_non_authoritative';root.mkdir()
    sources=dict(bridge=BRIDGE,witness=WITNESS,common=COMMON)
    names={role:'experiments.protocol_'+role+'_non_authoritative' for role in sources}
    paths={role:root/(name.split('.')[-1]+'.py') for role,name in names.items()}
    for role,source in sources.items():paths[role].write_text(source,encoding='utf-8',newline='\n')
    pins={names[role]:sha256(path.read_bytes()).hexdigest() for role,path in paths.items()}
    plan=dict(names,graph=tuple(names.values()),activate_qualname='load',deactivate_qualname='unload',
        verify_qualname='_build.<locals>.verify',route_qualname='_build.<locals>.route',
        bridge_runtime='_RUNTIME',witness_runtime='_runtime_check',common_runtime='_FIXED',
        bridge_runtime_qualname='_install_runtime.<locals>.check',
        witness_runtime_qualname='_install_runtime.<locals>.check',common_runtime_qualname='_install_runtime.<locals>.check')
    register,activate,deactivate,checked=m.build_provenance(root,pins,dict(genesis=plan))
    modules={}
    def load(role):
        name=names[role];spec=importlib.util.spec_from_file_location(name,paths[role])
        module=importlib.util.module_from_spec(spec)
        module._register=register
        if role=='bridge':module._activate=activate;module._deactivate=deactivate
        monkeypatch.setitem(sys.modules,name,module)
        monkeypatch.setattr(experiments,name.split('.')[-1],module,raising=False)
        modules[role]=module
        exec(compile(paths[role].read_bytes(),str(paths[role]),'exec',dont_inherit=True),vars(module))
        return module
    return SimpleNamespace(root=root,names=names,paths=paths,pins=pins,plan=plan,
        register=register,activate=activate,deactivate=deactivate,checked=checked,load=load,modules=modules)


def all_loaded(case):
    for role in ('bridge','witness','common'):case.load(role)
    return case.modules['bridge']


def test_pinned_definition_is_distinct_from_completed_loader_activation(case):
    bridge=all_loaded(case)
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')
    with pytest.raises(ValueError,match='loader not complete'):bridge.load(False)
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')
    bridge.load();assert case.checked('genesis')['generation']==1
    with pytest.raises(ValueError,match='one active'):bridge.load()
    bridge.unload()
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')


def test_unpinned_source_cannot_become_definition_baseline(case):
    case.paths['bridge'].write_text(BRIDGE+'\n# changed source\n',encoding='utf-8')
    with pytest.raises(ValueError,match='predeclared Common source pin'):
        m.build_provenance(case.root,case.pins,dict(genesis=case.plan))


def test_direct_and_repeated_footer_cannot_register(case):
    module=case.load('bridge')
    with pytest.raises(ValueError,match='original Common source footer'):case.register(module)
    with pytest.raises(ValueError,match='one Common definition'):
        exec(compile(BRIDGE,str(case.paths['bridge']),'exec',dont_inherit=True),vars(module))


@pytest.mark.parametrize('fault',['globals','runtime','extra_module','extra_class','loader','edge'])
def test_source_and_active_callable_graph_mutations_fail_closed(case,fault):
    bridge=all_loaded(case);bridge.load();witness=case.modules['witness'];common=case.modules['common']
    if fault=='globals':
        original=common.prepare
        common.prepare=FunctionType(original.__code__,dict(original.__globals__),original.__name__)
    elif fault=='runtime':witness._runtime_check.__code__=(lambda:None).__code__
    elif fault=='extra_module':common.extra=common.prepare
    elif fault=='extra_class':witness.Session.extra=witness.Session.check
    elif fault=='loader':common.__loader__=object()
    else:common.witness=bridge
    with pytest.raises(ValueError):case.checked('genesis')
    bridge.unload()
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')


def test_same_code_foreign_globals_is_refused_before_activation(case):
    all_loaded(case);common=case.modules['common'];original=common.prepare
    common.prepare=FunctionType(original.__code__,dict(original.__globals__),original.__name__)
    with pytest.raises(ValueError,match='original weak Common definition changed'):case.modules['bridge'].load()
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')


def test_foreign_creator_cannot_use_or_clear_live_activation(case):
    bridge=all_loaded(case);bridge.load();errors=[]
    def foreign():
        for fn,args in ((case.checked,('genesis',)),(bridge.unload,())):
            try:fn(*args)
            except ValueError as error:errors.append(str(error))
    worker=Thread(target=foreign);worker.start();worker.join(timeout=5)
    assert not worker.is_alive() and len(errors)==2
    assert case.checked('genesis')['generation']==1;bridge.unload()


def test_deactivation_failure_clears_all_active_strong_references(case):
    bridge=all_loaded(case);bridge.load();bridge._DEACTIVATE_FAILURE=True
    with pytest.raises(OSError,match='deactivate primary'):bridge.unload()
    with pytest.raises(ValueError,match='active original'):case.checked('genesis')
    references=[ref(module) for module in case.modules.values()]
    for role,name in case.names.items():
        assert sys.modules.get(name) is case.modules[role]
        del sys.modules[name]
        # Leave a non-owning sentinel for monkeypatch's original teardown; its
        # undo requires the attribute to exist when the original was absent.
        setattr(experiments,name.split('.')[-1],None)
    del bridge;case.modules.clear();gc.collect()
    assert all(reference() is None for reference in references)
