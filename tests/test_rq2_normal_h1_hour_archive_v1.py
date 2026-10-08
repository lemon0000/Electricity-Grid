from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import sqlite3
import pytest
from pyomo.environ import SolverFactory
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_archive as api

replay=api.replay
LIMITS=replay.H1HourReplayLimits(232,1000,2000)
SAMPLE=Path(__file__).resolve().parents[1]/'results/tables/rq2_normal_h1_projection_store_v1_non_authoritative/sample_archive.json'


@pytest.fixture(scope='module')
def saved():
    raw=SAMPLE.read_bytes()
    assert sha256(raw).hexdigest()=='0a8f3ddbd3dd6895dc957378e361a88d3ef27ef08c419db744c1a7d0cd335fca'
    item=json.loads(raw)
    rows=tuple(v.encode('ascii') for v in item['reports'])
    assert [sha256(v).hexdigest() for v in rows]==item['report_sha256']
    return item,rows


@pytest.fixture(autouse=True)
def no_solver(monkeypatch):
    def denied(*a,**k):pytest.fail('hour archive/replay entered a solver')
    monkeypatch.setattr(type(SolverFactory),'__call__',denied)
    monkeypatch.setattr(replay.native.capture,'solve_once',denied)
    monkeypatch.setattr(replay.native,'run_h1_chain',denied)
    monkeypatch.setattr(replay.current,'solve_current',denied)
    monkeypatch.setattr(replay.native.capture.provenance.adapter,'create_solver',denied)


def make(tmp_path,**kw):
    return api.DevelopmentH1HourArchive(tmp_path/'hour_non_authoritative',packet(),spec(),LIMITS,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,create=True,**kw)


def fill(store,rows):
    for raw in rows:store.record_report(raw,expected_head=store.head)
    return store.finish(expected_head=store.head)


def test_stream_replay_matches_retained_old_chain(saved):
    item,rows=saved
    p=packet()
    old=replay.old.replay_reports(p,spec(),budget(),rows,expected_key=item['request_key'])
    key=replay.request_key(p,spec(),LIMITS)
    new=replay.replay_stream(p,spec(),LIMITS,iter(rows),expected_key=key)
    assert type(new) is replay.H1HourReplayedProjection
    assert type(new) is not type(old) and key!=old.request_key
    assert new.projection_payload==old.projection_payload and new.projection_identity==old.projection_identity
    assert new.canonical_locks==old.canonical_locks and new.report_sha256==old.report_sha256
    assert new.solver_calls_by_replay==0 and not new.native_execution_authenticated and not new.exact_mathematical_certificate
    assert not hasattr(new,'candidate_boundary')


def test_archive_terminal_reopen_and_single_snapshot_scan(tmp_path,saved,monkeypatch):
    _,rows=saved
    store=make(tmp_path)
    result=fill(store,rows)
    assert result.status=='accepted' and result.stored_reports==3 and result.canonical_locks==(20.,1.,20.)
    assert result.projection.projection_payload==replay.native.capture.encode(saved[0]['projection'])
    assert not result.source_authenticated and not result.parent_intent_verified and not result.formal_result
    scans=[]
    original=store._journal._scan
    def scan(connection):scans.append(1);return original(connection)
    monkeypatch.setattr(store._journal,'_scan',scan)
    assert store.inspect()==result and scans==[1]
    head=store.head
    store.close()
    opened=api.DevelopmentH1HourArchive(tmp_path/'hour_non_authoritative',packet(),spec(),LIMITS,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,expected_head=head)
    try:assert opened.inspect()==result
    finally:opened.close()


def test_rejected_raw_retained_and_no_lock_advance(tmp_path,saved):
    store=make(tmp_path)
    raw=json.loads(saved[1][0]);raw['normal_accepted']=True
    bad=replay.native.capture.encode(raw)
    try:
        result=store.record_report(bad,expected_head=store.head)
        assert result.status=='rejected' and result.stored_reports==1 and result.canonical_locks==() and result.projection is None
        assert b''.join(store._journal.iter_event(1,expected_head=store._journal.head))==bad
        with pytest.raises(ValueError,match='complete'):store.finish(expected_head=store.head)
    finally:store.close()


@pytest.mark.parametrize('kind',['missing','reverse','extra','repeat'])
def test_full_order_required(saved,kind):
    rows=saved[1]
    values=rows[:-1] if kind=='missing' else tuple(reversed(rows)) if kind=='reverse' else rows+rows[-1:] if kind=='extra' else (rows[0],rows[0],rows[-1])
    p=packet()
    with pytest.raises(ValueError):replay.replay_stream(p,spec(),LIMITS,iter(values),expected_key=replay.request_key(p,spec(),LIMITS))


@pytest.mark.parametrize('fault',['before','after','noop'])
def test_durability_unknown_does_not_advance_lock(tmp_path,saved,monkeypatch,fault):
    store=make(tmp_path)
    commit=store._journal._commit
    def fail(connection):
        if fault=='after':commit(connection)
        if fault!='noop':raise RuntimeError('injected durability ambiguity')
    monkeypatch.setattr(store._journal,'_commit',fail)
    try:
        with pytest.raises((ValueError,RuntimeError)):store.record_report(saved[1][0],expected_head=store.head)
        assert store._state.canonical_locks==()
        with pytest.raises(ValueError,match='unresolved'):_=store.head
    finally:store.close()


@pytest.mark.parametrize('limits',[(233,1000,2000),(True,1,1),(232,False,1),(232,1,1000001)])
def test_replay_size_limits(limits):
    with pytest.raises(ValueError):replay.H1HourReplayLimits(*limits)


def test_legacy_budget_rejected_in_new_api_and_new_limits_rejected_in_legacy(saved):
    with pytest.raises(ValueError,match='exact'):replay.request_key(packet(),spec(),budget())
    with pytest.raises(ValueError):replay.current.request_key(packet(),spec(),LIMITS)


def test_awaiting_terminal_has_no_projection(tmp_path,saved):
    store=make(tmp_path)
    try:
        for row in saved[1]:result=store.record_report(row,expected_head=store.head)
        assert result.status=='awaiting_terminal' and result.projection is None
    finally:store.close()


@pytest.mark.parametrize('field,value',[
    ('index',True),('request_key','0'*64),('lock_hex',float(21).hex()),
    ('prior_locks_sha256','0'*64),('stage_identity','0'*64),('numeric_sha256','0'*64),
    ('objective',['generation','G1']),('extra',None),
])
def test_self_consistent_storage_cannot_forge_stage_metadata(tmp_path,saved,field,value):
    store=make(tmp_path)
    raw=saved[1][0]
    try:
        stage=replay._audit_stage(packet(),spec(),LIMITS,0,(),raw)
        metadata=store._stage_metadata(0,(),raw,stage,None)
        metadata[field]=value
        store._journal.append(metadata,iter([raw]),expected_head=store._journal.head,
            declared_payload_bytes=len(raw),expected_payload_sha256=sha256(raw).hexdigest())
        with pytest.raises(ValueError,match='metadata'):store.inspect()
        with pytest.raises(ValueError,match='unresolved'):_=store.head
    finally:store.close()


@pytest.mark.parametrize('field',['parent','source','packet','limits'])
def test_external_binding_drift_rejected_on_reopen(tmp_path,saved,field):
    store=make(tmp_path)
    store.record_report(saved[1][0],expected_head=store.head)
    head=store.head
    store.close()
    with pytest.raises(ValueError):api.DevelopmentH1HourArchive(tmp_path/'hour_non_authoritative',
        packet(raw_workload='0.1') if field=='packet' else packet(),spec(),
        replace(LIMITS,max_variables=999) if field=='limits' else LIMITS,
        parent_intent_head='3'*64 if field=='parent' else '1'*64,
        source_lineage_identity='3'*64 if field=='source' else '2'*64,expected_head=head)


def test_native_bound_failure_preserves_raw_and_stops(tmp_path,saved):
    store=make(tmp_path)
    try:
        first=store.record_report(saved[1][0],expected_head=store.head)
        report=json.loads(saved[1][1])
        report['provenance']['native']['ObjBound']['hex']=float(2).hex()
        raw=replay.native.capture.encode(report)
        rejected=store.record_report(raw,expected_head=store.head)
        assert rejected.status=='rejected' and rejected.canonical_locks==first.canonical_locks
        assert rejected.projection is None and rejected.stored_reports==2
        assert b''.join(store._journal.iter_event(2,expected_head=store._journal.head))==raw
        with pytest.raises(ValueError):store.record_report(saved[1][2],expected_head=store.head)
    finally:store.close()


def test_assignment_rejection_even_when_numeric_gate_forced_true(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    report=json.loads(saved[1][0])
    found=False
    for pair in report['assignment']:
        if pair[0]=='generation[normal,0,G1]':pair[1]=float(21).hex();found=True
    assert found
    monkeypatch.setattr(replay.native.replay,'verify_numerical',lambda *a:None)
    monkeypatch.setattr(replay.native.predicate,'evaluate',lambda *a,**k:{'candidate_numeric_predicate_passed':True})
    try:
        result=store.record_report(replay.native.capture.encode(report),expected_head=store.head)
        assert result.status=='rejected' and result.projection is None and result.canonical_locks==()
    finally:store.close()


def test_fresh_archive_replay_failure_after_physical_commit_poisoned(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    original=store._restore
    calls=[]
    def restore():
        calls.append(1)
        if len(calls)==2:raise ValueError('injected semantic readback failure')
        return original()
    monkeypatch.setattr(store,'_restore',restore)
    try:
        with pytest.raises(ValueError):store.record_report(saved[1][0],expected_head=store.head)
        assert store._state.canonical_locks==()
        with pytest.raises(ValueError,match='unresolved'):_=store.head
        connection=sqlite3.connect(store._journal._database)
        try:assert connection.execute('SELECT count(*) FROM events').fetchone()==(1,)
        finally:connection.close()
    finally:store.close()


def test_wrong_predecessor_consumes_no_report(tmp_path,saved):
    store=make(tmp_path)
    try:
        with pytest.raises(ValueError,match='predecessor'):store.record_report(saved[1][0],expected_head='0'*64)
        connection=sqlite3.connect(store._journal._database)
        try:assert connection.execute('SELECT count(*) FROM events').fetchone()==(0,)
        finally:connection.close()
    finally:store.close()


def test_terminal_metadata_is_recomputed(tmp_path,saved):
    store=make(tmp_path)
    try:
        for row in saved[1]:store.record_report(row,expected_head=store.head)
        projection=store._replay_complete_prefix()
        metadata=store._terminal_metadata(projection)
        metadata['projection_identity']='0'*64
        store._journal.append(metadata,iter(()),expected_head=store._journal.head,
            declared_payload_bytes=0,expected_payload_sha256=sha256(b'').hexdigest())
        with pytest.raises(ValueError,match='metadata'):store.inspect()
    finally:store.close()


def test_complete_terminal_rejects_extra_report(tmp_path,saved):
    store=make(tmp_path)
    try:
        fill(store,saved[1])
        with pytest.raises(ValueError,match='terminal'):store.record_report(saved[1][0],expected_head=store.head)
    finally:store.close()


def test_stream_drift_after_last_report_rejects(saved):
    p=packet()
    key=replay.request_key(p,spec(),LIMITS)
    def reports():
        yield from saved[1]
        object.__setattr__(p,'input_identity','0'*64)
    with pytest.raises(ValueError):replay.replay_stream(p,spec(),LIMITS,reports(),expected_key=key)


@pytest.mark.parametrize('limits',[replace(LIMITS,max_variables=1),replace(LIMITS,max_constraints=1)])
def test_replay_resource_mismatch_is_not_report_rejection(tmp_path,saved,limits):
    store=api.DevelopmentH1HourArchive(tmp_path/'hour_non_authoritative',packet(),spec(),limits,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,create=True)
    try:
        with pytest.raises(ValueError,match='size limits') as error:store.record_report(saved[1][0],expected_head=store.head)
        assert type(error.value) is ValueError
        assert store._state.canonical_locks==()
        connection=sqlite3.connect(store._journal._database)
        try:assert connection.execute('SELECT count(*) FROM events').fetchone()==(0,)
        finally:connection.close()
        with pytest.raises(ValueError,match='unresolved'):_=store.head
    finally:store.close()


def test_model_failure_is_not_raw_report_rejection(tmp_path,saved,monkeypatch):
    store=make(tmp_path)
    def broken(*a,**k):raise ValueError('model construction failed')
    monkeypatch.setattr(replay.native.model_api,'build_h1_stage_model',broken)
    try:
        with pytest.raises(ValueError,match='construction'):store.record_report(saved[1][0],expected_head=store.head)
        connection=sqlite3.connect(store._journal._database)
        try:assert connection.execute('SELECT count(*) FROM events').fetchone()==(0,)
        finally:connection.close()
    finally:store.close()



def test_report_iterator_cannot_hide_solver_call(saved):
    p=packet()
    def rows():
        yield from saved[1]
        try:replay.native.capture.solve_once()
        except RuntimeError:pass
    with pytest.raises(RuntimeError,match='attempted'):
        replay.replay_stream(p,spec(),LIMITS,rows(),expected_key=replay.request_key(p,spec(),LIMITS))


def test_absolute_source_clock_excluded_from_new_computational_key():
    from datetime import timedelta
    p=packet()
    row=replace(p.inputs.data.hourly_points[0],timestamp=p.inputs.data.hourly_points[0].timestamp+timedelta(days=900))
    q=packet(data=p.inputs.data,row=row)
    assert p.audit_identity!=q.audit_identity
    assert replay.request_key(p,spec(),LIMITS)==replay.request_key(q,spec(),LIMITS)


def test_fixed_rts_232_stage_declaration_does_not_admit_native():
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_binding as binding
    root=Path(__file__).resolve().parents[1]
    config=Path(binding.windows.audit.DEFAULT_CONFIG)
    d=binding.H1SourceDeclaration('training',0,0,20260822,sha256(config.read_bytes()).hexdigest())
    receipt=binding.load_pinned_current(d,root/'data/raw/rts_gmlc/v0.2.3/upstream',config_path=config)
    assert receipt.identity=='b9eba05a8f993c849642ce4fe2a15deb9767a07fd5b3aedcd1672c03767c36fe'
    p=replay.current.source.assemble_current_normal(receipt.network,receipt.row,receipt.raw_workload,
        relative_hour=0,dc_bus=108,source_time_basis=receipt.source_time_basis)
    assert len(replay.native.model_api.stage_order(p.inputs))==232
    key=replay.request_key(p,spec(),LIMITS)
    with pytest.raises(ValueError,match='incomplete'):replay.replay_stream(p,spec(),LIMITS,iter(()),expected_key=key)
    with pytest.raises(ValueError):replay.current.request_key(p,spec(),budget())
    with pytest.raises(ValueError,match='count'):replay.request_key(p,spec(),replace(LIMITS,max_stages=231))
