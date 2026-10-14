"""Source-backed declarations; isolated import probe never executes a solver."""
from dataclasses import asdict
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from experiments import h1_selector_launch_preparation_development_v1 as m
canonical=m
from tests.test_h1_selector_input_snapshot_development_v1 import context,case,setup,legacy_setup,reference,archive


@pytest.fixture
def no_solver(monkeypatch):
    # Apply the existing deny fixture only to source-dependent tests. Clean
    # canonical scope tests must see the original callable inventory.
    from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver as protect
    protect.__wrapped__(monkeypatch)


def load_alias(monkeypatch,name):
    spec=importlib.util.spec_from_file_location(name,canonical.__file__)
    alias=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,alias);spec.loader.exec_module(alias)
    return alias


@pytest.fixture
def source_module(context,monkeypatch):
    # Synthetic source helpers cannot satisfy canonical import-fixed closure.
    # Only an explicitly distinct, read-only diagnostic module sees those seams.
    alias=load_alias(monkeypatch,'selector_launch_synthetic_test_alias')
    monkeypatch.setattr(sys.modules[__name__],'m',alias)
    return alias


@pytest.fixture
def prepared(context,tmp_path,source_module):
    root=tmp_path/"parent 'quoted' 中文_non_authoritative"
    raw=reference(context)
    options=dict(max_timing_archive_bytes=2**28,scratch_bytes=8*1024**2,
        parent_extra_commit_bytes=64*1024**2,commit_reserve_bytes=32*1024**2,disk_reserve_bytes=32*1024**2)
    return root,raw,options


def directories(root):
    (root/'worker_non_authoritative'/'scratch_non_authoritative').mkdir(parents=True)


def test_prepare_and_bind_rebuild_source_and_preserve_role_budget(prepared,context):
    root,raw,options=prepared
    data=m.prepare(root,raw,**options);doc=json.loads(data)
    assert not root.exists()
    assert doc['request']['budget']==asdict(context.config.reference_job_budget)
    assert doc['argv'][:4]==[str(Path(sys.executable).resolve()),'-I','-B','-c']
    assert doc['argv'][4]==m._SCRIPT and str(root) not in m._SCRIPT
    assert doc['argv'][5]==str(m._REPO)
    assert doc['argv'][-2:]==[str(root/'worker_non_authoritative'/'request.json'),doc['request_sha256']]
    assert set(doc['environment'])==set(m.worker.runtime.development_environment())
    assert not any(doc[k] for k in m.FLAGS)
    assert doc['host']['additional_commit_bytes']==context.config.reference_job_budget.max_job_commit_bytes+options['parent_extra_commit_bytes']
    demands=doc['host']['directories']
    assert [d['additional_bytes'] for d in demands]==[
        m.worker.content_bound(doc['request']),options['scratch_bytes'],m.PARENT_BYTES]
    with pytest.raises(ValueError):m.bind(data,raw)
    assert not root.exists()
    directories(root)
    launch=json.loads(m.bind(data,raw))
    assert set(launch)=={'request_sha256','process_identity','argv','cwd','environment_sha256','budget','host'}
    assert launch['request_sha256']==doc['request_sha256']
    assert launch['argv']==doc['argv'] and launch['budget']==doc['request']['budget']
    host=m.resources.HostResourceBudget(doc['host']['additional_commit_bytes'],doc['host']['commit_reserve_bytes'],
        tuple(m.resources.DirectoryDemand(**d) for d in demands))
    observation=m.resources.observe_headroom(host,expected_request_identity=m.resources.resource_identity(host))
    # Same-volume demands sum, while the reserve is the maximum, not triple-counted.
    assert len(observation.volume_requirements)==1
    _,total,reserve,_=observation.volume_requirements[0]
    assert total==sum(d['additional_bytes'] for d in demands)
    assert reserve==options['disk_reserve_bytes']
    assert list(root.rglob('*.json'))==[]


@pytest.mark.parametrize('field',['scratch_bytes','parent_extra_commit_bytes','commit_reserve_bytes','disk_reserve_bytes'])
def test_resource_preflight_rejects_invalid_values_before_side_effects(prepared,field):
    root,raw,options=prepared
    for bad in (0,-1,True,1.5,2**63):
        with pytest.raises(ValueError,match='resource bytes'):m.prepare(root,raw,**dict(options,**{field:bad}))
        assert not root.exists()


def test_bind_rejects_rehashed_declaration_changes(prepared):
    root,raw,options=prepared
    data=m.prepare(root,raw,**options);directories(root)
    mutations=(lambda d:d['argv'].__setitem__(4,'print(1)'),
        lambda d:d['argv'].__setitem__(5,str(root)),
        lambda d:d['environment'].__setitem__('GOOGLE_API_KEY','synthetic-test-value'),
        lambda d:d.__setitem__('executable_sha256','0'*64),
        lambda d:d.__setitem__('request_sha256','0'*64),
        lambda d:d['request']['budget'].__setitem__('max_elapsed_seconds',1),
        lambda d:d['host'].__setitem__('additional_commit_bytes',1),
        lambda d:d.__setitem__('native_execution_authorized',True))
    for change in mutations:
        doc=json.loads(data);change(doc)
        with pytest.raises(ValueError,match='declaration differs'):m.bind(m.io.encode(doc),raw)
    assert list(root.rglob('*.json'))==[]


def test_preinstalled_worker_replacement_rejected(prepared,monkeypatch):
    root,raw,options=prepared
    original=m.worker.request_document
    monkeypatch.setattr(m.worker,'request_document',lambda *a,**k:original(*a,**k))
    with pytest.raises(ValueError,match='scope changed'):m.prepare(root,raw,**options)
    assert not root.exists()


def test_executable_hardlinks_and_same_bytes_replacement(tmp_path):
    path=tmp_path/'python-fixture.exe';path.write_bytes(b'fake-executable-for-read-only-test')
    alias=tmp_path/'hardlink.exe';os.link(path,alias)
    raw,stamp=m._executable(alias)
    assert raw==path.read_bytes() and stamp[2]==2
    replacement=tmp_path/'replacement.exe';replacement.write_bytes(raw)
    os.replace(replacement,alias)
    after=m._executable(alias)
    assert after[0]==raw and after[1]!=stamp


def test_fresh_source_change_between_preparation_bookends(context,tmp_path,monkeypatch):
    root=tmp_path/'source_drift_non_authoritative';raw=reference(context)
    options=dict(max_timing_archive_bytes=2**28,scratch_bytes=2**20,
        parent_extra_commit_bytes=2**20,commit_reserve_bytes=2**20,disk_reserve_bytes=2**20)
    original=m.worker.snapshot._build;calls=[]
    def change(d):
        out=original(d);calls.append(True)
        if len(calls)==2:
            current=context.s.currents[0]
            object.__setattr__(current,'source_projection_audit_payload',current.source_projection_audit_payload+b' ')
        return out
    monkeypatch.setattr(m.worker.snapshot,'_build',change)
    alias=load_alias(monkeypatch,'selector_launch_source_drift_test_alias')
    with pytest.raises(ValueError):alias.prepare(root,raw,**options)
    assert len(calls)>=2 and not root.exists()


def test_flag_and_script_replacement_rejected(prepared,monkeypatch):
    root,raw,options=prepared
    for name,value in (('FLAGS',dict(m.FLAGS)),('_SCRIPT',m._SCRIPT+'print(1)\n')):
        with monkeypatch.context() as patch:
            patch.setattr(m,name,value)
            with pytest.raises(ValueError,match='scope changed'):m.prepare(root,raw,**options)
        assert not root.exists()


@pytest.mark.parametrize('helper',['projection','rebuild','build','fresh','configuration','resource','task_identity'])
def test_transitive_preinstalled_helpers_rejected(prepared,monkeypatch,helper):
    root,raw,options=prepared
    mapping={'projection':(m.worker,'_projection'),'rebuild':(m.worker.snapshot,'rebuild'),
        'build':(m.worker.snapshot,'_build'),'fresh':(m.worker.snapshot.phase,'_fresh'),
        'configuration':(m.worker.sequence,'_configuration'),
        'resource':(m.resources,'resource_identity'),'task_identity':(m.process,'task_process_identity')}
    owner,name=mapping[helper];original=getattr(owner,name)
    # Cache substitution is rejected even if its output would be unchanged.
    monkeypatch.setattr(owner,name,lambda *a,**k:original(*a,**k))
    with pytest.raises(ValueError,match='scope changed'):m.prepare(root,raw,**options)
    assert not root.exists()


def test_canonical_interpreter_preinstalled_replacement_rejected(tmp_path,monkeypatch):
    fake=tmp_path/'fake.exe';fake.write_bytes(b'ordinary-file')
    monkeypatch.setattr(sys,'executable',str(fake))
    root=tmp_path/'rejected_non_authoritative'
    with pytest.raises(ValueError,match='scope changed'):
        canonical.prepare(root,b'',max_timing_archive_bytes=2**28,scratch_bytes=1,
            parent_extra_commit_bytes=1,commit_reserve_bytes=1,disk_reserve_bytes=1)
    assert not root.exists()


def test_alias_is_distinct_and_canonical_rejects_synthetic_source(prepared):
    root,raw,options=prepared
    data=m.prepare(root,raw,**options);doc=json.loads(data)
    assert m.__name__!=canonical.__name__ and not any(doc[k] for k in m.FLAGS)
    with pytest.raises(ValueError,match='scope changed'):canonical.prepare(root,raw,**options)
    with pytest.raises(ValueError,match='scope changed'):canonical.bind(data,raw)
    assert not root.exists()


def test_alias_dependency_restore_invalidates_alias_and_its_declaration(monkeypatch):
    original=canonical.worker._projection
    with monkeypatch.context() as patch:
        patch.setattr(canonical.worker,'_projection',lambda *a,**k:original(*a,**k))
        alias=load_alias(patch,'selector_launch_restore_test_alias')
        pin=alias.implementation_identity()
        with pytest.raises(ValueError,match='scope changed'):canonical._verify()
    assert not [(getattr(owner,'__name__',''),name) for owner,name,original in canonical._SOURCE_FIXED
        if vars(owner).get(name) is not original]
    canonical._verify()
    assert canonical.implementation_identity()!=pin
    with pytest.raises(ValueError,match='scope changed'):alias._verify()
    forged=canonical.io.encode(dict(schema=canonical.SCHEMA,implementation=pin))
    with pytest.raises(ValueError,match='declaration implementation'):canonical.bind(forged,b'')


def test_executable_same_bytes_replaced_during_second_source_bookend(context,tmp_path,monkeypatch):
    raw=reference(context);root=tmp_path/'exe_drift_non_authoritative'
    fake=tmp_path/'fake.exe';fake.write_bytes(b'read-only-executable-fixture')
    replacement=tmp_path/'replacement.exe';replacement.write_bytes(fake.read_bytes())
    before=fake.stat().st_ino
    original=canonical.worker.snapshot._build;calls=[]
    def change(d):
        out=original(d);calls.append(True)
        if len(calls)==3:os.replace(replacement,fake)
        return out
    monkeypatch.setattr(canonical.worker.snapshot,'_build',change)
    monkeypatch.setattr(sys,'executable',str(fake))
    alias=load_alias(monkeypatch,'selector_launch_executable_drift_test_alias')
    with pytest.raises(ValueError,match='executable changed during launch preparation'):
        alias.prepare(root,raw,max_timing_archive_bytes=2**28,scratch_bytes=1,
            parent_extra_commit_bytes=1,commit_reserve_bytes=1,disk_reserve_bytes=1)
    assert len(calls)==4 and fake.stat().st_ino!=before and not root.exists()


def test_actual_uses_its_own_budget_and_remains_plain_declaration(context,monkeypatch,tmp_path,source_module):
    from dataclasses import replace
    config=replace(context.config,actual_job_budget=m.process.TaskProcessBudget(311,.05,512*1024**2,768*1024**2,2))
    context.config=config
    ref=archive(context,monkeypatch,tmp_path)
    raw=m.worker.snapshot.capture_actual(context.owner,config,max_archive_bytes=context.cap,lane_id='joint',**ref)
    # archive() installs its fabricated stage only for this synthetic source.
    alias=load_alias(monkeypatch,'selector_launch_actual_test_alias')
    root=tmp_path/'actual_parent_non_authoritative'
    doc=json.loads(alias.prepare(root,raw,max_timing_archive_bytes=2**28,scratch_bytes=2**20,
        parent_extra_commit_bytes=2**20,commit_reserve_bytes=2**20,disk_reserve_bytes=2**20))
    assert doc['request']['role']=='actual' and doc['request']['budget']['max_elapsed_seconds']==311
    assert not any(doc[k] for k in m.FLAGS) and not root.exists()


def test_isolated_fixed_script_imports_checkout_and_rejects_missing_request(tmp_path):
    # No synthetic source fixture: its deliberately substituted implementation
    # identity must not be accepted by a clean isolated interpreter.
    root=tmp_path/"parent 'quoted' 中文_non_authoritative";directories(root)
    scratch=root/'worker_non_authoritative'/'scratch_non_authoritative'
    environment=m.worker.runtime.development_environment()
    environment.update(TEMP=str(scratch),TMP=str(scratch))
    argv=[str(Path(sys.executable).resolve()),'-I','-B','-c',m._SCRIPT,str(m._REPO),
        m.worker.implementation_identity(),str(root/'worker_non_authoritative'/'request.json'),'0'*64]
    # A poisoned cwd import must not shadow the bound checkout under -I.
    (scratch/'experiments').mkdir()
    (scratch/'experiments'/'__init__.py').write_text("raise RuntimeError('CWD_SHADOW_IMPORTED')",encoding='utf-8')
    result=subprocess.run(argv,cwd=scratch,env=environment,capture_output=True,timeout=30)
    error=result.stderr.decode('utf-8',errors='replace')
    assert result.returncode!=0
    assert 'CWD_SHADOW_IMPORTED' not in error and 'ModuleNotFoundError' not in error
    assert 'implementation differs' not in error and 'import path differs' not in error
    assert 'h1_selector_released_worker_development_v1.py' in error
    assert 'FileNotFoundError' in error or 'selector root namespace differs' in error or 'directory' in error
    assert not (root/'worker_non_authoritative'/'consumed.json').exists()
    wrong=list(argv);wrong[6]='0'*64
    mismatch=subprocess.run(wrong,cwd=scratch,env=environment,capture_output=True,timeout=30)
    assert mismatch.returncode!=0 and b'selector worker implementation differs' in mismatch.stderr
    assert not (root/'worker_non_authoritative'/'consumed.json').exists()
