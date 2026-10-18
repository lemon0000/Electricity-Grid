"""Read-only host headroom observations for a declared normal task.

No reservation, quota, worker launch, retry, or formal admission is performed.
"""
import ctypes as c
from ctypes import wintypes as w
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import time

from . import episode_store as local


SCHEMA = 'draft_normal_host_headroom_v1'


class _Performance(c.Structure):
    _fields_ = [('cb', w.DWORD)] + [(name, c.c_size_t) for name in
        ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
         'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
        (name, w.DWORD) for name in ('HandleCount', 'ProcessCount', 'ThreadCount')]


def _api():
    if os.name != 'nt':
        raise OSError('Windows host resource observation required')
    api = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'K32GetPerformanceInfo': ([c.POINTER(_Performance), w.DWORD], w.BOOL),
        'GetDiskFreeSpaceExW': ([w.LPCWSTR] + [c.POINTER(c.c_ulonglong)]*3, w.BOOL),
        'GetVolumePathNameW': ([w.LPCWSTR, w.LPWSTR, w.DWORD], w.BOOL),
        'GetVolumeNameForVolumeMountPointW': ([w.LPCWSTR, w.LPWSTR, w.DWORD], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(api, name)
        fn.argtypes, fn.restype = args, result
    return api


def _check(value):
    if not value:
        raise c.WinError(c.get_last_error())


def _positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('explicit positive integer resource bytes required')


@dataclass(frozen=True)
class DirectoryDemand:
    name: str
    directory: str
    additional_bytes: int
    reserve_bytes: int

    def __post_init__(self):
        if type(self.name) is not str or not self.name or len(self.name) > 64:
            raise ValueError('bounded named disk demand required')
        if (type(self.directory) is not str or '\0' in self.directory
                or not Path(self.directory).is_absolute()):
            raise ValueError('explicit absolute disk directory required')
        _positive(self.additional_bytes)
        _positive(self.reserve_bytes)


@dataclass(frozen=True)
class HostResourceBudget:
    additional_commit_bytes: int
    commit_reserve_bytes: int
    directories: tuple[DirectoryDemand, ...]

    def __post_init__(self):
        _positive(self.additional_commit_bytes)
        _positive(self.commit_reserve_bytes)
        if (type(self.directories) is not tuple or not 1 <= len(self.directories) <= 16
                or any(type(item) is not DirectoryDemand for item in self.directories)):
            raise ValueError('one to sixteen explicit directory demands required')
        for item in self.directories:
            item.__post_init__()
        if len({item.name for item in self.directories}) != len(self.directories):
            raise ValueError('unique disk demand names required')


@dataclass(frozen=True)
class CommitObservation:
    committed_pages: int
    limit_pages: int
    page_size_bytes: int

    @property
    def available_bytes(self):
        return (self.limit_pages-self.committed_pages)*self.page_size_bytes


@dataclass(frozen=True)
class DiskObservation:
    name: str
    directory: str
    volume_guid: str
    caller_available_bytes: int
    caller_total_bytes: int
    volume_free_bytes: int


@dataclass(frozen=True)
class HostHeadroomObservation:
    request_identity: str
    started_monotonic_seconds: float
    finished_monotonic_seconds: float
    commit: CommitObservation
    disks: tuple[DiskObservation, ...]
    # volume GUID, combined demand, reserve, minimum observed caller available
    volume_requirements: tuple[tuple[str, int, int, int], ...]
    errors: tuple[str, ...]
    observed_headroom_sufficient: bool
    resource_reservation_held: bool = False
    hard_resource_limits_enforced: bool = False
    whole_task_resources_verified: bool = False
    formal_run_authorized: bool = False
    formal_result: bool = False


def _directory_binding(directory):
    path = local._path(directory)
    local._local_ntfs(path)
    if not path.is_dir():
        raise ValueError('existing local resource directory required')
    before = path.stat()
    api = _api()
    mount, guid = c.create_unicode_buffer(32768), c.create_unicode_buffer(64)
    _check(api.GetVolumePathNameW(str(path), mount, len(mount)))
    _check(api.GetVolumeNameForVolumeMountPointW(mount.value, guid, len(guid)))
    after = local._path(directory).stat()
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise ValueError('resource directory changed during binding')
    if not guid.value.startswith('\\\\?\\Volume{') or not guid.value.endswith('}\\'):
        raise ValueError('local volume GUID required')
    return os.path.normcase(str(path)), before.st_dev, before.st_ino, guid.value.lower()


def resource_identity(budget):
    if type(budget) is not HostResourceBudget:
        raise ValueError('typed host resource budget required')
    budget.__post_init__()
    bindings = tuple(_directory_binding(item.directory) for item in budget.directories)
    content = (SCHEMA, asdict(budget), bindings,
        sha256(Path(__file__).read_bytes()).hexdigest(), sha256(Path(local.__file__).read_bytes()).hexdigest())
    return sha256(json.dumps(content, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _observe_commit():
    value = _Performance()
    value.cb = c.sizeof(value)
    _check(_api().K32GetPerformanceInfo(c.byref(value), c.sizeof(value)))
    if value.cb != c.sizeof(value):
        raise ValueError('invalid performance information structure size')
    return CommitObservation(int(value.CommitTotal), int(value.CommitLimit), int(value.PageSize))


def _observe_disk(item, volume):
    available, total, free = c.c_ulonglong(), c.c_ulonglong(), c.c_ulonglong()
    _check(_api().GetDiskFreeSpaceExW(item.directory, c.byref(available), c.byref(total), c.byref(free)))
    return DiskObservation(item.name, item.directory, volume, available.value, total.value, free.value)


def observe_headroom(budget, *, expected_request_identity):
    """Synchronous read-only observation; failure never returns sufficient=True."""
    if (type(expected_request_identity) is not str or len(expected_request_identity) != 64
            or any(x not in '0123456789abcdef' for x in expected_request_identity)):
        raise ValueError('independently retained resource identity required')
    began = time.monotonic()
    if resource_identity(budget) != expected_request_identity:
        raise ValueError('host resource request identity drift')
    commit = _observe_commit()
    if (type(commit) is not CommitObservation or type(commit.committed_pages) is not int
            or commit.committed_pages < 0 or type(commit.limit_pages) is not int
            or commit.limit_pages <= 0 or commit.limit_pages < commit.committed_pages or type(commit.page_size_bytes) is not int
            or commit.page_size_bytes <= 0):
        raise ValueError('invalid host commit observation')
    errors, disks, groups = [], [], {}
    if commit.available_bytes < budget.additional_commit_bytes+budget.commit_reserve_bytes:
        errors.append('insufficient_system_commit_headroom')
    for item in budget.directories:
        volume = _directory_binding(item.directory)[3]
        disk = _observe_disk(item, volume)
        if (type(disk) is not DiskObservation or (disk.name, disk.directory, disk.volume_guid)
                != (item.name, item.directory, volume)
                or any(type(x) is not int or x < 0 for x in
                    (disk.caller_available_bytes, disk.caller_total_bytes, disk.volume_free_bytes))
                or disk.caller_available_bytes > min(disk.caller_total_bytes, disk.volume_free_bytes)):
            raise ValueError('invalid caller disk observation')
        disks.append(disk)
        demand, reserve, available = groups.get(volume, (0, 0, disk.caller_available_bytes))
        groups[volume] = (demand+item.additional_bytes, max(reserve, item.reserve_bytes),
                          min(available, disk.caller_available_bytes))
    requirements = tuple((volume, *values) for volume, values in sorted(groups.items()))
    for volume, demand, reserve, available in requirements:
        if available < demand+reserve:
            errors.append('insufficient_caller_disk_headroom:'+volume)
    if resource_identity(budget) != expected_request_identity:
        raise ValueError('host resource binding changed during observation')
    return HostHeadroomObservation(expected_request_identity, began, time.monotonic(), commit, tuple(disks),
        requirements, tuple(errors), not errors)
