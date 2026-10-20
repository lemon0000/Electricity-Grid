"""Synthetic alias FSM/worker replay tests. No Windows Job or real native call."""
import builtins
from copy import copy,deepcopy
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType,SimpleNamespace
import uuid

import pytest

from experiments import h1_selector_parent_controller_development_v2 as canonical
from tests.test_h1_selector_input_snapshot_development_v1 import context,case,setup,legacy_setup,reference
from tests.test_h1_timed_selector_sequence_development_v1 import factory as sequence_factory,producer


@pytest.fixture
def no_solver(monkeypatch):
    from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver as forbid
    forbid.__wrapped__(monkeypatch)


def load(file,name,patch,dependencies=None):
    spec=importlib.util.spec_from_file_location(name,file);module=importlib.util.module_from_spec(spec)
    if dependencies:
        original=builtins.__import__
        def importing(package,globals=None,locals=None,fromlist=(),level=0):
            if package=='experiments' and globals and globals.get('__name__')==name and fromlist:
                if all(item in dependencies for item in fromlist):
                    return SimpleNamespace(**{item:dependencies[item] for item in fromlist})
            return original(package,globals,locals,fromlist,level)
        module.__builtins__=dict(vars(builtins),__import__=importing)
    patch.setitem(sys.modules,name,module);spec.loader.exec_module(module);return module


@pytest.fixture
def harness(context,sequence_factory,monkeypatch,tmp_path):
    w=canonical.worker;timed=w.sequence.timed
    sequence_factory(producer.fixtures.R);reference_run=timed._run_stage
    sequence_factory(producer.fixtures.A);actual_run=timed._run_stage
    def dispatch(*args,**kw):
        return (reference_run if kw['lane'].role=='Rref' else actual_run)(*args,**kw)
    monkeypatch.setattr(timed,'_run_stage',dispatch)
    calls=[];faults={};writes=[];root=tmp_path/'parent_non_authoritative'
    original_write=w.io.write_new
    def write(path,raw):
        target=path.parent==root or path.parent==root/'worker_non_authoritative'
        name=path.relative_to(root).as_posix() if target else None
        if target:writes.append(name)
        if faults.get('write')==(name,'before'):raise OSError('synthetic before write')
        original_write(path,raw)
        if target and faults.get('write_hook'):faults['write_hook']()
        if faults.get('write')==(name,'after'):raise OSError('synthetic after write')
    monkeypatch.setattr(w.io,'write_new',write)
    original_lifecycle=canonical.lifecycle
    proxy=ModuleType('selector_parent_synthetic_lifecycle_proxy')
    for name in ('FLAGS','INSPECTION_SCHEMA','INSPECTION_CAP','_integer'):
        setattr(proxy,name,getattr(original_lifecycle,name))
    proxy.SCHEMA='synthetic_selector_parent_lifecycle_test_v1'
    proxy.implementation_identity=lambda:w.io.digest(b'synthetic_selector_parent_lifecycle_test_v1')
    def run_job(argv,*,cwd,environment,budget,host_budget,expected_process_identity,before_release,on_quiescent):
        # Explicit in-process fake. Canonical lifecycle is never mutated/called.
        calls.append('acquire');clock=w.sequence.timed.capture._CLOCK;start=clock()
        initial=json.loads(w.io.encode(asdict(w.process.resources.observe_headroom(host_budget,
            expected_request_identity=w.process.resources.resource_identity(host_budget)))))
        pid,creation=w._current_process()
        child=dict(pid=pid,creation_filetime=creation,process_identity=expected_process_identity)
        if faults.get('before_release_hook'):faults['before_release_hook']()
        before_release(child,initial);calls.append('release');released=clock()
        if faults.get('after_release_hook'):faults['after_release_hook']()
        if faults.get('before_worker'):raise RuntimeError('synthetic failure before worker')
        if faults.get('duplicate_release'):before_release(child,initial)
        with monkeypatch.context() as patch:
            patch.chdir(cwd);patch.setattr(os,'environ',dict(sorted(environment.items())))
            patch.setattr(sys,'orig_argv',list(argv))
            w.execute(argv[-2],argv[-1])
        quiet=clock();calls.append('quiescent')
        commit=initial['commit'];available=(commit['limit_pages']-commit['committed_pages'])*commit['page_size_bytes']
        observed=asdict(w.process.TaskProcessObservation(expected_process_identity,pid,creation,0,'child_exited',
            (quiet-start)/1e9,1,available,tuple((v,free) for v,_,_,free in initial['volume_requirements']),
            (),None,('direct_child_exit_observed',),1,1,True))
        diagnostic=on_quiescent(observed);calls.append('inspected')
        if faults.get('duplicate_quiet'):on_quiescent(observed)
        out=dict(schema=proxy.SCHEMA,implementation=proxy.implementation_identity(),**child,
            observation=json.loads(w.io.encode(observed)),inspection=diagnostic,clock=w.sequence.timed.capture.clock_profile(),
            diagnostic_window=dict(start_ns=start,release_ns=released,quiescent_ns=quiet,end_ns=clock()),**proxy.FLAGS)
        if faults.get('observation_mismatch'):out['observation']['pid']+=1
        if faults.get('inspection_mismatch'):out['inspection']['data']['native_interval_ns']+=1
        return out
    proxy.run_job=run_job
    prep=load(canonical.preparation.__file__,'selector_parent_preparation_test_alias',monkeypatch)
    original_uuid=uuid.uuid4
    monkeypatch.setattr(uuid,'uuid4',lambda:SimpleNamespace(hex=faults['nonce']) if 'nonce' in faults else original_uuid())
    module=load(canonical.__file__,'selector_parent_controller_test_alias',monkeypatch,dict(
        h1_selector_launch_preparation_development_v2=prep,h1_selector_job_lifecycle_development_v2=proxy))
    options=dict(max_timing_archive_bytes=2**28,scratch_bytes=8*1024**2,parent_extra_commit_bytes=64*1024**2,
        commit_reserve_bytes=32*1024**2,disk_reserve_bytes=32*1024**2)
    raw=reference(context)
    return SimpleNamespace(module=module,context=context,raw=raw,options=options,root=tmp_path/'parent_non_authoritative',
        calls=calls,faults=faults,proxy=proxy,writes=writes)



def reference(c):
    return canonical.worker.snapshot.capture_reference(c.owner,c.config,max_archive_bytes=c.cap)
