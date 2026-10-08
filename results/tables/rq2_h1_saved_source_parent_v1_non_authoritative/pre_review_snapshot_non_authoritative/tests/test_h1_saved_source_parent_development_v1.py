"""Zero-solver tests; synthetic source and child seams never grant native scope."""
from dataclasses import replace
from datetime import timedelta
import json

import pytest

from experiments import h1_saved_source_parent_development_v1 as api
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import saved, no_solver, spec


@pytest.fixture
def environment(supplied, monkeypatch):
    supplied[3]['workload'] = '0'
    original = api.binding.windows.load_source_window
    def same_chain(*a, **k):
        result = original(*a, **k)
        result.pop('window_identity')
        result['chain']['start'] = 0
        result['window_identity'] = api.binding.windows._hash(result)
        return result
    monkeypatch.setattr(api.binding.windows, 'load_source_window', same_chain)
    return supplied


def owner(root, env, **kwargs):
    upstream,config,origin,state = env
    return api.SavedSourceParent(root, api.source.static_network(state['data']),spec(),
        api.replay.H1HourReplayLimits(3,100,500),origin=origin,upstream_root=upstream,
        config_path=config,dc_bus=1,**kwargs)


def source_pin(env, hour=0):
    upstream,config,origin,_ = env
    return api.binding.load_pinned_current(replace(origin,power_raw_hour=origin.power_raw_hour+hour,
        workload_raw_hour=origin.workload_raw_hour+hour),upstream,config_path=config).identity


def step(instance, env, rows, hour=0):
    return instance.step_saved(iter(rows),expected_source_identity=source_pin(env,hour),
        expected_head=instance.inspect().head)


def anchor_pin(instance):
    return instance._anchor.inspect().record_sha256


def test_saved_origin_fresh_reopen_and_no_execution(tmp_path,environment,saved):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=1,create=True)
    try:
        result=step(p,environment,saved[1])
        assert result.completed_hours == result.attempted_hours == 1
        assert result.status == 'complete' and result.declared_stage_slots == 3
        assert result.solver_calls == 0 and not result.independent_hour_jobs_integrated
        assert not result.resource_admission and not result.formal_execution_ready
        pin=anchor_pin(p)
    finally:
        p.close()
    q=owner(root,environment,hours=1,expected_anchor_record=pin)
    try:
        assert q.inspect()==result
        with pytest.raises(ValueError,match='inspection only'):
            step(q,environment,saved[1])
    finally:
        q.close()


def test_origin_raw_cannot_be_reused_for_second_hour(tmp_path,environment,saved):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,saved[1])
        assert one.status=='ready'
        two=step(p,environment,saved[1],1)
        assert two.status=='halted' and two.completed_hours==1 and two.attempted_hours==2
        assert p._journal.inspect().events==4
        with pytest.raises(ValueError,match='ready exact'):
            p.step_saved(iter(saved[1]),expected_source_identity=source_pin(environment,1),expected_head=two.head)
    finally:
        p.close()


@pytest.mark.parametrize('bad',['pin','future_pin','head','bool_hours','missing_source'])
def test_admission_failures_never_consume_reports(tmp_path,environment,bad):
    if bad=='bool_hours':
        with pytest.raises(ValueError): owner(tmp_path/'bad',environment,hours=True,create=True)
        return
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    head=p.inspect().head
    pin=source_pin(environment,1 if bad=='future_pin' else 0)
    if bad=='missing_source':
        environment[3]['data']=replace(environment[3]['data'],hourly_points=())
    def forbidden():
        pytest.fail('bad source consumed reports')
        yield b''
    try:
        with pytest.raises((ValueError,IndexError)):
            p.step_saved(forbidden(),expected_source_identity='0'*64 if bad=='pin' else pin,
                expected_head='0'*64 if bad=='head' else head)
        assert p._journal.inspect().events==0
        with pytest.raises(ValueError,match='unresolved'):p.inspect()
    finally:
        p.close()


@pytest.mark.parametrize('bad',['clock','chain','missing_tail'])
def test_next_source_failure_retains_committed_prefix(tmp_path,environment,saved,bad,monkeypatch):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=192,create=True)
    try:
        one=step(p,environment,saved[1])
        state=environment[3]
        if bad=='clock':
            points=state['data'].hourly_points
            state['data']=replace(state['data'],hourly_points=(points[0],replace(points[1],timestamp=points[1].timestamp+timedelta(hours=1))))
        elif bad=='missing_tail':
            state['data']=replace(state['data'],hourly_points=state['data'].hourly_points[:1])
        else:
            original=api.binding.windows.load_source_window
            def changed(*a,**k):
                value=original(*a,**k)
                if value['raw_start']==1:
                    value.pop('window_identity')
                    value['chain']['start']=1
                    value['window_identity']=api.binding.windows._hash(value)
                return value
            monkeypatch.setattr(api.binding.windows,'load_source_window',changed)
        pin='0'*64 if bad=='missing_tail' else source_pin(environment,1)
        with pytest.raises((ValueError,IndexError)):
            p.step_saved(iter(()),expected_source_identity=pin,expected_head=one.head)
        assert p._journal.inspect().events==2
        assert not (p._root/'hour_001_non_authoritative').exists()
    finally:p.close()


@pytest.mark.parametrize('window',['after_intent','reports','before_outcome','anchor'])
def test_failure_windows_no_retry_and_inspection_only(tmp_path,environment,saved,monkeypatch,window):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=2,create=True)
    head=p.inspect().head
    original=p._append
    def append(item,payload=b''):
        if window=='before_outcome' and item['kind']!='intent':raise OSError('before outcome')
        result=original(item,payload)
        if window=='after_intent' and item['kind']=='intent':raise OSError('after intent')
        return result
    monkeypatch.setattr(p,'_append',append)
    if window=='anchor':
        monkeypatch.setattr(p._anchor,'advance',lambda *a,**k: (_ for _ in ()).throw(OSError('anchor')))
    def rows():
        if window=='reports':raise OSError('saved reader failed')
        yield from saved[1]
    try:
        with pytest.raises(OSError):
            p.step_saved(rows(),expected_source_identity=source_pin(environment),expected_head=head)
        assert p._journal.inspect().events==1
        pin=anchor_pin(p)
        with pytest.raises(ValueError,match='unresolved'):
            p.step_saved(iter(saved[1]),expected_source_identity=source_pin(environment),expected_head=head)
    finally:p.close()
    if window=='anchor':
        with pytest.raises(ValueError):owner(root,environment,hours=2,expected_anchor_record=pin)
    else:
        q=owner(root,environment,hours=2,expected_anchor_record=pin)
        try:
            assert q.inspect().status=='pending_unknown'
            assert q.inspect().completed_hours==0
        finally:q.close()


@pytest.mark.parametrize('bad',['short','extra'])
def test_report_count_failure_preserves_child_without_parent_outcome(tmp_path,environment,saved,bad):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        with pytest.raises(ValueError,match='saved report'):
            step(p,environment,saved[1][:-1] if bad=='short' else (*saved[1],saved[1][0]))
        assert p._journal.inspect().events==1
        assert (p._root/'hour_000_non_authoritative').is_dir()
    finally:p.close()


@pytest.mark.parametrize('window',['outcome_anchor','outcome_confirm','outcome_restore','fresh_child'])
def test_post_child_failure_windows(tmp_path,environment,saved,monkeypatch,window):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=2,create=True)
    head=p.inspect().head
    original=p._anchor.advance
    def advance(*a,**k):
        if window=='outcome_anchor' and p._journal.inspect().events==2:
            raise OSError('outcome anchor')
        return original(*a,**k)
    monkeypatch.setattr(p._anchor,'advance',advance)
    confirm=p._anchor.confirm
    def bad_confirm(receipt):
        if window=='outcome_confirm' and p._journal.inspect().events==2:
            raise OSError('outcome confirm')
        return confirm(receipt)
    monkeypatch.setattr(p._anchor,'confirm',bad_confirm)
    restore=p._restore
    def bad_restore():
        if window=='outcome_restore' and p._journal.inspect().events==2:
            raise OSError('outcome restore')
        return restore()
    monkeypatch.setattr(p,'_restore',bad_restore)
    create_child=p._child
    def changed_child(*a,**k):
        if window=='fresh_child' and not k.get('create',False):
            raise OSError('fresh child failed')
        return create_child(*a,**k)
    monkeypatch.setattr(p,'_child',changed_child)
    try:
        with pytest.raises(OSError):
            p.step_saved(iter(saved[1]),expected_source_identity=source_pin(environment),expected_head=head)
        assert p._journal.inspect().events==(1 if window=='fresh_child' else 2)
        pin=anchor_pin(p)
        with pytest.raises(ValueError,match='unresolved'):p.inspect()
    finally:p.close()
    if window=='outcome_anchor':
        with pytest.raises(ValueError):owner(root,environment,hours=2,expected_anchor_record=pin)
    else:
        q=owner(root,environment,hours=2,expected_anchor_record=pin)
        try:
            state=q.inspect()
            assert state.completed_hours==(0 if window=='fresh_child' else 1)
            assert state.status==('pending_unknown' if window=='fresh_child' else 'ready')
            with pytest.raises(ValueError,match='inspection only'):
                q.step_saved(iter(saved[1]),expected_source_identity=source_pin(environment),expected_head=state.head)
        finally:q.close()


def test_192_hour_synthetic_parent_capacity_and_carry_not_native_coverage(tmp_path,environment,monkeypatch):
    """Real source binder/journal/anchor; test-only child inspection oracle.

    Build the complete parent journal once, then fully restore it. This avoids
    quadratic repeated replay while testing all 384 events and 385 anchors.
    The synthetic projections are NOT evidence of 192 native hour solutions.
    """
    from tests.test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
    environment[3]['data']=fixture(192).data
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=192,create=True)
    outcomes={}
    def synthetic_child(self,hour,packet,head,lineage,**kwargs):
        bound,result=outcomes[hour]
        assert bound==(packet.input_identity,api.source._digest(packet.before),head,lineage)
        assert kwargs==dict(expected_head=result.head)
        class Reader:
            def inspect(self):return result
            def close(self):pass
        return Reader()
    monkeypatch.setattr(api.SavedSourceParent,'_child',synthetic_child)
    before=previous=None
    try:
        for hour in range(192):
            receipt=p._load(hour,source_pin(environment,hour))
            packet=p._packet(receipt,hour,before,previous)
            assert packet.relative_hour==hour and packet.before.completed_hours==hour
            p._append(p._intent(hour,receipt,packet),receipt.audit_payload)
            intent_head=p._journal.head
            projection=api.replay._projection(packet,(20.,1.,20.),assignment_for(packet.inputs),
                ['1'*64]*3,['2'*64]*3,['3'*64]*3,
                key=api.replay.request_key(packet,p._spec,p._limits),implementation=api.replay.implementation_identity())
            result=api.child.H1HourArchiveInspection('4'*64,f'{hour+1:064x}','accepted',3,
                projection.canonical_locks,projection)
            outcomes[hour]=((packet.input_identity,api.source._digest(packet.before),intent_head,receipt.identity),result)
            p._append(p._outcome(hour,intent_head,result))
            before=p._after(packet,result)
            assert before.completed_hours==hour+1
            previous=receipt
        state=p.inspect()
        assert state.completed_hours==state.attempted_hours==192 and state.status=='complete'
        assert state.declared_stage_slots==576 and state.solver_calls==0
        assert not state.producer_coverage_proven and not state.independent_hour_jobs_integrated
        assert p._journal.inspect().events==384
        assert p._anchor.inspect().sequence==384
        assert len(list((root/'parent_anchor_non_authoritative').glob('[0-9][0-9][0-9].json')))==385
        pin=anchor_pin(p)
        with pytest.raises(ValueError,match='ready exact'):
            p.step_saved(iter(()),expected_source_identity='0'*64,expected_head=state.head)
        assert p._journal.inspect().events==384
    finally:p.close()
    q=owner(root,environment,hours=192,expected_anchor_record=pin)
    try:assert q.inspect()==state
    finally:q.close()
