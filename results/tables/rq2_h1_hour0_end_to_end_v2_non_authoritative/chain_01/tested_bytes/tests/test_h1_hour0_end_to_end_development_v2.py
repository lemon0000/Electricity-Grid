"""Complete synthetic N0 roster and common science replay.

Raw source rows and outage mechanism are explicit test inputs. Three short
Windows Jobs export saved synthetic reports through fake solver objects. The
historical, registry prepare, exact-current, roster and common readers are real.
Enrollment and registry load identity are synthetic seams. Successor dependency verification runs fresh at every original boundary.
This is not accepted RTS input, native execution or formal admission evidence.
"""
from dataclasses import asdict, replace
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter_ns

import pytest

from experiments import h1_group_n0_common_input_binding_development_v2 as common
from experiments import h1_common_owner_genesis_development_v2 as genesis
from experiments import h1_bootstrap_integration_development_v2 as m
from experiments import h1_group_execution_roster_development_v2 as roster_api
from tests import test_h1_bootstrap_integration_development_v1 as base_fixture
from tests import test_h1_bootstrap_N0_registration_numerical_development_v1 as numerical_fixture
from tests.test_h1_bootstrap_N0_registration_numerical_development_v1 import (
    environment, supplied, no_solver, synthetic_reports, saved, retained)
from tests.test_h1_bootstrap_selector_configuration_development_v1 import bound


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(base_fixture, 'm', m)
        return base_fixture.example.__wrapped__(tmp_path_factory)


@pytest.fixture
def setup(tmp_path, example, monkeypatch):
    monkeypatch.setattr(base_fixture, 'm', m)
    return base_fixture.setup.__wrapped__(tmp_path, example, monkeypatch)


@pytest.fixture
def numerical(setup, environment, synthetic_reports, tmp_path, monkeypatch):
    monkeypatch.setattr(numerical_fixture, 'm', m)
    monkeypatch.setattr(numerical_fixture, 'owned', m.owned)
    return numerical_fixture.numerical.__wrapped__(setup, environment, synthetic_reports, tmp_path, monkeypatch)


def declaration(d):
    return replace(bound(d), phase_archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0))


def roster(owner, s, **kw):
    return roster_api.GroupRoster(owner, max_record_bytes=65536, retain_head=s.retain, **kw)


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='synthetic Windows Jobs')
OWNED_CONTINUATION=m.BootstrapOwner._continue_owned_development
BOOTSTRAP_IDENTITY=m.implementation_identity
_START=perf_counter_ns()
_LAST=_START


def trace(label):
    global _LAST
    now=perf_counter_ns()
    row=dict(label=label,elapsed_seconds=(now-_START)/1e9,interval_seconds=(now-_LAST)/1e9)
    _LAST=now
    path=os.environ.get('H1_E2E_TIMING_FILE')
    if path:
        with Path(path).open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)


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
    assert [s.close_calls for s in solvers]==[1,1,1]


@pytest.fixture
def complete_group(numerical,environment,synthetic_reports,tmp_path,monkeypatch):
    s,d,captured=numerical
    monkeypatch.setattr(m,'implementation_identity',BOOTSTRAP_IDENTITY)
    monkeypatch.setattr(m.BootstrapOwner,'_continue_owned_development',OWNED_CONTINUATION)
    binding=m.owned.binding
    def precheck(resolver,declaration,*,family,ordinal,relative_hour):
        return resolver.resolve(family,ordinal)
    monkeypatch.setattr(binding,'precheck',precheck)
    def bind(resolver,declaration,**kw):
        node=precheck(resolver,declaration,**{k:kw[k] for k in ('family','ordinal','relative_hour')})
        reader=binding.snapshot.open_snapshot(declaration,expected_parent_identity=kw['expected_parent_identity'],
            expected_anchor_record=kw['expected_anchor_record'])
        try:item=reader.pending_input(**kw['pending_arguments'])
        finally:reader.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        request=dict(parent_declaration=declaration,pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,budget=asdict(kw['job_budget']))
        return m.owned.phase._historical_binding(item.packet,request,node,dict(test_only_synthetic_source=True))
    monkeypatch.setattr(binding,'bind',bind)
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
    code=(f'import sys;sys.path.insert(0,{str(Path.cwd())!r});sys.path.insert(0,{str(Path.cwd()/'tests')!r});sys.path.append({dependency!r});'
          'from tests.test_h1_group_n0_scientific_integration_development_v1 import child_main;'
          f'child_main({str(tmp_path)!r},{str(raw_root)!r},*sys.argv[1:])')
    wrapped='try:\n    '+code+'\nexcept BaseException:\n    import traceback\n    from pathlib import Path\n    Path("synthetic_child_error.txt").write_text(traceback.format_exc(),encoding="utf-8")\n    raise\n'
    monkeypatch.setattr(api,'_argv',lambda path,pin:[sys.executable,'-I','-B','-c',wrapped,str(path),pin])
    d=declaration(d)
    # Explicit test-only selector budgets; these declare no production allowance.
    c=d.selector_configuration
    c=replace(c,reference_job_budget=replace(c.reference_job_budget,max_elapsed_seconds=300),
        actual_job_budget=replace(c.actual_job_budget,max_elapsed_seconds=300),
        reference_non_solver_seconds=240,actual_non_solver_seconds=240)
    d=replace(d,selector_configuration=c)
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
    from src.scenarios.rts_gmlc_n1_chronology import N1ReliabilityComponent
    components=(N1ReliabilityComponent('generator','G1',0.1,4.0),)
    def context(split):
        seed=20260822
        row=source.windows.load_source_window('power',split,0,1,outage_seed=seed,
            expected_config_sha256=d.run_configuration.source_config_sha256)['rows'][0]
        return dict(split=split,protocol=protocol,caps={'G1':registry.Q(20)},components=components,
            rows={seed:{0:row}},catalog_entries=[dict(source_start=0,observed_end_inclusive=0,
                outage_seed=seed,chain_id=f'power:{split}:outage_seed={seed}')],
            gaps=[dict(split=split,outage_seed=seed,raw_start=0)],identity=identity,
            split_hour=99,archive_member_sha256='d'*64,cap_table_sha256='e'*64)
    monkeypatch.setattr(registry,'_load',context)
    monkeypatch.setattr(registry.frozen,'prefix_overlay',lambda *a:(('','',''),))
    final={}
    trace('source_and_fixture_setup')
    yield s,d,captured,final
    if final:
        owner=s.open(create=False,create_study=False,declaration=final['declaration'],**final['heads'])
        group=None
        try:
            group=roster(owner,s,create=False,expected_head=final['group_head'])
            assert group.inspect()['independent_N0_mapping_complete']
            assert common.inspect(group)==final['report']
        finally:
            if group is not None:group.close()
            owner.close()
        trace('reopen_bootstrap_roster_common_and_close')
        from tests.h1_group_selector_integration_helpers_v2 import reopen_paired
        replay=reopen_paired(final['handoff'],trace)
        (tmp_path/'complete_integration_report.json').write_bytes(m.encode(dict(
            scope='synthetic_hour0',formal_result=False,real_native_calls=0,
            synthetic_N0_jobs=3,canonical_selector_jobs=0,paired_replay=replay,
            N0_records=final['records'],common_report=final['report'])))
        trace('integration_report_saved')


def test_complete_independent_N0_roster_reaches_paired_handoff(complete_group,tmp_path,monkeypatch):
    s,d,captured,final=complete_group
    heads=None;group_head=None;ordinals=None;records=[]
    for index in range(3):
        current=d if index==0 else replace(d,ordinal=ordinals[index])
        args={} if heads is None else dict(create_study=False,global_head=heads['global_head'])
        owner=s.open(declaration=current,**args);group=None
        trace(f'arm_{index}_open')
        try:
            assert owner.bootstrap()['state']=='pending_post_N'
            trace(f'arm_{index}_N0')
            group=roster(owner,s,create=index==0,expected_head=group_head)
            view=group.inspect()
            if index==0:
                direct_arms={e['sibling']['arm_id'] for e in view['entries']
                    if e['classification']=='direct_shared_lane'}
                ordinals=sorted(e['sibling']['ordinal'] for e in view['entries']
                    if e['classification']=='direct_shared_lane')
                assert len(ordinals)==3 and ordinals[0]==d.ordinal
            arm=next(e['sibling']['arm_id'] for e in view['entries'] if e['sibling']['ordinal']==current.ordinal)
            group_head=group.attach(arm,expected_head=view['head'])
            records.append(owner._bootstrap.rows()[-1][1])
            trace(f'arm_{index}_roster_attach')
            if index<2:
                with pytest.raises(ValueError,match='every direct sibling'):common.inspect(group)
            else:
                report=common.inspect(group)
                trace('complete_common_scientific_replay')
                assert report['independent_N0_scientific_correspondence_checked']
                assert set(report['arm_audits'])==direct_arms
                assert all(report[k] is False for k in common.FLAGS)
                refs=[v['reference'] for v in report['arm_audits'].values()]
                for key in ('slot_id','episode_root'):
                    assert len({v[key] for v in refs})==3
                for key in ('claim','release','local_terminal','global_terminal'):
                    assert len({v[key]['head'] for v in refs})==3
                assert all(v['reuse_edge'] is None for v in refs)
                b6=next(e for e in group.inspect()['entries'] if e['sibling']['arm_id']=='joint-B6')
                assert b6['classification']=='pending_separate_B6_planning' and b6['attachment'] is None
                assert len({v['historical_audit']['normal_request_key'] for v in report['arm_audits'].values()})==1
                with genesis.CommonOwnerGenesis(group,create=True,retain_binder_head=s.retain,
                        retain_holder_receipt=lambda v:v,retain_owner_receipt=lambda v:v,
                        max_record_bytes=1024**2) as common_owner:
                    checked=common_owner.inspect()
                    assert checked['stage']==3 and checked['persistent_empty_genesis_bound'] is True
                    assert common_owner._holder.inspect()==()
                    assert common_owner._phase.heads==(common_owner._phase.genesis,)*2
                    assert json.loads(common_owner._initial_report)==report
                    assert common.encode(asdict(common_owner._manifest))==common.encode(
                        report['phase_manifest_candidate']['audit']['manifest'])
                    assert common.encode(asdict(common_owner._binding))==common.encode(report['canonical_source_binding'])
                    assert all(checked[k] is False for k in genesis.FLAGS)
                    trace('common_genesis_and_inspect')
                    from tests.h1_group_selector_integration_helpers_v2 import consume_zero_workload
                    handoff_result=consume_zero_workload(common_owner,current.selector_configuration,monkeypatch,tmp_path,trace)
                    assert handoff_result['result']['completed_hours']==1
            heads=retained(owner,s)
        finally:
            if group is not None:group.close()
            owner.close()
            trace(f'arm_{index}_close')
    assert len(captured)==3
    for controller,record in zip(captured,records):
        assert all(lease.stream is None for lease in controller._owned_original_cleanup)
        observed=json.loads((Path(record['controller_root'])/'job_000_non_authoritative/observation.json').read_bytes())
        assert observed['exit_code']==0 and observed['whole_job_quiescent'] is True
    assert len({v['controller_root'] for v in records})==3
    final.update(declaration=current,heads=heads,group_head=group_head,report=report,
                 handoff=handoff_result,records=records)
