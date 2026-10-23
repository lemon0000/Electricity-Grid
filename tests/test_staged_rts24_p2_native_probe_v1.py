"""P2 transport in pytest temp: FakeApi only, no public native attempt."""
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pytest

from experiments import staged_rts24_p2_native_probe_v1 as d
from src import staged_rts24_journal_v2 as journal,staged_rts24_highs_backend_v1 as backend
from src import staged_rts24_process_guard_v2 as guard
from test_staged_rts24_numeric_interface_v1 import frame,raw_snapshot
from test_staged_rts24_highs_backend_v1 import FakeApi
from test_staged_rts24_p2_controller_v1 import analytic_fixture,analytic_provider,synthetic_rows

REAL_FINGERPRINTS=d.fingerprints


@pytest.fixture(autouse=True)
def ordinary(monkeypatch):
    monkeypatch.setattr(d,'fingerprints',lambda:{'ordinary_test':True})
    monkeypatch.setattr(journal,'runtime_identity',lambda:{'ordinary_test':True})
    monkeypatch.setattr(backend,'call_highs',lambda *a,**k:pytest.fail('real backend requested by ordinary P2 test'))


def one_slot(query):
    q=query.request
    return dict(ordinal=1,serial_after=None,section='actual',hour=q.hour,role=q.role,objective=q.objective,
        outage=d.control.c.plain(q.outages),request_sha=q.identity,parent_request_sha=q.anchor_id,
        parent_slot=None,state_after_actual_slot=None,reference_slots=[],evidence_kind='economic_kkt')


def test_point_protocol_recompiles_and_imports_fake_raw_twice(tmp_path,monkeypatch):
    item=frame().reference;problem,raw=raw_snapshot(item);row=one_slot(item.query)
    monkeypatch.setattr(d,'load_packet',lambda **kw:{'schedule':[row]})
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('ordinary_P2_backend_copy',Path(backend.__file__))
    copied=module_from_spec(spec);spec.loader.exec_module(copied)
    monkeypatch.setattr(backend,'call_highs',lambda problem,log:copied.call_highs(problem,log,api=FakeApi(raw)))
    def monitor(argv,**kw):
        assert Path(argv[3]).name=='staged_rts24_p2_native_probe_v1.py' and argv[1:3]==['-B','-s']
        relative=argv[argv.index('--point')+1];sha=argv[argv.index('--request-sha')+1]
        code=d.point_worker(tmp_path,relative,sha)
        return dict(job_quiet_confirmed=True,stop_reason=None,exit_code=code)
    client=d.PointTransport(tmp_path,{'ordinary_test':True},lambda *a,**k:None,monitor=monitor)
    cursor=d.control.Cursor([row],client)
    assert cursor(item.query)==item and client.reserved==client.imported==1
    record=d.load(tmp_path/'points/point_0001/request.json')
    assert record['execution_binding']['bound_query_sha']==item.query.identity
    assert record['execution_binding']['request_sha']==item.query.request.identity


@pytest.mark.parametrize('failure',['spawn','quiet','exit','binding','cap'])
def test_failed_reservation_never_retries_or_adopts(tmp_path,monkeypatch,failure):
    query=frame().reference.query;row=one_slot(query)
    monkeypatch.setattr(d,'load_packet',lambda **kw:{'schedule':[row]})
    def monitor(*a,**kw):
        if failure=='spawn':raise OSError('ordinary spawn failure')
        return dict(job_quiet_confirmed=failure!='quiet',stop_reason='child_exit_nonzero',exit_code=7)
    client=d.PointTransport(tmp_path,{'ordinary_test':True},lambda *a,**k:None,monitor=monitor)
    if failure=='cap':client.reserved=319
    if failure=='binding':row['request_sha']='f'*64
    cursor=d.control.Cursor([row],client)
    with pytest.raises((ValueError,OSError,d.TransportUnresolved)):cursor(query)
    assert client.imported==0
    if failure in ('cap','binding'):assert not (tmp_path/'points').exists()
    else:
        assert client.reserved==1 and cursor.failed
        with pytest.raises(ValueError):cursor(query)


def test_fresh_is_original_scientific_replay_with_zero_backend(tmp_path,monkeypatch):
    fixture=analytic_fixture();cursor=d.control.Cursor(synthetic_rows(fixture),lambda q,b:analytic_provider(q))
    session,failure=d.control.actual_prefix(fixture,tmp_path/'journal',cursor,lambda *a,**k:None)
    assert failure is None
    session=journal.finish(session)
    d.write(tmp_path/'start.json',dict(pins={'ordinary_test':True}))
    d.write(tmp_path/'trusted_binding.json',journal.trusted_binding(session))
    monkeypatch.setattr(d.control.c,'load_fixture',lambda:fixture)
    assert d.fresh_worker(tmp_path)==0
    saved=d.load(tmp_path/'fresh.json')
    replay=journal.reopen(session.root,fixture,d.PLAN,d.CLEAN,d.METHOD,journal.trusted_binding(session))
    assert saved['solver_calls']==0 and saved['metrics']==d.metrics(replay)


@pytest.mark.parametrize('stage',['actual','contract','finish'])
def test_worker_unknown_failure_never_proceeds_to_fresh(tmp_path,monkeypatch,stage):
    fixture=analytic_fixture();rows=synthetic_rows(fixture);packet=dict(schedule=rows,schedule_sha=d.prep.digest(rows))
    monkeypatch.setattr(d,'OUTPUT',tmp_path);monkeypatch.setattr(d,'REGISTRATION',tmp_path/'registration.json')
    monkeypatch.setattr(d,'preserve',lambda:{})
    monkeypatch.setattr(d,'load_packet',lambda **kw:packet)
    monkeypatch.setattr(d.control.c,'load_fixture',lambda:fixture)
    d.write(d.REGISTRATION,dict(pins={'ordinary_test':True},preserved={},schedule_sha=packet['schedule_sha']))
    d.write(tmp_path/'launcher_start.json',dict(limits=d.LIMITS,package='staged_rts24_P2_v1',registration_sha='ordinary'))
    class AnalyticTransport:
        def __init__(self,*a,**kw):pass
        def __call__(self,q,b):
            if stage=='actual' and q.request.role=='actual_P':raise d.TransportUnresolved('ordinary transport')
            return analytic_provider(q)
    monkeypatch.setattr(d,'PointTransport',AnalyticTransport)
    def contracts(*a,**kw):
        if stage=='contract':raise d.TransportUnresolved('ordinary contract failure')
    monkeypatch.setattr(d.control,'full_contracts',contracts)
    if stage=='finish':monkeypatch.setattr(journal,'finish',lambda s:replace(s,closed=True,scientific_outcome='persistence_failure',publication_outcome='unknown'))
    else:monkeypatch.setattr(journal,'finish',lambda *a:pytest.fail('finish after transport failure'))
    monkeypatch.setattr(guard,'supervise',lambda *a,**kw:pytest.fail('fresh after transport failure'))
    with pytest.raises(d.TransportUnresolved):d.worker(tmp_path,'ordinary')
    assert not (tmp_path/'fresh_process.json').exists() and not (tmp_path/'report.json').exists()


def test_default_cli_does_not_create_registration_or_public_output():
    script=Path(d.__file__)
    result=subprocess.run([sys.executable,'-B','-s',str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    assert result.returncode==2 and not d.OUTPUT.exists() and not d.REGISTRATION.exists()


@pytest.mark.parametrize('target',['src/staged_rts24_p2_packet_v1.py','experiments/staged_rts24_saved_profile_v1.py'])
@pytest.mark.parametrize('phase',['before_point','after_quiet','fresh'])
def test_preparation_source_drift_is_rejected_across_execution_bookends(tmp_path,monkeypatch,target,phase):
    item=frame().reference;row=one_slot(item.query);active=[False]
    monkeypatch.setattr(d.p1,'fingerprints',lambda:{'ordinary_legacy':True})
    monkeypatch.setattr(d,'fingerprints',REAL_FINGERPRINTS)
    pins=REAL_FINGERPRINTS();assert target in pins['preparation_sources']
    stamp=d.stamp
    def altered(path):
        value=stamp(path)
        return dict(value,sha256='0'*64) if active[0] and Path(path).resolve()==(d.ROOT/target).resolve() else value
    monkeypatch.setattr(d,'stamp',altered)
    if phase=='fresh':
        active[0]=True
        monkeypatch.setattr(journal,'reopen',lambda *a,**k:pytest.fail('replay after preparation drift'))
        with pytest.raises(ValueError,match='preparation source'):d.fresh_worker(tmp_path)
        assert not (tmp_path/'fresh.json').exists();return
    problem,raw=raw_snapshot(item)
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('ordinary_drift_backend',Path(backend.__file__));copied=module_from_spec(spec);spec.loader.exec_module(copied)
    monkeypatch.setattr(backend,'call_highs',lambda problem,log:copied.call_highs(problem,log,api=FakeApi(raw)))
    monkeypatch.setattr(d,'load_packet',lambda **kw:{'schedule':[row]})
    def monitor(argv,**kw):
        if phase=='before_point':active[0]=True
        code=d.point_worker(tmp_path,argv[argv.index('--point')+1],argv[argv.index('--request-sha')+1])
        active[0]=True
        return dict(job_quiet_confirmed=True,stop_reason=None,exit_code=code)
    transport=d.PointTransport(tmp_path,pins,lambda *a,**k:None,monitor=monitor)
    cursor=d.control.Cursor([row],transport)
    with pytest.raises(ValueError,match='preparation source'):cursor(item.query)
    assert cursor.failed and transport.imported==0 and transport.reserved==1
    assert (tmp_path/'points/point_0001/native.json').exists() is (phase=='after_quiet')


@pytest.mark.parametrize('fault',['after_terminal','observation_write'])
def test_cli_failure_does_not_deny_an_existing_terminal_or_publish_completion(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(d,'OUTPUT',tmp_path)
    monkeypatch.setattr(sys,'argv',[str(Path(d.__file__)),'--worker','--root',str(tmp_path),'--registration-sha','ordinary'])
    monkeypatch.setattr(d,'verify_registration',lambda *a,**k:None)
    monkeypatch.setattr(d.p1,'install_observers',lambda **kw:lambda:{'ordinary_observations':True})
    def worker(*a):
        session=journal.create_session(tmp_path/'journal',analytic_fixture(),d.PLAN,d.CLEAN,d.METHOD)
        session=journal.finish(session);assert session.closed
        if fault=='after_terminal':raise OSError('failure after terminal')
        return 0
    monkeypatch.setattr(d,'worker',worker)
    monkeypatch.setattr(d.p1,'complete_core',lambda *a:pytest.fail('completion after failed publication'))
    if fault=='observation_write':
        write=d.write
        def failed_write(path,value):
            if path.name=='worker_observations.json':raise OSError('observation write failed')
            return write(path,value)
        monkeypatch.setattr(d,'write',failed_write)
    assert d.cli()==3
    assert d.load(tmp_path/'journal/entry_000001.json')['kind']=='terminal'
    failure=d.load(tmp_path/'worker_failure.json')
    assert failure['adoption_prohibited'] is True and failure['journal_terminal_status']=='not_inspected'
    assert 'no_new_journal_terminal_or_resume' not in failure and not (tmp_path/'completion.json').exists()


@pytest.mark.parametrize('fault',['bool_as_int','count_as_float','extra'])
def test_execution_registration_closed_schema_and_scalar_types(tmp_path,monkeypatch,fault):
    monkeypatch.setattr(d.p1,'require_compute',lambda:None)
    monkeypatch.setattr(d,'preserve',lambda:{})
    monkeypatch.setattr(d,'load_packet',lambda **kw:{'schedule_sha':'a'*64})
    monkeypatch.setattr(d,'REGISTRATION',tmp_path/'registration.json')
    record=d.registration_record()
    if fault=='bool_as_int':record['native_authorized']=0
    elif fault=='count_as_float':record['max_point_attempts']=319.0
    else:record['future_permission']=True
    sha=d.write(d.REGISTRATION,record)
    with pytest.raises(ValueError,match='registration scope'):d.verify_registration(sha,full=False)
