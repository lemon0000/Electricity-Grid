"""Complete synthetic N0 roster and common science replay.

Raw source rows and outage mechanism are explicit test inputs. Three short
Windows Jobs export saved synthetic reports through fake solver objects. The
historical, registry prepare, exact-current, roster and common readers are real.
This is not accepted RTS input, native execution or formal admission evidence.
"""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from experiments import h1_group_n0_common_input_binding_development_v1 as common
from experiments import h1_common_owner_genesis_development_v1 as genesis
from tests.test_h1_bootstrap_N0_registration_numerical_development_v1 import (
    numerical, setup, example, environment, supplied, no_solver, synthetic_reports,
    saved, m, retained)
from tests.test_h1_group_execution_roster_development_v1 import (
    cached_declarations, declaration, roster)

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='synthetic Windows Jobs')


def complete_source_rows(mp):
    source=common.phase.source.source
    original=source.windows.load_source_window
    def load(kind,*args,**kwargs):
        value=original(kind,*args,**kwargs)
        value['chain']['chain_id']='test-only-synthetic-'+kind
        if kind=='power':
            value['rows'][0].update(block_id='synthetic',active_event_id='',
                active_component_type='',active_component_uid='')
        else:value['chain']['trace_identity_basis']={'source':'synthetic integration fixture'}
        value.pop('window_identity')
        value['window_identity']=source.windows._hash(value)
        return value
    mp.setattr(source.windows,'load_source_window',load)


def child_main(base,raw_root,path,pin):
    from tests.test_h1_saved_job_development_v1 import install_child_source
    from tests.test_h1_timed_worker_hour_development_v1 import install,RealClockSyntheticDirect
    from tests.test_h1_timed_job_controller_development_v1 import api
    mp=install_child_source(Path(base))
    no_solver.__wrapped__(mp)
    complete_source_rows(mp)
    reports=[(Path(raw_root)/f'{i:03d}.bin').read_bytes() for i in range(3)]
    solvers=install(mp,Path(path).parent/'worker_non_authoritative',reports)
    api.entry.execute(path,pin)
    assert len(solvers)==3 and all(type(s) is RealClockSyntheticDirect for s in solvers)
    assert [s.apply_calls for s in solvers]==[1,1,1]


@pytest.fixture
def complete_group(numerical,environment,synthetic_reports,cached_declarations,tmp_path,monkeypatch):
    s,d,captured=numerical
    complete_source_rows(monkeypatch)
    source=common.phase.source.source;registry=common.phase.source.registry
    monkeypatch.setattr(source.rts,'load_rts_gmlc_chronological_data',lambda root:environment[3]['data'])
    # The inherited loader's one-episode assertion is intentionally absent here.
    original_load=m.BootstrapOwner._load_network
    def static_then_current(self):
        monkeypatch.setattr(source.rts,'load_rts_gmlc_chronological_data',lambda root:environment[3]['data'])
        return original_load(self)
    monkeypatch.setattr(m.BootstrapOwner,'_load_network',static_then_current)
    raw_root=tmp_path/'group_reports';raw_root.mkdir()
    for i,raw in enumerate(synthetic_reports):(raw_root/f'{i:03d}.bin').write_bytes(raw)
    dependency=str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
    from tests.test_h1_timed_job_controller_development_v1 import api
    code=(f'import sys;sys.path.insert(0,{str(Path.cwd())!r});sys.path.append({dependency!r});'
          'from tests.test_h1_group_n0_scientific_integration_development_v1 import child_main;'
          f'child_main({str(tmp_path)!r},{str(raw_root)!r},*sys.argv[1:])')
    monkeypatch.setattr(api,'_argv',lambda path,pin:[sys.executable,'-I','-B','-c',code,str(path),pin])
    d=declaration(d)
    # Build a separate test declaration after installing the synthetic package
    # basis; frozen declaration files are never edited or relabelled.
    manifest=source.windows.load_source_window('power','training',0,1,outage_seed=20260822,
        expected_config_sha256=d.run_configuration.source_config_sha256)['package_manifest_sha256']
    monkeypatch.setattr(registry.frozen,'PACKAGE_SHA',manifest)
    raw=m.registry_declaration.build('training');path=tmp_path/'synthetic_registry.json';path.write_bytes(raw)
    identity=json.loads(raw)['expected_registry_identity']
    d=replace(d,registry_binding=m.RegistryBinding(str(path),m.sha256(raw).hexdigest(),'training'))
    protocol=registry.events.DisclosureProtocol((registry.events.OutageComponent('generator','G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    def context(split):
        seed=20260822
        row=source.windows.load_source_window('power',split,0,1,outage_seed=seed,
            expected_config_sha256=d.run_configuration.source_config_sha256)['rows'][0]
        return dict(split=split,protocol=protocol,caps={'G1':registry.Q(20)},components=(),
            rows={seed:{0:row}},catalog_entries=[dict(source_start=0,observed_end_inclusive=0,
                outage_seed=seed,chain_id=f'power:{split}:outage_seed={seed}')],
            gaps=[dict(split=split,outage_seed=seed,raw_start=0)],identity=identity,
            split_hour=99,archive_member_sha256='d'*64,cap_table_sha256='e'*64)
    monkeypatch.setattr(registry,'_load',context)
    monkeypatch.setattr(registry.frozen,'prefix_overlay',lambda *a:(('','',''),))
    return s,d,captured


def test_complete_independent_N0_roster_reaches_common_genesis(complete_group):
    s,d,captured=complete_group
    heads=None;group_head=None;ordinals=None;records=[]
    for index in range(3):
        current=d if index==0 else replace(d,ordinal=ordinals[index])
        args={} if heads is None else dict(create_study=False,global_head=heads['global_head'])
        owner=s.open(declaration=current,**args);group=None
        try:
            assert owner.bootstrap()['state']=='pending_post_N'
            group=roster(owner,s,create=index==0,expected_head=group_head)
            view=group.inspect()
            if index==0:
                ordinals=sorted(e['sibling']['ordinal'] for e in view['entries']
                    if e['classification']=='direct_shared_lane')
                assert len(ordinals)==3 and ordinals[0]==d.ordinal
            arm=next(e['sibling']['arm_id'] for e in view['entries'] if e['sibling']['ordinal']==current.ordinal)
            group_head=group.attach(arm,expected_head=view['head'])
            records.append(owner._bootstrap.rows()[-1][1])
            if index<2:
                with pytest.raises(ValueError,match='every direct sibling'):common.inspect(group)
            else:
                report=common.inspect(group)
                assert report['independent_N0_scientific_correspondence_checked']
                assert set(report['arm_audits'])=={'network-only','CFE-only','joint'}
                assert all(report[k] is False for k in common.FLAGS)
                assert len({v['reference']['episode_root'] for v in report['arm_audits'].values()})==3
                assert len({v['historical_audit']['normal_request_key'] for v in report['arm_audits'].values()})==1
                with genesis.CommonOwnerGenesis(group,create=True,retain_binder_head=s.retain,
                        retain_holder_receipt=lambda v:v,retain_owner_receipt=lambda v:v,
                        max_record_bytes=1024**2) as common_owner:
                    assert common_owner.inspect()
            heads=retained(owner,s)
        finally:
            if group is not None:group.close()
            owner.close()
    assert len(captured)==3
    assert len({v['controller_root'] for v in records})==3
