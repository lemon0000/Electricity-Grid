"""Genuine Bootstrap7/Roster5 empty journals and phase scopes; no execution."""
from contextlib import closing
from dataclasses import fields
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

from tests.test_h1_bootstrap_integration_development_v1 import example
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_bootstrap7_roster5_empty_headers_create_inspect_close_and_reopen(example,tmp_path,monkeypatch):
    assert 'experiments.h1_bootstrap_integration_development_v7' not in sys.modules
    from experiments import h1_owned_bootstrap_controller_development_v7 as owned
    from experiments import h1_selector_configuration_development_v1 as selectors
    phase=owned.phase;capture=selectors.inspector.bridge.capture;calls={}
    def deny(label):
        calls[label]=0
        def denied(*args,**kwargs):
            calls[label]+=1;raise AssertionError('empty header reached execution: '+label)
        return denied
    seams=((owned.OwnedController,'__init__','owned_controller'),
        (owned.OwnedController,'_owned_native_job','owned_Job'),
        (phase.Controller,'__init__','legacy_controller'),
        (phase.binding.source_binding,'load_pinned_current','source'),
        (phase.binding.source_binding.rts,'load_rts_gmlc_chronological_data','external_data'),
        (capture.old.provenance.adapter,'create_solver','solver'),
        (selectors.inspector.bridge,'_run_stage','stage'),(capture,'StageCapture','capture'),
        (selectors.process,'normal_task_child','job'))
    for target,name,label in seams:monkeypatch.setattr(target,name,deny(label))
    from experiments import h1_bootstrap_integration_development_v7 as m
    from experiments import h1_group_execution_roster_development_v5 as roster
    assert roster.bootstrap is m
    start=perf_counter();stages=[]
    def trace(stage):
        stages.append(dict(stage=stage,seconds=perf_counter()-start))
        print(json.dumps(stages[-1]),flush=True)
    _,_,_,prior,_=example
    run=m.RunConfiguration(**{field.name:getattr(prior,field.name) for field in fields(m.RunConfiguration)})
    profile=m.symbolic.build(m.symbolic.StaticProfile(**run.declared_profile()))
    path=tmp_path/'bootstrap7_profile.json';path.write_bytes(profile.raw)
    selector=configuration(tuple(uid for kind,uid in run.stage_order if kind=='generation'),run.network_sha256)
    archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(path),
        sha256(profile.raw).hexdigest(),'training_ub',0,12,65536,run,
        selector_configuration=selector,phase_archive=archive)
    callbacks=[]
    def retain(*args):callbacks.append(args);raise AssertionError('empty journal retained a head')
    trace('declaration_prepared')
    with closing(m.BootstrapOwner(declaration,create=True,create_study=True,
            retain_global_head=retain,retain_bootstrap_head=retain)) as owner:
        trace('Bootstrap7_created')
        owner_view=owner.inspect();trace('Bootstrap7_inspected')
        assert owner_view['state']=='new' and not owner_view['N0_numerical_evidence_audited']
        assert owner._controller is None and not Path(owner.roots['controller']).exists()
        with closing(roster.GroupRoster(owner,create=True,retain_head=retain,max_record_bytes=2**20)) as group:
            trace('Roster5_created')
            view=group.inspect();trace('Roster5_inspected')
            assert len(view['entries'])==4 and not view['independent_N0_mapping_complete']
            assert all(row['attachment'] is None and not row['independent_N0_available'] for row in view['entries'])
            assert all(view[name] is False for name in roster.FLAGS)
            group_head=group._journal.head;group_root=group.root
            heads=dict(global_head=owner._global.head,bootstrap_head=owner._bootstrap.head)
            for root in (owner._bootstrap.root,owner._global.root,group.root):
                assert not list(root.glob('[0-9]*.json'))
    trace('original_headers_closed')
    with closing(m.BootstrapOwner(declaration,create=False,create_study=False,
            retain_global_head=retain,retain_bootstrap_head=retain,**heads)) as reopened:
        trace('Bootstrap7_reopened')
        assert reopened.inspect()==owner_view;trace('Bootstrap7_reopen_inspected')
        with closing(roster.GroupRoster(reopened,create=False,expected_head=group_head,
                retain_head=retain,max_record_bytes=2**20)) as re_group:
            trace('Roster5_reopened')
            assert re_group.root==group_root and re_group.inspect()==view
            trace('Roster5_reopen_inspected')
    trace('reopened_headers_closed')
    cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    assert not any(calls.values()) and not callbacks
    phase_receipts=[];owner_reads=[];roster_reads=[];sessions=[]
    for current,current_group in ((owner,group),(reopened,re_group)):
        assert current.closed and current_group.closed
        assert not current._operation.locked() and not current_group._operation.locked()
        assert current._operation_nonce is None and not current.poisoned and not current_group.poisoned
        assert m.historical_verifier.registry_validation_scope(current) is None
        phase_receipt=current.phase_validation_receipt();phase_receipts.append(phase_receipt)
        assert phase_receipt['segments_opened']==4 and phase_receipt['lifecycle_complete']
        assert phase_receipt['all_segments_closed'] and phase_receipt['pending_cleanup_windows']==0
        for row in phase_receipt['segments']:
            identity=row['implementation_observation'];receipt=row['receipt']
            assert identity['entry_raw_attempts']==identity['exit_raw_attempts']==1
            assert identity['entry_exit_equal'] and identity['cached_calls']>0
            assert receipt['lifecycle_complete'] and receipt['cached_science_cleared']
            assert receipt['phase_kernel_receipt']['all_handles_closed']
        own=current.registry_read_validation_receipt();owner_reads.append(own)
        foreign=current_group.registry_read_validation_receipt();roster_reads.append(foreign)
        assert [row['mode'] for row in own['reads']]==['constructor','inspect']
        assert [row['mode'] for row in foreign['reads']]==['constructor_owner_replay','replay','replay']
        assert foreign['failed_read_count']==0 and foreign['pending_registry_records']==0
        for observation in (own,foreign):
            assert not observation['cached_numerical_proofs_retained'] and not observation['detached_consumer_credential']
            for row in observation['reads']:
                proof=row['registry_execution'];sessions.append(proof['session_identity'])
                assert row['metadata_read_complete'] and not row['producer_nonce_borrowed']
                assert proof['closed'] and not proof['complete'] and proof['first_failure'] is None
                assert not proof['root_receipts'] and not proof['builds'] and proof['confirmed_builds']==0
                assert proof['full_numerical_hour_replays']==proof['fresh_byte_context_revalidations']==proof['context_observations']==0
        assert all(row['registry_execution']['consumer_route']=='roster_read' for row in foreign['reads'])
    assert len(sessions)==len(set(sessions))==10
    (tmp_path/'roster5_live_header_observation.json').write_bytes(m.encode(dict(
        stages=stages,phase_receipts=phase_receipts,owner_read_observations=owner_reads,
        roster_read_observations=roster_reads,inspection=view,cleanup=cleanup,
        execution_denial_calls=calls,real_header_classes=True,real_phase_dependency_inventory=True,
        predefinition_execution_denial_seams=True,unmodified_execution_dispatch_verified=False,
        numerical_roster_read_verified=False,retention_callback_exercised=False,
        completed_N0=0,new_N0_Jobs=0,real_native_calls=0,phase_segments=8,registry_scopes=10,
        full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)))
