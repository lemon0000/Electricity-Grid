from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import sqlite3

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_episode as api
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_episode_v1 import first_result
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec


@pytest.fixture
def environment(supplied, monkeypatch):
    supplied[3]['workload'] = '0'
    original = api.binding.windows.load_source_window
    def same_chain(*a,**k):
        value=original(*a,**k)
        value.pop('window_identity')
        value['chain']['start']=0
        value['window_identity']=api.binding.windows._hash(value)
        return value
    monkeypatch.setattr(api.binding.windows,'load_source_window',same_chain)
    return supplied


def owner(root,environment,*,create=True,expected_head=None,origin=None):
    upstream,config,d,state=environment
    return api.DevelopmentH1SourceEpisode(root,api.source.static_network(state['data']),spec(),budget(),
        api.H1EpisodeBudget(2,6,6.),dc_bus=1,origin=origin or d,upstream_root=upstream,config_path=config,
        create=create,expected_head=expected_head)


def pin(environment,hour=0):
    upstream,config,d,_=environment
    return api.binding.load_pinned_current(replace(d,power_raw_hour=d.power_raw_hour+hour,
        workload_raw_hour=d.workload_raw_hour+hour),upstream,config_path=config).identity


def step(instance,environment,hour=0):
    return instance.step(expected_source_identity=pin(environment,hour),expected_head=instance.head)


def records(root):
    db=sqlite3.connect(root/'h1_source_normal_episode.sqlite3')
    try:
        return [(head,api._decode_event(raw)) for raw,head in db.execute('SELECT archive,head FROM events ORDER BY seq')]
    finally:
        db.close()


def test_two_hours_source_intent_and_zero_solver_reopen(tmp_path,environment,monkeypatch):
    root=tmp_path/'bound_non_authoritative'
    instance=owner(root,environment)
    try:
        a,one=step(instance,environment)
        b,two=step(instance,environment,1)
        assert a.current_decision_accepted and b.current_decision_accepted
        assert two.completed_hours==2 and two.source_bound_hours==2 and two.status=='complete'
        assert not two.source_authenticated and not two.selection_registered and not two.formal_result
        head=instance.head
    finally:
        instance.close()
    entries=records(root)
    assert [x['kind'] for _,x in entries]==['intent','accepted','intent','accepted']
    assert all(type(entries[i][1]['source_binding_audit']) is bytes for i in (0,2))
    def forbidden(*a,**k):
        pytest.fail('reopen invoked native')
    monkeypatch.setattr(api.current,'solve_current',forbidden)
    monkeypatch.setattr(api.replay.native.capture,'solve_once',forbidden)
    instance=owner(root,environment,create=False,expected_head=head)
    try:
        assert instance.inspect()==two
    finally:
        instance.close()


@pytest.mark.parametrize('bad', ['wrong_pin','future_pin','workload_above_one'])
def test_source_admission_failure_has_no_intent_or_call(tmp_path,environment,monkeypatch,bad):
    instance=owner(tmp_path/'reject_non_authoritative',environment)
    initial=instance.inspect()
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:pytest.fail('bad source called solver'))
    try:
        if bad=='workload_above_one':
            environment[3]['workload']='1.25'
        expected='0'*64 if bad=='wrong_pin' else pin(environment,1 if bad=='future_pin' else 0)
        with pytest.raises(ValueError):
            instance.step(expected_source_identity=expected,expected_head=instance.head)
        assert instance.inspect()==initial
    finally:
        instance.close()


def test_source_drift_after_intent_poison_and_no_native(tmp_path,environment,monkeypatch):
    root=tmp_path/'intent_drift_non_authoritative'
    instance=owner(root,environment)
    original=instance._commit
    def drift(db):
        original(db)
        environment[3]['workload']='0.1'
    monkeypatch.setattr(instance,'_commit',drift)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:pytest.fail('source drift called native'))
    with pytest.raises(ValueError):
        step(instance,environment)
    with pytest.raises(ValueError,match='unresolved'):
        instance.inspect()
    instance.close()
    entries=records(root)
    assert len(entries)==1 and entries[0][1]['kind']=='intent'
    environment[3]['workload']='0'
    instance=owner(root,environment,create=False,expected_head=entries[-1][0])
    try:
        assert instance.inspect().status=='unresolved_intent'
        with pytest.raises(ValueError,match='cannot retry'):
            step(instance,environment)
    finally:
        instance.close()


def test_postsolve_source_drift_keeps_evidence_but_no_returned_decision(tmp_path,environment,monkeypatch,first_result):
    root=tmp_path/'postsolve_non_authoritative'
    instance=owner(root,environment)
    def solve(*a,**k):
        environment[3]['workload']='0.1'
        return first_result
    monkeypatch.setattr(api.current,'solve_current',solve)
    with pytest.raises(ValueError):
        step(instance,environment)
    with pytest.raises(ValueError,match='unresolved'):
        instance.inspect()
    instance.close()
    entries=records(root)
    assert entries[-1][1]['kind']=='accepted'
    with pytest.raises(ValueError):
        owner(root,environment,create=False,expected_head=entries[-1][0])
    environment[3]['workload']='0'
    instance=owner(root,environment,create=False,expected_head=entries[-1][0])
    try:
        assert instance.inspect().completed_hours==1
    finally:
        instance.close()


def test_source_chain_change_refused_before_next_call(tmp_path,environment,monkeypatch,first_result):
    root=tmp_path/'chain_non_authoritative'
    instance=owner(root,environment)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:first_result)
    _,state=step(instance,environment)
    original=api.binding.windows.load_source_window
    def foreign(*a,**k):
        value=original(*a,**k)
        if value['raw_start']==1:
            value.pop('window_identity')
            value['chain']['start']=1
            value['window_identity']=api.binding.windows._hash(value)
        return value
    monkeypatch.setattr(api.binding.windows,'load_source_window',foreign)
    try:
        with pytest.raises(ValueError,match='source chain'):
            step(instance,environment,1)
        assert instance.inspect()==state
    finally:
        instance.close()


@pytest.mark.parametrize('change', ['audit','identity','observation'])
def test_rehashed_source_intent_tamper_is_rebuilt_not_trusted(tmp_path,environment,monkeypatch,first_result,change):
    root=tmp_path/'tamper_non_authoritative'
    instance=owner(root,environment)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:first_result)
    step(instance,environment)
    instance.close()
    db=sqlite3.connect(root/'h1_source_normal_episode.sqlite3')
    try:
        rows=db.execute('SELECT * FROM events ORDER BY seq').fetchall()
        previous=rows[0][1]
        for seq,_,key,_,payload,_ in rows:
            item=api._decode_event(payload)
            if seq==1:
                if change=='audit': item['source_binding_audit']=b'{}'
                elif change=='identity': item['source_binding_identity']='0'*64
                else: item['observation']['raw_workload']='0.1'
            else:
                item['intent_head']=previous
            payload=api._encode_event(item)
            digest=sha256(payload).hexdigest()
            head=api._head(seq,previous,key,digest)
            db.execute('UPDATE events SET predecessor=?,archive_sha256=?,archive=?,head=? WHERE seq=?',
                (previous,digest,payload,head,seq))
            previous=head
        db.commit()
    finally:
        db.close()
    with pytest.raises(ValueError):
        owner(root,environment,create=False,expected_head=head)


def test_distinct_type_and_origin_reopen_binding(tmp_path,environment):
    root=tmp_path/'distinct_non_authoritative'
    instance=owner(root,environment)
    assert not isinstance(instance,api.base.DevelopmentH1NormalEpisode)
    head=instance.head
    instance.close()
    with pytest.raises(ValueError):
        owner(root,environment,create=False,expected_head=head,origin=replace(environment[2],outage_seed=8))
    with pytest.raises(FileNotFoundError):
        api.base.DevelopmentH1NormalEpisode(root,api.source.static_network(environment[3]['data']),
            spec(),budget(),api.H1EpisodeBudget(2,6,6.),dc_bus=1,expected_head=head)


@pytest.mark.parametrize('phase',['intent_noop','outcome_noop','outcome_after_commit','final_restore'])
def test_commit_ambiguity_poison_and_explicit_recovery(tmp_path,environment,monkeypatch,first_result,phase):
    root=tmp_path/'commit_non_authoritative'
    instance=owner(root,environment)
    genesis=instance.head
    invokes=[]
    def solve(*a,**k):
        invokes.append(1)
        return first_result
    monkeypatch.setattr(api.current,'solve_current',solve)
    original_commit,original_restore=instance._commit,instance._restore
    commits,restores=[],[]
    def commit(db):
        commits.append(1)
        if (phase=='intent_noop' and len(commits)==1) or (phase=='outcome_noop' and len(commits)==2):
            return
        original_commit(db)
        if phase=='outcome_after_commit' and len(commits)==2:
            raise RuntimeError('lost commit response')
    def restore():
        restores.append(1)
        if phase=='final_restore' and len(restores)==3:
            raise RuntimeError('lost final verification')
        return original_restore()
    monkeypatch.setattr(instance,'_commit',commit)
    monkeypatch.setattr(instance,'_restore',restore)
    with pytest.raises((ValueError,RuntimeError)):
        step(instance,environment)
    assert len(invokes)==(0 if phase=='intent_noop' else 1)
    with pytest.raises(ValueError,match='unresolved'):
        instance.inspect()
    instance.close()
    entries=records(root)
    head=entries[-1][0] if entries else genesis
    instance=owner(root,environment,create=False,expected_head=head)
    try:
        state=instance.inspect()
        assert state.completed_hours==int(phase in ('outcome_after_commit','final_restore'))
        assert state.status==('unresolved_intent' if phase=='outcome_noop' else 'ready')
    finally:
        instance.close()


def test_native_exception_halts_with_source_intent(tmp_path,environment,monkeypatch):
    root=tmp_path/'failure_non_authoritative'
    instance=owner(root,environment)
    def failed(*a,**k):
        raise RuntimeError('synthetic native failure')
    monkeypatch.setattr(api.current,'solve_current',failed)
    result,state=step(instance,environment)
    assert result is None and state.status=='halted' and state.completed_hours==0 and state.source_bound_hours==1
    head=instance.head
    instance.close()
    instance=owner(root,environment,create=False,expected_head=head)
    try:
        assert instance.inspect()==state
        with pytest.raises(ValueError,match='cannot retry'):
            step(instance,environment)
    finally:
        instance.close()


def test_power_time_gap_has_no_next_intent(tmp_path,environment,monkeypatch,first_result):
    root=tmp_path/'gap_non_authoritative'
    instance=owner(root,environment)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:first_result)
    _,before=step(instance,environment)
    data=environment[3]['data']
    environment[3]['data']=replace(data,hourly_points=(data.hourly_points[0],
        replace(data.hourly_points[1],timestamp=data.hourly_points[1].timestamp+timedelta(hours=1))))
    try:
        with pytest.raises(ValueError,match='clock gap'):
            step(instance,environment,1)
        assert instance.inspect()==before and len(records(root))==2
    finally:
        instance.close()


def test_source_byte_cap_is_checked_before_intent(tmp_path,environment,monkeypatch):
    monkeypatch.setattr(api,'MAX_SOURCE_AUDIT_BYTES',1)
    instance=owner(tmp_path/'bytes_non_authoritative',environment)
    before=instance.inspect()
    try:
        with pytest.raises(ValueError,match='byte admission'):
            step(instance,environment)
        assert instance.inspect()==before
    finally:
        instance.close()


def test_changed_config_path_and_content_cannot_reopen(tmp_path,environment):
    root=tmp_path/'config_non_authoritative'
    instance=owner(root,environment)
    head=instance.head
    instance.close()
    upstream,config,d,state=environment
    alternate=tmp_path/'alternate.yaml'
    alternate.write_bytes(config.read_bytes())
    with pytest.raises(ValueError):
        owner(root,(upstream,alternate,d,state),create=False,expected_head=head)


@pytest.mark.parametrize('completed',[0,1])
def test_source_implementation_drift_rejected_before_new_intent(tmp_path,environment,monkeypatch,first_result,completed):
    root=tmp_path/'implementation_non_authoritative'
    instance=owner(root,environment)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:first_result)
    if completed:
        step(instance,environment)
    monkeypatch.setattr(api.current,'solve_current',lambda *a,**k:pytest.fail('implementation drift called native'))
    monkeypatch.setattr(api.binding,'implementation_identity',lambda:'0'*64)
    expected=pin(environment,completed)
    try:
        with pytest.raises(ValueError):
            instance.step(expected_source_identity=expected,expected_head=instance.head)
        assert len(records(root))==2*completed
    finally:
        instance.close()


def test_mutated_loader_receipt_rejected_before_intent(tmp_path,environment,monkeypatch):
    root=tmp_path/'receipt_non_authoritative'
    instance=owner(root,environment)
    expected=pin(environment)
    original=api.binding.load_pinned_current
    def changed(*a,**k):
        value=original(*a,**k)
        value.row.demand_by_bus_mw[1]+=1
        return value
    monkeypatch.setattr(api.binding,'load_pinned_current',changed)
    try:
        with pytest.raises(ValueError,match='admission mismatch'):
            instance.step(expected_source_identity=expected,expected_head=instance.head)
        assert instance.inspect().source_bound_hours==0 and not records(root)
    finally:
        instance.close()


def test_origin_is_private_snapshot(tmp_path,environment):
    instance=owner(tmp_path/'private_origin_non_authoritative',environment)
    before=instance.inspect()
    object.__setattr__(environment[2],'outage_seed',8)
    try:
        assert instance._origin.outage_seed==7
        assert instance.inspect()==before
    finally:
        instance.close()
