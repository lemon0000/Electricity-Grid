"""Real Windows handle checks for the development path-traversal lease."""
from pathlib import Path
import os
import struct
import subprocess
import threading

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
    return root, file, None, prior


def test_original_check_then_fresh_leaf_and_content(sample):
    root, file, calls, module = sample
    original = module._path
    with candidate.CanonicalPathLease(module, [root]) as lease:
        assert module._path(file) == original(file)
        count = lease.fallbacks
        file.write_bytes(b'changed')
        assert module._path(file).read_bytes() == b'changed'
        assert lease.fallbacks == count
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
        assert not lease._directories
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


@pytest.mark.parametrize('field', ['_original', '_path', '_check'])
def test_instance_dispatch_drift_rejected(sample, field):
    root, file, calls, module = sample
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises(ValueError, match='binding'):
        with lease:
            module._path(file)
            retained = module._path
            setattr(lease, field, lambda value=None: value)
            retained(file)
    # Cleanup must restore the independently bound original, not a changed field.
    assert module._path is original


def test_exact_spelling_keys_keep_case_sensitive_ancestors_separate():
    assert candidate._key(Path('D:/Case/tree')) != candidate._key(Path('D:/case/tree'))


def test_failed_second_observation_rolls_back_new_handles(sample, monkeypatch):
    root, file, calls, module = sample
    resolve = Path.resolve
    observed = []
    def drift(path, *args, **kwargs):
        if path == file:
            observed.append(path)
            if len(observed) == 2:
                raise ValueError('injected second observation failure')
        return resolve(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'resolve', drift)
    with candidate.CanonicalPathLease(module, [root]) as lease:
        with pytest.raises(ValueError, match='second observation'):
            module._path(file)
        assert not lease._directories and not lease._paths


def test_existing_writer_forces_clean_fallback(sample):
    root, file, calls, module = sample
    kernel = candidate._kernel_api()
    writer = kernel.CreateFileW(str(root), 0x40000000, 7, None, 3, 0x02000000, None)
    assert writer != candidate.ctypes.c_void_p(-1).value
    try:
        with candidate.CanonicalPathLease(module, [root]) as lease:
            assert module._path(file) == file
            assert not lease._directories and not lease._paths
    finally:
        kernel.CloseHandle(writer)


def test_real_case_sensitive_ancestors_if_supported(tmp_path):
    root = tmp_path / 'sensitive_non_authoritative'
    root.mkdir()
    enabled = subprocess.run(['fsutil', 'file', 'setCaseSensitiveInfo', str(root), 'enable'],
        capture_output=True, text=True, timeout=10)
    if enabled.returncode:
        pytest.skip('NTFS case-sensitive feature unavailable for this process')
    upper, lower = root / 'Case', root / 'case'
    upper.mkdir()
    lower.mkdir()
    a, b = upper / 'leaf', lower / 'leaf'
    a.write_bytes(b'A')
    b.write_bytes(b'B')
    with candidate.CanonicalPathLease(prior, [root]) as lease:
        assert prior._path(a).read_bytes() == b'A'
        assert prior._path(b).read_bytes() == b'B'
        assert lease._directories[candidate._key(upper)][2] != lease._directories[candidate._key(lower)][2]
        for directory in (upper, lower):
            with pytest.raises(OSError):
                directory.rename(root / 'moved')


def test_case_sensitive_sibling_is_outside_exact_root(tmp_path):
    root = tmp_path / 'sensitive_scope_non_authoritative'
    root.mkdir()
    enabled = subprocess.run(['fsutil', 'file', 'setCaseSensitiveInfo', str(root), 'enable'],
        capture_output=True, text=True, timeout=10)
    if enabled.returncode:
        pytest.skip('NTFS case-sensitive feature unavailable for this process')
    upper, lower = root / 'Case', root / 'case'
    upper.mkdir()
    lower.mkdir()
    leaf = lower / 'leaf'
    with candidate.CanonicalPathLease(prior, [upper]) as lease:
        assert prior._path(leaf) == leaf
        assert not lease._directories and not lease._paths
        assert lease.hits == 0


def test_in_place_reparse_via_attribute_only_handle_is_rejected(sample, tmp_path):
    root, file, calls, module = sample
    ancestor = root / 'mutable'
    ancestor.mkdir()
    target = tmp_path / 'junction_target'
    target.mkdir()
    leaf = ancestor / 'missing'
    substitute = ('\\??\\' + str(target)).encode('utf-16le')
    printable = str(target).encode('utf-16le')
    payload = (struct.pack('<HHHH', 0, len(substitute), len(substitute) + 2, len(printable))
        + substitute + b'\0\0' + printable + b'\0\0')
    raw = struct.pack('<IHH', 0xA0000003, len(payload), 0) + payload
    with candidate.CanonicalPathLease(module, [root]) as lease:
        module._path(leaf)
        kernel = lease._kernel
        kernel.DeviceIoControl.argtypes = (candidate.wintypes.HANDLE, candidate.wintypes.DWORD,
            candidate.wintypes.LPVOID, candidate.wintypes.DWORD, candidate.wintypes.LPVOID,
            candidate.wintypes.DWORD, candidate.ctypes.POINTER(candidate.wintypes.DWORD), candidate.wintypes.LPVOID)
        kernel.DeviceIoControl.restype = candidate.wintypes.BOOL
        handle = kernel.CreateFileW(str(ancestor), 0x100, 7, None, 3, 0x02200000, None)
        assert handle != candidate.ctypes.c_void_p(-1).value
        try:
            buffer = candidate.ctypes.create_string_buffer(raw)
            count = candidate.wintypes.DWORD()
            assert kernel.DeviceIoControl(handle, 0x900A4, buffer, len(raw), None, 0, candidate.ctypes.byref(count), None)
        finally:
            kernel.CloseHandle(handle)
        with pytest.raises(ValueError, match='reparse ancestor'):
            module._path(leaf)


@pytest.mark.parametrize('field', ['_restore_dispatch', '_directories', '_kernel'])
@pytest.mark.parametrize('remove', [False, True])
def test_cleanup_uses_independent_bindings(sample, field, remove):
    root, file, calls, module = sample
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises((ValueError, AttributeError)):
        with lease:
            module._path(file)
            handles = lease._directories
            if remove:
                delattr(lease, field)
            else:
                setattr(lease, field, None)
    assert module._path is original
    assert not handles
    assert lease._state == 'closed'


def test_replaced_predecessor_rejected_before_entry(sample, monkeypatch):
    root, file, calls, module = sample
    monkeypatch.setattr(module, '_path', lambda value: Path(value))
    with pytest.raises(ValueError, match='exact unchanged'):
        candidate.CanonicalPathLease(module, [root])


def test_process_identity_drift_rejected(sample):
    root, file, calls, module = sample
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises(ValueError, match='lifetime'):
        with lease:
            module._path(file)
            lease._owner = os.getpid() + 1, threading.get_ident()
            module._path(file)
    assert module._path is original and not lease._directories


@pytest.mark.parametrize('close_fault', ['false', 'raise'])
def test_all_handles_attempted_and_body_error_preserved(sample, monkeypatch, close_fault):
    root, file, calls, module = sample
    real_kernel = candidate._kernel_api()
    class Proxy:
        armed = False
        attempts = 0
        failed = False
        def __getattr__(self, name):
            return getattr(real_kernel, name)
        def CloseHandle(self, handle):
            self.attempts += 1
            if self.armed and not self.failed:
                self.failed = True
                if close_fault == 'raise':
                    raise OSError('injected close error')
                return False
            return real_kernel.CloseHandle(handle)
    proxy = Proxy()
    monkeypatch.setattr(candidate, '_kernel_api', lambda: proxy)
    original = module._path
    lease = candidate.CanonicalPathLease(module, [root])
    with pytest.raises(BaseExceptionGroup) as errors:
        with lease:
            module._path(file)
            handles = len(lease._directories)
            proxy.armed = True
            raise RuntimeError('original body error')
    assert proxy.attempts == handles
    assert any(isinstance(e, RuntimeError) and str(e) == 'original body error' for e in errors.value.exceptions)
    assert any(isinstance(e, candidate.HandleCleanupError) for e in errors.value.exceptions)
    assert module._path is original and lease._state == 'cleanup_failed'
    assert len(lease._directories) == 1
    lease._rollback(tuple(lease._directories))
    assert not lease._directories
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
