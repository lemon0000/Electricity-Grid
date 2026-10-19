"""Safe defaults, closure drift, bounded literals and non-owning observations."""
import gc
from types import FunctionType,ModuleType
from weakref import ref

import pytest

from experiments import h1_validation_callable_state_development_v1 as m


def test_nested_builtin_defaults_and_kwdefaults_are_observed_before_use(tmp_path):
    def function(value={'x':[1,2]},*,flag=True):return value,flag
    observation=m.weak_observation(function);m.check_weak(observation,function)
    function.__defaults__[0]['x'].append(3)
    with pytest.raises(ValueError,match='original callable'):m.check_weak(observation,function)
    observation=m.weak_observation(function);function.__kwdefaults__['flag']=False
    with pytest.raises(ValueError,match='original callable'):m.check_weak(observation,function)


@pytest.mark.parametrize('kind',['raising','reentrant'])
def test_nonliteral_default_repr_never_executes(kind):
    calls=[]
    class Argument:
        def __repr__(self):
            calls.append('repr')
            if kind=='raising':raise RuntimeError('repr failure')
            return m.literal(self)
    def function():return None
    function.__defaults__=(Argument(),)
    with pytest.raises(ValueError,match='exact builtin literal'):m.weak_observation(function)
    assert not calls


def test_closure_cell_replacement_and_same_code_forged_closure_are_refused():
    module=ModuleType('owned_source_non_authoritative')
    def factory(value):
        def function():return value
        return function
    function=factory(module);observation=m.weak_observation(function)
    forged=FunctionType(function.__code__,function.__globals__,function.__name__,
        function.__defaults__,factory(ModuleType('foreign_non_authoritative')).__closure__)
    with pytest.raises(ValueError,match='original callable'):m.check_weak(observation,forged)
    function.__closure__[0].cell_contents=ModuleType('replacement_non_authoritative')
    with pytest.raises(ValueError,match='original callable'):m.check_weak(observation,function)


def test_mutable_private_container_identity_is_fixed_and_observation_is_non_owning():
    module=ModuleType('temporary_non_authoritative');reference=ref(module);state={}
    def factory():
        def function():return module,state
        return function
    function=factory();observation=m.weak_observation(function)
    state['step']=1;m.check_weak(observation,function)
    del function,module;gc.collect()
    assert reference() is None and observation[0]() is None


@pytest.mark.parametrize('kind',['cycle','depth','width','scalar'])
def test_literal_resource_limits_fail_before_arbitrary_representation(kind):
    if kind=='cycle':value=[];value.append(value)
    elif kind=='depth':
        value=None
        for _ in range(34):value=[value]
    elif kind=='width':value=[0]*8193
    else:value='x'*65537
    with pytest.raises(ValueError):m.literal(value)


def test_raising_repr_and_note_override_cannot_replace_primary():
    calls=[]
    class Error(RuntimeError):
        def __repr__(self):calls.append('repr');raise AssertionError('repr executed')
        def add_note(self,message):calls.append('note');raise AssertionError('note override executed')
    primary=Error('primary');secondary=Error('cleanup')
    m.note(primary,'cleanup: '+m.describe(secondary))
    assert primary.args==('primary',) and primary.__notes__==['cleanup: BaseException: cleanup']
    assert not calls
