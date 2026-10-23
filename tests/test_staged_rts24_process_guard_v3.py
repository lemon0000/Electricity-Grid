"""Bounded storage reservation and tiny Python Jobs, no numeric backend."""
import os
import sys

import pytest

from src import staged_rts24_process_guard_v3 as d
from test_staged_rts24_process_guard_v1 import FakeOwner, LIMITS


def run(tmp_path, owner=None, limits=None):
    return d.supervise([], cwd=tmp_path, output=tmp_path, progress=tmp_path/'events', limits=limits or LIMITS,
        owner_factory=lambda *a, **kw: owner or FakeOwner())


@pytest.mark.parametrize('extra', [0, 1])
@pytest.mark.parametrize('when', ['running', 'terminal'])
def test_both_record_reservations_count_at_every_scan(tmp_path, monkeypatch, extra, when):
    (tmp_path/'payload').write_bytes(b'x'*(LIMITS['output_bytes']-d.RESERVED_BYTES+extra))
    owner = FakeOwner()
    if when == 'terminal': monkeypatch.setattr(owner, 'poll', lambda: 0)
    result = run(tmp_path, owner)
    assert result['terminal_reserved_bytes'] == result['parent_reserved_bytes'] == 131072
    assert result['terminal_reserved_files'] == result['parent_reserved_files'] == 1
    assert result['member_handle_cap'] == 1024
    assert result['stop_reason'] == (('terminal_storage_limit' if when == 'terminal' else 'storage_limit') if extra else None)


@pytest.mark.parametrize('extra', [0, 1])
def test_two_file_slots_reserved(tmp_path, extra):
    for i in range(LIMITS['files']-2+extra): (tmp_path/str(i)).touch()
    assert run(tmp_path)['stop_reason'] == ('storage_limit' if extra else None)


@pytest.mark.parametrize('limits', [dict(LIMITS, output_bytes=262143), dict(LIMITS, files=1)])
def test_reservations_must_fit_before_owner_constructed(tmp_path, limits):
    def denied(*a, **kw): pytest.fail('owner constructed without reserve')
    with pytest.raises(ValueError, match='reservation'):
        d.supervise([], cwd=tmp_path, output=tmp_path, progress=tmp_path/'events', limits=limits, owner_factory=denied)


@pytest.mark.parametrize('fault', ['sample', 'cleanup', 'close', 'terminal_scan'])
def test_failed_observations_preserve_diagnostics_and_quiet(tmp_path, monkeypatch, fault):
    owner = FakeOwner()
    def fail(*a, **kw): raise OSError('\U0001f600'*5000)
    if fault == 'terminal_scan':
        monkeypatch.setattr(owner, 'poll', lambda: 0)
        monkeypatch.setattr(d, 'scan_output', fail)
    else: monkeypatch.setattr(owner, {'sample':'sample', 'cleanup':'quiesce', 'close':'close'}[fault], fail)
    result = run(tmp_path, owner)
    assert result['job_quiet_confirmed'] is (fault not in ('cleanup', 'close'))
    assert result['stop_reason']
    assert all(value is None or len(value) <= 514 for value in (result['monitor_error'], result['cleanup_error']))
    assert '[truncated]' in (result['monitor_error'] or result['cleanup_error'])


@pytest.mark.parametrize('fault', ['rss', 'commit'])
def test_terminal_memory_is_checked_even_after_fast_exit(tmp_path, monkeypatch, fault):
    owner = FakeOwner()
    monkeypatch.setattr(owner, 'poll', lambda: 0)
    monkeypatch.setattr(owner, 'sample', lambda: dict(rss_bytes=LIMITS['rss_bytes']+1 if fault == 'rss' else 2,
        peak_job_commit_bytes=2*1024**3+1 if fault == 'commit' else 2, pids=[], processes=0))
    result = run(tmp_path, owner)
    assert result['stop_reason'] == 'terminal_'+fault+'_limit'
    assert result['rss_observation_available'] is False and result['sampled_tree_peak_rss_bytes'] is None


@pytest.mark.skipif(os.name != 'nt', reason='Windows complete Job ownership')
def test_real_short_child_keeps_complete_historical_handles_and_final_accounting(tmp_path):
    result = d.supervise([sys.executable, '-B', '-s', '-c', 'import time; time.sleep(.3)'], cwd=tmp_path,
        output=tmp_path, progress=tmp_path/'events', limits=LIMITS)
    assert result['exit_code'] == 0 and result['stop_reason'] is None and result['job_quiet_confirmed']
    w = result['quiescence_witness']
    assert w['total_processes'] == w['observed_unique_member_handles'] == len(w['member_identities']) >= 1
    assert dict(pid=result['owner_pid'],creation_filetime=result['owner_creation_filetime']) in w['member_identities']
    assert w['all_handles_signaled'] and w['complete_inventory'] and w['active_processes'] == 0 and w['final_pids'] == []
    assert len(d.record_image(result)) < 131072


def test_original_owner_rejects_1025th_retained_handle_and_closes_new_handle():
    from types import SimpleNamespace
    owner=object.__new__(d.OwnedChild)
    owner.pid=1;owner._members={(i,1):i for i in range(1,1025)}
    closed=[]
    owner.job_pids=lambda:[2048]
    owner.open_member=lambda *a:777
    owner._k=SimpleNamespace(GetProcessTimes=lambda *a:True,CloseHandle=lambda h:closed.append(h) or True)
    with pytest.raises(OSError,match='HANDLE cap'):owner.capture_members()
    assert len(owner._members)==1024 and closed==[777]


@pytest.mark.parametrize('name,value',[('wall_seconds',3601),('no_progress_seconds',66),('files',8193),
    ('rss_bytes',True),('output_bytes',1.5),('files',0),('wall_seconds',float('nan'))])
def test_invalid_caps_never_construct_owner(tmp_path,name,value):
    def denied(*a,**k):pytest.fail('owner constructed for invalid proposal')
    with pytest.raises(ValueError):d.supervise([],cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',
        limits={**LIMITS,name:value},owner_factory=denied)


@pytest.mark.parametrize('stage',['sample','cleanup','close'])
def test_unprintable_exception_still_returns_bounded_diagnostic(tmp_path,monkeypatch,stage):
    class Unprintable(OSError):
        def __str__(self):raise RuntimeError('str failed')
    def fail(*a,**kw):raise Unprintable()
    owner=FakeOwner()
    monkeypatch.setattr(owner,{'sample':'sample','cleanup':'quiesce','close':'close'}[stage],fail)
    saved=run(tmp_path,owner)
    assert saved['stop_reason'] and '[message unavailable]' in (saved['monitor_error'] or saved['cleanup_error'])
    assert owner.closed is (stage!='close')


def test_job_peak_commit_is_observed_after_quiesce(tmp_path,monkeypatch):
    owner=FakeOwner();quiesced=[]
    monkeypatch.setattr(owner,'poll',lambda:0)
    monkeypatch.setattr(owner,'quiesce',lambda **kw:quiesced.append(True))
    monkeypatch.setattr(owner,'sample',lambda:dict(rss_bytes=0,peak_job_commit_bytes=2*1024**3+int(bool(quiesced)),pids=[],processes=0))
    saved=run(tmp_path,owner)
    assert saved['peak_job_commit_bytes']==2*1024**3+1 and saved['stop_reason']=='post_quiesce_commit_limit'


def test_guard_itself_checks_serialized_record_cap_after_cleanup(tmp_path):
    owner=FakeOwner();owner.quiescence_witness={'unexpected':'x'*131072}
    with pytest.raises(ValueError,match='128 KiB'):run(tmp_path,owner)
    assert owner.closed
