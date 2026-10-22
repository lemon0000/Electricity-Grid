"""Finite runtime/failure windows and all-hour retention, without solver calls."""
import ast
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import pytest

from experiments import h1_phase_historical_batch_development_v3 as history
from experiments import h1_phase_exact_source_batch_development_v3 as source
from experiments import h1_constructor_source_batch_validation_development_v2 as validator
from experiments import h1_constructor_rejection_support_development_v1 as support
from tests.test_h1_constructor_rejection_support_development_v1 import reader_with_owners
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.mark.parametrize('target', ['number_global','validator_global','model_json','borrowed_digest',
    'borrowed_identity','packet_validate','inventory','Path_read','Path_read_code','Path_stat',
    'Path_resolve','Path_truediv','Path_parents','concrete_new','guard_check','guard_state'])
def test_named_runtime_rejects_concrete_drift(monkeypatch,target):
    history._check_dependencies()
    with monkeypatch.context() as patch:
        if target=='number_global':patch.setattr(history.model,'isfinite',lambda value:False)
        elif target=='validator_global':patch.setitem(history.model._validate_request.__globals__,'_finite',lambda *a:None)
        elif target=='model_json':patch.setattr(history.model,'json',SimpleNamespace(dumps=lambda *a,**k:' '))
        elif target=='borrowed_digest':patch.setattr(history.packet_source,'_digest',lambda *a:'0'*64)
        elif target=='borrowed_identity':patch.setattr(history.packet_source,'normal_input_identity',lambda *a:'0'*64)
        elif target=='packet_validate':patch.setattr(history.packet_source,'validate_current',lambda *a:None)
        elif target=='inventory':patch.setattr(history.history,'_inventory',lambda *a,**k:set())
        elif target=='Path_read':patch.setattr(Path,'read_bytes',lambda path:b'')
        elif target=='Path_read_code':patch.setattr(Path.read_bytes,'__code__',Path.read_bytes.__code__.replace(co_name='fault'))
        elif target=='Path_stat':patch.setattr(Path,'stat',lambda path:None)
        elif target=='Path_resolve':patch.setattr(Path,'resolve',lambda path:path)
        elif target=='Path_truediv':patch.setattr(Path,'__truediv__',lambda path,other:path)
        elif target=='Path_parents':patch.setattr(Path,'parents',property(lambda path:()))
        elif target=='concrete_new':patch.setattr(type(Path()),'__new__',lambda *a:None)
        elif target=='guard_check':patch.setattr(history.runtime.NamedRuntimeSnapshot,'check',lambda self:None)
        elif target=='guard_state':patch.setattr(history.runtime,'same_function',lambda *a:True)
        with pytest.raises(ValueError,match='changed'):
            history._check_dependencies()
    history._check_dependencies()


def closure_cell(function,name):
    return dict(zip(function.__code__.co_freevars,function.__closure__))[name]


def replay_ast():
    tree=ast.parse(Path(history.__file__).read_text(encoding='utf-8'))
    return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='replay_prefixes')


def real_finally_program():
    """Execute the actual replay finally block against owned-resource stand-ins."""
    function=replay_ast()
    attempt=next(n for n in function.body if isinstance(n,ast.Try))
    args='close_reader,reader,leases,captured,completed,all_packets,seen_hours,stage_seconds,metrics,began'
    text='def finish('+args+'):\n'+''.join('    '+line+'\n' for node in attempt.finalbody
        for line in ast.unparse(node).splitlines())
    namespace=dict(time=time,sys=sys)
    exec(compile(text,'<actual replay finally>','exec'),namespace)
    return namespace['finish']


@pytest.mark.parametrize('drift', ['alias','code','defaults','kwdefaults','cell',
                                 'inner_parent_code','inner_parent_global','inner_driver_code'])
@pytest.mark.parametrize('failure', [None,'_anchor','outer'])
def test_helper_fault_rejected_and_independent_cleanup_attempts_original_owners(monkeypatch,drift,failure):
    reader,owners,calls,Owner=reader_with_owners(failure)
    outer=Owner('outer');captured={0:object()};primary=ValueError('original validation fault')
    function=support.close_replay
    with monkeypatch.context() as patch:
        if drift=='alias':patch.setattr(support,'close_replay',lambda *a:None)
        elif drift=='code':patch.setattr(function,'__code__',function.__code__.replace(co_name='fault'))
        elif drift=='defaults':patch.setattr(function,'__defaults__',(None,))
        elif drift=='kwdefaults':patch.setattr(function,'__kwdefaults__',{'fault':True})
        elif drift=='cell':patch.setattr(closure_cell(function,'frozen_parent'),'cell_contents',lambda *a:None)
        elif drift=='inner_parent_code':
            inner=closure_cell(function,'frozen_parent').cell_contents
            patch.setattr(inner,'__code__',(lambda self:None).__code__)
        elif drift=='inner_parent_global':
            inner=closure_cell(function,'frozen_parent').cell_contents
            patch.setitem(inner.__globals__['__builtins__'],'setattr',lambda *a:None)
        elif drift=='inner_driver_code':
            inner=closure_cell(function,'frozen_driver').cell_contents
            patch.setattr(inner,'__code__',(lambda *a:None).__code__)
        with pytest.raises(ValueError,match='changed'):history._check_dependencies()
        history._close_replay(reader,[outer],captured,False,primary)
    assert calls==['_journal','_anchor','_root_lease','outer'] and captured=={}
    assert all(owner.closed for owner in (*owners,outer) if owner.name!=failure)
    assert reader._closed and all(getattr(reader,name) is None for name in ('_journal','_anchor','_root_lease'))
    assert reader._cic_value is history.capture._EMPTY
    if failure:assert 'batch historical cleanup also failed' in primary.__notes__
    history._check_dependencies()


@pytest.mark.parametrize('failure',[None,'_journal','outer'])
@pytest.mark.parametrize('completed',[False,True])
def test_private_packet_containers_clear_even_when_cleanup_raises(failure,completed):
    reader,owners,calls,Owner=reader_with_owners(failure)
    packets={0:(object(),('a','b','c'))};seen=[0];captured={0:object()};outer=Owner('outer')
    if failure:
        with pytest.raises(RuntimeError,match='named owner close failure'):
            real_finally_program()(history._close_replay,reader,[outer],captured,completed,packets,seen,{}, {},0.)
    else:
        real_finally_program()(history._close_replay,reader,[outer],captured,completed,packets,seen,{}, {},0.)
    assert packets=={} and seen==[]
    assert bool(captured)==(completed and failure is None)
    assert calls==['_journal','_anchor','_root_lease','outer']


@pytest.mark.parametrize('drift',['alias','code'])
def test_actual_new_program_hands_partial_constructor_instance_to_frozen_cleanup(monkeypatch,drift):
    function=replay_ast()
    reader_class=next(n for n in ast.walk(function) if isinstance(n,ast.ClassDef) and n.name=='Reader')
    new=next(n for n in reader_class.body if isinstance(n,ast.FunctionDef) and n.name=='__new__')
    text=('def make():\n    reader=None\n    class Reader(Capture,Historical):\n'
          +''.join('        '+line+'\n' for line in ast.unparse(new).splitlines())
          +'    return Reader,lambda:reader\n')
    namespace=dict(Capture=history.ConstructorInspectionCapture,Historical=history.HistoricalTimedSnapshot)
    exec(compile(text,'<actual replay Reader new>','exec'),namespace)
    Reader,partial=namespace['make']()
    reference,owners,calls,Owner=reader_with_owners()
    def failed_init(self,*args,**kwargs):
        self._guard=reference._guard;self._closed=False
        for name,owner in zip(('_journal','_anchor','_root_lease'),owners):setattr(self,name,owner)
        try:raise ValueError('constructor fault after inner owners')
        except BaseException:
            self.close()
            raise
    parent=history.binding.snapshot.parent.SourceParent
    with monkeypatch.context() as patch:
        patch.setattr(history.HistoricalTimedSnapshot,'__init__',failed_init)
        if drift=='alias':patch.setattr(parent,'close',lambda self:None)
        else:patch.setattr(parent.close,'__code__',(lambda self:None).__code__)
        with pytest.raises(ValueError,match='constructor fault after inner owners') as error:
            Reader()
        assert partial() is not None and calls==[]
        history._close_replay(partial(),[],{},False,error.value)
    assert calls==['_journal','_anchor','_root_lease'] and all(owner.closed for owner in owners)
    assert partial()._cic_value is history.capture._EMPTY


@pytest.mark.parametrize('field', ['input_identity','audit_identity','source_timestamp','workload_projection_payload'])
def test_all_hour_revalidation_rejects_packet_drift_even_if_hour_is_not_selected(field):
    value=packet();packets={}
    assert history._remember_packet(packets,value,1)>0
    history._validate_all_packets(packets,1)
    object.__setattr__(value,field,b'fault' if field=='workload_projection_payload' else 'fault')
    with pytest.raises((ValueError,KeyError)):
        history._validate_all_packets(packets,1)


def test_all_hour_full_digest_preserves_original_even_for_internally_valid_new_packet():
    value=packet();packets={};history._remember_packet(packets,value,1)
    stamp=value.source_timestamp.replace('2025','2024')
    if stamp==value.source_timestamp:
        stamp='2001-01-01T00:00:00' + ('+00:00' if value.source_time_basis=='aware_source' else '')
    object.__setattr__(value,'source_timestamp',stamp)
    object.__setattr__(value,'audit_identity',history.packet_source._audit_identity(stamp,
        value.source_time_basis,value.workload_projection_payload,value.input_identity))
    history.packet_source.validate_current(value)
    with pytest.raises(ValueError,match='all-hour packet identity changed'):
        history._validate_all_packets(packets,1)


def test_packet_inventory_rejects_overwrite_missing_and_wrong_type():
    packets={};value=packet();history._remember_packet(packets,value,2)
    with pytest.raises(ValueError,match='chronological'):history._remember_packet(packets,value,2)
    with pytest.raises(ValueError,match='complete chronological'):history._validate_all_packets(packets,2)
    with pytest.raises((ValueError,AttributeError)):history._remember_packet({},SimpleNamespace(relative_hour=0),1)


def metric(token):
    return dict(completed_hours=3,selected_hours=[2],parent_inspect_traversals=1,
        constructor_inspection_reused=True,normal_model_dependency_bookends_verified=True,
        all_hour_packet_count=3,all_hour_packet_revalidation_verified=True,
        parent_namespace_bookends_verified=True,parent_namespace_observations=3,
        final_post_revalidation_bookends_verified=True,named_runtime_bookends_verified=True,
        complete_dynamic_input_closure_proved=False,unobserved_between_bookends_ABA_covered=False,
        selected_frame_bytes=2,all_hour_packet_bytes=3,combined_retained_bytes=5,
        retained_cap_bytes=history.MAX_RETAINED_BYTES,observation_token=token*32,
        named_runtime_inventory=dict(history._RUNTIME.summary))


@pytest.mark.parametrize('reader',[0,1])
@pytest.mark.parametrize('name,value', [('all_hour_packet_count',True),('all_hour_packet_count',2),
    ('all_hour_packet_revalidation_verified',None),('parent_namespace_bookends_verified',False),
    ('parent_namespace_observations',2),('final_post_revalidation_bookends_verified',1),
    ('named_runtime_bookends_verified',False),('complete_dynamic_input_closure_proved',True),
    ('unobserved_between_bookends_ABA_covered',None),('combined_retained_bytes',4),
    ('all_hour_packet_bytes',True),('retained_cap_bytes',history.MAX_RETAINED_BYTES+1)])
def test_each_reader_metric_is_required_at_source_and_detached_validator(reader,name,value):
    metrics=[metric('a'),metric('b')];metrics[reader][name]=value
    with pytest.raises(ValueError):source._validate_reader_metrics(*metrics,3)
    result=source.CurrentBatch({},tuple(metrics))
    with pytest.raises(ValueError):validator.validate_detached_batch(result,None,{0:'x',1:'x',2:'x'},(),None)


def test_combined_retention_cap_and_independent_tokens_are_enforced():
    a,b=metric('a'),metric('b');source._validate_reader_metrics(a,b,3)
    a.update(selected_frame_bytes=history.MAX_RETAINED_BYTES-1,all_hour_packet_bytes=2,
             combined_retained_bytes=history.MAX_RETAINED_BYTES+1)
    with pytest.raises(ValueError):source._validate_reader_metrics(a,b,3)
    with pytest.raises(ValueError,match='distinct'):source._validate_reader_metrics(metric('a'),metric('a'),3)


def test_runtime_snapshot_has_hard_caps_and_explicit_endpoint_limits():
    value=history._RUNTIME
    assert len(value.functions)<=history.runtime.MAX_FUNCTIONS
    assert len(value.slots)<=history.runtime.MAX_SLOTS
    assert len(value.classes)<=history.runtime.MAX_CLASSES
    assert value.summary['complete_dynamic_input_closure_proved'] is False
    assert value.summary['unobserved_between_bookends_ABA_covered'] is False


def test_required_solver_forbidden_window_keeps_runtime_guard_usable():
    with history.history.replay.guard.solver_calls_forbidden():
        history._check_dependencies()


@pytest.mark.parametrize('field',['functions','slots','classes','objects','summary'])
def test_runtime_record_removal_is_rejected_before_runtime_check(monkeypatch,field):
    original=getattr(history._RUNTIME,field)
    with monkeypatch.context() as patch:
        patch.setattr(history._RUNTIME,field,{} if field=='summary' else ())
        with pytest.raises(ValueError,match='observation structure changed'):history._check_dependencies()
    assert getattr(history._RUNTIME,field) is original
    history._check_dependencies()


def test_runtime_summary_mutation_is_rejected(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setitem(history._RUNTIME.summary,'functions',0)
        with pytest.raises(ValueError,match='observation structure changed'):history._check_dependencies()
    history._check_dependencies()


@pytest.mark.parametrize('module,name',[(history,'_check_dependencies'),(source,'_check_reader_entry')])
@pytest.mark.parametrize('drift',['alias','code','defaults'])
def test_operation_uses_independent_checker_before_entering_changed_public_guard(monkeypatch,module,name,drift):
    function=getattr(module,name)
    with monkeypatch.context() as patch:
        if drift=='alias':patch.setattr(module,name,lambda:None)
        elif drift=='code':patch.setattr(function,'__code__',(lambda:None).__code__)
        else:patch.setattr(function,'__defaults__',(True,))
        with pytest.raises(ValueError,match='changed'):
            if module is history:
                module.replay_prefixes('unused',expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
                    completed_hours=1,expected_terminals={0:'b'*64},selected_hours=(0,))
            else:
                module.prepare_many('unused',expected_binding_sha256='a'*64,expected_terminals={0:'b'*64},
                    selected_hours=(0,),expected_registry_identity='c'*64)


def test_all_packet_loop_is_followed_by_original_and_new_final_bookends():
    # Structural order supplements behavioral helpers; saved H3 exercises the
    # actual constructor/replay path independently of this narrow assertion.
    tree=ast.parse(Path(history.__file__).read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='replay_prefixes')
    calls=[(ast.unparse(n.func),n.lineno) for n in ast.walk(function) if isinstance(n,ast.Call)]
    loop=next(line for name,line in calls if name=='_validate_all_packets')
    for name in ('base.entry.unchanged','inventory','_observe_prefix','_observe_sources',
                 'support.observe_parent_names','_model_dependencies_unchanged','check_dependencies'):
        assert any(found==name and line>loop for found,line in calls)
    returns=[n.lineno for n in ast.walk(function) if isinstance(n,ast.Return) and isinstance(n.value,ast.Tuple)]
    assert max(returns)>max(line for name,line in calls if name=='check_dependencies')
