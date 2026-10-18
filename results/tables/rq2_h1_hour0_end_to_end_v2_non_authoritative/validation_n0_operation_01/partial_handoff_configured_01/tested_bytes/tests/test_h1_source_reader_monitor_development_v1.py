"""Real monitor function AST, explicit process doubles; no spawned processes."""
import ast
from pathlib import Path
import time
import traceback
from types import SimpleNamespace

import psutil
import pytest


REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_fresh_source_reader_bounded_v1.py'


def monitor(edge):
    dead=set();events=[]
    class Process:
        pid=41
        def create_time(self):
            if edge=='live':raise psutil.AccessDenied(self.pid)
            return 12.0 if edge!='reuse' else 13.0
        def is_running(self):return self.pid not in dead
        def children(self,**kwargs):
            if edge=='children':raise psutil.AccessDenied(self.pid)
            return []
        def memory_info(self):
            if edge=='rss':raise psutil.AccessDenied(self.pid)
            return SimpleNamespace(rss=17)
        def kill(self):dead.add(self.pid);events.append('observed_kill')
    class Popen:
        pid=41
        def poll(self):return 0 if edge=='reuse' or self.pid in dead else None
        def kill(self):dead.add(self.pid);events.append('popen_kill')
        def wait(self,**kwargs):events.append('popen_wait');return 0
    def wait_procs(*args,**kwargs):
        if edge=='wait_procs':raise psutil.AccessDenied(41)
        return [],[]
    fake=SimpleNamespace(Process=lambda pid:Process(),Error=psutil.Error,
        NoSuchProcess=psutil.NoSuchProcess,wait_procs=wait_procs)
    namespace=dict(psutil=fake,time=time,traceback=traceback,owned={41:12.0},proc=Popen(),
        errors=[],process_errors=set(),events=[],result={})
    tree=ast.parse(SOURCE.read_bytes(),filename=str(SOURCE))
    selected=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef)
        and node.name in ('live','observe','cleanup','resource_rss')],type_ignores=[])
    exec(compile(selected,str(SOURCE),'exec'),namespace)
    return namespace,dead,events


@pytest.mark.parametrize('edge',['live','children','rss','wait_procs'])
def test_psutil_failure_keeps_popen_cleanup_and_honest_unknown(edge):
    scope,dead,events=monitor(edge)
    if edge!='wait_procs':
        with pytest.raises(RuntimeError,match='observation failed'):scope['resource_rss']()
    scope['cleanup']()
    assert 41 in dead and 'popen_wait' in events
    assert scope['result']['process_observation_errors']
    assert not scope['result']['observed_owned_processes_absent']
    assert not scope['errors']
    if edge=='live':assert 'popen_kill' in events


def test_reused_pid_never_killed():
    scope,dead,events=monitor('reuse');scope['cleanup']()
    assert not dead and events==['popen_wait']
    assert scope['result']['observed_owned_processes_absent']
