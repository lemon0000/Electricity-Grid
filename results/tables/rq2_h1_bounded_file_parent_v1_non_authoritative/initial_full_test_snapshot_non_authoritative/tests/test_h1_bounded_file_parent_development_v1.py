import ast
import inspect
import textwrap
from dataclasses import replace

import pytest

from experiments import h1_bounded_file_parent_development_v1 as api
from tests.test_h1_saved_source_parent_development_v1 import environment, source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import spec,no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour


def owner(root,env,**kwargs):
    upstream,config,origin,state=env
    return api.SavedSourceParent(root,api.source.static_network(state['data']),
        replace(spec(),time_limit_seconds=5.),api.replay.H1HourReplayLimits(3,100,500),
        origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,**kwargs)


def step(p,env,raw,hour=0):
    return p.step_saved(iter(raw),expected_source_identity=source_pin(env,hour),expected_head=p.inspect().head)


def test_chronology_matches_prior_except_storage_lookup():
    old=textwrap.dedent(inspect.getsource(api.prior.prior.SavedSourceParent._restore))
    new=textwrap.dedent(inspect.getsource(api.SavedSourceParent._restore))
    block="""            connection = self._journal._connect()
            try:
                head = connection.execute('SELECT head FROM events WHERE seq=?',(seq,)).fetchone()[0]
            finally:
                connection.close()"""
    assert block in old
    old=old.replace(block,"            head = self._journal.event_head(seq,expected_head=physical.head)")
    assert ast.dump(ast.parse(old))==ast.dump(ast.parse(new))


def test_two_hours_real_carry_reopen_and_full_content_bound(tmp_path,environment,synthetic_reports):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=2,create=True)
    try:
        assert step(p,environment,synthetic_reports).completed_hours==1
        raw,_=synthetic_next_hour(p,environment,synthetic_reports)
        result=step(p,environment,raw,1)
        assert result.completed_hours==2 and result.status=='complete'
        assert p._journal.inspect().events==4
        pin=p._anchor.inspect().record_sha256
        files=[f for f in root.rglob('*') if f.is_file()]
        bound=api.storage_bound(2,3)
        assert not list(root.rglob('*.sqlite3'))
        assert len(files)<=bound['files']
        assert sum(f.stat().st_size for f in files)<=bound['logical_bytes']
        assert 1+sum(f.is_dir() for f in root.rglob('*'))<=bound['directories']
    finally:p.close()
    q=owner(root,environment,hours=2,expected_anchor_record=pin)
    try:
        assert q.inspect()==result
        with pytest.raises(ValueError,match='inspection only'):step(q,environment,synthetic_reports)
    finally:q.close()


@pytest.mark.parametrize('window',['before_anchor','after_anchor'])
def test_intent_anchor_failure_stops_without_child(tmp_path,environment,monkeypatch,window):
    root=tmp_path/'parent_non_authoritative'
    p=owner(root,environment,hours=1,create=True)
    old=p._anchor.inspect().record_sha256
    original=p._anchor.advance
    def advance(*args,**kwargs):
        if window=='after_anchor':original(*args,**kwargs)
        raise OSError('anchor window')
    monkeypatch.setattr(p._anchor,'advance',advance)
    try:
        with pytest.raises(OSError):step(p,environment,())
        assert not (root/'hour_000_non_authoritative').exists()
        pin=p._anchor.inspect().record_sha256
    finally:p.close()
    if window=='before_anchor':
        assert pin==old
        with pytest.raises(ValueError,match='head differs'):
            owner(root,environment,hours=1,expected_anchor_record=pin)
    else:
        assert pin!=old
        q=owner(root,environment,hours=1,expected_anchor_record=pin)
        try:assert q.inspect().status=='pending_unknown'
        finally:q.close()
