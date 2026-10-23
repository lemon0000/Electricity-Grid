"""P2 monitor proposals checked using fake owners or a tiny real Python child."""
import os
import sys

import pytest

from src import staged_rts24_process_guard_v1 as old,staged_rts24_process_guard_v2 as d
from test_staged_rts24_process_guard_v1 import FakeOwner,LIMITS


def test_new_caps_accept_proposals_and_preserve_owner_memory_limits(tmp_path):
    calls=[]
    def owner(*a,**kw):calls.append(kw);return FakeOwner()
    limits={**LIMITS,'wall_seconds':3600,'no_progress_seconds':65,'files':8192}
    result=d.supervise([],cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',limits=limits,owner_factory=owner)
    assert result['job_quiet_confirmed'] and result['stop_reason'] is None
    assert calls[0]['max_process_commit_bytes']==1024**3 and calls[0]['max_job_commit_bytes']==2*1024**3
    with pytest.raises(ValueError):old.supervise([],cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',limits=limits,owner_factory=owner)
    assert len(calls)==1


@pytest.mark.parametrize('name,value',[('wall_seconds',3601),('no_progress_seconds',66),('files',8193),
    ('rss_bytes',True),('output_bytes',1.5),('files',0),('wall_seconds',float('nan'))])
def test_invalid_caps_never_construct_owner(tmp_path,name,value):
    def denied(*a,**k):pytest.fail('owner constructed for invalid proposal')
    with pytest.raises(ValueError):d.supervise([],cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',
        limits={**LIMITS,name:value},owner_factory=denied)


@pytest.mark.parametrize('fault',['sample','cleanup','close','storage'])
def test_failures_preserve_quiet_boundary(tmp_path,monkeypatch,fault):
    owner=FakeOwner()
    if fault=='storage':(tmp_path/'large').write_bytes(b'x'*LIMITS['output_bytes'])
    else:monkeypatch.setattr(owner,{'sample':'sample','cleanup':'quiesce','close':'close'}[fault],
        lambda *a,**kw:(_ for _ in ()).throw(OSError('ordinary fault')))
    result=d.supervise([],cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',limits=LIMITS,owner_factory=lambda *a,**kw:owner)
    assert result['stop_reason'] and result['job_quiet_confirmed'] is (fault not in ('cleanup','close'))


@pytest.mark.skipif(os.name!='nt',reason='Windows Job ownership')
def test_real_short_child_uses_same_complete_handle_inventory(tmp_path):
    result=d.supervise([sys.executable,'-B','-s','-c','import time; time.sleep(.3)'],cwd=tmp_path,
        output=tmp_path,progress=tmp_path/'events',limits=LIMITS)
    assert result['exit_code']==0 and result['stop_reason'] is None and result['job_quiet_confirmed']
    w=result['quiescence_witness']
    assert w['complete_inventory'] and w['all_handles_signaled'] and w['active_processes']==0
