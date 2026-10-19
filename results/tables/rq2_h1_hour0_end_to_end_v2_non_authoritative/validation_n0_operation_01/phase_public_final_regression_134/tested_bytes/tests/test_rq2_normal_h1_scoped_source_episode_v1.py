import pytest
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_source_episode_v1 import environment,pin
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,spec,budget,LIMITS
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_scoped_source_episode as api


def make(tmp_path,environment,*,create=True,cls=api.DevelopmentH1ScopedSourceEpisode):
    upstream,config,origin,state=environment
    return cls(tmp_path/'parent_non_authoritative',
        api.old.source.static_network(state['data']),spec(),budget(),api.old.old.H1EpisodeBudget(1,3,3.),
        LIMITS,dc_bus=1,origin=origin,upstream_root=upstream,config_path=config,create=create)


def test_parent_successor_preserves_result_and_single_child_replay_per_restore(tmp_path,environment,saved,monkeypatch):
    owner=make(tmp_path,environment)
    rows=iter(saved[1])
    monkeypatch.setattr(api.reader.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    try:
        result=owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert result.status=='complete' and result.completed_hours==1
    finally:owner.close()
    calls=[]
    audit=api.reader.base.replay._audit_stage
    def counted(*a,**k):calls.append(a[3]);return audit(*a,**k)
    monkeypatch.setattr(api.reader.base.replay,'_audit_stage',counted)
    reopened=make(tmp_path,environment,create=False)
    try:
        assert calls==[0,1,2]
        assert reopened.inspect()==result
        assert calls==[0,1,2,0,1,2]
        with pytest.raises(ValueError,match='reopened'):
            reopened.step(expected_source_identity=pin(environment),expected_head=result.head)
    finally:reopened.close()


@pytest.mark.parametrize('fault',['type','identity','inner_type','inner_authority'])
def test_bad_audit_receipt_prevents_parent_outcome(tmp_path,environment,saved,monkeypatch,fault):
    owner=make(tmp_path,environment)
    rows=iter(saved[1])
    monkeypatch.setattr(api.reader.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    inspect=api.reader.DevelopmentH1ScopedChildInspection.inspect
    def altered(child):
        receipt=inspect(child)
        if fault=='type':return receipt.inspection
        if fault=='identity':object.__setattr__(receipt,'auditor_identity','0'*64)
        elif fault=='inner_type':object.__setattr__(receipt,'inspection',object())
        else:object.__setattr__(receipt.inspection,'formal_result',True)
        return receipt
    monkeypatch.setattr(api.reader.DevelopmentH1ScopedChildInspection,'inspect',altered)
    try:
        with pytest.raises(ValueError,match='auditor identity|non-authoritative collector'):
            owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert owner._journal.inspect().events==1
    finally:owner.close()
    reopened=make(tmp_path,environment,create=False)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.completed_hours==0
        assert state.reserved_solver_calls==3
    finally:reopened.close()


def test_parent_binding_isolation(tmp_path,environment):
    for index,(writer,reader) in enumerate([
        (api.DevelopmentH1ScopedSourceEpisode,api.old.DevelopmentH1AnchoredSourceEpisode),
        (api.old.DevelopmentH1AnchoredSourceEpisode,api.DevelopmentH1ScopedSourceEpisode)]):
        root=tmp_path/str(index)
        root.mkdir()
        owner=make(root,environment,cls=writer)
        owner.close()
        with pytest.raises(ValueError):make(root,environment,create=False,cls=reader)
