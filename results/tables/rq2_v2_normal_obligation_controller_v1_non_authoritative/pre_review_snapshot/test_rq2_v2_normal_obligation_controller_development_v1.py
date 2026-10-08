from contextlib import contextmanager
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path

import pytest

from experiments import rq2_v2_normal_obligation_controller_development_v1 as m
from tests.test_h1_timed_job_controller_development_v1 import install_launcher,step
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour


@pytest.fixture(scope='module')
def real():
    b=m.binding
    resolver=b.open_manifest()
    axes=resolver.data()['catalog']['axes']['training_ub']
    point={k:v[0] for k,v in axes.items()}
    point.update(power=axes['power'][8],workload=axes['workload'][17])
    ordinal=resolver.encode_coordinate('training_ub',point)
    config=json.loads((b.ROOT/'configs/rq2_normal_h1_calibration_v3.json').read_bytes())
    origin=b.source_binding.H1SourceDeclaration('training',192,408,20260822,b.SOURCE_CONFIG_PIN)
    source=b.source_binding.load_pinned_current(origin,config['upstream_root'],config_path=config['config_path'])
    return resolver,ordinal,config,origin,source


def make_real(root,real):
    resolver,ordinal,config,origin,source=real
    return m.Controller(root,source.network,m.binding.snapshot.old.Rq2SolverSpec(**config['work']['specification']),
        m.base.old.replay.H1HourReplayLimits(232,891,1272),resolver=resolver,family='training_ub',ordinal=ordinal,
        origin=origin,upstream_root=config['upstream_root'],config_path=config['config_path'],dc_bus=config['dc_bus'],
        hours=168,budget=m.base.old.process.TaskProcessBudget(300.,.05,512*1024**2,768*1024**2,2.))


@dataclass
class FakeInitial:
    test_only: bool=True


def fake_suspended_child(monkeypatch,c,fault,events):
    """Test release interception only: no process, Job, worker or result."""
    @contextmanager
    def child(argv,**kwargs):
        events.append('entered')
        path=Path(argv[-2])
        if fault=='request':
            raw=path.read_bytes();stamp=path.stat()
            path.write_bytes(raw.replace(b'owned_timed_hour_development',b'owned_timed_hour_developmenX'))
            os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        if fault=='binding':
            path=c.obligation_root/'000.binding.json';raw=path.read_bytes();stamp=path.stat()
            path.write_bytes(raw.replace(b'normal_environment_prerequisite',b'Normal_environment_prerequisite',1))
            os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        class Child:
            pid=123
            creation_filetime=456
            initial_observation=FakeInitial()
            def release(self):
                events.append('released')
                raise RuntimeError('TEST_RELEASE_REACHED')
        yield Child()
    monkeypatch.setattr(m.base.old.process,'normal_task_child',child)
    monkeypatch.setattr(m.base.old,'_validate_initial',lambda *a:None)


@pytest.mark.parametrize('fault',['none','request','binding'])
def test_real_source_gate_at_existing_child_release(tmp_path,real,monkeypatch,fault):
    c=make_real(tmp_path/'real_release_non_authoritative',real);events=[]
    fake_suspended_child(monkeypatch,c,fault,events)
    try:
        head=c.inspect().head
        with pytest.raises((RuntimeError,ValueError)) as error:
            c.step(expected_source_identity=real[-1].identity,expected_head=head)
        assert events==(['entered','released'] if fault=='none' else ['entered'])
        if fault=='none':assert 'TEST_RELEASE_REACHED' in str(error.value)
        assert c._parent._journal.inspect().events==1
        assert c._parent._poisoned and c._clock_poisoned and c._active_request is None
        assert not (c._lease.root/'job_000_non_authoritative/worker_result.json').exists()
        with pytest.raises(ValueError):c.step(expected_source_identity=real[-1].identity,expected_head=head)
        assert events==(['entered','released'] if fault=='none' else ['entered'])
    finally:c.close()


@pytest.mark.parametrize('fault',['prevalidation','binding_before','binding_after','fixed_ordinal'])
def test_failures_before_release_preserve_intent_and_poison(tmp_path,real,monkeypatch,fault):
    c=make_real(tmp_path/'early_fault_non_authoritative',real);events=[]
    fake_suspended_child(monkeypatch,c,'none',events)
    try:
        head=c.inspect().head
        if fault=='prevalidation':
            def fail(*a,**kw):raise ValueError('test source prevalidation')
            monkeypatch.setattr(m.binding,'prevalidate_enrollment',fail)
        elif fault=='fixed_ordinal':c._obligation_ordinal+=1
        else:
            original=c._save_obligation
            def save(path,value):
                if path.name=='000.binding.json':
                    if fault=='binding_after':original(path,value)
                    raise OSError('test binding confirmation')
                return original(path,value)
            monkeypatch.setattr(c,'_save_obligation',save)
        with pytest.raises((ValueError,OSError)):
            c.step(expected_source_identity=real[-1].identity,expected_head=head)
        assert events==[]
        assert c._parent._journal.inspect().events==(0 if fault in ('prevalidation','fixed_ordinal') else 1)
        assert c._parent._poisoned and c._clock_poisoned
        with pytest.raises(ValueError):c.step(expected_source_identity=real[-1].identity,expected_head=head)
    finally:c.close()


def test_outer_guard_and_full_horizon(tmp_path,real):
    for bad in (1,167,169,True):
        with pytest.raises(ValueError,match='168-hour'):m.Controller(hours=bad,resolver=real[0],family='training_ub',ordinal=real[1])
    assert m.additional_content_bound(168)['files']==506
    c=make_real(tmp_path/'guard_non_authoritative',real)
    try:
        assert c._obligation_guard.acquire(False)
        try:
            for call in (c.inspect,c.close,lambda:c.step(expected_source_identity='1'*64,expected_head='2'*64)):
                with pytest.raises(ValueError,match='active'):call()
        finally:c._obligation_guard.release()
        assert c.inspect().status=='ready' and not c._parent._poisoned
    finally:c.close()


def synthetic_controller(root,env,real,monkeypatch):
    """Test-only source/catalog seam; never evidence of real RTS acceptance."""
    resolver,ordinal,*_=real
    node=resolver.resolve('training_ub',ordinal)
    enrollment=dict(test_only_synthetic_source=True)
    monkeypatch.setattr(m.binding,'precheck',lambda *a,**kw:node)
    monkeypatch.setattr(m.binding,'prevalidate_enrollment',lambda *a,**kw:enrollment)
    def bind(resolver,declaration,**kw):
        owner=m.binding.snapshot.open_snapshot(declaration,expected_parent_identity=kw['expected_parent_identity'],
            expected_anchor_record=kw['expected_anchor_record'])
        try:item=owner.pending_input(**kw['pending_arguments'])
        finally:owner.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        from dataclasses import asdict
        req=dict(parent_declaration=declaration,pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,budget=asdict(kw['job_budget']))
        return m._historical_binding(item.packet,req,node,enrollment)
    monkeypatch.setattr(m.binding,'bind',bind)
    upstream,config,origin,state=env
    return m.Controller(root,m.base.parent.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        m.base.old.replay.H1HourReplayLimits(3,100,500),resolver=resolver,family='training_ub',ordinal=ordinal,
        origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,hours=168,
        budget=m.base.old.process.TaskProcessBudget(300.,.05,512*1024**2,768*1024**2,2.))


def test_synthetic_two_hour_carry_and_historical_replay(tmp_path,real,environment,synthetic_reports,monkeypatch):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=synthetic_controller(tmp_path/'synthetic_controller_non_authoritative',environment,real,monkeypatch)
    try:
        first=step(c,environment)
        assert first.completed_hours==1
        reports,_=synthetic_next_hour(c._parent,environment,synthetic_reports)
        install_launcher(monkeypatch,tmp_path,reports,label='second')
        last=step(c,environment,1)
        assert last.completed_hours==2
        header=m.io.digest((c.obligation_root/'binding.json').read_bytes())
        terminal=c._obligation_previous
        result=m.inspect(c._lease.root,expected_binding_sha256=header,expected_terminal_sha256=terminal,completed_hours=2)
        assert result['historical_parent_prefix_verified'] and not result['live_release_authenticated']
        assert not result['worker_obligation_authenticated'] and not result['formal_result']
        path=c.obligation_root/'000.binding.json';raw=path.read_bytes()
        path.write_bytes(raw.replace(b'normal_environment_prerequisite',b'Normal_environment_prerequisite',1))
        with pytest.raises(ValueError):m.inspect(c._lease.root,expected_binding_sha256=header,expected_terminal_sha256=terminal,completed_hours=2)
    finally:c.close()


@pytest.mark.parametrize('fault',['job_before','job_after','terminal_before','terminal_after'])
def test_synthetic_result_publication_failure_has_no_completion_or_retry(tmp_path,real,environment,synthetic_reports,monkeypatch,fault):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=synthetic_controller(tmp_path/'publication_non_authoritative',environment,real,monkeypatch)
    original=c._save_obligation
    def save(path,value):
        if path.name==('000.job.json' if fault.startswith('job') else '000.terminal.json'):
            if fault.endswith('after'):original(path,value)
            raise OSError('test publication confirmation')
        return original(path,value)
    monkeypatch.setattr(c,'_save_obligation',save)
    try:
        with pytest.raises(OSError,match='publication'):step(c,environment)
        assert c._parent._journal.inspect().events==(1 if fault.startswith('job') else 2)
        assert (c._lease.root/'job_000_non_authoritative/worker_result.json').exists()
        assert c.last_observation is None and c._parent._poisoned and c._clock_poisoned
        with pytest.raises(ValueError):c.step(expected_source_identity='1'*64,expected_head='2'*64)
        assert not (c._lease.root/'job_001_non_authoritative').exists()
    finally:c.close()
