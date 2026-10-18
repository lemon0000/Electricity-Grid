import pytest

from experiments import h1_historical_controller_development_v1 as m
from tests.test_rq2_v2_normal_obligation_controller_development_v1 import real,synthetic_controller
from tests.test_h1_timed_job_controller_development_v1 import install_launcher,step
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour


def inventory_root(tmp_path):
    root=tmp_path/'obligation';root.mkdir()
    for name in ('execution.lock','binding.json','000.binding.json','000.job.json','000.terminal.json'):
        (root/name).write_bytes(b'0')
    return root


@pytest.mark.parametrize('extra',[
    '001.job.json','001.terminal.json','002.binding.json','168.binding.json',
    '001.extra.json','0000.binding.json','\u0660\u0660\u0661.binding.json',
])
def test_obligation_namespace_rejects_gap_order_and_unbounded_names(tmp_path,extra):
    root=inventory_root(tmp_path);(root/extra).write_bytes(b'0')
    with pytest.raises(ValueError):m._obligation_inventory(root,1,{})


def test_obligation_namespace_append_and_identity_retention(tmp_path):
    root=inventory_root(tmp_path);seen={}
    m._obligation_inventory(root,1,seen)
    for kind in ('binding','job','terminal'):
        (root/f'001.{kind}.json').write_bytes(b'0');m._obligation_inventory(root,1,seen)
    p=root/'001.job.json';p.rename(tmp_path/'saved_job');p.write_bytes(b'0')
    with pytest.raises(ValueError,match='replaced'):m._obligation_inventory(root,1,seen)


def test_obligation_namespace_rejects_hardlink(tmp_path):
    root=inventory_root(tmp_path)
    (root/'001.binding.json').hardlink_to(root/'000.binding.json')
    with pytest.raises(ValueError,match='single-link'):m._obligation_inventory(root,1,{})


def test_two_synthetic_jobs_historical_current_and_suffix_isolation(tmp_path,real,environment,synthetic_reports,monkeypatch):
    # The shared fixture deliberately replaces the source/catalog loaders.
    monkeypatch.setattr(m,'_source_paths',lambda d:({m.Path(d['config_path']),m.Path(d['upstream_root'])/'SHA256SUMS'},
        {m.Path(d['upstream_root'])}))
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=synthetic_controller(tmp_path/'historical_controller_non_authoritative',environment,real,monkeypatch)
    try:
        first=step(c,environment);one=c.last_obligation_observation
        args=dict(expected_binding_sha256=one.header_sha256,expected_terminal_sha256=one.terminal_sha256,completed_hours=1)
        legacy=m.old.inspect(c._lease.root,**args)
        fresh=m.inspect(c._lease.root,**args)
        assert all(fresh[k]==v for k,v in legacy.items())
        assert fresh['historical_job_clock_prefix_verified'] and fresh['parent_head']==first.head
        initial=m.prepare(c._lease.root,**args)
        # Exercise actual prepare wiring, not just the observation helper.
        target=c._lease.root/'clock_bridge_non_authoritative'/'000'/'terminal.json'
        held=tmp_path/'original_clock_terminal';replacement=tmp_path/'replaced_clock_terminal'
        replay=m._replay_prefix;calls=[]
        def replace_between(*a,**kw):
            result=replay(*a,**kw);calls.append(kw.get('_observed'))
            if len(calls)==1:
                raw=target.read_bytes();target.rename(held);target.write_bytes(raw)
            return result
        try:
            with monkeypatch.context() as patch:
                patch.setattr(m,'_replay_prefix',replace_between)
                with pytest.raises(ValueError,match='retained'):m.prepare(c._lease.root,**args)
        finally:
            if held.exists():target.rename(replacement);held.rename(target)
        reports,_=synthetic_next_hour(c._parent,environment,synthetic_reports)
        install_launcher(monkeypatch,tmp_path,reports,label='second')
        assert step(c,environment,1).completed_hours==2
        with pytest.raises(ValueError):m.old.inspect(c._lease.root,**args)
        # Bad unused suffix content is not consumed by historical replay.
        for p in (c.obligation_root/'001.terminal.json',c._lease.root/'job_001_non_authoritative'/'request.json',
                  c._lease.root/'clock_bridge_non_authoritative'/'001'/'terminal.json'):
            p.write_bytes(b'not historical evidence')
        original=m.io.read_stable
        def read(path,*a,**kw):
            path=m.Path(path)
            assert not (path.parent==c.obligation_root and path.name.startswith('001.'))
            assert 'job_001_non_authoritative' not in path.parts
            assert not (path.parent.name=='001' and path.parent.parent.name=='clock_bridge_non_authoritative')
            return original(path,*a,**kw)
        monkeypatch.setattr(m.io,'read_stable',read)
        final=m.prepare(c._lease.root,**args)
        assert final.decision.decision_bytes==initial.decision.decision_bytes
        assert final.audit_payload==initial.audit_payload
        audit=m.current.json.loads(final.audit_payload)
        assert not audit['historical_controller']['suffix_chain_verified']
        assert not audit['formal_execution_ready'] and not audit['formal_result']
        for relative in (
            'obligation_non_authoritative/binding.json',
            'obligation_non_authoritative/000.job.json',
            'obligation_non_authoritative/000.binding.json',
            'job_000_non_authoritative/request.json',
            'clock_bridge_non_authoritative/000/terminal.json',
            'source_parent_non_authoritative/hour_000_non_authoritative/reference.json',
            'source_parent_non_authoritative/parent_events_non_authoritative/001/metadata.bin',
            'source_parent_non_authoritative/parent_anchor_non_authoritative/001.json',
        ):
            p=c._lease.root/relative;raw=p.read_bytes();p.write_bytes(b'bad prefix')
            try:
                with pytest.raises((ValueError,KeyError)):m.inspect(c._lease.root,**args)
            finally:p.write_bytes(raw)
    finally:c.close()


@pytest.mark.parametrize('relative',[
    'source_parent_non_authoritative/parent_events_non_authoritative/001/metadata.bin',
    'source_parent_non_authoritative/parent_anchor_non_authoritative/001.json',
    'source_parent_non_authoritative/hour_000_non_authoritative/reference.json',
    'clock_bridge_non_authoritative/000/terminal.json',
    'job_000_non_authoritative/worker_result.json',
])
def test_prefix_observation_retains_same_byte_inode_across_calls(tmp_path,monkeypatch,relative):
    root=tmp_path/'controller_non_authoritative';root.mkdir()
    parent=root/'source_parent_non_authoritative'
    paths=[]
    for name in ('parent_events_non_authoritative','parent_anchor_non_authoritative'):
        paths += [parent/name/'header.json',parent/name/'execution.lock']
    paths += [parent/'parent_anchor_non_authoritative'/f'{i:03d}.json' for i in range(3)]
    paths += [parent/'parent_events_non_authoritative'/f'{i:03d}'/n for i in (1,2) for n in ('metadata.bin','payload.bin','commit.json')]
    paths += [parent/'hour_000_non_authoritative'/'reference.json',root/'clock_bridge_non_authoritative'/'binding.json']
    paths += [root/'clock_bridge_non_authoritative'/'000'/n for n in ('intent.json','job.json','terminal.json')]
    paths += [root/'job_000_non_authoritative'/'worker_result.json']
    for p in paths:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'0')
    monkeypatch.setattr(m.base.parent,'job_view',lambda p,n:m.history._read_single(p/'worker_result.json',100))
    observed={};m._observe_prefix(observed,root,1,3)
    p=root/relative;p.rename(tmp_path/'original_evidence');p.write_bytes(b'0')
    with pytest.raises(ValueError,match='retained observation'):m._observe_prefix(observed,root,1,3)


def test_source_observation_rejects_same_bytes_replacement(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir();p=root/'config';p.write_bytes(b'0')
    monkeypatch.setattr(m,'_source_paths',lambda d:({p},{root}))
    observed={};m._observe_sources(observed,{})
    p.rename(tmp_path/'old_config');p.write_bytes(b'0')
    with pytest.raises(ValueError,match='retained observation'):m._observe_sources(observed,{})


def test_frozen_source_support_inventory_is_rebuilt(real):
    _,_,config,origin,_=real
    declaration=dict(config_path=config['config_path'],upstream_root=config['upstream_root'],origin=m.asdict(origin))
    files,directories=m._source_paths(declaration)
    assert len(files)>20 and all(p.is_file() for p in files)
    assert all(p.is_dir() for p in directories)
    observed={};m._observe_sources(observed,declaration);m._observe_sources(observed,declaration)
