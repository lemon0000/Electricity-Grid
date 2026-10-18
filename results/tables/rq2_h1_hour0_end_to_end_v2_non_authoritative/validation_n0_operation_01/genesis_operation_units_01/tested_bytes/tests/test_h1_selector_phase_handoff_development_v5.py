"""Genuine partial Parent3/Handoff5 persistence with explicit fake common source.

The common bridge, source rows, selector solver and Job transport are synthetic.
The real Handoff validates an issued Rref, records business-unresolved, retains,
closes, and reopens the saved phase. This is not three-arm N0 acceptance.
"""
import json
from contextlib import contextmanager,nullcontext
from dataclasses import asdict,replace
from fractions import Fraction
from pathlib import Path
import sys
from types import ModuleType

import pytest
import experiments

from tests.h1_hour0_synthetic_harness_v3 import harness,load
from tests.test_h1_selector_parent_controller_development_v3 import (
    context as base_context,case,setup,base_setup,legacy_setup,sequence_factory,no_solver)


@contextmanager
def static_identity_test_seam(monkeypatch):
    """Protocol/fault tests only; all cached identities have original bookends."""
    from experiments import h1_origin_selector_replay_development_v1 as selector
    targets=((selector.physical,'implementation_identity'),(selector.native,'_identity'),
        (selector,'implementation_identity'))
    originals=[(obj,name,getattr(obj,name)) for obj,name in targets];values={};arguments={}
    def cached(index):
        original=originals[index][2]
        def read(*args):
            key=(index,json.dumps([asdict(arg) for arg in args],sort_keys=True))
            if key not in values:
                values[key]=original(*args);arguments[key]=args
            return values[key]
        return read
    with monkeypatch.context() as patch:
        for index,(obj,name,_) in enumerate(originals):patch.setattr(obj,name,cached(index))
        yield
    for key,value in values.items():assert originals[key[0]][2](*arguments[key])==value


@pytest.fixture
def context(case,setup,monkeypatch,no_solver,request):
    mode=getattr(request,'param','business_unresolved')
    if mode=='mixed':
        first=setup.manifest.lanes[0]
        limited=replace(first,lane_id='limited',
            mechanism=replace(first.mechanism,flexible_fraction=Fraction(1,2)))
        setup.manifest=replace(setup.manifest,lanes=(first,limited))
    # The two-lane protocol matrix explicitly uses fixed-identity test seams.
    # It is not a runtime measurement of original dependency validation.
    with static_identity_test_seam(monkeypatch) if mode=='mixed' else nullcontext():
        for c in base_context.__wrapped__(case,setup,monkeypatch,no_solver,request):
            c.partial_faults={}
            if mode=='mixed':
                from experiments import h1_selector_input_snapshot_development_v2 as snapshot
                source=snapshot.phase.source;original=source.prepare
                def prepare(*args,**kwargs):
                    value=original(*args,**kwargs)
                    hook=c.partial_faults.get('hook')
                    if hook is not None:
                        frame=sys._getframe(1)
                        while frame is not None:
                            if (frame.f_code.co_name=='validate' and 'p' in frame.f_locals
                                    and frame.f_globals.get('SCHEMA')=='h1_selector_phase_handoff_development_v5'):
                                hook(frame.f_locals['p']);break
                            frame=frame.f_back
                    return value
                monkeypatch.setattr(source,'prepare',prepare)
            yield c


def explicit_fake_common_bridge(common):
    bridge=ModuleType('explicit_fake_common_validation_for_partial_test')
    bridge.__file__=__file__
    def bind(api,kind,verify,operation,finalized):
        def attach(owner,token):
            verify(owner);operation(owner,token)
        def prepare(owner):
            verify(owner)
            return common.common._prepare_locked(owner._genesis._roster)
        def declaration(owner):
            return dict(explicit_fake_common_source=True,formal_result=False,resource_admission=False)
        def finish(owner):verify(owner)
        def abort(owner,error):pass
        def receipt(owner):
            return dict(explicit_fake_common_source=True,complete=False,formal_result=False)
        return attach,prepare,declaration,finish,abort,receipt,receipt
    bridge._bind_handoff=bind
    return bridge


def load_handoff(h,monkeypatch):
    p=h.module
    from experiments import h1_common_owner_genesis_development_v2 as common
    root=Path(p.__file__).parent
    helper=load(str(root/'h1_selector_parent_validation_operation_development_v3.py'),
        'experiments.h1_selector_parent_validation_operation_development_v3',monkeypatch)
    monkeypatch.setattr(experiments,'h1_selector_parent_validation_operation_development_v3',helper,raising=False)
    bridge=explicit_fake_common_bridge(common)
    consumer=load(str(root/'h1_selector_phase_handoff_development_v5.py'),
        'experiments.h1_selector_phase_handoff_development_v5',monkeypatch,{
            'h1_selector_parent_controller_development_v3':p,
            'h1_common_validation_operation_development_v3':bridge,
            'h1_selector_parent_validation_operation_development_v3':helper})
    monkeypatch.setattr(experiments,'h1_selector_phase_handoff_development_v5',consumer,raising=False)
    return consumer


@pytest.mark.parametrize('context',['business_unresolved'],indirect=True)
def test_business_unresolved_partial_closes_and_replays_original_science(harness,monkeypatch):
    h=harness;p=h.module;c=h.context;consumer=load_handoff(h,monkeypatch)
    retained=[]
    def retain(path,before,after):
        assert reference._guard.locked() and c.case.guard.locked()
        retained.append((before,after));return after
    options=dict(retain_head=retain,max_packet_bytes=64*1024**2,
        max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
    with p.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        with consumer.Handoff(c.owner,(reference,issued),{'joint':None},**options) as owner:
            result=owner.consume()
            assert result['completed_hours']==1 and len(retained)==5
            assert result['parent_validation_receipt'] is None
            assert result['validation_receipt']['explicit_fake_common_source']
            lane=json.loads(owner._plan.projection)['lanes'][0]
            assert lane['status'] in ('business_input_unresolved','business_unresolved')
            assert lane['before_business']==lane['after_business']
            assert lane['before_actual']==lane['after_actual']
            saved=dict(tickets=owner._plan.tickets,after=owner._plan.after,
                projection=owner._plan.projection,holder_head=owner._holder.head,phase_heads=owner._phase.heads)
            assert not reference._guard.locked() and c.owner.closed
            p._WINDOWS.assert_idle(reference)
    assert not c.case.guard.locked()
    phase=consumer.phase;manifest=c.owner._manifest
    def deny(*args):raise AssertionError('saved replay cannot retain events')
    with phase.tickets.TicketHolder(c.owner.holder_root,owner_root=c.owner.owner_root,
            max_tickets=manifest.max_events,max_ticket_bytes=manifest.max_event_bytes,
            max_total_ticket_bytes=manifest.max_archive_bytes,create=False,
            expected_head=saved['holder_head'],retain_head=deny) as holder:
        assert holder.inspect()==saved['tickets']
        with phase.DevelopmentOwner(c.owner.owner_root,manifest,c.owner._binding,holder=holder,
                create=False,expected_heads=saved['phase_heads']) as reopened:
            report=reopened.inspect(expected_heads=saved['phase_heads'])
            with phase.closing(reopened._connect()) as db:rows=reopened._rows(db)
            replay,state,_=reopened._restore(rows)
            assert replay==report and report.completed_hours==1
            assert phase.encode(state.scientific)==saved['after']
            assert phase.encode(json.loads(rows[-1][3])['projection'])==saved['projection']
            assert rows==[ticket.event for ticket in saved['tickets']]


@contextmanager
def complete_mixed_parents(h):
    p=h.module;c=h.context
    with p.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        raw=p.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
            reference_root=issued.scientific_root,reference_terminal_sha256=issued.scientific_terminal_sha256,
            reference_request_sha256=issued.scientific_request_sha256,
            reference_max_archive_bytes=issued.max_archive_bytes)
        with p.Parent(h.root.parent/'mixed_actual_non_authoritative',raw,**h.options,
                reference_owner=reference,reference_completion=issued) as actual:
            yield reference,issued,actual,actual.run()


@pytest.mark.parametrize('context',['mixed'],indirect=True)
def test_present_actual_and_unresolved_lane_keep_both_dispositions(harness,monkeypatch):
    h=harness;c=h.context;p=h.module;retained=[]
    with complete_mixed_parents(h) as (reference,issued,actual,completed):
        consumer=load_handoff(h,monkeypatch)
        def retain(root,before,after):
            assert reference._guard.locked() and actual._guard.locked() and actual._reference_held
            retained.append(after);return after
        with consumer.Handoff(c.owner,(reference,issued),{'joint':(actual,completed),'limited':None},
                retain_head=retain,max_packet_bytes=64*1024**2,max_record_bytes=1024**2,
                max_archive_bytes=128*1024**2) as owner:
            result=owner.consume();lanes=json.loads(owner._plan.projection)['lanes']
            assert result['completed_hours']==1 and len(retained)==5
            assert [row['status'] for row in lanes]==['paired_committed','business_unresolved']
            assert lanes[1]['before_business']==lanes[1]['after_business']
            assert lanes[1]['before_actual']==lanes[1]['after_actual']
            assert owner._bundle.held==owner._bundle.marked==[]
            assert not reference._guard.locked() and not actual._guard.locked() and not actual._reference_held
            assert c.owner.closed and result['parent_validation_receipt'] is None
            assert owner._holder.inspect()==owner._plan.tickets
            view=owner._phase.inspect(expected_heads=owner._phase.heads)
            assert view.completed_hours==1
            with consumer.phase.closing(owner._phase._connect()) as db:rows=owner._phase._rows(db)
            replay,state,_=owner._phase._restore(rows)
            assert replay==view and consumer.phase.encode(state.scientific)==owner._plan.after


@pytest.mark.parametrize('context',['mixed'],indirect=True)
@pytest.mark.parametrize('fault',['source_error','raw','issued','reference','caught_reentry'])
def test_partial_failure_is_sticky_and_releases_original_guards(harness,monkeypatch,fault):
    import inspect
    h=harness;c=h.context;p=h.module;retained=[]
    with complete_mixed_parents(h) as (reference,issued,actual,completed):
        consumer=load_handoff(h,monkeypatch)
        with consumer.Handoff(c.owner,(reference,issued),{'joint':(actual,completed),'limited':None},
                retain_head=lambda *args:retained.append(args),max_packet_bytes=64*1024**2,
                max_record_bytes=1024**2,max_archive_bytes=128*1024**2) as owner:
            original=(reference._raw,reference._issued,actual._reference_completion)
            triggered=[];nested=[]
            def hook(parent):
                if triggered or fault=='reference' and parent is not actual:return
                triggered.append(True)
                if fault=='source_error':raise RuntimeError('first partial source failure')
                if fault=='raw':reference._raw=bytes(bytearray(reference._raw))
                if fault=='issued':reference._issued=None
                if fault=='reference':actual._reference_completion=None
                if fault=='caught_reentry':
                    try:owner._bundle.validate()
                    except ValueError as error:nested.append(str(error))
            c.partial_faults['hook']=hook
            try:
                with pytest.raises((ValueError,RuntimeError)):owner.consume()
            finally:
                c.partial_faults.clear()
                reference._raw,reference._issued,actual._reference_completion=original
            assert triggered and owner._state=='failed' and not retained and not owner.root.exists()
            record=inspect.getclosurevars(consumer._PARTIAL_VALIDATE).nonlocals['owned'][id(owner)]
            assert record['partial_failure'] is not None and not record['partial_active']
            if fault=='source_error':assert 'first partial source failure' in record['partial_failure']
            if fault=='caught_reentry':
                assert nested and 'nonreentrant' in nested[0]
                assert 'nonreentrant' in record['partial_failure']
            assert not owner._guard.locked() and owner._bundle.held==owner._bundle.marked==[]
            assert not actual._reference_held and not reference._guard.locked() and not actual._guard.locked()
            assert not c.case.guard.locked() and not c.owner.closed
            with pytest.raises(ValueError,match='single-attempt'):owner.consume()
