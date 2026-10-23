"""Three-bus analytic control checks, never public P2 numeric evidence."""
from dataclasses import replace
from fractions import Fraction as Q
from types import SimpleNamespace

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture,analytic_point,analytic_economic,analytic_child
from src import staged_rts24_p2_controller_v1 as d
from src.staged_rts24_reference_queries_v1 import reference_requests
from src.staged_rts24_causal_v1 import PointEvidence


@pytest.fixture(autouse=True)
def ordinary(monkeypatch):
    from src import staged_rts24_highs_backend_v1 as backend
    monkeypatch.setattr(backend,'call_highs',lambda *a,**k:pytest.fail('native requested in ordinary controller test'))
    monkeypatch.setattr(d.journal,'runtime_identity',lambda:{'ordinary_test':True})


def analytic_provider(query):
    if query.request.role in ('reference_base_P0','normal_contract_C'):
        point=analytic_point(query,query.request.meter_min)
        return PointEvidence(query,point,economic=analytic_economic(query,point))
    if query.request.role=='actual_P':return PointEvidence(query,analytic_point(query,query.request.meter_min))
    if query.request.role=='fault_firm_F':return PointEvidence(query,analytic_point(query,query.request.meter_min))
    return analytic_child(query)


def synthetic_rows(fixture):
    """Small fixture data for the cursor protocol; no production scope override."""
    rows=[];prior=None
    def add(q,section,parent=None,dynamic=False,refs=()):
        ordinal=len(rows)+1
        rows.append(dict(ordinal=ordinal,serial_after=ordinal-1 if ordinal>1 else None,section=section,hour=q.hour,
            role=q.role,objective=q.objective,outage=d.c.plain(q.outages),request_sha=None if dynamic else q.identity,
            parent_request_sha=q.anchor_id,parent_slot=parent,state_after_actual_slot=prior,reference_slots=list(refs),
            evidence_kind='child_lp_kkt' if q.objective!='economic' else 'primal_point' if parent else 'economic_kkt'))
        return ordinal
    for hour in range(fixture.first_hour,fixture.observation_end):
        h=reference_requests(fixture,d.PLAN,d.CLEAN,d.METHOD,hour);root=len(rows)+1;refs=[]
        for q in h['requests']:refs.append(add(q,'actual',root if q.anchor_id else None))
        prior=add(replace(h['requests'][0],role='actual_P',outages=h['actual_outage'],anchor_id=h['requests'][0].identity),
            'actual',root,True,refs)
    for hour in (1,2):
        h=d.c.hour_requests(fixture,d.PLAN,d.CLEAN,d.METHOD,hour);normal=next(q for q in h['requests'] if q.role=='normal_contract_C')
        root=add(normal,'contract')
        for outage in fixture.selected:
            for role in ('fault_firm_F','fault_raw_need'):
                q=next(q for q in h['requests'] if q.role==role and q.outages==outage);add(q,'contract',root)
    return rows


def test_observation_end_extends_beyond_registration_and_keeps_runtime_bindings(tmp_path,monkeypatch):
    fixture=replace(analytic_fixture(),rights_before=(Q(50),Q(100)),rights_after=(Q(50),Q(100)),
        source_identity=d.c.digest('analytic_P2_F50_X100_control_fixture'))
    bindings=[]
    def solve(query,binding):bindings.append(binding);return analytic_provider(query)
    point=d.Cursor(synthetic_rows(fixture),solve)
    session,failure=d.actual_prefix(fixture,tmp_path/'journal',point,lambda *a,**k:None)
    assert failure is None and point.actual_finished and session.state.next_hour==5
    assert session.fixture.registration_end==3 and len(session.state.records)==5 and len(point.accepted)==5
    assert [b['ordinal'] for b in bindings]==list(range(1,point.reserved+1))
    assert all(b['request_sha'] and b['bound_query_sha'] for b in bindings)
    later=next(b for b in bindings if b['state_after_actual_slot'] is not None)
    assert later['accepted_state_sha']==point.accepted[later['state_after_actual_slot']]
    contracts=[];before=session.state
    from src import staged_rts24_audit_v1 as audit
    # Explicit negative-verdict control injection, not an analytic counterexample.
    monkeypatch.setattr(audit,'audit_legal_x',lambda *a:dict(point_legal_under_X=False))
    d.full_contracts(fixture,point,lambda *a,**k:None,contracts)
    assert len(contracts)==2 and point.reserved==len(point.rows) and session.state==before
    assert all(r['legal_X']['point_legal_under_X'] is False and r['raw_optimality_audit']['lp_optimality_conditions_satisfied'] for r in contracts)


@pytest.mark.parametrize('kind',['reference_numeric','actual_numeric','reference_transport','actual_transport'])
def test_first_failure_preserves_prefix_and_never_fabricates_actual(tmp_path,kind):
    fixture=analytic_fixture();seen=[]
    def solve(query,binding):
        seen.append(query.request.role)
        if (kind.startswith('reference') and len(seen)==2) or (kind.startswith('actual') and query.request.role=='actual_P'):
            raise (d.NumericUnresolved if kind.endswith('numeric') else d.TransportUnresolved)('ordinary failure')
        return analytic_provider(query)
    cursor=d.Cursor(synthetic_rows(fixture),solve)
    if kind.endswith('transport'):
        with pytest.raises(d.TransportUnresolved):d.actual_prefix(fixture,tmp_path/'journal',cursor,lambda *a,**k:None)
        assert not list((tmp_path/'journal').glob('entry_*.json'))
    else:
        session,failure=d.actual_prefix(fixture,tmp_path/'journal',cursor,lambda *a,**k:None)
        assert not session.state.records and failure['stage']==kind
        if kind.startswith('reference'):
            assert not session.closed and 'actual_P' not in seen and failure['candidate_adopted'] is False
        else:
            assert session.closed and session.scientific_outcome=='actual_unresolved'
            fresh=d.journal.reopen(session.root,fixture,d.PLAN,d.CLEAN,d.METHOD,d.journal.trusted_binding(session))
            assert fresh['unaccepted_attempt']['adopted'] is False
    assert cursor.failed and not cursor.actual_finished
    with pytest.raises(ValueError):cursor(d.c.bind(reference_requests(fixture,d.PLAN,d.CLEAN,d.METHOD,0)['requests'][0]))


@pytest.mark.parametrize('fault',['parent','request','gate','contract','return','family'])
def test_cursor_rejects_wrong_binding_or_phase_before_more_transport(fault):
    fixture=analytic_fixture();rows=synthetic_rows(fixture);calls=[]
    def solve(q,b):
        calls.append(b)
        if fault=='return':return None
        value=analytic_provider(q)
        return replace(value,economic=None) if fault=='family' else value
    cursor=d.Cursor(rows,solve);h=reference_requests(fixture,d.PLAN,d.CLEAN,d.METHOD,0)
    root=d.c.bind(h['requests'][0])
    if fault=='request':cursor.rows=(dict(rows[0],request_sha='f'*64),*rows[1:])
    elif fault=='gate':cursor.rows=(dict(rows[0],state_after_actual_slot=99),*rows[1:])
    elif fault=='contract':cursor.rows=(dict(rows[0],section='contract'),*rows[1:])
    if fault in ('request','gate','contract','return','family'):
        with pytest.raises(ValueError):cursor(root)
        assert len(calls)==int(fault in ('return','family'))
        assert cursor.failed
        with pytest.raises(ValueError):cursor(root)
        assert len(calls)==int(fault in ('return','family'))
        return
    parent=cursor(root);q=d.c.bind(h['requests'][1],parent.query,parent.point,parent.economic)
    wrong=replace(q,base_point=replace(parent.point,meter_load_mw=parent.point.meter_load_mw+1))
    with pytest.raises(ValueError):cursor(wrong)
    assert len(calls)==1 and cursor.reserved==1
    with pytest.raises(ValueError):cursor(q)
    assert cursor.failed and len(calls)==1


def test_known_projection_stop_skips_actual_reservation(tmp_path,monkeypatch):
    state=SimpleNamespace(next_hour=0,stopped=False,records=())
    session=SimpleNamespace(state=state,ordinal=0,closed=False)
    monkeypatch.setattr(d.journal,'create_session',lambda *a:session)
    monkeypatch.setattr(d.journal,'trusted_binding',lambda s:{'ordinary':'binding'})
    monkeypatch.setattr(d.p1,'hour_evidence',lambda *a:object())
    pending=SimpleNamespace(proposal=SimpleNamespace(violations=('network_projection_exclusion',)))
    monkeypatch.setattr(d.journal,'begin_step',lambda *a:pending)
    def commit(s,p,actual):
        assert actual is None
        s.state=SimpleNamespace(next_hour=1,stopped=True,records=({'actual_accepted':False},));s.ordinal=1;return s
    monkeypatch.setattr(d.journal,'commit_step',commit)
    def denied(*a,**kw):pytest.fail('actual call/accept/phase finish after exclusion')
    point=SimpleNamespace(__call__=denied,accept_actual=denied,finish_actual=denied,begin_hour=lambda s:None)
    got,failure=d.actual_prefix(analytic_fixture(),tmp_path/'journal',point,lambda *a,**k:None)
    assert got.state.stopped and failure is None


@pytest.mark.parametrize('fault',['state_before_next_hour','accepted_actual'])
def test_current_state_and_accepted_actual_protocol_failures_are_permanent(tmp_path,fault):
    fixture=analytic_fixture();calls=[]
    def solve(q,b):calls.append(b);return analytic_provider(q)
    cursor=d.Cursor(synthetic_rows(fixture),solve)
    session=d.journal.create_session(tmp_path/'journal',fixture,d.PLAN,d.CLEAN,d.METHOD)
    cursor.begin_hour(session)
    evidence=d.p1.hour_evidence(fixture,session.state,cursor)
    pending=d.journal.begin_step(session,evidence)
    session=d.journal.commit_step(session,pending,cursor(d.p1.actual_query(pending)))
    if fault=='accepted_actual':
        row=dict(session.state.records[-1],actual=None)
        changed=replace(session,state=replace(session.state,records=(row,)))
        with pytest.raises(ValueError):cursor.accept_actual(changed)
        with pytest.raises(ValueError):cursor.accept_actual(session)
        assert cursor.failed and not cursor.accepted
        return
    cursor.accept_actual(session);cursor.begin_hour(session)
    before=len(calls)
    changed=replace(session,state=replace(session.state,call_energy=session.state.call_energy+1))
    with pytest.raises(ValueError,match='accepted state'):cursor.begin_hour(changed)
    assert cursor.failed and len(calls)==before


def test_incomplete_actual_finish_cannot_be_repaired_and_retried():
    fixture=analytic_fixture();rows=synthetic_rows(fixture)
    cursor=d.Cursor(rows,lambda *a:pytest.fail('transport during finish check'))
    expected={r['ordinal'] for r in rows if r['role']=='actual_P'}
    cursor.reserved=max(expected);cursor.accepted={n:'0'*64 for n in expected}
    state=SimpleNamespace(stopped=False,next_hour=fixture.observation_end,
        records=tuple({'actual_accepted':True} for _ in range(fixture.observation_end-fixture.first_hour)))
    session=SimpleNamespace(closed=False,state=state,fixture=fixture)
    saved=dict(cursor.accepted);cursor.accepted.pop(min(expected))
    with pytest.raises(ValueError):cursor.finish_actual(session)
    cursor.accepted=saved
    with pytest.raises(ValueError):cursor.finish_actual(session)
    assert cursor.failed and not cursor.actual_finished
