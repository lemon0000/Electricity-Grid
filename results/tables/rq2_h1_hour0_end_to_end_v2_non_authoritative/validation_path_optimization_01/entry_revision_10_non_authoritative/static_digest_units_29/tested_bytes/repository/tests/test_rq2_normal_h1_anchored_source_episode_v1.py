import pytest
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_source_episode_v1 import environment,pin
from tests.test_rq2_normal_h1_hour_archive_v1 import saved,no_solver,spec,budget,LIMITS
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_anchored_source_episode as api


def make(tmp_path,environment,*,create=True,hours=1):
    upstream,config,origin,state=environment
    return api.DevelopmentH1AnchoredSourceEpisode(tmp_path/'parent_non_authoritative',
        api.source.static_network(state['data']),spec(),budget(),api.old.H1EpisodeBudget(hours,3*hours,float(3*hours)),
        LIMITS,dc_bus=1,origin=origin,upstream_root=upstream,config_path=config,create=create)


def test_source_parent_owned_child_and_reopen(tmp_path,environment,saved,monkeypatch):
    owner=make(tmp_path,environment)
    rows=iter(saved[1])
    def solve(*a,**k):
        state=owner._restore()[0]
        assert state.status=='pending_unknown' and state.completed_hours==0
        return next(rows)
    monkeypatch.setattr(api.child.base.native.capture,'solve_once',solve)
    try:
        result=owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert result.status=='complete' and result.completed_hours==1 and result.reserved_solver_calls==3
        assert not result.formal_result and not result.source_authenticated
    finally:owner.close()
    reopened=make(tmp_path,environment,create=False)
    try:
        assert reopened.inspect()==result
        with pytest.raises(ValueError,match='reopened'):reopened.step(expected_source_identity=pin(environment),expected_head=result.head)
    finally:reopened.close()


def test_second_hour_uses_owned_before_and_pending_cannot_retry(tmp_path,environment,saved,monkeypatch):
    owner=make(tmp_path,environment,hours=2)
    rows=iter(saved[1])
    monkeypatch.setattr(api.child.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    try:
        one=owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert one.completed_hours==1 and one.status=='ready'
        assert owner._restore()[1].completed_hours==1
        def unknown(*a,**k):raise RuntimeError('second hour unknown')
        monkeypatch.setattr(api.child.base.native.capture,'solve_once',unknown)
        with pytest.raises(RuntimeError):owner.step(expected_source_identity=pin(environment,1),expected_head=one.head)
    finally:owner.close()
    reopened=make(tmp_path,environment,create=False,hours=2)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.completed_hours==1 and state.reserved_solver_calls==6
        with pytest.raises(ValueError,match='reopened'):reopened.step(expected_source_identity=pin(environment,1),expected_head=state.head)
    finally:reopened.close()


def test_source_drift_after_intent_prevents_child_creation(tmp_path,environment,monkeypatch):
    owner=make(tmp_path,environment)
    append=owner._append
    def drift(*a,**k):
        append(*a,**k)
        environment[3]['workload']='0.1'
    monkeypatch.setattr(owner,'_append',drift)
    try:
        with pytest.raises(ValueError):owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert not owner._paths(0)[0].exists()
    finally:owner.close()


def test_parent_namespace_rejects_duplicate_creation(tmp_path,environment):
    owner=make(tmp_path,environment)
    owner.close()
    with pytest.raises((ValueError,FileExistsError,OSError)):make(tmp_path,environment)


def test_bad_source_has_no_intent(tmp_path,environment):
    owner=make(tmp_path,environment)
    try:
        with pytest.raises(ValueError):owner.step(expected_source_identity='0'*64,expected_head=owner.inspect().head)
        assert owner._journal.inspect().events==0 and not owner._paths(0)[0].exists()
    finally:owner.close()


def test_parent_anchor_failure_prevents_child_creation(tmp_path,environment,monkeypatch):
    owner=make(tmp_path,environment)
    def fail(*a,**k):raise RuntimeError('parent anchor failed')
    monkeypatch.setattr(owner._anchor,'advance',fail)
    try:
        with pytest.raises(RuntimeError):owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert not owner._paths(0)[0].exists()
    finally:owner.close()
    with pytest.raises(ValueError):make(tmp_path,environment,create=False)


def test_child_complete_without_parent_outcome_does_not_advance(tmp_path,environment,saved,monkeypatch):
    owner=make(tmp_path,environment)
    rows=iter(saved[1])
    monkeypatch.setattr(api.child.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    append=owner._append
    def fail(metadata,*a):
        if metadata['kind']=='accepted':raise RuntimeError('parent outcome unavailable')
        return append(metadata,*a)
    monkeypatch.setattr(owner,'_append',fail)
    try:
        with pytest.raises(RuntimeError):owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
    finally:owner.close()
    reopened=make(tmp_path,environment,create=False)
    try:
        state=reopened.inspect()
        assert state.status=='pending_unknown' and state.completed_hours==0 and state.last_projection_identity is None
        assert state.reserved_solver_calls==3
    finally:reopened.close()


@pytest.mark.parametrize('fault',['anchor_corrupt','reopened_result_drift'])
def test_fresh_child_reopen_failure_precedes_parent_outcome(tmp_path,environment,saved,monkeypatch,fault):
    from dataclasses import replace
    owner=make(tmp_path,environment)
    rows=iter(saved[1])
    monkeypatch.setattr(api.child.base.native.capture,'solve_once',lambda *a,**k:next(rows))
    collector=owner._collector
    def altered(*a,**k):
        value=collector(*a,**k)
        if k.get('create') and fault=='anchor_corrupt':
            close=value.close
            def corrupt():
                close()
                (value._anchor._lease.root/'006.json').write_bytes(b'{}')
            monkeypatch.setattr(value,'close',corrupt)
        elif not k.get('create') and fault=='reopened_result_drift':
            inspect=value.inspect
            monkeypatch.setattr(value,'inspect',lambda:replace(inspect(),stored_reports=99))
        return value
    monkeypatch.setattr(owner,'_collector',altered)
    try:
        with pytest.raises(ValueError):owner.step(expected_source_identity=pin(environment),expected_head=owner.inspect().head)
        assert owner._journal.inspect().events==1
    finally:owner.close()
