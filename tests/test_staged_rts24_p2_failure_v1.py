"""P2-specific FakeApi and 319-slot control faults, never public numeric evidence."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from experiments import staged_rts24_p2_native_probe_v1 as d
from experiments.staged_rts24_causal_examples_v1 import analytic_fixture,analytic_point
from src import staged_rts24_evidence_store_v1 as codec,staged_rts24_journal_v2 as journal
from src import staged_rts24_highs_backend_v1 as backend,staged_rts24_process_guard_v2 as guard
from src.staged_rts24_causal_v1 import PointEvidence
from test_staged_rts24_numeric_interface_v1 import frame
from test_staged_rts24_native_probe_v1 import install_fake_backend


@pytest.fixture(autouse=True)
def ordinary(monkeypatch):
    import pyomo.environ as pyo
    monkeypatch.setattr(pyo,'SolverFactory',lambda *a,**k:pytest.fail('solver requested in ordinary fault test'))
    monkeypatch.setattr(backend,'call_highs',lambda *a,**k:pytest.fail('real native requested'))
    monkeypatch.setattr(d,'fingerprints',lambda:{'ordinary_test':True})
    monkeypatch.setattr(journal,'runtime_identity',lambda:{'ordinary_test':True})


def slot(query):
    q=query.request
    return dict(ordinal=1,serial_after=None,section='actual',hour=q.hour,role=q.role,objective=q.objective,
        outage=d.control.c.plain(q.outages),request_sha=q.identity,parent_request_sha=q.anchor_id,
        parent_slot=None,state_after_actual_slot=None,reference_slots=[],evidence_kind='economic_kkt')


@pytest.mark.parametrize('mode',['nonoptimal','warning','getInfo','getRunTime','store','raw_publish','log'])
def test_P2_raw_failure_is_reproduced_or_stays_transport_without_retry(tmp_path,monkeypatch,mode):
    api=install_fake_backend(monkeypatch,(lambda raw,path:path.unlink()) if mode=='log' else None)
    if mode=='nonoptimal':api.model_status='kTimeLimit'
    elif mode=='warning':api.fail_at='run'
    elif mode in ('getInfo','getRunTime'):
        api.model_status='kTimeLimit'
        monkeypatch.setattr(api,mode,lambda:(_ for _ in ()).throw(OSError('ordinary getter failure')))
    query=frame().reference.query;row=slot(query);monkeypatch.setattr(d,'load_packet',lambda **kw:dict(schedule=[row]))
    def monitor(argv,**kw):
        if mode=='store':
            original=codec.EvidenceStore.put
            def put(store,value):
                if type(value) is PointEvidence:raise OSError('ordinary point CAS failure')
                return original(store,value)
            monkeypatch.setattr(codec.EvidenceStore,'put',put)
        elif mode=='raw_publish':
            original=d.write
            def write(path,value):
                if path.name=='native.json':raise OSError('ordinary raw publication failure')
                return original(path,value)
            monkeypatch.setattr(d,'write',write)
        code=d.point_worker(tmp_path,argv[argv.index('--point')+1],argv[argv.index('--request-sha')+1])
        return dict(job_quiet_confirmed=True,exit_code=code,stop_reason='child_exit_nonzero')
    transport=d.PointTransport(tmp_path,{'ordinary_test':True},lambda *a,**k:None,monitor=monitor)
    cursor=d.control.Cursor([row],transport)
    expected=d.NumericUnresolved if mode in ('nonoptimal','warning') else d.TransportUnresolved
    with pytest.raises(expected):cursor(query)
    assert cursor.failed and (transport.reserved,transport.imported)==(1,0)
    result=d.load(tmp_path/'points/point_0001/result.json')
    assert result['status']==('numeric_unresolved' if mode in ('nonoptimal','warning') else 'transport_unresolved')
    if mode in ('nonoptimal','warning'):assert (transport.run_invoked,transport.run_returned)==(1,1)
    with pytest.raises(ValueError):cursor(query)
    assert transport.reserved==1


@pytest.fixture
def worker_control(tmp_path,monkeypatch):
    """Only original worker/full_contracts control runs; journal, audit, transport are explicit substitutes."""
    core=d.control.c;base=analytic_fixture()
    # Unique control labels share one analytic branch shape; they are not 69 public contingencies.
    selected=tuple(core.Outage('ordinary_label_'+str(i),(2,)) for i in range(69))
    fixture=replace(base,selected=selected)
    root=tmp_path/'worker';root.mkdir();trace=[];fault={'kind':None}
    monkeypatch.setattr(d,'OUTPUT',root);monkeypatch.setattr(d,'REGISTRATION',tmp_path/'registration.json')
    monkeypatch.setattr(d,'preserve',lambda:{'ordinary':'prior'})
    monkeypatch.setattr(d,'load_packet',lambda **kw:dict(schedule=[],schedule_sha='a'*64))
    monkeypatch.setattr(core,'load_fixture',lambda:fixture)
    monkeypatch.setattr(core,'bind',lambda request,*a:SimpleNamespace(request=request,identity=request.identity))
    from src import staged_rts24_audit_v1 as audit,staged_rts24_child_optimality_v1 as child
    monkeypatch.setattr(audit,'audit_point',lambda *a:dict(point_constraints_satisfied=True))
    monkeypatch.setattr(audit,'audit_legal_x',lambda *a:dict(point_legal_under_X=False))
    monkeypatch.setattr(child,'audit_child_lp',lambda *a:dict(lp_optimality_conditions_satisfied=True))
    class Transport:
        def __init__(self,*a,**kw):
            self.reserved=self.imported=self.run_invoked=self.run_returned=41
        def __call__(self,query,binding=None):
            self.reserved+=1;self.run_invoked+=1;self.run_returned+=1
            if self.reserved==319 and fault['kind'] in ('late_numeric','late_transport'):
                raise (d.NumericUnresolved if fault['kind']=='late_numeric' else d.TransportUnresolved)('ordinary last raw')
            self.imported+=1
            return SimpleNamespace(query=query,point=analytic_point(query,query.request.meter_min),economic={'ordinary':True},child_lp={'ordinary':True})
    class Cursor:
        def __init__(self,rows,transport):
            self.transport=transport;self.actual_finished=True
            self.accepted={n:'b'*64 for n in (4,8,12,17,21,25,29,33,37,41)}
        @property
        def reserved(self):return self.transport.reserved
        def __call__(self,q):return self.transport(q)
    monkeypatch.setattr(d,'PointTransport',Transport);monkeypatch.setattr(d.control,'Cursor',Cursor)
    state=SimpleNamespace(stopped=False,records=tuple({'ordinary_accepted':True} for _ in range(10)))
    session=SimpleNamespace(closed=False,state=state,fixture=fixture,publication_outcome='committed',scientific_outcome='complete')
    monkeypatch.setattr(d.control,'actual_prefix',lambda *a:(session,None))
    def finish(s):
        trace.append('finish');s.closed=True
        d.write(root/'ordinary_terminal_marker.json',dict(scope='control substitute only'));return s
    monkeypatch.setattr(journal,'finish',finish)
    monkeypatch.setattr(journal,'trusted_binding',lambda s:dict(ordinary_binding=True))
    def reopen(*a):trace.append('parent_reopen');return dict(ordinary_metrics=True)
    monkeypatch.setattr(journal,'reopen',reopen);monkeypatch.setattr(d,'metrics',lambda value:value)
    def monitor(*a,**kw):
        trace.append('fresh_monitor')
        d.write(root/'fresh.json',dict(metrics={'ordinary_metrics':False} if fault['kind']=='metrics' else {'ordinary_metrics':True},solver_calls=0))
        return dict(job_quiet_confirmed=fault['kind']!='quiet',exit_code=2 if fault['kind']=='fresh_exit' else 0,
            stop_reason='wall_limit' if fault['kind']=='fresh_timeout' else None)
    monkeypatch.setattr(guard,'supervise',monitor)
    d.write(d.REGISTRATION,dict(pins={'ordinary_test':True},preserved={'ordinary':'prior'},schedule_sha='a'*64))
    d.write(root/'launcher_start.json',dict(limits=d.LIMITS,package='staged_rts24_P2_v1',registration_sha='ordinary'))
    return SimpleNamespace(root=root,trace=trace,fault=fault)


def test_last_contract_numeric_failure_preserves_137_rows_and_completes_diagnostic(worker_control):
    case=worker_control;case.fault['kind']='late_numeric'
    assert d.worker(case.root,'ordinary')==2
    report=d.load(case.root/'report.json');rows=d.load(case.root/'contract_rows.json')
    assert (report['point_attempts_reserved'],report['points_imported'])==(319,318) and len(rows)==137
    assert len(report['actual_accepted_slots'])==10 and report['failure']['stage']=='contract_numeric'
    assert case.trace==['finish','fresh_monitor','parent_reopen']
    assert report['package_complete'] is report['full_139_executed'] is False
    assert all(r['legal_X']['point_legal_under_X'] is False for r in rows)


def test_last_contract_transport_failure_does_not_finish_or_publish_in_memory_rows(worker_control):
    case=worker_control;case.fault['kind']='late_transport'
    with pytest.raises(d.TransportUnresolved):d.worker(case.root,'ordinary')
    assert not case.trace and not (case.root/'contract_rows.json').exists() and not (case.root/'report.json').exists()


@pytest.mark.parametrize('fault',['fresh_exit','fresh_timeout','quiet','metrics'])
def test_fresh_or_parent_failure_retains_terminal_marker_and_does_not_claim_report(worker_control,fault):
    case=worker_control;case.fault['kind']=fault
    with pytest.raises(ValueError,match='fresh'):d.worker(case.root,'ordinary')
    assert (case.root/'ordinary_terminal_marker.json').exists() and len(d.load(case.root/'contract_rows.json'))==138
    assert not (case.root/'report.json').exists()
    assert case.trace==['finish','fresh_monitor']+(['parent_reopen'] if fault=='metrics' else [])


def test_original_P2_fresh_reopen_rejection_does_not_publish_fresh(tmp_path,monkeypatch):
    d.write(tmp_path/'start.json',dict(pins={'ordinary_test':True}));d.write(tmp_path/'trusted_binding.json',dict(ordinary=True))
    monkeypatch.setattr(d.control.c,'load_fixture',lambda:analytic_fixture())
    monkeypatch.setattr(journal,'reopen',lambda *a:(_ for _ in ()).throw(ValueError('ordinary corrupt retained evidence')))
    with pytest.raises(ValueError,match='corrupt retained'):d.fresh_worker(tmp_path)
    assert not (tmp_path/'fresh.json').exists()
