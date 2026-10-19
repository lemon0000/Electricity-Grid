from dataclasses import replace
from pathlib import Path
import ctypes as c
import os

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_resources as api


@pytest.fixture
def sample(tmp_path, monkeypatch):
    budget = api.HostResourceBudget(80, 20, (
        api.DirectoryDemand('archive', str(tmp_path/'archive'), 40, 10),
        api.DirectoryDemand('scratch', str(tmp_path/'scratch'), 30, 20)))
    monkeypatch.setattr(api, '_directory_binding', lambda p: (p, 1, 2, 'volume-a'))
    monkeypatch.setattr(api, '_observe_commit', lambda: api.CommitObservation(50, 75, 4))
    monkeypatch.setattr(api, '_observe_disk', lambda item, volume:
        api.DiskObservation(item.name, item.directory, volume, 90, 1000, 999))
    return budget


def run(budget):
    return api.observe_headroom(budget, expected_request_identity=api.resource_identity(budget))


def test_shared_volume_demands_added_reserve_max_at_exact_boundary(sample):
    result = run(sample)
    assert result.observed_headroom_sufficient and not result.errors
    assert result.commit.available_bytes == 100
    assert result.volume_requirements == (('volume-a', 70, 20, 90),)
    assert result.finished_monotonic_seconds >= result.started_monotonic_seconds
    assert not any((result.resource_reservation_held, result.hard_resource_limits_enforced,
        result.whole_task_resources_verified, result.formal_run_authorized, result.formal_result))


@pytest.mark.parametrize('commit,disk,expected', [(99, 90, 1), (100, 89, 1), (99, 89, 2)])
def test_each_insufficient_resource_and_both_are_reported(sample, monkeypatch, commit, disk, expected):
    monkeypatch.setattr(api, '_observe_commit', lambda: api.CommitObservation(0, commit, 1))
    monkeypatch.setattr(api, '_observe_disk', lambda item, volume:
        api.DiskObservation(item.name, item.directory, volume, disk, 1000, 10**12))
    result = run(sample)
    assert not result.observed_headroom_sufficient
    assert len(result.errors) == expected


def test_shared_volume_uses_minimum_of_nonatomic_samples(sample, monkeypatch):
    monkeypatch.setattr(api, '_observe_disk', lambda item, volume:
        api.DiskObservation(item.name, item.directory, volume, 100 if item.name == 'archive' else 89, 1000, 1000))
    assert not run(sample).observed_headroom_sufficient


def test_separate_volumes_do_not_combine_space(sample, monkeypatch):
    monkeypatch.setattr(api, '_directory_binding', lambda p: (p, 1, 2, Path(p).name))
    monkeypatch.setattr(api, '_observe_disk', lambda item, volume:
        api.DiskObservation(item.name, item.directory, volume, 50, 1000, 1000))
    result = run(sample)
    assert result.observed_headroom_sufficient
    assert result.volume_requirements == (('archive', 40, 10, 50), ('scratch', 30, 20, 50))


@pytest.mark.parametrize('bad', [0, -1, True, 1., float('inf'), None])
def test_invalid_explicit_byte_budgets_rejected(sample, bad):
    with pytest.raises(ValueError):
        replace(sample, additional_commit_bytes=bad)
    with pytest.raises(ValueError):
        replace(sample.directories[0], reserve_bytes=bad)


def test_duplicate_roles_empty_and_mutable_inventory_rejected(sample):
    for inventory in ((), list(sample.directories), (sample.directories[0],)*2):
        with pytest.raises(ValueError):
            replace(sample, directories=inventory)


def test_wrong_pin_rejected_before_observation(sample, monkeypatch):
    def forbidden(): raise AssertionError('must reject before observation')
    monkeypatch.setattr(api, '_observe_commit', forbidden)
    with pytest.raises(ValueError, match='identity drift'):
        api.observe_headroom(sample, expected_request_identity='0'*64)


def test_budget_change_does_not_inherit_pin(sample):
    pin = api.resource_identity(sample)
    with pytest.raises(ValueError, match='identity drift'):
        api.observe_headroom(replace(sample, commit_reserve_bytes=21), expected_request_identity=pin)


def test_directory_drift_during_observation_rejects(sample, monkeypatch):
    pin = api.resource_identity(sample)
    def observe():
        monkeypatch.setattr(api, '_directory_binding', lambda p: (p, 1, 999, 'volume-a'))
        return api.CommitObservation(50, 75, 4)
    monkeypatch.setattr(api, '_observe_commit', observe)
    with pytest.raises(ValueError, match='binding changed'):
        api.observe_headroom(sample, expected_request_identity=pin)


@pytest.mark.parametrize('stage', ['commit', 'disk'])
def test_api_failure_propagates_without_sufficient_report(sample, monkeypatch, stage):
    def fail(*a): raise OSError('injected observation failure')
    monkeypatch.setattr(api, '_observe_'+stage, fail)
    with pytest.raises(OSError, match='injected'):
        run(sample)


@pytest.mark.parametrize('observation', [api.CommitObservation(2, 1, 4096),
    api.CommitObservation(0, 0, 4096), api.CommitObservation(0, 1, 0), api.CommitObservation(False, 100, 1), None])
def test_malformed_commit_rejected(sample, monkeypatch, observation):
    monkeypatch.setattr(api, '_observe_commit', lambda: observation)
    with pytest.raises(ValueError, match='commit observation'):
        run(sample)


@pytest.mark.parametrize('fault', ['caller_exceeds_total', 'caller_exceeds_free', 'negative', 'bool', 'binding'])
def test_malformed_disk_rejected(sample, monkeypatch, fault):
    def observe(item, volume):
        original = api.DiskObservation(item.name, item.directory, volume, 90, 1000, 1000)
        return replace(original, **{'caller_exceeds_total': {'caller_total_bytes': 89},
            'caller_exceeds_free': {'volume_free_bytes': 89}, 'negative': {'caller_available_bytes': -1},
            'bool': {'caller_available_bytes': True}, 'binding': {'volume_guid': 'other'}}[fault])
    monkeypatch.setattr(api, '_observe_disk', observe)
    with pytest.raises(ValueError, match='disk observation'):
        run(sample)


def test_native_measurement_width_and_structure_size(monkeypatch):
    class Fake:
        def K32GetPerformanceInfo(self, pointer, size):
            assert size == c.sizeof(api._Performance)
            value = c.cast(pointer, c.POINTER(api._Performance)).contents
            assert value.cb == size
            value.CommitTotal, value.CommitLimit, value.PageSize = 2**34, 2**34+3, 4096
            return 1
    monkeypatch.setattr(api, '_api', lambda: Fake())
    assert api._observe_commit().available_bytes == 3*4096


def test_disk_output_preserves_64_bit_caller_available(tmp_path, monkeypatch):
    class Fake:
        def GetDiskFreeSpaceExW(self, directory, available, total, free):
            for pointer, value in ((available, 2**40+1), (total, 2**42), (free, 2**41)):
                c.cast(pointer, c.POINTER(c.c_ulonglong)).contents.value = value
            return 1
    monkeypatch.setattr(api, '_api', lambda: Fake())
    disk = api._observe_disk(api.DirectoryDemand('tmp', str(tmp_path), 1, 1), 'volume-a')
    assert disk.caller_available_bytes == 2**40+1
    assert disk.volume_free_bytes == 2**41


@pytest.mark.parametrize('stage', ['commit', 'disk', 'cb'])
def test_native_failure_and_bad_cb_fail_closed(tmp_path, monkeypatch, stage):
    class Fake:
        def K32GetPerformanceInfo(self, pointer, size):
            if stage == 'cb':
                c.cast(pointer, c.POINTER(api._Performance)).contents.cb = 1
                return 1
            return 0
        def GetDiskFreeSpaceExW(self, *args):
            return 0
    monkeypatch.setattr(api, '_api', lambda: Fake())
    with pytest.raises(ValueError if stage == 'cb' else OSError):
        if stage == 'disk':
            api._observe_disk(api.DirectoryDemand('tmp', str(tmp_path), 1, 1), 'volume-a')
        else:
            api._observe_commit()


@pytest.mark.skipif(os.name != 'nt', reason='Windows native observation')
def test_real_readonly_host_observation_and_abi(tmp_path):
    budget = api.HostResourceBudget(1, 1, (api.DirectoryDemand('tmp', str(tmp_path), 1, 1),))
    before = list(tmp_path.iterdir())
    result = run(budget)
    assert list(tmp_path.iterdir()) == before
    assert result.commit.page_size_bytes > 0
    assert result.commit.available_bytes >= 0
    assert result.disks[0].volume_guid.startswith('\\\\?\\volume{')
    assert c.sizeof(api._Performance) == (104 if c.sizeof(c.c_void_p) == 8 else 56)
    assert api._api().K32GetPerformanceInfo.restype is api.w.BOOL


@pytest.mark.skipif(os.name != 'nt', reason='Windows directory identity')
def test_real_directory_replacement_invalidates_identity(tmp_path):
    directory = tmp_path/'resource'
    directory.mkdir()
    budget = api.HostResourceBudget(1, 1, (api.DirectoryDemand('tmp', str(directory), 1, 1),))
    pin = api.resource_identity(budget)
    directory.rename(tmp_path/'retained_original')
    directory.mkdir()
    with pytest.raises(ValueError, match='identity drift'):
        api.observe_headroom(budget, expected_request_identity=pin)
