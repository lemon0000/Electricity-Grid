"""Phase schemas and numerical Job replay; no real solver, not a live owner gate."""
from dataclasses import replace
import json
import pytest
from experiments import h1_phase_obligation_controller_development_v1 as c
from experiments import h1_phase_historical_controller_development_v1 as m
from experiments import h1_historical_controller_development_v1 as legacy
from tests.test_rq2_v2_normal_obligation_controller_development_v1 import real
from tests.test_h1_timed_job_controller_development_v1 import install_launcher
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour


def synthetic_controller(root,env,real,monkeypatch):
    """Test-only source/catalog seam; never evidence of real RTS acceptance."""
    resolver,ordinal,*_=real
    node=resolver.resolve('training_ub',ordinal)
    enrollment=dict(test_only_synthetic_source=True)
    monkeypatch.setattr(c.binding,'open_manifest',lambda:resolver)
    monkeypatch.setattr(c.binding,'precheck',lambda *a,**kw:node)
    monkeypatch.setattr(c.binding,'prevalidate_enrollment',lambda *a,**kw:enrollment)
    def bind(resolver,declaration,**kw):
        owner=c.binding.snapshot.open_snapshot(declaration,expected_parent_identity=kw['expected_parent_identity'],
            expected_anchor_record=kw['expected_anchor_record'])
        try:item=owner.pending_input(**kw['pending_arguments'])
        finally:owner.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        from dataclasses import asdict
        req=dict(parent_declaration=declaration,pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,budget=asdict(kw['job_budget']))
        return c._historical_binding(item.packet,req,node,enrollment)
    monkeypatch.setattr(c.binding,'bind',bind)
    upstream,config,origin,state=env
    return c.Controller(root,c.base.parent.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        c.base.old.replay.H1HourReplayLimits(3,100,500),resolver=resolver,family='training_ub',ordinal=ordinal,
        origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,hours=192,
        budget=c.base.old.process.TaskProcessBudget(300.,.05,512*1024**2,768*1024**2,2.))


@pytest.mark.parametrize('hours',[168,191,193,True,0])
def test_phase_requires_new192_root(hours):
    with pytest.raises(ValueError,match='192-hour'):
        c.Controller(hours=hours,resolver=None,family='training_ub',ordinal=0)


def test_public_entry_cannot_bypass_owner_gate():
    # Rejection precedes even construction/state access or source arguments.
    with pytest.raises(ValueError,match='attached owner'):
        c.Controller.step(object(),expected_source_identity='0'*64,expected_head='1'*64)


@pytest.mark.parametrize('completed',[167,168,191,192])
def test_phase_inventory_covers_boundary_without_claiming_execution(tmp_path,completed):
    root=tmp_path/'inventory';root.mkdir()
    for name in ('execution.lock','binding.json'):(root/name).write_bytes(b'0')
    for h in range(completed):
        for kind in ('binding','job','terminal'):(root/f'{h:03d}.{kind}.json').write_bytes(b'0')
    m._obligation_inventory(root,completed,{})
    (root/'192.binding.json').write_bytes(b'0')
    with pytest.raises(ValueError):m._obligation_inventory(root,completed,{})


def test_two_numerical_jobs_phase_history_and_legacy_rejection(tmp_path,real,environment,synthetic_reports,monkeypatch):
    monkeypatch.setattr(m,'_source_paths',lambda d:({m.Path(d['config_path']),m.Path(d['upstream_root'])/'SHA256SUMS'},
        {m.Path(d['upstream_root'])}))
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    controller=synthetic_controller(tmp_path/'phase_controller_non_authoritative',environment,real,monkeypatch)
    try:
        with pytest.raises(ValueError,match='attached owner'):controller.step()
        assert controller._parent._journal.inspect().events==0
        first=controller._step_development(expected_source_identity=source_pin(environment,0),expected_head=controller.inspect().head)
        observation=controller.last_obligation_observation
        args=dict(expected_binding_sha256=observation.header_sha256,
            expected_terminal_sha256=observation.terminal_sha256,completed_hours=1)
        current=m.prepare(controller._lease.root,**args)
        assert current.decision.relative_hour==0 and first.completed_hours==1
        with monkeypatch.context() as patch:
            patch.setattr(legacy,'_source_paths',m._source_paths)
            patch.setattr(legacy.binding,'open_manifest',c.binding.open_manifest)
            patch.setattr(legacy.binding,'precheck',c.binding.precheck)
            patch.setattr(legacy.binding,'prevalidate_enrollment',c.binding.prevalidate_enrollment)
            with pytest.raises(ValueError,match='header differs'):legacy.inspect(controller._lease.root,**args)
        reports,_=synthetic_next_hour(controller._parent,environment,synthetic_reports)
        install_launcher(monkeypatch,tmp_path,reports,label='second')
        second=controller._step_development(expected_source_identity=source_pin(environment,1),expected_head=controller.inspect().head)
        last=controller.last_obligation_observation
        result=m.inspect(controller._lease.root,expected_binding_sha256=last.header_sha256,
            expected_terminal_sha256=last.terminal_sha256,completed_hours=2)
        assert second.completed_hours==2 and second.status=='ready'
        assert result['historical_job_clock_prefix_verified'] and not result['live_release_authenticated']
        assert m.prepare(controller._lease.root,**args).audit_payload==current.audit_payload
        header=json.loads((controller.obligation_root/'binding.json').read_bytes())
        assert header['hours']==header['parent_declaration']['hours']==192
        assert not header['paired_owner_guard_authenticated']
    finally:controller.close()
