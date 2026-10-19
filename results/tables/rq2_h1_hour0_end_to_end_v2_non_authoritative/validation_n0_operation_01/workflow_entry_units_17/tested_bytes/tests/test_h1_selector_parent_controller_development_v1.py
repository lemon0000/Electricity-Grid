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

from experiments import h1_selector_parent_controller_development_v1 as canonical
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
        h1_selector_launch_preparation_development_v1=prep,h1_selector_job_lifecycle_development_v1=proxy))
    options=dict(max_timing_archive_bytes=2**28,scratch_bytes=8*1024**2,parent_extra_commit_bytes=64*1024**2,
        commit_reserve_bytes=32*1024**2,disk_reserve_bytes=32*1024**2)
    raw=reference(context)
    return SimpleNamespace(module=module,context=context,raw=raw,options=options,root=tmp_path/'parent_non_authoritative',
        calls=calls,faults=faults,proxy=proxy,writes=writes)


def test_create_persists_binding_before_worker_and_close_preserves_files(harness):
    h=harness;m=h.module
    with m.Parent(h.root,h.raw,**h.options) as owner:
        assert h.calls==[] and owner._state=='prepared'
        assert set(p.name for p in h.root.iterdir())=={'binding.json','execution.lock','worker_non_authoritative'}
        assert set(p.name for p in owner.worker_root.iterdir())=={'request.json','selector_snapshot.json','launch.json','scratch_non_authoritative'}
        doc=json.loads((h.root/'binding.json').read_bytes())
        assert doc['implementation']==m.implementation_identity()
        assert not any(doc[k] for k in m.FLAGS)
        assert doc['declaration']['implementation']==m.preparation.implementation_identity()
        assert m.preparation.__name__!=canonical.preparation.__name__
        owner._lease.check()
        files={p:p.read_bytes() for p in h.root.rglob('*') if p.is_file() and p.name!='execution.lock'}
    assert all(p.read_bytes()==raw for p,raw in files.items())
    assert (h.root/'execution.lock').read_bytes()==b'0'
    with pytest.raises(ValueError):owner.run()
    with pytest.raises(FileExistsError):m.Parent(h.root,h.raw,**h.options)
    assert h.calls==[]


def test_reference_parent_issues_only_after_joint_terminal_and_replays(harness):
    h=harness;m=h.module
    with m.Parent(h.root,h.raw,**h.options) as owner:
        receipt=owner.run()
        assert h.calls==['acquire','release','quiescent','inspected']
        assert type(receipt) is m.ParentCompletion and owner._issued is receipt
        terminal=json.loads((h.root/'terminal.json').read_bytes())
        assert receipt.terminal_sha256==m.io.digest((h.root/'terminal.json').read_bytes())
        assert receipt.scientific_terminal_sha256==terminal['lifecycle']['inspection']['data']['scientific_terminal_sha256']
        science=json.loads((Path(receipt.scientific_root)/'terminal.json').read_bytes())
        assert receipt.scientific_request_sha256==science['request_sha256']
        assert receipt.scientific_request_sha256!=receipt.sequence_request_sha256
        assert terminal['request_keys']==dict(scientific_request_sha256=receipt.scientific_request_sha256,
            sequence_request_sha256=receipt.sequence_request_sha256)
        assert terminal['lifecycle']['schema']==h.proxy.SCHEMA!=canonical.lifecycle.SCHEMA
        assert terminal['lifecycle']['implementation']!=canonical.lifecycle.implementation_identity()
        assert not any(terminal[k] for k in m.FLAGS)
        owner.validate_completion(receipt)
        forged=object.__new__(m.ParentCompletion)
        for name in m._COMPLETION_FIELDS:object.__setattr__(forged,name,getattr(receipt,name))
        with pytest.raises(ValueError):owner.validate_completion(forged)
        with pytest.raises(TypeError):m.ParentCompletion(tuple(getattr(receipt,k) for k in m._COMPLETION_FIELDS))
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(ValueError):pool.submit(owner.validate_completion,receipt).result()
        with pytest.raises(TypeError):canonical.Parent.validate_completion(owner,receipt)
        for f in (copy,deepcopy,pickle.dumps):
            with pytest.raises(TypeError):f(receipt)
        with pytest.raises(ValueError):owner.run()
        owner.validate_completion(receipt)
    with pytest.raises(ValueError):owner.validate_completion(receipt)


@pytest.mark.parametrize('fault',['before_worker','duplicate_release','duplicate_quiet',
    'observation_mismatch','inspection_mismatch'])
def test_failed_attempt_never_issues_completion_or_retries(harness,fault):
    h=harness;m=h.module;h.faults[fault]=True
    with m.Parent(h.root,h.raw,**h.options) as owner:
        with pytest.raises((ValueError,RuntimeError)):owner.run()
        assert owner._state=='failed' and owner._issued is None and owner._issued_bytes is None
        assert not (h.root/'terminal.json').exists()
        before=list(h.calls)
        with pytest.raises(ValueError):owner.run()
        assert h.calls==before
        assert (owner.worker_root/'release_intent.json').is_file()


def test_preflight_invalid_budget_has_no_parent_side_effects(harness):
    h=harness
    options=dict(h.options,scratch_bytes=-1)
    with pytest.raises(ValueError):h.module.Parent(h.root,h.raw,**options)
    assert not h.root.exists() and h.calls==[]


def test_actual_requires_live_reference_and_closing_reference_invalidates_completion(harness):
    h=harness;m=h.module;c=h.context
    with m.Parent(h.root,h.raw,**h.options) as reference_owner:
        receipt=reference_owner.run()
        raw=m.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
            reference_root=receipt.scientific_root,reference_terminal_sha256=receipt.scientific_terminal_sha256,
            reference_request_sha256=receipt.scientific_request_sha256,reference_max_archive_bytes=receipt.max_archive_bytes)
        actual_root=h.root.parent/'actual_parent_non_authoritative'
        with pytest.raises(TypeError):m.Parent(actual_root,raw,**h.options)
        assert not actual_root.exists()
        forged=object.__new__(m.ParentCompletion)
        for name in m._COMPLETION_FIELDS:object.__setattr__(forged,name,getattr(receipt,name))
        with pytest.raises(ValueError):m.Parent(actual_root,raw,**h.options,
            reference_owner=reference_owner,reference_completion=forged)
        assert not actual_root.exists()
        with m.Parent(actual_root,raw,**h.options,reference_owner=reference_owner,reference_completion=receipt) as owner:
            def locked():
                with pytest.raises(ValueError):reference_owner.close()
                with pytest.raises(ValueError):reference_owner.validate_completion(receipt)
            h.faults['after_release_hook']=locked
            actual=owner.run()
            assert actual.role=='actual'
            owner.validate_completion(actual)
            terminal=json.loads((owner.root/'terminal.json').read_bytes())
            assert terminal['reference_execution']['parent_terminal_sha256']==receipt.terminal_sha256
            assert json.loads(raw)['declaration']['reference']['terminal_sha256']==receipt.scientific_terminal_sha256
            h.faults['before_worker']=True
            failed_root=h.root.parent/'failed_actual_non_authoritative'
            with m.Parent(failed_root,raw,**h.options,reference_owner=reference_owner,reference_completion=receipt) as failed:
                with pytest.raises(RuntimeError,match='synthetic'):failed.run()
                assert failed._state=='failed' and failed._issued is None
                reference_owner.validate_completion(receipt)
            h.faults.clear()
            closed_root=h.root.parent/'closed_reference_actual_non_authoritative'
            waiting=m.Parent(closed_root,raw,**h.options,reference_owner=reference_owner,reference_completion=receipt)
            reference_owner.close()
            with pytest.raises(ValueError):owner.validate_completion(actual)
            before=list(h.calls)
            try:
                with pytest.raises(ValueError):waiting.run()
                assert waiting._state=='failed' and waiting._issued is None and h.calls==before
            finally:waiting.close()


@pytest.mark.parametrize('name',['binding.json','worker_non_authoritative/selector_snapshot.json',
    'worker_non_authoritative/request.json','worker_non_authoritative/launch.json'])
@pytest.mark.parametrize('when',['before','after'])
def test_constructor_write_failure_preserves_partial_root_and_rejects_retry(harness,name,when):
    h=harness;m=h.module;h.faults['write']=(name,when)
    with pytest.raises(OSError,match='synthetic'):m.Parent(h.root,h.raw,**h.options)
    assert h.calls==[] and (h.root/name).exists()==(when=='after')
    assert h.writes[0]=='binding.json' and not m._OWNERS
    assert (h.root/'execution.lock').read_bytes()==b'0'
    files={p:p.read_bytes() for p in h.root.rglob('*') if p.is_file()}
    h.faults.clear()
    with pytest.raises(FileExistsError):m.Parent(h.root,h.raw,**h.options)
    assert all(p.read_bytes()==raw for p,raw in files.items())


@pytest.mark.parametrize('name',['worker_non_authoritative/initial_observation.json',
    'worker_non_authoritative/child.json','worker_non_authoritative/release_intent.json','terminal.json'])
@pytest.mark.parametrize('when',['before','after'])
def test_run_write_failure_is_terminal_even_after_terminal_publication(harness,name,when):
    h=harness;m=h.module
    with m.Parent(h.root,h.raw,**h.options) as owner:
        h.faults['write']=(name,when)
        with pytest.raises(OSError,match='synthetic'):owner.run()
        assert owner._state=='failed' and owner._issued is None
        assert (h.root/name).exists()==(when=='after')
        assert ('release' in h.calls)==(name=='terminal.json')
        before=list(h.calls)
        with pytest.raises(ValueError):owner.run()
        assert h.calls==before


@pytest.mark.parametrize('fault',['metadata_replace','extra_parent','extra_worker','nonce_collision'])
def test_prepared_owner_integrity_and_registry_collision(harness,fault):
    h=harness;m=h.module
    with m.Parent(h.root,h.raw,**h.options) as owner:
        if fault=='nonce_collision':
            h.faults['nonce']=owner._nonce
            other=h.root.parent/'other_parent_non_authoritative'
            for _ in range(2):
                with pytest.raises(ValueError,match='nonce'):m.Parent(other,h.raw,**h.options)
                assert not other.exists() and m._OWNERS[owner._nonce] is owner
                owner._check()
            # A failed foreign object must not remove this owner's entry on close.
            foreign=object.__new__(m.Parent)
            for name in m.Parent.__slots__:setattr(foreign,name,getattr(owner,name))
            foreign._state='failed'
            with pytest.raises(ValueError,match='registered'):foreign.close()
            assert owner._lease.locked and owner._lease.stream is not None
            assert m._OWNERS[owner._nonce] is owner
            owner._check()
            return
        if fault=='metadata_replace':
            path=h.root/'binding.json';replacement=h.root.parent/'replacement.json'
            replacement.write_bytes(path.read_bytes());os.replace(replacement,path)
        elif fault=='extra_parent':(h.root/'extra.json').write_bytes(b'{}')
        else:(owner.worker_root/'extra.json').write_bytes(b'{}')
        with pytest.raises(ValueError):owner.run()
        assert h.calls==[] and owner._issued is None


@pytest.mark.parametrize('at_callback',[False,True])
@pytest.mark.parametrize('fault',['fixed','flags','helper'])
def test_original_scope_rejects_coordinated_replacement(harness,monkeypatch,at_callback,fault):
    h=harness;m=h.module
    def change():
        if fault=='fixed':
            monkeypatch.setattr(m,'_FIXED',())
            monkeypatch.setattr(m,'_CHECK',lambda:None)
            monkeypatch.setattr(m,'_IDENTITY',lambda:owner._own)
        elif fault=='flags':
            flags=dict(m.FLAGS,synthetic_extra=False)
            for key,value in [('FLAGS',flags),('_FLAGS',flags),('_KEYS',frozenset(flags))]:monkeypatch.setattr(m,key,value)
        else:monkeypatch.setattr(m,'get_ident',lambda:owner._thread)
    with m.Parent(h.root,h.raw,**h.options) as owner:
        original=m.Parent.run
        if at_callback:h.faults['before_release_hook']=change
        else:change()
        with pytest.raises(ValueError):original(owner)
        assert 'release' not in h.calls and owner._issued is None


def test_canonical_parent_rejects_alias_source_before_side_effects(harness):
    h=harness
    with pytest.raises(ValueError):canonical.Parent(h.root,h.raw,**h.options)
    assert not h.root.exists() and h.calls==[]


@pytest.mark.parametrize('kind',['science','timing'])
def test_same_byte_archive_replacement_invalidates_live_completion(harness,kind):
    h=harness;m=h.module
    with m.Parent(h.root,h.raw,**h.options) as owner:
        receipt=owner.run()
        path=owner.worker_root/('science_sequence_non_authoritative' if kind=='science' else 'timing_sequence_non_authoritative')/'binding.json'
        replacement=h.root.parent/'replacement.json';replacement.write_bytes(path.read_bytes())
        os.replace(replacement,path)
        with pytest.raises(ValueError):owner.validate_completion(receipt)


def test_canonical_borrowed_methods_reject_foreign_self_without_dependency_drift(tmp_path):
    canonical.preparation._CHECK()
    calls=[]
    fake=SimpleNamespace(_enter=lambda:calls.append('enter'),_validate=lambda *a:calls.append('validate'),
        _reference_owner=None,_reference_held=False,
        _guard=SimpleNamespace(acquire=lambda **kw:calls.append('acquire') or True,release=lambda:calls.append('release')))
    for name,args in [('run',()),('validate_completion',(object(),)),('__enter__',()),
                      ('__init__',(tmp_path/'foreign_non_authoritative',b'{}')),('close',()),('__exit__',())]:
        with pytest.raises(TypeError,match='exact'):
            getattr(canonical.Parent,name)(fake,*args)
    class Derived(canonical.Parent):pass
    with pytest.raises(TypeError,match='exact'):
        Derived(tmp_path/'derived_non_authoritative',b'{}')
    assert calls==[] and not list(tmp_path.iterdir())
    canonical.preparation._CHECK()


@pytest.mark.parametrize('during_constructor',[False,True])
def test_captured_cleanup_survives_callback_replacement(harness,monkeypatch,during_constructor):
    h=harness;m=h.module;registry=m._OWNERS
    saved={};calls=[]
    def change():
        if saved:return
        saved['owner']=next(iter(registry.values()));saved['lease']=saved['owner']._lease
        patch.setattr(m.Parent,'close',lambda *a:calls.append('fake_close'))
        patch.setattr(m.Parent,'__exit__',lambda *a:calls.append('fake_exit'))
        patch.setattr(m.local._Lease,'close',lambda *a:calls.append('fake_lease_close'))
        patch.setattr(m,'_OWNERS',{})
        patch.setattr(m,'_REGISTRY_LOCK',SimpleNamespace())
        patch.setattr(m,'get_ident',lambda:-1)
    with monkeypatch.context() as patch:
        # Restore the patched shared Lease before the source fixture tears down.
        if during_constructor:
            h.faults['write_hook']=change
            with pytest.raises(ValueError):m.Parent(h.root,h.raw,**h.options)
        else:
            with pytest.raises(ValueError):
                with m.Parent(h.root,h.raw,**h.options) as owner:
                    h.faults['before_release_hook']=change
                    owner.run()
        assert calls==[] and registry=={}
        assert saved['owner']._state=='closed'
        assert saved['lease'].stream is None and not saved['lease'].locked
        assert (h.root/'execution.lock').read_bytes()==b'0'
    h.faults.clear()
    with pytest.raises(FileExistsError):m.Parent(h.root,h.raw,**h.options)
