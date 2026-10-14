import pytest

from experiments import h1_historical_parent_prefix_development_v1 as m
from tests.test_h1_parent_snapshot_development_v1 import pending,files
from tests.test_h1_bounded_file_parent_development_v1 import owner,step
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved


def open_prefix(p,pin,**changes):
    kwargs=dict(completed_hours=1,expected_parent_identity=p.identity,expected_anchor_record=pin)
    kwargs.update(changes)
    return m.HistoricalSnapshot(p._declaration,**kwargs)


def test_old_prefix_survives_pending_suffix_and_does_not_read_it(tmp_path,environment,synthetic_reports,monkeypatch):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        pending(p,environment,1)
        before=files(p._root);original=m.io.read_stable
        def read(path,*args,**kwargs):
            path=m.Path(path)
            assert not (path.parent.name=='003' and path.parent.parent.name=='parent_events_non_authoritative')
            assert not (path.name=='003.json' and path.parent.name=='parent_anchor_non_authoritative')
            return original(path,*args,**kwargs)
        monkeypatch.setattr(m.io,'read_stable',read)
        q=open_prefix(p,pin)
        try:
            assert q.inspect()==one
            with pytest.raises(ValueError,match='read only'):q._append()
            with pytest.raises(ValueError,match='inspection only'):step(q,environment,())
        finally:q.close()
        assert files(p._root)==before
        p._root_lease.check()
    finally:p.close()


@pytest.mark.parametrize('bad',['pin','parent','progress','event','anchor','child'])
def test_prefix_pins_and_each_evidence_class_are_required(tmp_path,environment,synthetic_reports,bad):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        args={}
        if bad=='pin':pin='0'*64
        elif bad=='parent':args['expected_parent_identity']='0'*64
        elif bad=='progress':args['completed_hours']=2
        else:
            path={'event':p._root/'parent_events_non_authoritative'/'001'/'payload.bin',
                  'anchor':p._root/'parent_anchor_non_authoritative'/'001.json',
                  'child':p._root/'hour_000_non_authoritative'/'terminal.json'}[bad]
            path.write_bytes(path.read_bytes()+b' ')
        with pytest.raises(ValueError):open_prefix(p,pin,**args)
    finally:p.close()


def test_suffix_failure_cannot_rewrite_accepted_prefix(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        pending(p,environment,1)
        (p._root/'hour_001_non_authoritative').mkdir()
        (p._root/'parent_events_non_authoritative'/'004').mkdir()
        # Interrupted suffix remains untouched and unauthenticated.
        q=open_prefix(p,pin)
        try:assert q.inspect()==one
        finally:q.close()
    finally:p.close()


def test_suffix_append_while_reader_open_preserves_fixed_prefix(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        q=open_prefix(p,pin)
        try:
            pending(p,environment,1)
            assert q.inspect()==one
        finally:q.close()
    finally:p.close()
