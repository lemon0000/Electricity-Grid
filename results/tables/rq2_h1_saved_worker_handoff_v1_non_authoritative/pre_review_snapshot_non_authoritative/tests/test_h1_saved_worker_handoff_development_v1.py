from dataclasses import replace
import json

import pytest

from experiments import h1_saved_worker_handoff_development_v1 as api
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import spec,no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour
from tests.test_h1_bounded_file_parent_development_v1 import owner as reopen
from tests.test_h1_parent_snapshot_development_v1 import files


def controller(root,env,hours=1):
    upstream,config,origin,state=env
    return api.LiveSavedController(root,api.bounded.source.static_network(state['data']),
        replace(spec(),time_limit_seconds=5.),api.replay.H1HourReplayLimits(3,100,500),
        origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,hours=hours)


def step(c,env,rows,hour=0):
    return c.step_saved(rows,expected_source_identity=source_pin(env,hour),expected_head=c.inspect().head)


def assert_stopped(c,env):
    before=files(c._parent._root)
    with pytest.raises(ValueError):
        c.step_saved((),expected_source_identity=source_pin(env),expected_head='f'*64)
    assert files(c._parent._root)==before
    for lease in (c._parent._root_lease,c._parent._journal._lease,c._parent._anchor._lease):lease.check()


def test_two_hours_handoff_before_child_and_owned_carry(tmp_path,environment,synthetic_reports,monkeypatch):
    c=controller(tmp_path/'parent_non_authoritative',environment,2)
    observations=[]
    original=api.snapshot.Snapshot.pending_input
    def observe(reader,**kwargs):
        result=original(reader,**kwargs)
        assert not (reader._root/f'hour_{result.packet.relative_hour:03d}_non_authoritative').exists()
        observations.append(result.packet.before.completed_hours)
        return result
    monkeypatch.setattr(api.snapshot.Snapshot,'pending_input',observe)
    try:
        pulls=[]
        def reports():
            for i,raw in enumerate(synthetic_reports):
                pulls.append(i)
                if i==0:
                    for action in (c.close,c.inspect,lambda:step(c,environment,())):
                        with pytest.raises(ValueError,match='already active'):action()
                    c._parent._root_lease.check()
                yield raw
        first=step(c,environment,reports())
        assert first.completed_hours==1 and pulls==[0,1,2]
        one=json.loads(c.last_input_receipt)
        next_reports,_=synthetic_next_hour(c._parent,environment,synthetic_reports)
        final=step(c,environment,iter(next_reports),1)
        two=json.loads(c.last_input_receipt)
        assert observations==[0,1] and final.status=='complete'
        assert one['before_identity']!=two['before_identity']
        assert one['intent_head']!=two['intent_head']
        assert not final.independent_hour_jobs_integrated and not final.formal_execution_ready
        assert not two['native_execution_authorized'] and two['external_live_handoff_required']
        pin=c._parent._anchor.inspect().record_sha256
        assert not final.formal_result
    finally:c.close()
    q=reopen(c._parent._root,environment,hours=2,expected_anchor_record=pin)
    try:
        assert q.inspect()==final
        with pytest.raises(ValueError,match='inspection only'):
            q.step_saved((),expected_source_identity=source_pin(environment),expected_head=final.head)
    finally:q.close()
    with pytest.raises((ValueError,FileExistsError)):
        controller(c._parent._root,environment,2)


@pytest.mark.parametrize('window',['snapshot','receipt','constructor'])
def test_pre_child_failure_consumes_no_report_and_cannot_retry(tmp_path,environment,monkeypatch,window):
    c=controller(tmp_path/'parent_non_authoritative',environment)
    transfers=[]
    original=api._SavedTransfer.consume
    def consume(t,reports):
        transfers.append(t)
        if window=='receipt':t.receipt_pin='f'*64
        return original(t,reports)
    monkeypatch.setattr(api._SavedTransfer,'consume',consume)
    def fail(*a,**k):raise ValueError('injected pre-child failure')
    if window=='snapshot':monkeypatch.setattr(api.snapshot,'open_snapshot',fail)
    if window=='constructor':monkeypatch.setattr(api.bounded.prior,'AttestedChild',fail)
    def forbidden():
        raise AssertionError('reports consumed before successful handoff')
        yield
    try:
        with pytest.raises(ValueError):step(c,environment,forbidden())
        assert c._parent._journal.inspect().events==1
        assert not (c._parent._root/'hour_000_non_authoritative').exists()
        assert c.last_input_receipt is None
        for transfer in transfers:
            assert transfer.used
            with pytest.raises(ValueError,match='already consumed'):original(transfer,forbidden())
        assert_stopped(c,environment)
    finally:c.close()


@pytest.mark.parametrize('window',['iterator','finish','source','anchor_before','anchor_after'])
def test_worker_and_publication_failure_preserve_pending_evidence(tmp_path,environment,synthetic_reports,monkeypatch,window):
    c=controller(tmp_path/'parent_non_authoritative',environment)
    p=c._parent
    if window=='finish':
        def finish(*a,**k):raise ValueError('injected finish failure')
        monkeypatch.setattr(api.bounded.prior.AttestedChild,'finish',finish)
    if window.startswith('anchor_'):
        original=p._anchor.advance
        def advance(*a,**k):
            if p._anchor.inspect().sequence==1:
                if window=='anchor_after':original(*a,**k)
                raise ValueError('injected anchor publication failure')
            return original(*a,**k)
        monkeypatch.setattr(p._anchor,'advance',advance)
    def reports():
        for i,raw in enumerate(synthetic_reports):
            yield raw
            if window=='iterator' and i==0:raise ValueError('injected iterator failure')
        if window=='source':environment[3]['workload']='1'
    try:
        with pytest.raises(ValueError):step(c,environment,reports())
        assert p._poisoned and c.last_input_receipt is None
        root=p._root/'hour_000_non_authoritative'
        assert root.exists()
        assert (root/'attested_hour_non_authoritative'/'raw'/'000'/'raw.bin').read_bytes()==synthetic_reports[0]
        expected_events=2 if window.startswith('anchor_') else 1
        assert p._journal.inspect().events==expected_events
        assert p._anchor.inspect().sequence==(2 if window=='anchor_after' else 1)
        if window=='source':environment[3]['workload']='0'
        assert_stopped(c,environment)
    finally:c.close()
