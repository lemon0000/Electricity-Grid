from dataclasses import replace
import json

import pytest

from experiments import h1_attested_source_parent_development_v1 as api
from tests.test_h1_saved_source_parent_development_v1 import environment, source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec, packet
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports, saved


def owner(root, env, **kwargs):
    upstream,config,origin,state = env
    return api.SavedSourceParent(root,api.prior.source.static_network(state['data']),
        replace(spec(),time_limit_seconds=5.),api.replay.H1HourReplayLimits(3,100,500),
        origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,**kwargs)


def step(p, env, rows, hour=0):
    return p.step_saved(iter(rows),expected_source_identity=source_pin(env,hour),
                        expected_head=p.inspect().head)


def make_child(tmp_path):
    return api.AttestedChild(tmp_path/'hour_000_non_authoritative',packet(),replace(spec(),time_limit_seconds=5.),
        api.replay.H1HourReplayLimits(3,100,500),parent_intent_head='a'*64,
        source_lineage_identity='b'*64,create=True)


def fill_child(tmp_path, reports):
    c = make_child(tmp_path)
    for raw in reports:c.record_report(raw,expected_head=c.head)
    return c


def reopen(c, **kw):
    args=dict(parent_intent_head=c.parent_intent_head,source_lineage_identity=c.source_lineage_identity,
              expected_head=c.head)
    args.update(kw)
    return api.AttestedChild(c.root,c.packet,c.specification,c.limits,**args)


def synthetic_next_hour(p, environment, source_reports):
    """Synthetic fixture only: derive transition bits from actual carry, then
    rebuild model metadata. Real guard/audit must still accept this candidate.
    This is not a native capture or RTS producer-coverage witness.
    """
    state,before,previous=p._restore()
    receipt=p._load(state.completed_hours,source_pin(environment,state.completed_hours))
    current=p._packet(receipt,state.completed_hours,before,previous)
    reports,locks=[],()
    model_api=api.replay.native.model_api
    for original in source_reports:
        request=model_api.H1StageRequest(current.inputs,locks)
        model=model_api.build_h1_stage_model(request,expected_identity=model_api.h1_stage_identity(request))
        report=json.loads(original)
        scale=api.replay.native.capture.audit.model_scale(model)
        report['model_structure_identity']=api.replay.native.capture.audit._structure(model)
        report['variables'],report['constraints']=scale.variables,scale.constraints
        from pyomo.environ import Var
        values=dict(report['assignment'])
        for uid,on,_,_ in current.before.units:
            commitment=int(float.fromhex(values[f'commitment[0,{uid}]']))
            values[f'startup[0,{uid}]']=float(max(commitment-int(on),0)).hex()
            values[f'shutdown[0,{uid}]']=float(max(int(on)-commitment,0)).hex()
        report['assignment']=sorted(values.items())
        provenance=report['provenance']
        referenced=tuple((name,values[name]) for name,_ in provenance['referenced_assignment'])
        provenance['referenced_assignment']=referenced
        provenance['assignment_sha256']=api.io.digest(repr(referenced).encode())
        for channel in ('ordered_objective_terms','ordered_native_objective_terms'):
            provenance[channel]=[(name,coefficient,values[name]) for name,coefficient,_ in provenance[channel]]
        fixed_valid=True
        for variable in model.component_data_objects(Var):
            value=float.fromhex(values[variable.name])
            if variable.fixed and abs(value-variable.value)>1e-9:fixed_valid=False
            variable.set_value(value,skip_validation=True)
        residual=api.replay.native.capture.audit._constraint_violation(model)
        integer=api.replay.native.capture.audit._integrality_violation(model)
        assert fixed_valid and residual<=1e-9 and integer<=1e-9
        report['maximum_residual'],report['maximum_integrality_violation']=residual,integer
        report['assignment_valid']=True
        reports.append(api.io.encode(report))
        locks=(*locks,float.fromhex(report['provenance']['canonical_objective_hex']))
    return reports,current


def test_parent_origin_and_carry_attested_outcome_fresh_reopen(tmp_path, environment, synthetic_reports):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=2,create=True)
    try:
        first=step(p,environment,synthetic_reports)
        assert first.status=='ready' and first.completed_hours==1
        assert source_pin(environment,0)!=source_pin(environment,1)
        with pytest.raises(ValueError):p._load(1,source_pin(environment,0))
        future,current=synthetic_next_hour(p,environment,synthetic_reports)
        assert current.relative_hour==current.before.completed_hours==1
        probe=api.AttestedChild(tmp_path/'origin_reuse_probe_non_authoritative',current,p._spec,p._limits,
            parent_intent_head='a'*64,source_lineage_identity=source_pin(environment,1),create=True)
        try:
            with pytest.raises(ValueError):probe.record_report(synthetic_reports[0],expected_head=probe.head)
            assert probe.poisoned and probe.owner.locks==()
            assert (probe.owner.stages.raw.root/'000/raw.bin').read_bytes()==synthetic_reports[0]
        finally:probe.close()
        result=step(p,environment,future,hour=1)
        assert result.status=='complete' and result.completed_hours==result.attempted_hours==2
        assert p._journal.inspect().events==4 and p._anchor.inspect().sequence==4
        assert len(list((root/'parent_anchor_non_authoritative').glob('[0-9][0-9][0-9].json')))==5
        assert not result.independent_hour_jobs_integrated and not result.formal_execution_ready
        event=json.loads(p._journal.event_metadata(2,expected_head=p._journal.head))
        assert event['child_protocol']==api.hour_api.SCHEMA
        assert len(event['hour_terminal_sha256'])==64
        anchor=p._anchor.inspect().record_sha256
    finally:p.close()
    q=owner(root,environment,hours=2,expected_anchor_record=anchor)
    try:
        assert q.inspect()==result
        with pytest.raises(ValueError,match='inspection only'):
            step(q,environment,synthetic_reports)
    finally:q.close()
    # A copied hour-0 wrapper terminal cannot stand in for the hour-1 child.
    (root/'hour_001_non_authoritative/terminal.json').write_bytes(
        (root/'hour_000_non_authoritative/terminal.json').read_bytes())
    with pytest.raises(ValueError):owner(root,environment,hours=2,expected_anchor_record=anchor)


def test_bad_source_never_consumes_saved_reports(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    def denied():
        pytest.fail('bad source consumed a raw')
        yield b''
    try:
        with pytest.raises(ValueError):
            p.step_saved(denied(),expected_source_identity='0'*64,expected_head=p.inspect().head)
        assert p._journal.inspect().events==0
    finally:p.close()


def test_child_fresh_reopen_and_wrong_parent_pins(tmp_path,synthetic_reports):
    c=fill_child(tmp_path,synthetic_reports)
    accepted=c.finish(expected_head=c.head)
    assert accepted.status=='accepted'
    assert accepted.projection.canonical_locks==(20.,1.,20.)
    assert not accepted.native_execution_authenticated and not accepted.collector_integrated
    assert reopen(c).inspect()==accepted
    for kwargs in (dict(expected_head='c'*64),dict(parent_intent_head='c'*64),dict(source_lineage_identity='c'*64)):
        with pytest.raises(ValueError):reopen(c,**kwargs)
    with pytest.raises(ValueError,match='writable'):c.record_report(synthetic_reports[0],expected_head=c.head)


@pytest.mark.parametrize('fault',['before','after','reader'])
def test_wrapper_terminal_failure_no_accepted_child(tmp_path,synthetic_reports,monkeypatch,fault):
    c=fill_child(tmp_path,synthetic_reports)
    original=api.io.write_metadata
    def write(path,doc):
        if path==c.root/'terminal.json':
            if fault=='before':raise OSError('before terminal')
            pin=original(path,doc)
            if fault=='after':raise OSError('lost terminal confirmation')
            return pin
        return original(path,doc)
    monkeypatch.setattr(api.io,'write_metadata',write)
    if fault=='reader':
        monkeypatch.setattr(c,'_read_terminal',lambda: (_ for _ in ()).throw(ValueError('reader failure')))
    with pytest.raises((ValueError,OSError)):c.finish(expected_head=c.head)
    assert c.poisoned
    with pytest.raises(ValueError,match='poisoned'):c.inspect()


def test_parent_child_failure_keeps_anchored_pending_intent(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        with pytest.raises(ValueError):step(p,environment,synthetic_reports[:1])
        assert p._journal.inspect().events==1
        anchor=p._anchor.inspect().record_sha256
    finally:p.close()
    q=owner(tmp_path/'parent_non_authoritative',environment,hours=2,expected_anchor_record=anchor)
    try:
        result=q.inspect()
        assert result.status=='pending_unknown' and result.completed_hours==0 and result.attempted_hours==1
        with pytest.raises(ValueError,match='inspection only'):step(q,environment,synthetic_reports)
    finally:q.close()


def test_parent_outcome_failure_never_adopts_child_without_anchor(tmp_path,environment,synthetic_reports,monkeypatch):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    original=p._append
    def fail(metadata,payload=b''):
        if metadata['kind']=='accepted':raise OSError('before outcome')
        return original(metadata,payload)
    monkeypatch.setattr(p,'_append',fail)
    try:
        with pytest.raises(OSError):step(p,environment,synthetic_reports)
        assert p._journal.inspect().events==1
        assert (p._root/'hour_000_non_authoritative/terminal.json').exists()
        anchor=p._anchor.inspect().record_sha256
    finally:p.close()
    q=owner(tmp_path/'parent_non_authoritative',environment,hours=1,expected_anchor_record=anchor)
    try:assert q.inspect().status=='pending_unknown'
    finally:q.close()


def test_core_tamper_not_accepted_through_wrapper(tmp_path,synthetic_reports):
    c=fill_child(tmp_path,synthetic_reports)
    c.finish(expected_head=c.head)
    (c.owner.attest/'000.mapping.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='unresolved'):reopen(c)


@pytest.mark.parametrize('path',['binding.json','terminal.json',
    'attested_hour_non_authoritative/attestation_terminal.json'])
def test_wrapper_endpoints_tampered(tmp_path,synthetic_reports,path):
    c=fill_child(tmp_path,synthetic_reports)
    c.finish(expected_head=c.head)
    (c.root/path).write_bytes(b'{}')
    with pytest.raises((ValueError,KeyError)):reopen(c)


def test_outcome_checks_all_typed_child_context(tmp_path,synthetic_reports):
    c=fill_child(tmp_path,synthetic_reports)
    result=c.finish(expected_head=c.head)
    p=object.__new__(api.SavedSourceParent)
    p._root=tmp_path;p._stages=3
    assert p._outcome(0,'a'*64,result)['child_head']==result.head
    for changes in (dict(stored_reports=2),dict(request_key='c'*64),dict(packet_audit_identity='c'*64),
                    dict(source_lineage_identity='c'*64),dict(hour_binding_sha256='c'*64),dict(formal_result=True)):
        with pytest.raises(ValueError):p._outcome(0,'a'*64,replace(result,**changes))


def test_wrapper_storage_increment():
    old,new=api.hour_api.storage_bound(232),api.child_storage_bound(232)
    assert new['logical_bytes']==old['logical_bytes']+4096
    assert new['files']==old['files']+2 and new['directories']==old['directories']+1
    assert not new['resource_admission']


def test_outcome_journal_without_anchor_is_unresolved(tmp_path,environment,synthetic_reports,monkeypatch):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=1,create=True)
    original=p._anchor.advance
    def advance(*args,**kwargs):
        if p._journal.inspect().events==2:raise OSError('outcome anchor failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(p._anchor,'advance',advance)
    try:
        with pytest.raises(OSError):step(p,environment,synthetic_reports)
        assert p._journal.inspect().events==2
        anchor=p._anchor.inspect().record_sha256
    finally:p.close()
    with pytest.raises(ValueError,match='independent chunk head'):
        owner(root,environment,hours=1,expected_anchor_record=anchor)


def test_core_change_during_owned_projection_replay_rejected(tmp_path,synthetic_reports,monkeypatch):
    c=fill_child(tmp_path,synthetic_reports)
    c.finish(expected_head=c.head)
    original=api.replay.replay_stream
    calls=0
    def replay(*args,**kwargs):
        nonlocal calls
        result=original(*args,**kwargs)
        calls+=1
        if calls==2:(c.owner.attest/'000.mapping.json').write_bytes(b'{}')
        return result
    monkeypatch.setattr(api.replay,'replay_stream',replay)
    with pytest.raises(ValueError):reopen(c)
    assert calls==2
