from dataclasses import replace
from types import SimpleNamespace as NS
import os

import pytest

from src.rq2_joint_deliverability_boundary_v1 import scale_episode as ep

r = ep.resources
MIB = 1024**2


def budget():
    return ep.EpisodeBudget(22, 22, ep.controller.process.TaskProcessBudget(30., .1, 768*MIB, 768*MIB, 3.),
        32*MIB, 16*MIB, 16*MIB, 8*MIB, 2*MIB,
        r.contract.TaskEnvelope('episode', 600, 60, 768*MIB, 512*MIB, 256*MIB, 1, 10000, 10000),
        1024*MIB, 1024*MIB, 10000)


def declaration(b):
    selection = NS(task_id='episode', max_threads=1, max_variables=10000, max_constraints=10000)
    return r.admit(b, NS(budget=selection), tuple(NS(budget=selection) for _ in range(4)), (1, 2))


@pytest.mark.parametrize('field,value', [('max_wall_seconds', 389), ('max_job_commit_bytes', 1),
    ('archive_bytes', 320*MIB), ('scratch_bytes', 1), ('max_threads', 0), ('max_variables', 9999)])
def test_whole_window_reservation_shortfall(field, value):
    b = budget()
    with pytest.raises(ValueError): declaration(replace(b, envelope=replace(b.envelope, **{field: value})))


def test_complete_declaration_covers_metadata_without_reclamation():
    assert declaration(budget()) == 390


def measured(tmp_path, monkeypatch, b=None):
    b = budget() if b is None else b
    monkeypatch.setattr(r.memory, '_peak_working_set_bytes', lambda: 123)
    monkeypatch.setattr(r.host, 'observe_headroom', lambda *a, **k: NS(
        observed_headroom_sufficient=True, commit=NS(available_bytes=2*1024*MIB)))
    return b, lambda **kw: r.observe(tmp_path, b, r.time.monotonic(), **kw)


def test_archive_scratch_and_prospective_write_bytes(tmp_path, monkeypatch):
    (tmp_path/'header.json').write_bytes(b'a'*11)
    task = tmp_path/'phase_non_authoritative'
    (task/'scratch'/'nested').mkdir(parents=True)
    (task/'scratch'/'nested'/'work.bin').write_bytes(b'b'*17)
    (task/'result.json').write_bytes(b'c'*13)
    b, observe = measured(tmp_path, monkeypatch)
    report = observe()
    assert report['archive_logical_bytes'] == 24 and report['scratch_logical_bytes'] == 17
    r.validate_observation(report, b)
    small = replace(b, envelope=replace(b.envelope, archive_bytes=24))
    with pytest.raises(ValueError, match='logical byte'):
        r.observe(tmp_path, small, r.time.monotonic(), extra_archive_bytes=1)


@pytest.mark.parametrize('fault', ['time', 'memory', 'entries', 'headroom'])
def test_sampled_limit_refusal(tmp_path, monkeypatch, fault):
    (tmp_path/'one').write_bytes(b'1')
    (tmp_path/'two').write_bytes(b'2')
    b, _ = measured(tmp_path, monkeypatch)
    start = r.time.monotonic()
    if fault == 'time': start -= 601
    elif fault == 'memory': monkeypatch.setattr(r.memory, '_peak_working_set_bytes', lambda: 1024*MIB+1)
    elif fault == 'entries': b = replace(b, max_tree_entries=1)
    else: monkeypatch.setattr(r.host, 'observe_headroom', lambda *a, **k: NS(observed_headroom_sufficient=False))
    with pytest.raises((ValueError, TimeoutError)): r.observe(tmp_path, b, start)


def test_hardlink_refused(tmp_path, monkeypatch):
    file = tmp_path/'one'
    file.write_bytes(b'1')
    os.link(file, tmp_path/'two')
    _, observe = measured(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='single-link'): observe()


@pytest.mark.parametrize('key,value', [('whole_task_resources_verified', True), ('elapsed_seconds', float('nan')),
    ('archive_logical_bytes', 1024*MIB), ('tree_entries', False)])
def test_resource_record_cannot_claim_more_than_observed(tmp_path, monkeypatch, key, value):
    b, observe = measured(tmp_path, monkeypatch)
    report = observe()
    report[key] = value
    with pytest.raises(ValueError): r.validate_observation(report, b)


@pytest.mark.parametrize('key', ['elapsed_seconds', 'controller_lifetime_peak_working_set_bytes',
    'archive_logical_bytes', 'scratch_logical_bytes', 'tree_entries'])
def test_retained_resource_observations_cannot_decrease(tmp_path, monkeypatch, key):
    b, observe = measured(tmp_path, monkeypatch)
    previous = observe()
    previous[key] = 10
    current = dict(previous, **{key: 9})
    with pytest.raises(ValueError, match='decreased: '+key):
        r.validate_observation(current, b, previous)


def test_available_host_commit_can_decrease(tmp_path, monkeypatch):
    b, observe = measured(tmp_path, monkeypatch)
    previous = observe()
    current = dict(previous, system_commit_available_bytes=previous['system_commit_available_bytes']-1)
    r.validate_observation(current, b, previous)
