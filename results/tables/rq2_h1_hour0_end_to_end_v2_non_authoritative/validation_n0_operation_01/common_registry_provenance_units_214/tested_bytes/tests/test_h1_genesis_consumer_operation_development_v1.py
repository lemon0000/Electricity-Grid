"""Real Snapshot/Genesis observations over explicit fake N0 and common routes.

This exercises consumer code and guards; it is not numerical source or Job
acceptance. Scientific equivalence and the connected workflow have separate
bounded diagnostics.
"""
from contextlib import ExitStack,nullcontext
from dataclasses import replace,fields,is_dataclass
from fractions import Fraction
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace,ModuleType,FunctionType

import experiments
import pytest

from tests.test_h1_common_genesis_validation_operation_development_v1 import case,create,setup,legacy_setup
from tests.test_h1_selector_phase_handoff_development_v5 import static_identity_test_seam,load_handoff
from tests.test_h1_selector_parent_controller_development_v3 import ExplicitSyntheticPreparedCurrent,sequence_factory
from tests import h1_hour0_synthetic_harness_v3 as parent_cases
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.h1_hour0_synthetic_harness_v3 import load
from tests.h1_gil_stack_observer_development_v1 import observe_owner_stack


class CloseFaultStream:
    """One owned OS stream; failed close leaves the actual handle open."""
    def __init__(self,stream,faults):self.stream=stream;self.faults=faults
    def __getattr__(self,name):return getattr(self.stream,name)
    @property
    def closed(self):return self.stream.closed
    def close(self):
        if self.faults.get('target_stream') is self and self.faults.get('stream_close_failures',0):
            self.faults['stream_close_failures']-=1
            raise RuntimeError('synthetic capsule stream close failure')
        self.stream.close()


@pytest.fixture
def observed(case,monkeypatch,no_solver,request,sequence_factory,tmp_path):
    c=case;s=c.phase_setup
    s.manifest=replace(s.manifest,solver_specification=replace(s.manifest.solver_specification,
        name='gurobi',expected_package_version=version('gurobipy')))
    if getattr(request,'param',None)=='unresolved':
        first=s.manifest.lanes[0]
        s.manifest=replace(s.manifest,lanes=(replace(first,
            mechanism=replace(first.mechanism,flexible_fraction=Fraction(1,2))),))
    elif getattr(request,'param',None)=='three':
        first=s.manifest.lanes[0]
        s.manifest=replace(s.manifest,lanes=tuple(replace(first,lane_id=name) for name in ('a','b','c')))
    for hour,current in tuple(s.currents.items()):
        if not is_dataclass(current.prepared_current):
            values={field.name:getattr(current,field.name) for field in fields(current)}
            values['prepared_current']=ExplicitSyntheticPreparedCurrent(**vars(current.prepared_current))
            s.currents[hour]=c.host.phase.source.normal._owned(c.host.phase.source.ExactSourceCurrent,**values)
    prepare_parent=None
    if getattr(request,'param',None) in ('unresolved','three'):
        # All explicit producer/identity/I/O seams precede the active Genesis
        # observation. Only the consumer imports and snapshots follow it.
        prepare_parent=parent_cases.harness.__wrapped__(None,sequence_factory,monkeypatch,tmp_path,prepare_only=True)
    fault=getattr(getattr(request.node,'callspec',None),'params',{}).get('fault')
    c.external_faults={}
    if fault in ('close_before','close_middle'):
        original_close=c.host.CommonOwnerGenesis._close_handles;faults=c.external_faults
        original_init=c.host.bootstrap.local._Lease.__init__
        def init(lease,*args,**kwargs):
            original_init(lease,*args,**kwargs)
            lease.stream=CloseFaultStream(lease.stream,faults)
        monkeypatch.setattr(c.host.bootstrap.local._Lease,'__init__',init)
        def failing_close(owner):
            if faults.pop('close_once',False):
                if fault=='close_middle':owner._original_phase.close()
                raise RuntimeError('synthetic predecessor close failure')
            return original_close(owner)
        monkeypatch.setattr(c.host.CommonOwnerGenesis,'_close_handles',failing_close)
    from experiments import h1_owned_selector_sequence_development_v1 as sequence
    original_sequence_identity=sequence_factory.original_identity_functions.get(sequence)
    if original_sequence_identity is not None:
        monkeypatch.setattr(sequence,'implementation_identity',original_sequence_identity)
    with static_identity_test_seam(monkeypatch):
        context,receipt=c.adapter.operation(c.host)
        stacks=(observe_owner_stack(tmp_path/'genesis_python_stacks.jsonl',interval_seconds=30,
            max_samples=24,max_bytes=1024**2) if request.node.name.startswith('test_three_actual_parents_')
            else nullcontext(None))
        with context,stacks as stack_receipt:
            root=Path(c.host.__file__).parent
            snapshot=load(str(root/'h1_selector_input_snapshot_development_v2.py'),
                'experiments.h1_selector_input_snapshot_development_v2',monkeypatch,
                {'h1_common_owner_genesis_development_v2':c.host})
            monkeypatch.setattr(experiments,'h1_selector_input_snapshot_development_v2',snapshot)
            frame=s.currents[0].prepared_current.frame
            budget=snapshot.sequence.configuration_api.process.TaskProcessBudget(
                300,.05,512*1024**2,768*1024**2,2)
            config=snapshot.sequence.configuration_api.SelectorRunConfiguration(frame.normal_network_identity,
                tuple(g.uid for g in frame.info.network.units),s.manifest.reference_selector,
                s.manifest.actual_selector,s.manifest.solver_specification,s.manifest.replay_limits,
                budget,budget,2,2)
            owner=create(c)
            c.original_resource_streams=tuple(getattr(getattr(owner,name),
                '_original_lease' if name=='_original_journal' else '_lease_object').stream
                for name in ('_original_phase','_original_holder','_original_journal'))
            try:
                if prepare_parent is not None:
                    monkeypatch.setattr(parent_cases.canonical.worker,'snapshot',snapshot)
                    monkeypatch.setattr(parent_cases.canonical.inspection,'snapshot',snapshot)
                    c.parent_harness=prepare_parent(SimpleNamespace(owner=owner,config=config,s=s,case=c,cap=2**30))
                yield c,snapshot,owner,config,receipt
            finally:
                if not hasattr(c,'expected_external_success'):owner.close()
        c.closed_observation_receipt=receipt()
        assert c.closed_observation_receipt['all_aliases_restored']
        assert c.closed_observation_receipt['all_private_sessions_cleared']
        if hasattr(c,'expected_external_success'):
            external=c.closed_observation_receipt['external_receipts']
            assert len(external)==1 and external[0]['guards_released']
            assert external[0]['complete'] is c.expected_external_success
            assert external[0]['handoff_committed'] is c.expected_external_success
            assert external[0]['original_resources_closed']
            assert external[0]['original_streams_closed']
            if not c.expected_external_success:assert external[0]['first_failure']
            assert owner.closed and all(getattr(owner,name).closed for name in
                ('_original_phase','_original_holder','_original_journal'))
            assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
            assert all(stream.closed for stream in c.original_resource_streams)
        with (tmp_path/'genesis_observation_closed.json').open('x',encoding='utf-8') as stream:
            json.dump(c.closed_observation_receipt,stream,indent=2)
        if stack_receipt is not None:
            assert stack_receipt['sampler_stopped'] and not stack_receipt['errors']
            with (tmp_path/'genesis_stack_observer_closed.json').open('x',encoding='utf-8') as stream:
                json.dump(stack_receipt,stream,indent=2)


def test_real_snapshot_capture_binds_active_genesis_and_two_common_calls(observed):
    c,snapshot,owner,config,receipt=observed
    raw=snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert json.loads(raw)['implementation']==snapshot.implementation_identity()
    assert owner._holder.inspect()==()
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    # The fixture checks the closed receipt after the real owner has closed.
    assert c.sessions[-1]._common_calls==2 and c.sessions[-1].closed


@pytest.mark.parametrize('symbol',['implementation_identity','_owner_view','_document','encode','sequence'])
def test_first_capture_rejects_changed_consumer_function_before_acquisition(observed,monkeypatch,symbol):
    c,snapshot,owner,config,receipt=observed
    with monkeypatch.context() as patch:
        if symbol=='sequence':
            foreign=ModuleType('foreign_snapshot_sequence');vars(foreign).update(vars(snapshot.sequence))
            patch.setattr(snapshot,symbol,foreign)
        else:patch.setattr(snapshot,symbol,lambda *args,**kw:'f'*64)
        with pytest.raises(ValueError,match='original Genesis consumer|canonical Genesis Snapshot aliases'):
            snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    assert owner.inspect()['stage']==3


@pytest.mark.parametrize('observed',['unresolved'],indirect=True)
@pytest.mark.parametrize('fault',['none','body','validation_commit','close_before','close_middle','guard_release'])
def test_real_handoff_closes_external_observation_after_commit_or_failure(
        observed,sequence_factory,monkeypatch,tmp_path,fault):
    c,snapshot,genesis,config,receipt=observed
    c.expected_external_success=fault=='none'
    h=c.parent_harness
    faults={};consumer=load_handoff(h,monkeypatch,genesis=c.host,validation_faults=faults)
    retained=[]
    def retain(path,before,after):
        if fault=='body':raise RuntimeError('synthetic handoff body failure')
        retained.append(after);return after
    with h.module.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        faults['validation_commit']=fault=='validation_commit'
        c.external_faults['close_once']=fault in ('close_before','close_middle')
        if fault in ('close_before','close_middle'):
            c.external_faults.update(target_stream=c.original_resource_streams[1],stream_close_failures=1)
        c.faults['external_guard_release_once']=fault=='guard_release'
        with consumer.Handoff(genesis,(reference,issued),{'joint':None},retain_head=retain,
                max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2) as owner:
            if fault=='none':
                result=owner.consume();assert result['completed_hours']==1
                assert owner._state=='complete' and genesis.closed
            else:
                with pytest.raises(RuntimeError,match='synthetic'):owner.consume()
                assert owner._state=='failed'
    assert not genesis._operation.locked() and not c.guard.locked()
    if fault=='guard_release':assert c.extra.locked()
    else:assert not c.extra.locked()
    if fault in ('close_before','close_middle'):
        assert genesis.closed and all(getattr(genesis,name).closed for name in
            ('_original_phase','_original_holder','_original_journal'))
        assert not c.original_resource_streams[1].closed


@pytest.mark.parametrize('observed',['unresolved'],indirect=True)
@pytest.mark.parametrize('mutation',['replacement','code'])
def test_first_handoff_bind_rejects_changed_guarded_wrapper(observed,monkeypatch,mutation):
    c,snapshot,genesis,config,receipt=observed;h=c.parent_harness
    consumer=load_handoff(h,monkeypatch,genesis=c.host)
    wrapped=consumer.Handoff.consume
    def template():
        check=function=owner_type=verify=None
        def entry(*args,**kwargs):
            captured=(check,owner_type,verify)
            return function(*args,**kwargs)
        return entry
    code=template().__code__
    assert code.co_freevars==wrapped.__code__.co_freevars
    with h.module.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        with consumer.Handoff(genesis,(reference,issued),{'joint':None},retain_head=lambda p,b,a:a,
                max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2) as owner:
            with monkeypatch.context() as patch:
                if mutation=='replacement':
                    changed=FunctionType(code,vars(consumer),closure=wrapped.__closure__)
                    patch.setattr(consumer.Handoff,'consume',changed)
                else:patch.setattr(wrapped,'__code__',code)
                with pytest.raises(ValueError,match='handoff original scope|original Genesis guarded consumer wrapper'):
                    owner.consume()
            assert not genesis._operation.locked() and not c.guard.locked() and not c.extra.locked()
    assert genesis.inspect()['stage']==3


@pytest.mark.parametrize('observed',['three'],indirect=True)
def test_three_actual_parents_commit_close_and_reopen_saved_phase(observed,monkeypatch,tmp_path):
    """Real four-Parent/Handoff3 record path; fake N0, source, native and Jobs."""
    c,snapshot,genesis,config,receipt=observed;h=c.parent_harness
    c.expected_external_success=True
    consumer=load_handoff(h,monkeypatch,genesis=c.host)
    start=perf_counter();stages=[];retained=[]
    def trace(stage):
        stages.append(dict(stage=stage,elapsed_seconds=perf_counter()-start))
        print(json.dumps(stages[-1]),flush=True)
    with ExitStack() as parents:
        reference=parents.enter_context(h.module.Parent(h.root,h.raw,**h.options))
        issued=reference.run();trace('reference_completed')
        actuals={}
        for lane in genesis._manifest.lanes:
            trace('actual_'+lane.lane_id+'_snapshot_start')
            raw=snapshot.capture_actual(genesis,config,max_archive_bytes=2**30,lane_id=lane.lane_id,
                reference_root=issued.scientific_root,reference_terminal_sha256=issued.scientific_terminal_sha256,
                reference_request_sha256=issued.scientific_request_sha256,
                reference_max_archive_bytes=issued.max_archive_bytes)
            trace('actual_'+lane.lane_id+'_construct_start')
            actual=parents.enter_context(h.module.Parent(h.root.parent/('actual_'+lane.lane_id+'_non_authoritative'),
                raw,**h.options,reference_owner=reference,reference_completion=issued))
            trace('actual_'+lane.lane_id+'_run_start')
            actuals[lane.lane_id]=(actual,actual.run());trace('actual_'+lane.lane_id+'_completed')
        def retain(path,before,after):
            assert reference._guard.locked()
            assert all(owner._guard.locked() and owner._reference_held for owner,_ in actuals.values())
            retained.append(after);return after
        trace('handoff_construct_start')
        with consumer.Handoff(genesis,(reference,issued),actuals,retain_head=retain,
                max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2) as owner:
            trace('handoff_constructed')
            result=owner.consume();trace('three_paired_committed')
            proof=result['parent_validation_receipt']
            assert proof['complete'] and proof['outer_cleanup_complete'] and proof['status']=='committed'
            assert proof['source_requests']==2408 and proof['source_prepares']==28
            assert proof['source_window_counts']==dict(bundle=13,records_bundle=1)
            lanes=json.loads(owner._plan.projection)['lanes']
            assert len(lanes)==3 and all(row['status']=='paired_committed' for row in lanes)
            assert len(retained)==5 and owner._state=='complete' and genesis.closed
            saved=dict(tickets=owner._plan.tickets,after=owner._plan.after,projection=owner._plan.projection,
                holder_head=owner._holder.head,phase_heads=owner._phase.heads)
            assert owner._bundle.held==owner._bundle.marked==[]
            assert not reference._guard.locked()
            assert all(not item._guard.locked() and not item._reference_held for item,_ in actuals.values())
    trace('all_original_parents_and_handoff_closed')
    phase=consumer.phase;m=genesis._manifest
    def deny(*args):raise AssertionError('saved replay must not retain new events')
    with phase.tickets.TicketHolder(genesis.holder_root,owner_root=genesis.owner_root,
            max_tickets=m.max_events,max_ticket_bytes=m.max_event_bytes,max_total_ticket_bytes=m.max_archive_bytes,
            create=False,expected_head=saved['holder_head'],retain_head=deny) as holder:
        assert holder.inspect()==saved['tickets']
        with phase.DevelopmentOwner(genesis.owner_root,m,genesis._binding,holder=holder,
                create=False,expected_heads=saved['phase_heads']) as reopened:
            report=reopened.inspect(expected_heads=saved['phase_heads'])
            with phase.closing(reopened._connect()) as db:rows=reopened._rows(db)
            replay,state,_=reopened._restore(rows)
            assert replay==report and report.completed_hours==1
            assert phase.encode(state.scientific)==saved['after']
            assert phase.encode(json.loads(rows[-1][3])['projection'])==saved['projection']
            assert rows==[ticket.event for ticket in saved['tickets']]
            assert holder.head==saved['holder_head'] and reopened.heads==saved['phase_heads']
    trace('fresh_phase_holder_saved_replay_closed')
    with (tmp_path/'three_actual_parent_handoff_observation.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(stages=stages,parent_validation_receipt=proof,paired_lanes=3,
            completed_hours=1,saved_replay=True,explicit_fake_N0_source_native_and_Job=True,
            complete_optimized_workflow_acceptance=False,formal_result=False),stream,indent=2)
