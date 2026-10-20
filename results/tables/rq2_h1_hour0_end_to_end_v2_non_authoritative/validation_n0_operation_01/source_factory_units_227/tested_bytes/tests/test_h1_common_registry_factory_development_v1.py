"""Source-defined factory order and weak output provenance, without N0 reads."""
import gc
from hashlib import sha256
import importlib.util
import sys
from threading import Thread
from types import FunctionType,SimpleNamespace
from weakref import ref

import experiments
import pytest

from experiments import h1_common_registry_factory_development_v1 as m


SOURCE='''import sys
from dataclasses import asdict,dataclass
from experiments import factory_dependency_non_authoritative as dependency
import experiments.factory_dependency_non_authoritative as dependency_alias
from experiments.factory_dependency_non_authoritative import symbol as direct_symbol
from .factory_dependency_non_authoritative import symbol as relative_symbol
_define_common_registry_component=_define_common_registry_component
_register_common_registry_component=_register_common_registry_component
_HOOK=_HOOK
_BUILD_CALLS=0
_FLAG='safe'
class Session:
    def check(self):return self
@dataclass(frozen=True,init=False)
class Data:
    value: bytes
def _helper(value='safe',*,flag=True):return value,flag
def _build():
    global _BUILD_CALLS
    _BUILD_CALLS+=1
    box={'helper':_helper(),'class':Session,'flag':_FLAG}
    def check(value={'first':[1],'last':[2]},*,flag=True):return box,value,flag
    return check
_HOOK('before_build',globals())
_CHECK=_define_common_registry_component(sys.modules[__name__],'_build')
_HOOK('after_build',globals())
def _install():
    def runtime():return _CHECK
    return runtime
_RUNTIME=_define_common_registry_component(sys.modules[__name__],'_install')
_HOOK('before_footer',globals())
_register_common_registry_component(sys.modules[__name__])
'''


@pytest.fixture
def case(tmp_path,monkeypatch):
    root=tmp_path/'source_factories_non_authoritative';root.mkdir()
    roles=('bridge','witness','source','common')
    names={role:'experiments.factory_'+role+'_non_authoritative' for role in roles}
    dependency_name='experiments.factory_dependency_non_authoritative'
    dependency_path=root/'factory_dependency_non_authoritative.py'
    dependency_path.write_text('def symbol():return None\n',encoding='utf-8')
    paths={role:root/(name.rsplit('.',1)[-1]+'.py') for role,name in names.items()}
    for path in paths.values():path.write_text(SOURCE,encoding='utf-8',newline='\n')
    pins={names[role]:sha256(path.read_bytes()).hexdigest() for role,path in paths.items()}
    pins[dependency_name]=sha256(dependency_path.read_bytes()).hexdigest()
    families={'genesis':tuple((names[role],('_build','_install')) for role in roles)}
    define,register,checked=m.build_factory_provenance(root,pins,families)
    hooks={};modules={}
    def install(name,path):
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,name,module)
        monkeypatch.setattr(experiments,name.rsplit('.',1)[-1],module,raising=False)
        return module
    dependency=install(dependency_name,dependency_path)
    exec(compile(dependency_path.read_bytes(),str(dependency_path),'exec',dont_inherit=True),vars(dependency))
    def load(role):
        module=install(names[role],paths[role]);modules[role]=module
        def hook(phase,space):
            function=hooks.get((role,phase))
            if function is not None:function(space)
        module._HOOK=hook;module._define_common_registry_component=define
        module._register_common_registry_component=register
        exec(compile(paths[role].read_bytes(),str(paths[role]),'exec',dont_inherit=True),vars(module))
        return module
    return SimpleNamespace(root=root,roles=roles,names=names,paths=paths,pins=pins,families=families,
        define=define,register=register,checked=checked,hooks=hooks,load=load,modules=modules,dependency=dependency)


def all_loaded(case):
    for role in case.roles:case.load(role)


def test_ordered_original_factories_complete_and_only_return_scalar_observation(case):
    all_loaded(case)
    assert case.checked('genesis')==('source_factory_definitions_complete','genesis',4)
    assert all(module._BUILD_CALLS==1 and module._RUNTIME() is module._CHECK for module in case.modules.values())
    for module in case.modules.values():module._CHECK()[0]['counter']=1
    assert case.checked('genesis')[2]==4


@pytest.mark.parametrize('fault',['function_missing','class_method_missing','factory_globals','factory_code'])
def test_pre_factory_plain_source_keysets_and_code_are_independent(case,fault):
    def change(space):
        if fault=='function_missing':space['Session'].check=None
        elif fault=='class_method_missing':del space['Session'].check
        elif fault=='factory_globals':
            original=space['_build'];space['_build']=FunctionType(original.__code__,dict(space),'_build')
        else:space['_build'].__code__=(lambda:None).__code__
    case.hooks['bridge','before_build']=change
    with pytest.raises(ValueError,match='original plain factory source function'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


@pytest.mark.parametrize('fault',['same_code_closure','cell','defaults','kwdefaults','new_module_callable','new_class_callable'])
def test_minted_outputs_cannot_change_before_footer(case,fault):
    def change(space):
        original=space['_CHECK']
        if fault=='same_code_closure':
            def factory(value):
                def function():return value
                return function
            cells=tuple(factory({}).__closure__[0] for _ in original.__closure__)
            space['_CHECK']=FunctionType(original.__code__,space,original.__name__,original.__defaults__,cells)
        elif fault=='cell':original.__closure__[0].cell_contents={}
        elif fault=='defaults':original.__defaults__[0]['first'].append(2)
        elif fault=='kwdefaults':original.__kwdefaults__['flag']=False
        elif fault=='new_module_callable':space['foreign_callable']=original
        else:space['Session'].foreign=space['Session'].check
    case.hooks['bridge','after_build']=change
    with pytest.raises(ValueError):case.load('bridge')
    with pytest.raises(ValueError,match='completed original'):case.checked('genesis')


@pytest.mark.parametrize('alias',['dependency','dependency_alias','direct_symbol','relative_symbol'])
def test_every_import_syntax_uses_its_canonical_module_or_symbol(case,alias):
    case.hooks['bridge','before_build']=lambda space:space.__setitem__(alias,object())
    with pytest.raises(ValueError,match='import edge'):case.load('bridge')


@pytest.mark.parametrize('fault',['defaults','kwdefaults','wrapped'])
def test_plain_helpers_match_source_defaults_before_factory_execution(case,fault):
    def change(space):
        helper=space['_helper']
        if fault=='defaults':helper.__defaults__=('evil',)
        elif fault=='kwdefaults':helper.__kwdefaults__={'flag':False}
        else:helper.__wrapped__=helper
    case.hooks['bridge','before_build']=change
    with pytest.raises(ValueError,match='source-declared callable defaults'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


@pytest.mark.parametrize('fault',['literal','function_dict','function_annotations','function_name'])
def test_plain_helper_metadata_and_source_literals_are_not_first_use_baselines(case,fault):
    def change(space):
        if fault=='literal':space['_FLAG']='evil'
        elif fault=='function_dict':space['_helper'].policy='evil'
        elif fault=='function_annotations':space['_helper'].__annotations__={'return':'evil'}
        else:space['_helper'].__name__='foreign'
    case.hooks['bridge','before_build']=change
    with pytest.raises(ValueError,match='source-declared .*literal|source-declared callable metadata'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


@pytest.mark.parametrize('fault',['module_getattr','module_dunder','fake_dataclass','generated_method'])
def test_callable_dunders_and_forged_dataclass_marker_do_not_enter_the_baseline(case,fault):
    def change(space):
        foreign=lambda *args:None
        if fault=='module_getattr':space['__getattr__']=foreign
        elif fault=='module_dunder':space['__foreign__']=foreign
        elif fault=='fake_dataclass':
            space['Session'].__dataclass_fields__={}
            space['Session'].__foreign__=foreign
        else:space['Data'].__eq__=foreign
    case.hooks['bridge','before_build']=change
    with pytest.raises(ValueError,match='additional factory'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


@pytest.mark.parametrize('fault',['code','defaults'])
def test_pinned_direct_project_function_semantics_are_checked_on_every_observation(case,fault):
    all_loaded(case)
    function=case.dependency.symbol
    if fault=='code':function.__code__=(lambda:False).__code__
    else:function.__defaults__=('evil',)
    with pytest.raises(ValueError,match='original imported callable|source-declared callable defaults'):
        case.checked('genesis')


@pytest.mark.parametrize('kind',[staticmethod,classmethod,property])
def test_first_inspection_checks_the_source_descriptor_binding_kind(case,kind):
    case.hooks['bridge','before_build']=lambda space:setattr(space['Session'],'check',kind(space['Session'].check))
    with pytest.raises(ValueError,match='descriptor kind'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


def test_additional_class_callable_objects_are_refused_before_factory(case):
    case.hooks['bridge','before_build']=lambda space:setattr(space['Session'],'foreign',dict)
    with pytest.raises(ValueError,match='additional factory class callable'):case.load('bridge')
    assert case.modules['bridge']._BUILD_CALLS==0


def test_factory_uses_independently_minted_class_instead_of_same_shape_offered_identity(case):
    offered=[]
    def change(space):
        original=space['Session']
        values={key:value for key,value in vars(original).items() if key not in ('__dict__','__weakref__')}
        forged=type('Session',original.__bases__,values)
        space['Session']=forged;offered.extend((original,forged))
    case.hooks['bridge','before_build']=change
    module=case.load('bridge')
    assert all(module.Session is not value for value in offered)
    assert module._CHECK()[0]['class'] is module.Session


@pytest.mark.parametrize('fault',['annotation','field','parameters','extra_value'])
def test_minted_class_noncallable_state_is_checked_after_definition(case,fault):
    all_loaded(case);kind=case.modules['source'].Data
    if fault=='annotation':kind.__annotations__['value']=str
    elif fault=='field':kind.__dataclass_fields__['value'].compare=False
    elif fault=='parameters':kind.__dataclass_params__.frozen=False
    else:kind.extra=1
    with pytest.raises(ValueError,match='class state'):case.checked('genesis')


@pytest.mark.parametrize('expression',['type("Export",(),{})','type(sys)("export_non_authoritative")'])
def test_factory_class_or_module_exports_require_a_separate_state_contract(tmp_path,monkeypatch,expression):
    name='experiments.factory_export_non_authoritative';path=tmp_path/'factory_export_non_authoritative.py'
    source=('import sys\ndef _build():return '+expression+'\n'
        "_OUT=_define_common_registry_component(sys.modules[__name__],'_build')\n"
        '_register_common_registry_component(sys.modules[__name__])\n')
    path.write_text(source,encoding='utf-8')
    define,register,_=m.build_factory_provenance(tmp_path,{name:sha256(path.read_bytes()).hexdigest()},
        {'genesis':((name,('_build',)),)})
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,module)
    monkeypatch.setattr(experiments,name.rsplit('.',1)[-1],module,raising=False)
    module._define_common_registry_component=define;module._register_common_registry_component=register
    with pytest.raises(ValueError,match='function export'):
        exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),vars(module))


@pytest.mark.parametrize('body',[
    '    marker=hook()',
    '    marker=HasSetName()',
    '    hook()',
    '    class Nested:pass',
    '    @hook\n    def method(self):pass',
    '    def method(self,value=hook()):pass',
    '    value:hook()',
])
@pytest.mark.parametrize('decorator',['','@dataclass(frozen=True,init=False)\n'])
def test_class_creation_grammar_is_checked_before_any_module_execution(tmp_path,body,decorator):
    name='experiments.factory_class_grammar_non_authoritative';path=tmp_path/'factory_class_grammar_non_authoritative.py'
    source=('import sys\nfrom dataclasses import dataclass\n'+decorator+'class Data:\n'+body+'\n'
        'def _build():return lambda:None\n'
        "_OUT=_define_common_registry_component(sys.modules[__name__],'_build')\n"
        '_register_common_registry_component(sys.modules[__name__])\n')
    path.write_text(source,encoding='utf-8')
    with pytest.raises(ValueError,match='source.class|source-specific contract'):
        m.build_factory_provenance(tmp_path,{name:sha256(path.read_bytes()).hexdigest()},{'genesis':((name,('_build',)),)})


def test_direct_repeated_and_skipped_factory_routes_are_refused(case):
    module=case.load('bridge')
    with pytest.raises(ValueError,match='CALLsite'):case.define(module,'_build')
    with pytest.raises(ValueError,match='CALLsite'):case.register(module)
    with pytest.raises(ValueError,match='one-shot'):
        exec(compile(SOURCE,str(case.paths['bridge']),'exec',dont_inherit=True),vars(module))
    with pytest.raises(ValueError,match='one-shot'):case.load('source')


def test_foreign_creator_cannot_claim_an_original_module_factory(case):
    errors=[]
    def foreign():
        try:case.load('bridge')
        except ValueError as error:errors.append(str(error))
    worker=Thread(target=foreign);worker.start();worker.join(timeout=5)
    assert not worker.is_alive() and len(errors)==1 and 'one-shot' in errors[0]
    assert case.load('bridge')._BUILD_CALLS==1


def test_same_code_module_reentry_during_factory_is_refused(case):
    # The injected callback executes the exact source while the first definition
    # reservation is live. It cannot claim a second original factory event.
    original=SOURCE.replace('    _BUILD_CALLS+=1','    _BUILD_CALLS+=1\n    _HOOK("during_factory",globals())')
    case.paths['bridge'].write_text(original,encoding='utf-8',newline='\n')
    pins=dict(case.pins);pins[case.names['bridge']]=sha256(case.paths['bridge'].read_bytes()).hexdigest()
    case.define,case.register,case.checked=m.build_factory_provenance(case.root,pins,case.families)
    # load closes over its original operations, so install a separate module.
    spec=importlib.util.spec_from_file_location(case.names['bridge'],case.paths['bridge'])
    module=importlib.util.module_from_spec(spec);name=case.names['bridge']
    prior=sys.modules.get(name);prior_alias=vars(experiments).get(name.rsplit('.',1)[-1])
    sys.modules[name]=module;setattr(experiments,name.rsplit('.',1)[-1],module)
    module._define_common_registry_component=case.define;module._register_common_registry_component=case.register
    def hook(phase,space):
        if phase=='during_factory':
            exec(compile(original,str(case.paths['bridge']),'exec',dont_inherit=True),space)
    module._HOOK=hook
    try:
        with pytest.raises(ValueError,match='one-shot'):
            exec(compile(original,str(case.paths['bridge']),'exec',dont_inherit=True),vars(module))
    finally:
        if prior is None:sys.modules.pop(name,None)
        else:sys.modules[name]=prior
        setattr(experiments,name.rsplit('.',1)[-1],prior_alias)


def test_source_pin_drift_and_post_footer_changes_are_refused(case):
    all_loaded(case);module=case.modules['source'];module._CHECK.__closure__[0].cell_contents={}
    with pytest.raises(ValueError,match='original callable'):case.checked('genesis')
    case.paths['bridge'].write_text(SOURCE+'\n# drift\n',encoding='utf-8')
    with pytest.raises(ValueError,match='source pin'):case.checked('genesis')


def test_completed_weak_observations_do_not_hold_unloaded_modules(case):
    all_loaded(case);references=[ref(module) for module in case.modules.values()]
    for name in case.names.values():
        sys.modules.pop(name,None);setattr(experiments,name.rsplit('.',1)[-1],None)
    case.modules.clear();gc.collect()
    assert all(reference() is None for reference in references)
    with pytest.raises(ValueError):case.checked('genesis')


@pytest.mark.parametrize('bad',[{'name':object()},[],{'x':(('experiments.bad',('_build',)),)}])
def test_nonliteral_or_unpinned_manifest_is_rejected_before_source_reads(case,bad):
    with pytest.raises(ValueError):m.build_factory_provenance(case.root,case.pins,bad)
