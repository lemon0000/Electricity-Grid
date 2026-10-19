"""Definition seals reject drift while permitting explicit state transitions."""
from types import ModuleType

import pytest

from experiments import h1_validation_runtime_closure_development_v1 as seals
from experiments import h1_validation_runtime_closure_development_v2 as frame_safe_seals


@pytest.fixture(autouse=True,params=(seals,frame_safe_seals),ids=('runtime_v1','runtime_v2'))
def runtime_implementation(request,monkeypatch):
    monkeypatch.setitem(globals(),'seals',request.param)


def module():
    result=ModuleType('explicit_runtime_protocol')
    exec('''
def build(runtime):
    binding=None
    records={}
    def bind(value):
        nonlocal binding
        runtime()
        if binding is not None:raise ValueError('already bound')
        nonce=runtime(transition='begin_binding')
        binding=(value,)
        runtime(transition='commit',token=nonce)
    def use():
        runtime()
        records[len(records)]=True
        return all(records.values())
    return bind,use
''',vars(result))
    return result


def test_one_time_binding_and_registry_contents_remain_usable():
    owner=module();runtime,arm=seals.make_runtime(vars(owner),'explicit protocol')
    owner._RUNTIME=runtime
    owner.bind,owner.use=owner.build(runtime)
    arm(transitions=((seals._cell(owner.bind,'binding'),'binding',owner.bind),))
    runtime();owner.bind(object());assert owner.use() and owner.use()
    with pytest.raises(ValueError,match='already bound'):owner.bind(object())
    assert owner.use()


def test_pre_arm_and_duplicate_arm_are_rejected():
    owner=module();owner._RUNTIME,arm=seals.make_runtime(vars(owner),'explicit protocol')
    with pytest.raises(ValueError,match='not armed'):owner._RUNTIME()
    other=module();other._RUNTIME,arm=seals.make_runtime(vars(other),'explicit protocol')
    arm()
    with pytest.raises(ValueError,match='already armed'):arm()


def test_explicit_registry_contents_can_change_but_object_identity_is_fixed(monkeypatch):
    owner=module();owner._OWNERS={}
    runtime,arm=seals.make_runtime(vars(owner),'explicit registry protocol')
    owner._RUNTIME=runtime
    arm(mutable_globals=('_OWNERS',))
    value=object();owner._OWNERS[id(value)]=value;runtime()
    owner._OWNERS.clear();runtime()
    monkeypatch.setattr(owner,'_OWNERS',{})
    with pytest.raises(ValueError,match='definition-time'):runtime()


@pytest.mark.parametrize('name',('LIMITS','_LIMITS'))
def test_public_and_unlisted_private_constant_maps_remain_frozen(name):
    owner=module();setattr(owner,name,dict(size=1))
    runtime,arm=seals.make_runtime(vars(owner),'constant protocol');owner._RUNTIME=runtime;arm()
    getattr(owner,name)['size']=2
    with pytest.raises(ValueError,match='constants changed'):runtime()


@pytest.mark.parametrize('name',('LIMITS','__dict__','_missing'))
def test_registry_role_cannot_waive_public_or_non_dictionary_bindings(name):
    owner=module();owner.LIMITS=dict(size=1)
    runtime,arm=seals.make_runtime(vars(owner),'constant protocol');owner._RUNTIME=runtime
    with pytest.raises(ValueError,match='private dictionary registry'):arm(mutable_globals=(name,))


def test_foreign_binding_pre_set_cannot_be_blessed_by_original_bind():
    owner=module();runtime,arm=seals.make_runtime(vars(owner),'explicit protocol')
    owner._RUNTIME=runtime;owner.bind,owner.use=owner.build(runtime)
    cell=seals._cell(owner.bind,'binding')
    arm(transitions=((cell,'binding',owner.bind),))
    cell.cell_contents=(object(),)
    with pytest.raises(ValueError,match='outside original transition'):owner.bind(object())


def active_module():
    owner=ModuleType('explicit_active_protocol')
    exec('''
def build(runtime):
    active=None
    def claim(row,hook=None):
        nonlocal active
        runtime()
        if active is not None:raise ValueError('nonreentrant')
        nonce=runtime(transition='begin_active_claim')
        if hook is not None:hook()
        active=row
        runtime(transition='commit',token=nonce)
    def clear(row):
        nonlocal active
        runtime()
        if active is not row:raise ValueError('original row required')
        nonce=runtime(transition='begin_active_clear')
        active=None
        runtime(transition='commit',token=nonce)
    return claim,clear
''',vars(owner))
    runtime,arm=seals.make_runtime(vars(owner),'explicit active protocol')
    owner._RUNTIME=runtime;owner.claim,owner.clear=owner.build(runtime)
    cell=seals._cell(owner.claim,'active')
    arm(transitions=((cell,'active',(owner.claim,owner.clear)),))
    return owner,runtime,cell


def test_active_claim_and_clear_are_synchronously_committed_even_after_body_failure():
    owner,runtime,cell=active_module()
    for fail in (True,False):
        row={};owner.claim(row)
        try:
            if fail:raise RuntimeError('body failure')
        except RuntimeError:pass
        finally:owner.clear(row)
        assert cell.cell_contents is None
        runtime()


@pytest.mark.parametrize('entry',('runtime','clear','claim'))
def test_foreign_active_clear_is_rejected_from_every_next_entry(entry):
    owner,runtime,cell=active_module();row={};owner.claim(row)
    cell.cell_contents=None
    with pytest.raises(ValueError,match='outside original transition'):
        if entry=='runtime':runtime()
        elif entry=='clear':owner.clear(row)
        else:owner.claim({})


def test_competing_thread_during_transition_cannot_poison_creator():
    from threading import Thread
    owner,runtime,cell=active_module();errors=[]
    def compete():
        try:runtime()
        except BaseException as error:errors.append(error)
    def hook():
        thread=Thread(target=compete);thread.start();thread.join(timeout=3)
        assert not thread.is_alive()
    row={};owner.claim(row,hook);owner.clear(row);runtime()
    assert len(errors)==1 and 'nonreentrant' in str(errors[0])


@pytest.mark.parametrize('command',('send','close'))
def test_direct_generator_transport_never_accepts_runtime_control(command):
    owner,runtime,cell=active_module()
    generator=seals._cell(runtime,'generator').cell_contents
    if command=='send':
        with pytest.raises(ValueError,match='transport caller'):generator.send(('check',()))
    else:generator.close()
    with pytest.raises(ValueError,match='definition-time'):runtime()


@pytest.mark.parametrize('fault',('alias','builtin','closure','code','defaults'))
def test_drift_rejected_before_registry_mutation(fault,monkeypatch):
    owner=module();runtime,arm=seals.make_runtime(vars(owner),'explicit protocol')
    owner._RUNTIME=runtime;owner.bind,owner.use=owner.build(runtime)
    arm(transitions=((seals._cell(owner.bind,'binding'),'binding',owner.bind),))
    records=seals._cell(owner.use,'records').cell_contents
    if fault=='alias':monkeypatch.setattr(owner,'_RUNTIME',lambda:None)
    elif fault=='builtin':monkeypatch.setattr(owner,'all',lambda *a:True,raising=False)
    elif fault=='closure':monkeypatch.setattr(seals._cell(owner.use,'records'),'cell_contents',{})
    elif fault=='code':monkeypatch.setattr(owner.build,'__code__',(lambda runtime:None).__code__)
    else:monkeypatch.setattr(owner.build,'__defaults__',(None,))
    with pytest.raises(ValueError,match='definition-time'):owner.use()
    assert records=={}


@pytest.mark.parametrize('name',('read','make','value'))
def test_descriptor_accessors_are_included(name,monkeypatch):
    owner=module()
    exec('''
class Protocol:
    @staticmethod
    def read():return 1
    @classmethod
    def make(cls):return cls()
    @property
    def value(self):return 1
''',vars(owner))
    runtime,arm=seals.make_runtime(vars(owner),'explicit protocol')
    owner._RUNTIME=runtime
    attributes=tuple((owner.Protocol,key,vars(owner.Protocol)[key]) for key in ('read','make','value'))
    arm(attributes=attributes);runtime()
    descriptor=vars(owner.Protocol)[name]
    function=descriptor.fget if name=='value' else descriptor.__func__
    monkeypatch.setattr(function,'__code__',(lambda *args:2).__code__)
    with pytest.raises(ValueError,match='definition-time'):runtime()
