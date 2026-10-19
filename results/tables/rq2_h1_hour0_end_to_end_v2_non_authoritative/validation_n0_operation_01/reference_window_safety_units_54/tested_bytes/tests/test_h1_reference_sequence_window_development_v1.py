"""Window reduction, differential literal payload and adversarial lifecycle cases.

Source/Parent method bodies are real; replay mathematics and transport here are
explicit synthetic fixtures. Genuine saved-root coverage is a separate gate.
"""
from dataclasses import dataclass
import json
import sys
from threading import Thread
from types import FunctionType

import pytest

from tests.test_h1_selector_source_window_development_v2 import case
from tests.h1_reference_window_test_helpers_v1 import Literal


KINDS=('run_pre','run_release','run_quiet','run_post','validate')


def released(case):
    assert all(not obj._guard.locked() and not obj._reference_held for obj in case.parents)
    case.api.assert_idle(case.ref)


@pytest.mark.parametrize('kind',KINDS)
def test_reduced_calls_preserve_entire_typed_scientific_payload(case,kind,tmp_path):
    owner=case.run(kind,True)
    receipt=case.api.receipts(owner)[0]['reference_window']
    assert case.reference_counts['original']==2
    assert case.reference_counts['configurations']==2
    first,tail=case.reference_results
    literal=case.engine.reference_windows.literal
    assert literal._source_signature(first)==literal._source_signature(tail)
    assert literal._source_types(first)==literal._source_types(tail)
    assert all(literal._source_signature(value['replay'])==literal._source_signature(first['replay'])
               for value in case.reference_payloads)
    assert len({id(value) for value in case.reference_payloads})==len(case.reference_payloads)
    assert all(set(value)=={'request_sha256','replay'} for value in case.reference_payloads)
    assert receipt['cache_cleared'] and receipt['legacy_observation_or_report_equal'] is False
    (tmp_path/'reference_window_observation.json').write_text(json.dumps(dict(
        receipt=receipt,counts=case.reference_counts,entire_typed_payload_equal=True,
        numerical_fixture='explicit_synthetic',real_Jobs=0,real_native_calls=0)),encoding='utf-8')
    released(case)


@pytest.mark.parametrize('kind',KINDS)
@pytest.mark.parametrize('at',(1,2))
def test_entry_and_tail_original_errors_keep_primary_and_release(case,kind,at):
    primary=RuntimeError('original reference failure')
    def fail(number):
        if number==at:raise primary
    case.faults['reference_original']=fail
    with pytest.raises(RuntimeError) as caught:case.run(kind,True)
    assert caught.value is primary
    assert case.reference_counts['original']==at
    assert not case.actuals[0]._source_windows
    released(case)


@pytest.mark.parametrize('mutation',('add','delete','bytes','replace_same_bytes'))
def test_full_saved_namespace_digest_and_stamp_drift_refuses_tail(case,mutation):
    def change(value):
        case.faults.pop('borrowed_reference',None)
        path=case.reference_root/'terminal.bin'
        if mutation=='add':(case.reference_root/'extra.bin').write_bytes(b'extra')
        elif mutation=='delete':path.unlink()
        elif mutation=='bytes':path.write_bytes(b'changed terminal')
        else:
            other=path.with_name('replacement.bin');other.write_bytes(path.read_bytes());other.replace(path)
    case.faults['borrowed_reference']=change
    with pytest.raises(ValueError,match='saved view'):case.run('validate',True)
    assert not case.actuals[0]._source_windows
    released(case)


@pytest.mark.parametrize('mutation',('replay','candidate','diagnostics','twin_class'))
def test_cached_replay_nested_graph_changes_are_fatal(case,mutation):
    def change(value):
        case.faults.pop('borrowed_reference',None)
        replay=value['replay']
        if mutation=='replay':object.__setattr__(replay,'request',('2','1'))
        elif mutation=='candidate':object.__setattr__(replay.candidate,'value','changed')
        elif mutation=='diagnostics':object.__setattr__(replay,'diagnostics',((0,'label','accepted',1.,0.),))
        else:
            @dataclass(frozen=True)
            class Twin:value:str
            Twin.__module__,Twin.__qualname__=Literal.__module__,Literal.__qualname__
            object.__setattr__(replay,'candidate',Twin(replay.candidate.value))
    case.faults['borrowed_reference']=change
    with pytest.raises(ValueError,match='reference.*graph'):case.run('validate',True)
    assert not case.actuals[0]._source_windows
    released(case)


def test_tail_error_and_mutated_graph_keep_original_error_and_clear(case):
    primary=RuntimeError('original tail error')
    def fail(number):
        if number==2:
            object.__setattr__(case.reference_results[0]['replay'].candidate,'value','changed at tail')
            raise primary
    case.faults['reference_original']=fail
    with pytest.raises(RuntimeError) as caught:case.run('validate',True)
    assert caught.value is primary
    assert any('reference graph cleanup' in note for note in primary.__notes__)
    assert not case.actuals[0]._source_windows
    released(case)


def test_body_error_after_first_reference_skips_tail_and_keeps_primary(case):
    primary=RuntimeError('body after reference')
    def fail(value):raise primary
    case.faults['borrowed_reference']=fail
    with pytest.raises(RuntimeError) as caught:case.run('validate',True)
    assert caught.value is primary and case.reference_counts['original']==1
    assert not case.actuals[0]._source_windows
    released(case)


def test_second_scientific_key_is_refused_without_a_second_full_replay(case):
    def change(value):
        case.faults.pop('borrowed_reference',None)
        case.reference_arguments['selector']=Literal('different selector')
    case.faults['borrowed_reference']=change
    with pytest.raises(ValueError,match='second reference key'):case.run('validate',True)
    assert case.reference_counts['original']==1
    released(case)


@pytest.mark.parametrize('mutation',('inspect_binding','inspect_code','replay_class','builtin_shadow'))
def test_canonical_dispatch_and_global_changes_are_not_hidden_by_cache(case,mutation):
    old=case.reference_sequence.inspect;code=old.__code__
    def change(value):
        case.faults.pop('borrowed_reference',None)
        if mutation=='inspect_binding':case.reference_sequence.inspect=lambda *a,**kw:None
        elif mutation=='inspect_code':old.__code__=code.replace(co_consts=code.co_consts+('changed',))
        elif mutation=='replay_class':case.reference_sequence.selection.ReplayResult=Literal
        else:old.__globals__['dict']=lambda *a,**kw:None
    case.faults['borrowed_reference']=change
    try:
        with pytest.raises(ValueError):case.run('validate',True)
        assert case.reference_counts['original']==1
        released(case)
    finally:
        old.__code__=code
        if mutation=='builtin_shadow':old.__globals__.pop('dict',None)


@pytest.mark.parametrize('mutation',('wrong_caller','wrong_globals','direct_protocol','close_protocol'))
def test_private_caller_and_protocol_cannot_be_bypassed(case,mutation):
    def change(value):
        case.faults.pop('borrowed_reference',None)
        frame=sys._getframe(1)
        try:
            inspect=frame.f_globals['sequence'].inspect
            if mutation=='wrong_caller':
                with pytest.raises(ValueError):inspect()
            elif mutation=='wrong_globals':
                foreign=FunctionType(frame.f_code,dict(frame.f_globals))
                with pytest.raises(ValueError):foreign(frame.f_locals['declaration'])
            else:
                engine,=[cell.cell_contents for cell in inspect.__closure__ or ()
                         if type(cell.cell_contents).__name__=='generator']
                if mutation=='close_protocol':engine.close()
                else:
                    with pytest.raises(ValueError,match='protocol caller'):engine.send(('finish',None))
        finally:del frame
    case.faults['borrowed_reference']=change
    with pytest.raises(ValueError):case.run('validate',True)
    assert case.reference_counts['original']==1
    assert not case.actuals[0]._source_windows
    released(case)


def test_foreign_thread_refusal_does_not_poison_the_original_creator(case):
    errors=[]
    def change(value):
        case.faults.pop('borrowed_reference',None)
        frame=sys._getframe(1)
        try:inspect=frame.f_globals['sequence'].inspect
        finally:del frame
        def foreign():
            try:inspect()
            except BaseException as error:errors.append(error)
        thread=Thread(target=foreign);thread.start();thread.join(3)
        assert not thread.is_alive()
    case.faults['borrowed_reference']=change
    owner=case.run('validate',True)
    assert len(errors)==1 and isinstance(errors[0],ValueError)
    assert case.api.receipts(owner)[0]['reference_window']['cache_cleared']
    released(case)


def test_reference_helper_runtime_rejects_a_new_builtin_shadow(case):
    module=case.engine.reference_windows
    assert 'dict' not in vars(module)
    vars(module)['dict']=dict
    try:
        with pytest.raises(ValueError):module._RUNTIME()
    finally:vars(module).pop('dict')


@pytest.mark.parametrize('name',('dict','len'))
def test_canonical_property_accessor_builtin_shadows_are_part_of_dependency_closure(monkeypatch,name):
    from experiments import h1_owned_selector_sequence_development_v1 as sequence
    from experiments import h1_reference_sequence_window_development_v1 as window
    from experiments import h1_exact_business_development_v1 as business
    check=window._dependencies(sequence)
    check()
    assert isinstance(vars(business.BusinessCarry)['scientific_payload'],property)
    assert name not in vars(business)
    monkeypatch.setitem(vars(business),name,{'dict':dict,'len':len}[name])
    with pytest.raises(ValueError,match='binding changed'):check()
