import pytest

from experiments import h1_historical_parent_prefix_development_v1 as m
from tests.test_h1_parent_snapshot_development_v1 import pending,files
from tests.test_h1_bounded_file_parent_development_v1 import owner,step,synthetic_next_hour
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved


def open_prefix(p,pin,**changes):
    head=m.bounded.json.loads((p._root/'parent_anchor_non_authoritative'/'002.json').read_bytes())['registry_head']
    kwargs=dict(completed_hours=1,expected_parent_identity=p.identity,expected_parent_head=head,expected_anchor_record=pin)
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
            result=q.inspect()
            assert result.head==one.head and result.completed_hours==one.completed_hours
            assert result.historical_parent_prefix_verified and not result.suffix_chain_verified
            assert not result.current_latest_parent_verified and not result.live_handoff_authenticated
            with pytest.raises(ValueError,match='read only'):q._append()
            with pytest.raises(ValueError,match='inspection only'):step(q,environment,())
        finally:q.close()
        assert files(p._root)==before
        p._root_lease.check()
    finally:p.close()


@pytest.mark.parametrize('bad',['pin','head','parent','progress','event','anchor','child'])
def test_prefix_pins_and_each_evidence_class_are_required(tmp_path,environment,synthetic_reports,bad):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        args={}
        if bad=='pin':pin='0'*64
        elif bad=='head':args['expected_parent_head']='0'*64
        elif bad=='parent':args['expected_parent_identity']='0'*64
        elif bad=='progress':args['completed_hours']=2
        else:
            path={'event':p._root/'parent_events_non_authoritative'/'001'/'payload.bin',
                  'anchor':p._root/'parent_anchor_non_authoritative'/'001.json',
                  'child':p._root/'hour_000_non_authoritative'/'terminal.json'}[bad]
            path.write_bytes(path.read_bytes()+b' ')
        with pytest.raises(ValueError):open_prefix(p,pin,**args)
    finally:p.close()


@pytest.mark.parametrize('name',['002','003','0000','001.json','\u0660\u0660\u0661'])
def test_namespace_rejects_gap_bounds_aliases_and_non_ascii(tmp_path,name):
    (tmp_path/'000').mkdir();(tmp_path/name).mkdir()
    with pytest.raises(ValueError):
        m._inventory(tmp_path,set(),pattern=r'([0-9]{3})',low=0,high=2,directories=True,retained={})


def test_namespace_allows_append_but_not_observed_replacement(tmp_path):
    root=tmp_path/'view';root.mkdir();(root/'000').mkdir();seen={}
    def inspect():return m._inventory(root,set(),pattern=r'([0-9]{3})',low=0,high=2,directories=True,retained=seen)
    assert inspect()=={0}
    (root/'001').mkdir();assert inspect()=={0,1}
    (root/'001').rename(tmp_path/'retained_old_suffix')
    (root/'001').mkdir()
    with pytest.raises(ValueError,match='removed or replaced'):inspect()


def test_suffix_failure_cannot_rewrite_accepted_prefix(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        pending(p,environment,1)
        (p._root/'hour_001_non_authoritative').mkdir()
        (p._root/'parent_events_non_authoritative'/'004').mkdir()
        # Interrupted suffix remains untouched and unauthenticated.
        q=open_prefix(p,pin)
        try:assert q.inspect().head==one.head and q.inspect().completed_hours==1
        finally:q.close()
    finally:p.close()


def test_suffix_append_while_reader_open_preserves_fixed_prefix(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        q=open_prefix(p,pin)
        try:
            pending(p,environment,1)
            assert q.inspect().head==one.head and q.inspect().completed_hours==1
        finally:q.close()
    finally:p.close()


def test_fully_accepted_second_hour_preserves_first_prefix(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        one=step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        reports,_=synthetic_next_hour(p,environment,synthetic_reports)
        assert step(p,environment,reports,hour=1).completed_hours==2
        q=open_prefix(p,pin)
        try:
            result=q.inspect()
            assert result.head==one.head and result.completed_hours==1
        finally:q.close()
    finally:p.close()


@pytest.mark.parametrize('prefix_alias',[True,False])
def test_anchor_namespace_rejects_hardlink_aliases(tmp_path,prefix_alias):
    root=tmp_path/'anchors';root.mkdir()
    for i in range(2): (root/f'{i:03d}.json').write_bytes(b'{}')
    (root/'002.json').hardlink_to(root/('000.json' if prefix_alias else '001.json'))
    with pytest.raises(ValueError,match='single-link'):
        m._inventory(root,set(),pattern=r'([0-9]{3})\.json',low=0,high=4,directories=False,retained={})


@pytest.mark.parametrize('relative',[
    'parent_events_non_authoritative/header.json',
    'parent_events_non_authoritative/001/metadata.bin',
    'parent_events_non_authoritative/001/payload.bin',
    'parent_events_non_authoritative/001/commit.json',
    'parent_anchor_non_authoritative/header.json',
    'parent_anchor_non_authoritative/001.json',
])
def test_consumed_evidence_rejects_external_hardlink(tmp_path,environment,synthetic_reports,relative):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        step(p,environment,synthetic_reports);pin=p._anchor.inspect().record_sha256
        suffix=p._root/'parent_events_non_authoritative'/'003';suffix.mkdir()
        (suffix/'unconsumed_alias.bin').hardlink_to(p._root/relative)
        with pytest.raises(ValueError,match='single-link'):open_prefix(p,pin)
    finally:p.close()


def test_single_read_rejects_same_bytes_replacement(tmp_path,monkeypatch):
    path=tmp_path/'record';path.write_bytes(b'{}');original=m.io.read_stable
    def replace(p,cap):
        result=original(p,cap)
        p.rename(tmp_path/'old_record');p.write_bytes(result[0])
        return result
    monkeypatch.setattr(m.io,'read_stable',replace)
    with pytest.raises(ValueError,match='replaced'):m._read_single(path,10)
