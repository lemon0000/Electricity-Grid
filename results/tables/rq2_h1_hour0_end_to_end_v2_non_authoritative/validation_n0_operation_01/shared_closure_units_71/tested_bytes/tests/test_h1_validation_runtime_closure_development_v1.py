"""Definition seals reject drift while permitting explicit state transitions."""
from types import ModuleType

import pytest

from experiments import h1_validation_runtime_closure_development_v1 as seals


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
        binding=(value,)
        runtime()
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
