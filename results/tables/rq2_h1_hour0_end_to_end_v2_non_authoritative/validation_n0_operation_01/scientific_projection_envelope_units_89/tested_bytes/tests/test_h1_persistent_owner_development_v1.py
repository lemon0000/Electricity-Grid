"""Synthetic source-controller seam, real selector/business replay, no native solver."""
from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256
import json
import sqlite3
from types import SimpleNamespace

import pytest

from experiments import h1_persistent_owner_development_v1 as m
from tests import test_h1_origin_selector_replay_development_v1 as selectors
from tests import test_h1_exact_business_development_v1 as biz
from tests.test_rq2_normal_h1_source_v1 import packet


def denied(*a,**k):raise AssertionError('real native solver is forbidden')


@pytest.fixture
def setup(monkeypatch,tmp_path):
    # The source producer is an explicit synthetic seam. Its transitive source
    # closure was independently checked by the source unit, not by these tests.
    monkeypatch.setattr(m.source,'implementation_identity',lambda:'a'*64)
    # Preserve the actual identities of previously closed, unchanged numerical
    # modules while isolating their recursive file hashing in this owner suite.
    # No physical, selector, business or replay mathematics is replaced.
    from functools import lru_cache
    physical_pin=m.selection.physical.implementation_identity()
    monkeypatch.setattr(m.selection.physical,'implementation_identity',lambda:physical_pin)
    monkeypatch.setattr(m.selection,'implementation_identity',lru_cache(None)(m.selection.implementation_identity))
    business_pin=m.business.implementation_identity()
    monkeypatch.setattr(m.business,'implementation_identity',lambda:business_pin)
    old=biz.origin(mechanism=m.business.Mechanism(Q(1,2),Q(1),Q(1)))
    cfg=m.LaneConfig('joint',old.cursor.spec,old.mechanism,tuple(sorted(old.cursor.initial.tracks[0][1].physical.envelope)))
    manifest=m.Manifest((cfg,),selectors.old.REF,selectors.old.ACT,selectors.old.SPEC,selectors.LIMITS,
                        800,8*1024**2,64*1024**2,'test-period')
    binding=m.SourceBinding(str(tmp_path/'normal'),'1'*64,'2'*64,'3'*64)
    initial_frame,initial_action,_,_=selectors.inputs()
    origin=initial_action.current_state;currents={};windows={}
    previous=None
    for h in range(3):
        p=packet(raw_workload='0.1',relative_hour=h,before=previous)
        after=m.selection.physical._owned(type(p.before),network_identity=p.network.identity,completed_hours=h+1,
            units=(('G1',True,45.,h+1),),evidence_role='numerical_lex_candidate')
        frame=m.selection.physical._frame(p,after);previous=after
        state=origin
        for i in range(1,h+1):
            step=m.selection.physical.events.disclose_current(state,m.selection.physical.events.CurrentOutageReport(i,None,None))
            state=step.after
        action=initial_action if h==0 else m.selection.physical.registry.TransitionAction(h,step)
        decl=dict(split='training',power_raw_hour=h,workload_raw_hour=h,outage_seed=7,config_sha256='4'*64)
        obs=dict(declaration=decl)
        for kind in ('power','workload'):
            row=dict(workload_fraction='0.1') if kind=='workload' else dict(cfe_call_fraction='0.6')
            row['raw_hour']=str(h)
            chain=dict(chain_id=kind+'-chain',trace_identity_basis='synthetic-fixed-basis')
            window=dict(rows=[row],chain=chain,package_manifest_sha256=('5' if kind=='power' else '6')*64,
                        window_identity=m.digest([kind,h]))
            windows[kind,h]=window
            obs.update({kind+'_source_row':row,kind+'_window_identity':window['window_identity'],
                        kind+'_chain_identity':m.source.source.windows._hash(chain),
                        kind+'_package_manifest_sha256':window['package_manifest_sha256']})
        audit=m.encode(dict(source_observation_audit_payload=obs,
            normal_audit_payload=dict(parent_declaration=dict(config_path='synthetic.yaml')),
            synthetic_source_controller_seam=True))
        scientific=m.encode(dict(hour=h,normal=p.input_identity,w=['1','10'],cfe=['3','5']))
        current=m.source.normal._owned(m.source.ExactSourceCurrent,
            prepared_current=SimpleNamespace(frame=frame,source_origin=origin,source_action=action),
            workload_exact=Q(1,10),source_cfe_at_alpha_one_exact=Q(3,5),exogenous_scientific_payload=scientific,
            source_observation_identity=m.digest(obs),source_projection_audit_payload=audit)
        currents[h]=current
    calls=[]
    def load(kind,split,raw,hours,**kw):
        assert hours==1 and split=='training' and kw['expected_config_sha256']=='4'*64
        calls.append((kind,raw));return windows[kind,raw]
    def fresh(root,**kw):
        assert root==binding.root and kw['expected_binding_sha256']==binding.binding_sha256
        assert kw['expected_registry_identity']==binding.registry_identity
        return currents[kw['completed_hours']-1]
    monkeypatch.setattr(m.source.source.windows,'load_source_window',load)
    monkeypatch.setattr(m.source,'prepare',fresh)
    monkeypatch.setattr(m.selection.native.capture,'create_solver',denied)
    tickets=[]
    def retain(ticket):tickets.append(ticket);return ticket.identity
    return SimpleNamespace(manifest=manifest,binding=binding,currents=currents,windows=windows,calls=calls,
        root=tmp_path/'owner_non_authoritative',tickets=tickets,retain=retain)


def saved(monkeypatch,s,state,h,*,actual=True,fault=None,flow_loop=False):
    cur=s.currents[h];frame=cur.prepared_current.frame;action=cur.prepared_current.source_action
    def produce(before,lane,power=None):
        chosen=s.manifest.reference_selector if lane.role=='Rref' else s.manifest.actual_selector
        with monkeypatch.context() as patch:
            selectors.old.install(patch,selectors.old.R if lane.role=='Rref' else selectors.old.A,
                                  fault if lane.role=='Rref' else None,flow_loop=flow_loop)
            key=m.selection.input_identity(frame,action,before,lane=lane,power=power);frozen=();result=[]
            for i,label in enumerate(m.selection.stage_labels(frame,lane)):
                builder=lambda:m.selection.build_development_stage(frame,action,before,lane=lane,power=power,
                    index=i,frozen=frozen,expected_identity=key)
                raw=m.selection.native.capture._solve(builder,s.manifest.solver_specification,selectors.old.BUDGET,
                    f'{m.selection.SCHEMA}:{lane.role}:{i}:{label}')
                result.append(m.selection.encode_development_record(frame,action,before,raw,index=i,frozen=frozen,
                    lane=lane,power=power,selector=chosen,specification=s.manifest.solver_specification,limits=s.manifest.replay_limits))
                if not raw.optimal or fault and i==1:break
                frozen+=(raw.objective,)
            return tuple(result)
    ref=produce(state.reference,m.RREF)
    acts={key:() for key,_ in state.lanes}
    if actual:
        for c,(key,lane) in zip(s.manifest.lanes,state.lanes):
            if not lane.halted:
                power=m.selection.physical.RelativeDcPower(h,'5','1','mechanism_assumption')
                acts[key]=produce(lane.actual,c.lane,power)
    return ref,acts


def initial(s):return m._initial(s.manifest,s.currents[0])


def open_owner(s,**kwargs):
    return m.DevelopmentOwner(s.root,s.manifest,s.binding,retain_prepared=s.retain,**kwargs)


def advance(owner,records):
    return owner.advance(expected_heads=owner.heads,terminal_sha256='3'*64,
                         reference_records=records[0],actual_records=records[1])


def restore(owner):
    from contextlib import closing
    with closing(owner._connect()) as db:rows=owner._rows(db)
    return owner._restore(rows)


def test_paired_commit_reopen_and_second_hour_use_own_carries(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with open_owner(s,create=True) as owner:
        result=advance(owner,records)
        assert result.completed_hours==1 and result.continuation_available
        assert not result.formal_result and not result.native_execution_authenticated
        _,state,_=restore(owner);lane=state.lanes[0][1]
        assert lane.business.cursor.records[-1].response.action.grid_served==Q(3,50)
        assert lane.business.cursor.records[-1].response.action.cfe_served==Q(1,50)
        assert lane.business.cursor.execution.tracks[0][1].ledger.debt==Q(2,25)
        assert state.reference.physical_carry.generation_mw==(('G1',30.),)
        assert lane.actual.physical_carry.generation_mw==(('G1',25.),)
        heads=owner.heads
    with open_owner(s,expected_heads=heads) as owner:
        _,state,_=restore(owner)
        result=advance(owner,saved(monkeypatch,s,state,1))
        assert result.completed_hours==2
        _,state,_=restore(owner)
        assert len(state.lanes[0][1].business.history)==2
        assert state.lanes[0][1].business.cursor.execution.tracks[0][1].ledger.debt==Q(4,25)
    assert max(raw for _,raw in s.calls)==1


def test_actual_unresolved_halts_both_carries_but_common_reference_commits(setup,monkeypatch):
    s=setup;before=initial(s)
    with open_owner(s,create=True) as owner:
        result=advance(owner,saved(monkeypatch,s,before,0,actual=False))
        _,after,_=restore(owner)
        assert after.reference.identity!=before.reference.identity
        assert after.lanes[0][1].business.identity==before.lanes[0][1].business.identity
        assert after.lanes[0][1].actual.identity==before.lanes[0][1].actual.identity
        assert result.completed_hours==1 and not result.continuation_available
        assert result.lane_status==( ('joint','halted'), )
        with pytest.raises(ValueError,match='no admitted'):advance(owner,((),{'joint':()}))


def test_reference_failure_keeps_intent_and_no_lane_or_outer_outcome(setup,monkeypatch):
    s=setup
    with open_owner(s,create=True) as owner:
        with pytest.raises(ValueError,match='reference unresolved'):
            advance(owner,saved(monkeypatch,s,initial(s),0,actual=False,fault='timeout'))
        assert owner.poisoned
        heads=owner.heads
    with open_owner(s,expected_heads=heads) as owner:
        report=owner.inspect(expected_heads=heads)
        assert report.pending_intent and report.completed_hours==0 and not report.continuation_available
        with pytest.raises(ValueError,match='pending intent'):advance(owner,((),{'joint':()}))


def test_same_projection_aux_flow_witness_only_changes_registry_head(setup,monkeypatch):
    s=setup;before=initial(s)
    with open_owner(s,create=True) as owner:
        advance(owner,saved(monkeypatch,s,before,0));oldheads=owner.heads
        ref,actual=saved(monkeypatch,s,before,0,flow_loop=True)
        report=owner.register_alternate_witness(expected_heads=oldheads,hour=0,terminal_sha256='3'*64,
            reference_records=ref,actual_records=actual)
        assert report.outcome_head==oldheads[0] and report.registry_head!=oldheads[1]
        assert not report.conflicted_keys and report.continuation_available
        with pytest.raises(ValueError,match='retained'):owner.inspect(expected_heads=oldheads)
        _,state,_=restore(owner)
        assert advance(owner,saved(monkeypatch,s,state,1)).completed_hours==2


def test_conflict_on_ancestor_preserves_suffix_and_denies_continuation(setup,monkeypatch):
    s=setup;before=initial(s)
    with open_owner(s,create=True) as owner:
        advance(owner,saved(monkeypatch,s,before,0))
        _,state,_=restore(owner);advance(owner,saved(monkeypatch,s,state,1));oldheads=owner.heads
        ref,actual=saved(monkeypatch,s,before,0,actual=False)
        report=owner.register_alternate_witness(expected_heads=oldheads,hour=0,terminal_sha256='3'*64,
            reference_records=ref,actual_records=actual)
        assert report.completed_hours==2 and report.outcome_head==oldheads[0]
        assert len(report.conflicted_keys)==1 and report.orphaned_after_conflicted_ancestor
        assert not report.continuation_available
        heads=owner.heads
    with open_owner(s,expected_heads=heads) as owner:
        assert owner.inspect(expected_heads=heads).conflicted_keys==report.conflicted_keys
        with pytest.raises(ValueError,match='sticky conflict'):advance(owner,((),{'joint':()}))


def test_changed_source_and_manifest_rejected_on_reopen(setup,monkeypatch):
    s=setup
    with open_owner(s,create=True) as owner:
        advance(owner,saved(monkeypatch,s,initial(s),0));heads=owner.heads
    with pytest.raises(ValueError,match='header changed'):
        m.DevelopmentOwner(s.root,replace(s.manifest,accounting_period_id='other'),s.binding,expected_heads=heads)
    s.windows['power',0]['rows'][0]['cfe_call_fraction']='0.7'
    with pytest.raises(ValueError,match='correspondence'):
        open_owner(s,expected_heads=heads)


def test_request_key_excludes_source_labels_and_accounting_label(setup):
    s=setup;before=initial(s);key=m._request(s.manifest,before,s.currents[0])
    assert m._request(replace(s.manifest,accounting_period_id='other'),before,s.currents[0])==key
    assert m._request(replace(s.manifest,max_events=1600,max_archive_bytes=128*1024**2),before,s.currents[0])==key
    science=s.manifest.scientific
    assert 'accounting_period_id' not in science and 'capacity_declaration_id' not in science['lanes'][0]['policy']
    assert not any(token in m.encode(science) for token in (b'power-chain',b'synthetic.yaml',b'test-period'))


def test_exclusive_lease_and_stale_heads(setup):
    s=setup
    with open_owner(s,create=True) as owner:
        with pytest.raises(ValueError,match='already held'):
            m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=owner.heads)
        with pytest.raises(ValueError,match='retained'):owner.inspect(expected_heads=('0'*64,'0'*64))


def test_before_publication_source_drift_preserves_intent(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    real=m._transition
    def changing(*args):
        result=real(*args)
        cur=s.currents[0]
        s.currents[0]=m.source.normal._owned(m.source.ExactSourceCurrent,**(vars(cur)|{
            'exogenous_scientific_payload':m.encode(dict(changed=True))}))
        return result
    with open_owner(s,create=True) as owner:
        monkeypatch.setattr(m,'_transition',changing)
        with pytest.raises(ValueError,match='source changed'):advance(owner,records)
        assert owner.poisoned
        with sqlite3.connect(owner.path) as db:
            assert db.execute('SELECT kind FROM events').fetchall()==[('intent',)]


def test_bounded_archive_and_noncanonical_records_rejected_before_intent(setup):
    s=setup
    with open_owner(s,create=True) as owner:
        heads=owner.heads
        with pytest.raises(ValueError,match='bytes'):advance(owner,((bytearray(b'x'),),{'joint':()}))
        assert owner.heads==heads
        with pytest.raises(ValueError,match='roster'):advance(owner,((),{}))


def test_modified_database_projection_is_rejected_even_with_rehashed_event(setup,monkeypatch):
    s=setup
    with open_owner(s,create=True) as owner:
        advance(owner,saved(monkeypatch,s,initial(s),0));heads=owner.heads
    with sqlite3.connect(s.root/'owner.sqlite') as db:
        seq,pred,kind,raw=db.execute('SELECT seq,predecessor,kind,body FROM events WHERE seq=2').fetchone()
        body=json.loads(raw);body['projection']['reference_request_mw']={'numerator':'14','denominator':'1'}
        raw=m.encode(body);head=m.digest([seq,pred,kind,sha256(raw).hexdigest()])
        db.execute('UPDATE events SET body=?,head=? WHERE seq=2',(raw,head))
    with pytest.raises(ValueError,match='reproduce'):
        m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=(head,head))


@pytest.mark.parametrize('kind',['intent','outcome'])
@pytest.mark.parametrize('phase',['before_commit','after_commit'])
def test_recovery_requires_exact_independently_retained_event(setup,monkeypatch,kind,phase):
    s=setup;records=saved(monkeypatch,s,initial(s),0);tripped=[]
    with open_owner(s,create=True) as owner:
        check,rows=owner._check,owner._rows
        def fault_check():
            check()
            if phase=='before_commit' and s.tickets and s.tickets[-1].kind==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected before commit')
        def fault_rows(db):
            result=rows(db)
            if phase=='after_commit' and result and result[-1][2]==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected after commit before return')
            return result
        monkeypatch.setattr(owner,'_check',fault_check);monkeypatch.setattr(owner,'_rows',fault_rows)
        with pytest.raises(RuntimeError,match='injected'):advance(owner,records)
        ticket=s.tickets[-1]
        assert ticket.kind==kind
    with m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=ticket.before_heads,recovery_ticket=ticket) as owner:
        report=owner.inspect(expected_heads=owner.heads)
        assert owner.heads==(ticket.after_heads if phase=='after_commit' else ticket.before_heads)
        assert report.completed_hours==(1 if kind=='outcome' and phase=='after_commit' else 0)
        assert report.pending_intent==((kind=='intent' and phase=='after_commit') or (kind=='outcome' and phase=='before_commit'))
        with sqlite3.connect(owner.path) as db:
            assert db.execute('SELECT count(*) FROM events').fetchone()[0]==ticket.sequence-(phase=='before_commit')
    wrong=replace(ticket,store_identity='0'*64)
    with pytest.raises(ValueError,match='ticket differs'):
        m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=ticket.before_heads,recovery_ticket=wrong)
    if phase=='after_commit':
        wrong=replace(ticket,body=m.encode(dict(forged=True)))
        with pytest.raises(ValueError,match='neither retained'):
            m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=ticket.before_heads,recovery_ticket=wrong)


@pytest.mark.parametrize('mode',['wrong_digest','exception','missing'])
def test_unacknowledged_ticket_cannot_write(setup,monkeypatch,mode):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    def retain(ticket):
        if mode=='exception':raise RuntimeError('holder failed')
        return '0'*64
    with m.DevelopmentOwner(s.root,s.manifest,s.binding,create=True,
            retain_prepared=None if mode=='missing' else retain) as owner:
        with pytest.raises((ValueError,RuntimeError)):advance(owner,records)
        with sqlite3.connect(owner.path) as db:assert db.execute('SELECT count(*) FROM events').fetchone()==(0,)


def test_copy_pickle_and_callback_reentry_are_rejected(setup,monkeypatch):
    from copy import copy,deepcopy
    import pickle
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with open_owner(s,create=True) as owner:
        for function in (copy,deepcopy,pickle.dumps):
            with pytest.raises(TypeError):function(owner)
        def retain(ticket):
            with pytest.raises(ValueError,match='already in progress'):owner.inspect(expected_heads=owner.heads)
            with pytest.raises(ValueError,match='already in progress'):owner.close()
            s.tickets.append(ticket);return ticket.identity
        owner.retain_prepared=retain
        assert advance(owner,records).completed_hours==1


def test_unknown_business_valueerror_is_not_a_scientific_outcome(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0,actual=False)
    def broken(**kwargs):raise ValueError('implementation drift')
    with open_owner(s,create=True) as owner:
        monkeypatch.setattr(m.business,'current',broken)
        with pytest.raises(ValueError,match='implementation drift'):advance(owner,records)
        assert owner.poisoned
        with sqlite3.connect(owner.path) as db:assert db.execute('SELECT kind FROM events').fetchall()==[('intent',)]


def test_defined_business_mapping_failure_preserves_reason(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0,actual=False)
    def unresolved(**kwargs):raise ValueError('positive reference request below business resolution')
    with open_owner(s,create=True) as owner:
        monkeypatch.setattr(m.business,'current',unresolved)
        report=advance(owner,records)
        assert report.completed_hours==1 and not report.continuation_available
        with sqlite3.connect(owner.path) as db:body=json.loads(db.execute("SELECT body FROM events WHERE kind='outcome'").fetchone()[0])
        assert body['projection']['lanes'][0]['business_candidate']['input_unresolved_reason']=='positive reference request below business resolution'


def test_stale_recovery_ticket_cannot_adopt_later_suffix(setup,monkeypatch):
    s=setup
    with open_owner(s,create=True) as owner:
        advance(owner,saved(monkeypatch,s,initial(s),0));ticket=s.tickets[0]
    with pytest.raises(ValueError,match='neither retained'):
        m.DevelopmentOwner(s.root,s.manifest,s.binding,expected_heads=ticket.before_heads,recovery_ticket=ticket)


def test_two_lanes_one_halts_without_blocking_other_and_skips_next_hour(setup,monkeypatch):
    s=setup;first=s.manifest.lanes[0]
    second=replace(first,lane_id='limited',mechanism=replace(first.mechanism,flexible_fraction=Q(1,2)))
    s.manifest=replace(s.manifest,lanes=(first,second))
    before=initial(s);ref,actual=saved(monkeypatch,s,before,0)
    actual['limited']=()
    with open_owner(s,create=True) as owner:
        result=advance(owner,(ref,actual));_,state,_=restore(owner)
        assert result.lane_status==( ('joint','active'),('limited','halted') )
        limited=state.lanes[1][1]
        assert limited.business.identity==before.lanes[1][1].business.identity
        assert limited.actual.identity==before.lanes[1][1].actual.identity
        result=advance(owner,saved(monkeypatch,s,state,1));_,after,_=restore(owner)
        assert result.completed_hours==2 and after.lanes[1][1]==limited
        with sqlite3.connect(owner.path) as db:body=json.loads(db.execute("SELECT body FROM events WHERE kind='outcome' ORDER BY seq DESC").fetchone()[0])
        assert body['projection']['lanes'][1]['status']=='skipped_halted'


def test_parallel_public_operation_fails_immediately_without_poison(setup):
    from concurrent.futures import ThreadPoolExecutor
    s=setup
    with open_owner(s,create=True) as owner:
        owner._operation.acquire()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                task=pool.submit(owner.inspect,expected_heads=owner.heads)
                with pytest.raises(ValueError,match='already in progress'):task.result(timeout=5)
        finally:owner._operation.release()
        assert not owner.poisoned and owner.inspect(expected_heads=owner.heads).completed_hours==0


def test_callback_cannot_change_live_scientific_configuration(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with open_owner(s,create=True) as owner:
        def retain(ticket):
            owner.manifest=replace(s.manifest,lanes=(replace(s.manifest.lanes[0],lane_id='changed'),))
            return ticket.identity
        owner.retain_prepared=retain
        with pytest.raises(ValueError,match='configuration changed'):advance(owner,records)
        with sqlite3.connect(owner.path) as db:assert db.execute('SELECT count(*) FROM events').fetchone()==(0,)


def test_explicit_record_count_bound_leaves_completed_intent(setup,monkeypatch):
    s=setup;s.manifest=replace(s.manifest,max_events=1)
    with open_owner(s,create=True) as owner:
        with pytest.raises(ValueError,match='reservation exceeded'):advance(owner,saved(monkeypatch,s,initial(s),0))
        assert owner.poisoned
        with sqlite3.connect(owner.path) as db:assert db.execute('SELECT kind FROM events').fetchall()==[('intent',)]


def test_callback_cannot_detach_ticket_from_genesis(setup,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with open_owner(s,create=True) as owner:
        def retain(ticket):owner.genesis='0'*64;return ticket.identity
        owner.retain_prepared=retain
        with pytest.raises(ValueError,match='genesis changed'):advance(owner,records)
        with sqlite3.connect(owner.path) as db:assert db.execute('SELECT count(*) FROM events').fetchone()==(0,)


def test_owner_still_rechecks_dependency_identity(setup,monkeypatch):
    s=setup
    with open_owner(s,create=True) as owner:
        monkeypatch.setattr(m.business,'implementation_identity',lambda:'0'*64)
        with pytest.raises(ValueError,match='implementation changed'):owner.inspect(expected_heads=owner.heads)
