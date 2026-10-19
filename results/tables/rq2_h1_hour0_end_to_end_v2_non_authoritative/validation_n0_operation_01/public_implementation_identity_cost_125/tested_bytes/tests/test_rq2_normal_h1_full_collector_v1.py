from dataclasses import replace
import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,packet,spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_collector as api

REQUIRE_GATE = api.DevelopmentH1FullCollector._require_execution_gate


@pytest.fixture(autouse=True)
def mocked_gate_with_solver_forbidden(no_solver, monkeypatch):
    monkeypatch.setattr(api.DevelopmentH1FullCollector, '_require_execution_gate', lambda *a: None)


@pytest.mark.parametrize('entry', ['_run_development', '_run_checkpoint_development'])
def test_native_entry_requires_gate_before_capture(tmp_path, monkeypatch, entry):
    monkeypatch.setattr(api.DevelopmentH1FullCollector, '_require_execution_gate', REQUIRE_GATE)
    owner = make(tmp_path, create=True)
    try:
        with pytest.raises(ValueError, match='seal/review/run-authority'):
            getattr(owner, entry)(expected_head=owner.inspect().inspection.registry_head)
        assert owner._registry.inspect().events == 0
    finally:
        owner.close()


def inputs():
    p=packet()
    order=api.base.native.model_api.stage_order(p.inputs)
    work=api.resources.H1NormalWork('normal',1,order,spec())
    content=api.resources.content_inventory(len(order),1)['total_content_limit_bytes']
    envelope=api.resources.serial.TaskEnvelope('normal',100,97,1000,content+100,100,1,100,500)
    resource=api.resources.H1TaskResources(envelope,100)
    total=api.resources.serial.SerialResourceBudget(110,10,100,100,1200,100,content+300,1)
    limits=api.base.replay.H1HourReplayLimits(3,100,500)
    return p,work,resource,total,limits


def make(tmp_path,*,values=None,**kwargs):
    return api.DevelopmentH1FullCollector(tmp_path/'collector_non_authoritative',*(values or inputs()),
        anchor_root=tmp_path/'anchor_non_authoritative',parent_intent_head='1'*64,
        source_lineage_identity='2'*64,**kwargs)


def test_complete_saved_chain_exact_new_receipt_and_readonly_reopen(tmp_path,saved,monkeypatch):
    owner=make(tmp_path,create=True)
    calls=[]
    def solve(*a,**k):
        assert owner._anchor.inspect().registry_head==owner._registry.head
        calls.append(k)
        return saved[1][len(calls)-1]
    monkeypatch.setattr(api.base.native.capture,'solve_once',solve)
    try:
        with pytest.raises(ValueError,match='Job controller'):owner.run()
        assert owner._registry.inspect().events==0 and not calls
        result=owner._run_development(expected_head=owner.inspect().inspection.registry_head)
        assert type(result) is api.H1FullCollectorInspection
        assert result.inspection.status=='accepted' and result.inspection.solver_calls==3
        assert len(calls)==3 and all(c['max_variables']==100 and c['max_constraints']==500 for c in calls)
        assert result.whole_task_resources_verified is False and result.formal_execution_ready is False
        pin=owner._anchor.inspect().record_sha256
    finally:owner.close()
    owner=make(tmp_path,expected_anchor_record=pin)
    try:
        assert owner.inspect()==result
        with pytest.raises(ValueError,match='retried'):
            owner._run_development(expected_head=result.inspection.registry_head)
    finally:owner.close()


@pytest.mark.parametrize('fault',['wall','disk','old_type','missing_stage','shape'])
def test_bad_complete_declaration_rejected_before_files(tmp_path,fault):
    p,work,resource,total,limits=inputs()
    if fault=='wall':total=replace(total,max_total_wall_seconds=1)
    elif fault=='disk':resource=replace(resource,envelope=replace(resource.envelope,archive_bytes=1))
    elif fault=='old_type':work=object()
    elif fault=='missing_stage':work=replace(work,stage_order=(work.stage_order[0],work.stage_order[-1]))
    elif fault=='shape':resource=replace(resource,envelope=replace(resource.envelope,max_variables=1))
    with pytest.raises(ValueError):make(tmp_path,values=(p,work,resource,total,limits),create=True)
    assert not (tmp_path/'collector_non_authoritative').exists()
    assert not (tmp_path/'anchor_non_authoritative').exists()


@pytest.mark.parametrize('persisted',[False,True])
def test_checkpoint_unknown_reopens_without_projection_or_retry(tmp_path,saved,monkeypatch,persisted):
    owner=make(tmp_path,create=True)
    monkeypatch.setattr(api.base.native.capture,'solve_once',lambda *a,**k:saved[1][0])
    commit=owner._child._journal._commit
    def fail(conn):
        if persisted:commit(conn)
        raise RuntimeError('child write unknown')
    monkeypatch.setattr(owner._child._journal,'_commit',fail)
    try:
        with pytest.raises(RuntimeError):owner._run_development(expected_head=owner.inspect().inspection.registry_head)
        pin=owner._anchor.inspect().record_sha256
    finally:owner.close()
    owner=make(tmp_path,expected_anchor_record=pin)
    try:
        state=owner.inspect().inspection
        assert state.status=='pending_unknown' and state.stored_reports==int(persisted)
        assert state.projection is None and state.solver_calls is None
        with pytest.raises(ValueError,match='retried'):owner._run_development(expected_head=state.registry_head)
    finally:owner.close()


@pytest.mark.parametrize('phase', [1, 2, 5, 6])
@pytest.mark.parametrize('persisted', [False, True])
def test_full_anchor_effect_windows_block_followup_calls(tmp_path, saved, monkeypatch, phase, persisted):
    owner = make(tmp_path, create=True)
    calls = []
    def solve(*a, **k):
        calls.append(1)
        return saved[1][len(calls)-1]
    monkeypatch.setattr(api.base.native.capture, 'solve_once', solve)
    advance = owner._anchor.advance
    def uncertain(*a, **k):
        if owner._anchor.inspect().sequence+1 != phase:
            return advance(*a, **k)
        if persisted: advance(*a, **k)
        raise RuntimeError('full anchor confirmation unknown')
    monkeypatch.setattr(owner._anchor, 'advance', uncertain)
    try:
        head = owner.inspect().inspection.registry_head
        with pytest.raises(RuntimeError): owner._run_development(expected_head=head)
        pin = owner._anchor.inspect().record_sha256
        assert len(calls) == {1: 0, 2: 1, 5: 3, 6: 3}[phase]
        with pytest.raises(ValueError): owner._run_development(expected_head=head)
    finally:
        owner.close()
    if not persisted:
        with pytest.raises(ValueError): make(tmp_path, expected_anchor_record=pin)
    else:
        reopened = make(tmp_path, expected_anchor_record=pin)
        try:
            state = reopened.inspect().inspection
            assert state.status == ('accepted' if phase==6 else 'pending_unknown')
            assert state.stored_reports == (3 if phase>=5 else 0)
            if phase != 6:
                assert state.projection is None and state.solver_calls is None
            with pytest.raises(ValueError, match='retried'):
                reopened._run_development(expected_head=state.registry_head)
        finally:
            reopened.close()


def test_full_anchor_exact_type_gate(tmp_path, monkeypatch):
    owner = make(tmp_path, create=True)
    anchor = owner._anchor
    try:
        owner._anchor = object()
        with pytest.raises(ValueError, match='exact full durable anchor'):
            owner._run_development(expected_head='0'*64)
    finally:
        owner._anchor = anchor
        owner.close()


def test_real_232_stage_inventory_stops_on_first_missing_raw(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_binding as source
    root = Path(__file__).resolve().parents[1]
    req = json.loads((root/'results/tables/rq2_normal_h1_shape_v1_non_authoritative/request.json').read_bytes())
    receipt = source.load_pinned_current(source.H1SourceDeclaration(**req['declaration']), req['upstream_root'],
        config_path=req['config_path'])
    p = source.assemble_pinned_current(receipt, req['upstream_root'], expected_identity=req['expected_source_identity'],
        config_path=req['config_path'], relative_hour=0, dc_bus=req['dc_bus'])
    order = api.base.native.model_api.stage_order(p.inputs)
    assert len(order) == 232
    work = api.resources.H1NormalWork('normal', 1, order, spec())
    content = api.resources.content_inventory(232, 1)['total_content_limit_bytes']
    envelope = api.resources.serial.TaskEnvelope('normal', 332, 100, 1000, content+100, 100, 1, 1000, 2000)
    resource = api.resources.H1TaskResources(envelope, 100)
    serial = api.resources.serial.SerialResourceBudget(342, 10, 100, 100, 1200, 100, content+300, 1)
    limits = api.base.replay.H1HourReplayLimits(232, 1000, 2000)
    values = (p, work, resource, serial, limits)
    owner = make(tmp_path, values=values, create=True)
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(1)
        assert owner._anchor.inspect().registry_head == owner._registry.head
        raise RuntimeError('test native unavailable; no solver created')
    monkeypatch.setattr(api.base.native.capture, 'solve_once', unavailable)
    try:
        assert len(owner._declaration['stage_order']) == 232
        with pytest.raises(RuntimeError):
            owner._run_development(expected_head=owner.inspect().inspection.registry_head)
        pin = owner._anchor.inspect().record_sha256
    finally:
        owner.close()
    reopened = make(tmp_path, values=values, expected_anchor_record=pin)
    try:
        state = reopened.inspect().inspection
        assert state.status == 'pending_unknown' and state.stored_reports == 0
        assert state.solver_calls is None and state.projection is None and len(calls)==1
        with pytest.raises(ValueError, match='retried'):
            reopened._run_development(expected_head=state.registry_head)
    finally:
        reopened.close()
