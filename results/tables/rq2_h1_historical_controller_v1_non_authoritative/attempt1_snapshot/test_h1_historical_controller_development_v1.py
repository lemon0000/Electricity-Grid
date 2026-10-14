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
        p=c.obligation_root/'000.job.json';p.write_bytes(b'bad prefix')
        with pytest.raises(ValueError):m.inspect(c._lease.root,**args)
    finally:c.close()
