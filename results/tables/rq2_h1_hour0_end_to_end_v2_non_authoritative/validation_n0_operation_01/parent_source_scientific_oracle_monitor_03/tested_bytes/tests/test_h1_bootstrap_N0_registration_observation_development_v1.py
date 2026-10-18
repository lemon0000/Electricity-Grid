"""Zero-Job protocol seams for evidence drift across terminal retention."""
from pathlib import Path

import pytest

from tests.test_h1_bootstrap_N0_registration_development_v1 import m, example, setup, protocol


@pytest.mark.parametrize('where',['local_observation','global_observation','local_replay'])
def test_terminal_retention_rechecks_same_observations_and_numerical_body(protocol,monkeypatch,where):
    s,d=protocol;marker=['before'];calls=[]
    observe=m.BootstrapOwner._observe_N0;build=m.BootstrapOwner._build_N0_terminal
    def observed(owner,root,declaration,views):
        observe(owner,root,declaration,views)
        m.historical._observe(views,'test_only_retention_marker',marker[0])
    def built(owner,claim_head,claim,release_head,ready,local_release,views,check):
        observed(owner,None,None,views)
        body=build(owner,claim_head,claim,release_head,ready,local_release,views,check)
        calls.append(1)
        if where=='local_replay' and marker[0]=='after':body['child_archive_identity']='1'*64
        return body
    monkeypatch.setattr(m.BootstrapOwner,'_observe_N0',observed)
    monkeypatch.setattr(m.BootstrapOwner,'_build_N0_terminal',built)
    def retain(root,before,after):
        result=s.retain(root,before,after)
        target=o._global.root if where=='global_observation' else o._bootstrap.root
        sequence=3 if where=='global_observation' else 5
        if Path(root)==target and (target/f'{sequence:020d}.json').exists():
            marker[0]='after'
        return result
    # In the replay-body seam the observed file view itself remains unchanged;
    # only the second numerical body's archive identity diverges.
    if where=='local_replay':
        def stable_observed(owner,root,declaration,views):observe(owner,root,declaration,views)
        observed=stable_observed
        monkeypatch.setattr(m.BootstrapOwner,'_observe_N0',observed)
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        match='N0 evidence changed after local retention' if where=='local_replay' else 'retained observation changed'
        with pytest.raises(ValueError,match=match):o.bootstrap()
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==5
        assert len(list(o._global.root.glob('[0-9]*.json')))==(3 if where=='global_observation' else 2)
        assert not list(Path(o.roots['controller']).glob('job_*'))
        if where=='local_replay':assert len(calls)>=2
    finally:o.close()
