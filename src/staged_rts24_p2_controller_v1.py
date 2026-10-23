"""Serial P2 scientific orchestration; transport is supplied by the P2 driver."""
from dataclasses import asdict
from pathlib import Path

from experiments import staged_rts24_native_probe_v1 as p1
from src import staged_rts24_development_v1 as c, staged_rts24_journal_v2 as journal
from src import staged_rts24_p2_packet_v1 as prep
from src.staged_rts24_causal_v1 import PointEvidence

PLAN,CLEAN,METHOD=prep.PLAN,prep.CLEAN,prep.METHOD
TransportUnresolved,NumericUnresolved=p1.TransportUnresolved,p1.NumericUnresolved


class Cursor:
    """Fail-closed reservations and parent/accepted-hour edges, separate from CAS."""
    def __init__(self,rows,transport):
        self.rows=tuple(rows);self.transport=transport
        self.reserved=0;self.evidence={};self.accepted={};self.actual_finished=False;self.failed=False

    def __call__(self,query):
        c.require(not self.failed and self.reserved<len(self.rows),'P2 cursor closed or exhausted')
        try:return self._solve(query)
        except BaseException:
            self.failed=True
            raise

    def _solve(self,query):
        slot=self.rows[self.reserved];q=query.request
        c.require(slot['ordinal']==self.reserved+1 and slot['serial_after']==(self.reserved or None),'P2 serial edge differs')
        c.require((q.plan,q.clean_path,q.method,q.hour,q.role,q.objective,q.anchor_id)==
            (PLAN,CLEAN,METHOD,slot['hour'],slot['role'],slot['objective'],slot['parent_request_sha']),'P2 slot frame differs')
        c.require(prep.digest(c.plain(q.outages))==prep.digest(slot['outage']),'P2 slot outage differs')
        c.require(slot['request_sha'] is None and q.role=='actual_P' or q.identity==slot['request_sha'],'P2 static request differs')
        gate=slot['state_after_actual_slot']
        c.require(gate is None or gate in self.accepted,'previous actual not accepted')
        c.require(slot['section']!='contract' or self.actual_finished,'actual phase not finished')
        c.require(all(n in self.evidence for n in slot['reference_slots']),'actual references incomplete')
        parent=self.evidence.get(slot['parent_slot'])
        if slot['parent_slot'] is None:
            c.require(query.base_query is query.base_point is query.base_economic is None,'unexpected P2 parent')
        else:
            c.require(parent is not None and parent.economic is not None and query.base_query==parent.query
                and query.base_point==parent.point and query.base_economic==parent.economic,'P2 parent point/economic differs')
        binding=dict(ordinal=slot['ordinal'],slot_sha=prep.digest(slot),request_sha=q.identity,bound_query_sha=query.identity,
            parent_slot=slot['parent_slot'],parent_point_sha=None if parent is None else c.digest(parent.point),
            parent_economic_sha=None if parent is None else c.digest(parent.economic),state_after_actual_slot=gate,
            accepted_state_sha=None if gate is None else self.accepted[gate])
        self.reserved+=1  # Never refunded after a valid reservation, even on storage failure.
        try:
            value=self.transport(query,binding)
            c.require(type(value) is PointEvidence and value.query==query,'P2 returned evidence query differs')
            family=slot['evidence_kind']
            c.require((family=='economic_kkt' and value.economic is not None and value.child_lp is None)
                or (family=='child_lp_kkt' and value.child_lp is not None and value.economic is None)
                or (family=='primal_point' and value.economic is value.child_lp is None),'P2 evidence family differs')
            self.evidence[self.reserved]=value
            return value
        except BaseException:
            self.failed=True
            raise

    def begin_hour(self,session):
        try:
            c.require(not self.failed and self.reserved<len(self.rows),'P2 actual cursor unavailable')
            slot=self.rows[self.reserved];gate=slot['state_after_actual_slot']
            c.require(slot['section']=='actual' and slot['hour']==session.state.next_hour,'P2 current hour differs')
            c.require((gate is None and not session.state.records and session.state.next_hour==session.fixture.first_hour)
                or gate in self.accepted and self.accepted[gate]==c.digest(session.state),'P2 accepted state changed')
        except BaseException:
            self.failed=True
            raise

    def accept_actual(self,session):
        try:
            c.require(not self.failed and not self.actual_finished and self.reserved not in self.accepted and not session.closed and not session.state.stopped,'actual acceptance unavailable')
            slot=self.rows[self.reserved-1];row=session.state.records[-1]
            c.require(slot['role']=='actual_P' and slot['hour']==session.state.next_hour-1 and row['actual_accepted'] is True
                and row['actual']==self.evidence[self.reserved],'accepted actual binding differs')
            self.accepted[self.reserved]=c.digest(session.state)
        except BaseException:
            self.failed=True
            raise

    def finish_actual(self,session):
        try:
            expected={r['ordinal'] for r in self.rows if r['role']=='actual_P'}
            c.require(not self.failed and not self.actual_finished and self.reserved==max(expected) and not session.closed and not session.state.stopped
                and session.state.next_hour==session.fixture.observation_end
                and len(session.state.records)==session.fixture.observation_end-session.fixture.first_hour
                and set(self.accepted)==expected and all(r['actual_accepted'] is True for r in session.state.records),'actual phase incomplete')
            self.actual_finished=True
        except BaseException:
            self.failed=True
            raise


def actual_prefix(fixture,root,point,events):
    session=journal.create_session(root,fixture,PLAN,CLEAN,METHOD)
    prefixes=Path(root).parent/'trusted_prefixes';prefixes.mkdir(exist_ok=False)
    def checkpoint():p1.write(prefixes/f'prefix_{session.ordinal:06d}.json',journal.trusted_binding(session))
    checkpoint()
    while session.state.next_hour<fixture.observation_end and not session.state.stopped:
        point.begin_hour(session)
        try:evidence=p1.hour_evidence(fixture,session.state,point)
        except NumericUnresolved as exc:
            return session,dict(stage='reference_numeric',type=type(exc).__name__,message=str(exc),
                current_observation=c.plain(c.observe(fixture,PLAN,CLEAN,session.state.next_hour)),
                unaccepted_status='numeric_unresolved_observed_current_inputs',candidate_adopted=False)
        try:pending=journal.begin_step(session,evidence)
        except journal.SessionClosed as exc:
            p1.write(Path(root).parent/'writer_closed_binding.json',journal.trusted_binding(exc.session))
            raise TransportUnresolved('journal closed while preparing') from exc
        excluded=any(code.startswith('network_projection_') or code=='connection_capacity' for code in pending.proposal.violations)
        try:actual=None if excluded else point(p1.actual_query(pending))
        except NumericUnresolved as exc:
            session=journal.commit_step(session,pending,None)
            p1.write(Path(root).parent/'writer_closed_binding.json',journal.trusted_binding(session))
            if session.scientific_outcome!='actual_unresolved' or session.publication_outcome!='committed':
                raise TransportUnresolved('numeric attempt publication unresolved')
            return session,dict(stage='actual_numeric',type=type(exc).__name__,message=str(exc))
        session=journal.commit_step(session,pending,actual)
        if session.closed:
            p1.write(Path(root).parent/'writer_closed_binding.json',journal.trusted_binding(session))
            raise TransportUnresolved('journal publication or audit unresolved')
        checkpoint()
        if session.state.records[-1]['actual_accepted']:point.accept_actual(session)
        events('hour_adopted',next_hour=session.state.next_hour,stopped=session.state.stopped)
    if not session.state.stopped:point.finish_actual(session)
    return session,None


def full_contracts(fixture,point,events,rows):
    from src.staged_rts24_audit_v1 import audit_legal_x,audit_point
    from src.staged_rts24_child_optimality_v1 import audit_child_lp
    c.require(point.actual_finished,'contract before actual completion')
    for hour in (1,2):
        h=c.hour_requests(fixture,PLAN,CLEAN,METHOD,hour)
        normal=next(q for q in h['requests'] if q.role=='normal_contract_C')
        root=point(c.bind(normal))
        for outage in fixture.selected:
            requests=[q for q in h['requests'] if q.outages==outage and q.role in ('fault_firm_F','fault_raw_need')]
            c.require([q.role for q in requests]==['fault_firm_F','fault_raw_need'],'contract roles differ')
            firm,raw=(point(c.bind(q,root.query,root.point,root.economic)) for q in requests)
            firm_audit=audit_point(firm.query,firm.point)
            c.require(firm_audit['point_constraints_satisfied'],'invalid firm point evidence')
            c.require(raw.child_lp is not None,'raw optimality evidence missing')
            raw_audit=audit_child_lp(raw.query,raw.point,raw.child_lp)
            c.require(raw_audit['lp_optimality_conditions_satisfied'],'invalid raw optimality evidence')
            rows.append(dict(hour=hour,outage=asdict(outage),normal_query=root.query.identity,
                firm_query=firm.query.identity,raw_query=raw.query.identity,raw_curtailment_mw=raw.point.curtailment_mw,
                normal_point_sha=c.digest(root.point),normal_economic_sha=c.digest(root.economic),
                firm_point_sha=c.digest(firm.point),raw_point_sha=c.digest(raw.point),raw_optimality_sha=c.digest(raw.child_lp),
                firm_audit=firm_audit,raw_optimality_audit=raw_audit,
                legal_X=audit_legal_x(raw.query,raw.point,*raw.query.request.rights)))
            events('contract_row',hour=hour,rows=len(rows))
