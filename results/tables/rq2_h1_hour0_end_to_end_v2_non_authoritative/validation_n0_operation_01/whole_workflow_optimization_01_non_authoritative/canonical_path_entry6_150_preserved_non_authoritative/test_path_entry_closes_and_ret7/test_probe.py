
import importlib.metadata as metadata
from pathlib import Path
import pytest
import performance.pinned_distribution_resolver_v1 as resolver
from src.rq2_joint_deliverability_boundary_v1 import episode_store as store
ORIGINAL=metadata.Distribution.from_name.__func__
@pytest.fixture
def prepared():
    # A same-name, unrelated fixture retains the original metadata resolver.
    assert metadata.Distribution.from_name.__func__ is ORIGINAL
    assert metadata.version('numpy')
    return True
def test_flow(prepared,tmp_path):
    assert prepared
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    assert metadata.version('numpy')
    path=tmp_path/'fresh.json';path.write_bytes(b'first')
    assert store._path(path).read_bytes()==b'first'
    path.write_bytes(b'second')
    assert store._path(path).read_bytes()==b'second'
    if 'cleanup_false'=='extra_root':
        outside=Path('D:\\h1_path_entry6_faults_150_non_authoritative\\test_path_entry_closes_and_ret7\\extra_non_authoritative\\fresh.json');outside.write_bytes(b'outside')
        assert store._path(outside).read_bytes()==b'outside'
        outside.write_bytes(b'outside changed')
        assert store._path(outside).read_bytes()==b'outside changed'
    if 'cleanup_false'=='body_and_reader_error':
        def refused():raise ValueError('expected receipt runtime failure')
        resolver._RUNTIME=refused
    if 'cleanup_false' not in ('normal','extra_root'):raise RuntimeError('expected original body primary')
