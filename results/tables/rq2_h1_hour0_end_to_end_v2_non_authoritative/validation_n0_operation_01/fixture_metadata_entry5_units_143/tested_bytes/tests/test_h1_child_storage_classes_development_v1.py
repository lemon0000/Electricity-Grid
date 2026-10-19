import pytest

from experiments import h1_child_storage_classes_development_v1 as api
from tests.test_h1_attested_source_parent_development_v1 import make_child
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports, saved
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.mark.parametrize('hours,stages',[(1,1),(1,232),(192,1),(192,232)])
def test_independent_first_failure_enumeration(hours,stages):
    result=api.envelope(hours,stages,allocation_quantum=4096)
    n=hours*stages
    cap=929218
    overhead=hours*((12*stages+14)*2048+(stages+1)*262144)
    # Enumerate each possible first failed raw after k successful guarded raws.
    maximum=max(overhead+k*cap+16*1024*1024 for k in range(n))
    assert result['retained_children_logical_bytes']==maximum
    assert result['complete_success_logical_bytes']==overhead+n*cap
    assert result['retained_children_logical_bytes']<=result['original_all_raw_caps_logical_bytes']
    assert result['file_content_allocation_bytes']>=maximum
    assert not result['resource_admission'] and not result['formal_execution_ready']


@pytest.mark.parametrize('hours,stages,quantum',[(True,1,None),(0,1,None),(193,1,None),
    (1,True,None),(1,0,None),(1,233,None),(1,1,True),(1,1,0),(1,1,3),(1,1,131072)])
def test_invalid_scope_rejected(hours,stages,quantum):
    with pytest.raises(ValueError):api.envelope(hours,stages,allocation_quantum=quantum)


@pytest.mark.parametrize('failed_size',[929219,16*1024*1024])
@pytest.mark.parametrize('prefix',[0,1])
def test_large_raw_preserved_and_only_first_failure_allowed(tmp_path,synthetic_reports,failed_size,prefix):
    c=make_child(tmp_path)
    try:
        for raw in synthetic_reports[:prefix]:c.record_report(raw,expected_head=c.head)
        bad=b' '*failed_size
        with pytest.raises(ValueError):c.record_report(bad,expected_head=c.head)
        assert c.poisoned and len(c.owner.locks)==prefix
        path=c.owner.stages.raw.root/f'{prefix:03d}/raw.bin'
        assert path.read_bytes()==bad
        before={p.relative_to(c.root).as_posix():p.stat().st_size for p in c.root.rglob('*') if p.is_file()}
        with pytest.raises(ValueError):c.record_report(bad,expected_head=c.head)
        after={p.relative_to(c.root).as_posix():p.stat().st_size for p in c.root.rglob('*') if p.is_file()}
        assert after==before
        bound=api.envelope(1,3)
        assert sum(after.values())<=bound['retained_children_logical_bytes']
        assert len(after)<=bound['files']
    finally:c.close()


def test_partial_raw_write_stops_before_guard(tmp_path,synthetic_reports,monkeypatch):
    c=make_child(tmp_path)
    original=api.parent.io.write_new
    raw=b' '*929219
    def partial(path,value):
        if path.name=='raw.bin':
            with path.open('xb') as stream:stream.write(value[:12345])
            raise OSError('partial raw write')
        return original(path,value)
    monkeypatch.setattr(api.parent.io,'write_new',partial)
    try:
        with pytest.raises(OSError):c.record_report(raw,expected_head=c.head)
        assert c.poisoned and c.owner.locks==()
        assert (c.owner.stages.raw.root/'000/raw.bin').read_bytes()==raw[:12345]
        assert not (c.owner.attest/'000.guard.json').exists()
        with pytest.raises(ValueError):c.record_report(synthetic_reports[0],expected_head=c.head)
        result=api.envelope(1,3,allocation_quantum=1)
        assert result['file_content_allocation_bytes']==result['retained_children_logical_bytes']
    finally:c.close()


def test_complete_child_files_fit_each_class(tmp_path,synthetic_reports):
    c=make_child(tmp_path)
    try:
        for raw in synthetic_reports:c.record_report(raw,expected_head=c.head)
        assert c.finish(expected_head=c.head).status=='accepted'
        files=[p for p in c.root.rglob('*') if p.is_file()]
        sizes=[p.stat().st_size for p in files]
        for p in files:
            cap=(929218 if p.name=='raw.bin' else 262144
                 if p.name.endswith('.mapping.json') or p.name=='projection.bin' else 2048)
            assert p.stat().st_size<=cap,p
        result=api.envelope(1,3,allocation_quantum=4096)
        assert sum(sizes)<=result['complete_success_logical_bytes']
        assert sum(((n+4095)//4096)*4096 for n in sizes)<=result['file_content_allocation_bytes']
        assert len(files)<=result['files']
    finally:c.close()
