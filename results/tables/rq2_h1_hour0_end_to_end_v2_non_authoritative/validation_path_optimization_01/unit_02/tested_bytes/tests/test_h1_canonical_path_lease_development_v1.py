"""Real Windows handle checks for the development path-traversal lease."""
from pathlib import Path
import os
import subprocess
import threading
from types import SimpleNamespace

import pytest

from experiments import h1_canonical_path_lease_development_v1 as candidate
from src.rq2_joint_deliverability_boundary_v1 import episode_store as prior


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows directory sharing')


@pytest.fixture
def sample(tmp_path):
    root = tmp_path / 'saved_non_authoritative'
    root.mkdir()
    file = root / 'evidence.json'
    file.write_bytes(b'first')
    calls = []
    def original(value):
        calls.append(value)
        return prior._path(value)
    return root, file, calls, SimpleNamespace(_path=original)


def test_original_check_then_fresh_leaf_and_content(sample):
    root, file, calls, module = sample
    original = module._path
    with candidate.CanonicalPathLease(module, [root]) as lease:
        assert module._path(file) == original(file)
        count = len(calls)
        file.write_bytes(b'changed')
        assert module._path(file).read_bytes() == b'changed'
        assert len(calls) == count
        assert lease.receipt()['hits'] == 1
    assert module._path is original
    assert not lease._directories


def test_ancestor_rename_blocked_and_released(sample):
    root, file, calls, module = sample
    destination = root.with_name('renamed_non_authoritative')
    with candidate.CanonicalPathLease(module, [root]):
        module._path(file)
        with pytest.raises(OSError):
            root.rename(destination)
    root.rename(destination)
    assert (destination / file.name).is_file()


def test_ancestor_write_handle_blocked_child_writes_allowed(sample):
    root, file, calls, module = sample
    with candidate.CanonicalPathLease(module, [root]) as lease:
        module._path(file)
        kernel = lease._kernel
        writer = kernel.CreateFileW(str(root), 0x40000000, 7, None, 3, 0x02000000, None)
        if writer != candidate.ctypes.c_void_p(-1).value:
            kernel.CloseHandle(writer)
            pytest.fail('protected ancestor accepted a write handle')
        file.write_bytes(b'new')
        extra = root / 'new_child'
        extra.mkdir()
        (extra / 'fresh').write_bytes(b'fresh')


def test_leaf_replacement_is_observed_without_caching_bytes(sample):
    root, file, calls, module = sample
    with candidate.CanonicalPathLease(module, [root]):
        module._path(file)
        file.unlink()
        file.write_bytes(b'replaced')
        assert module._path(file).read_bytes() == b'replaced'
        file.unlink()
        assert not module._path(file).exists()


def test_new_junction_at_cached_leaf_rejected(sample, tmp_path):
    root, file, calls, module = sample
    leaf = root / 'leaf'
    leaf.mkdir()
    target = tmp_path / 'target'
    target.mkdir()
    with candidate.CanonicalPathLease(module, [root]):
        module._path(leaf)
        leaf.rmdir()
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(leaf), str(target)],
            capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        with pytest.raises(ValueError, match='reparse'):
            module._path(leaf)
        with pytest.raises(ValueError, match='reparse'):
            prior._path(leaf)


def test_relative_dotdot_and_outside_paths_fall_back(sample, tmp_path):
    root, file, calls, module = sample
    with candidate.CanonicalPathLease(module, [root]) as lease:
        assert module._path('relative') == prior._path('relative')
        assert module._path(root / '..' / root.name / file.name) == prior._path(root / '..' / root.name / file.name)
        assert module._path(tmp_path / 'outside') == prior._path(tmp_path / 'outside')
        assert lease.hits == 0


def test_new_directory_paths_do_not_reuse_unheld_ancestors(sample):
    root, file, calls, module = sample
    parent = root / 'later'
    leaf = parent / 'child'
    with candidate.CanonicalPathLease(module, [root]) as lease:
        # A nonexistent intermediate directory cannot be put in the cache.
        assert module._path(leaf) == prior._path(leaf)
        assert candidate._key(leaf) not in lease._paths
        parent.mkdir()
        assert module._path(leaf) == prior._path(leaf)
        assert candidate._key(leaf) in lease._paths
        with pytest.raises(OSError):
            parent.rename(root / 'moved')


def test_capacity_saturation_retains_predecessor(sample):
    root, file, calls, module = sample
    with candidate.CanonicalPathLease(module, [root], max_directories=1) as lease:
        assert module._path(file) == prior._path(file)
        assert module._path(file) == prior._path(file)
        assert lease.hits == 0
    with candidate.CanonicalPathLease(module, [root], max_paths=1) as lease:
        module._path(file)
        other = root / 'second'
        module._path(other)
        module._path(other)
        assert lease.receipt()['canonical_paths'] == 1


def test_exception_cleanup_single_use_and_thread_rejection(sample):
    root, file, calls, module = sample
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises(RuntimeError, match='test interruption'):
        with lease:
            module._path(file)
            failures = []
            def cross_thread():
                try:
                    module._path(file)
                except ValueError as error:
                    failures.append(str(error))
            thread = threading.Thread(target=cross_thread)
            thread.start()
            thread.join(timeout=5)
            assert not thread.is_alive() and failures
            raise RuntimeError('test interruption')
    assert module._path is original and not lease._directories
    with pytest.raises(ValueError, match='single-use'):
        lease.__enter__()


def test_hook_drift_rejected_and_cleaned(sample):
    root, file, calls, module = sample
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises(ValueError, match='dispatch'):
        with lease:
            module._path(file)
            module._path = lambda value: value
            lease.receipt()
    assert module._path is original and not lease._directories
