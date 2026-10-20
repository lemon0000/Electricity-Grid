"""Real Bootstrap6 empty-header lifecycle; execution denied before definition.

No Roster successor or N0/source/Job/native execution is involved. Genuine
phase dependencies, original journals, guards and empty registry scopes run.
"""
from contextlib import closing
from dataclasses import fields
from hashlib import sha256
import json
from pathlib import Path
import sys
from threading import Thread
from time import perf_counter

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import example
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_bootstrap6_empty_registry_creates_inspects_closes_and_reopens(example,tmp_path,monkeypatch):
    assert 'experiments.h1_bootstrap_integration_development_v6' not in sys.modules
    from experiments import h1_owned_bootstrap_controller_development_v6 as owned
    from experiments import h1_selector_configuration_development_v1 as selectors
    phase=owned.phase;capture=selectors.inspector.bridge.capture;calls={}
    def deny(label):
        calls[label]=0
        def denied(*args,**kwargs):
            calls[label]+=1;raise AssertionError('header-only diagnostic reached execution: '+label)
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
    from experiments import h1_bootstrap_integration_development_v6 as m
    start=perf_counter();stages=[]
    def trace(stage):
        stages.append(dict(stage=stage,seconds=perf_counter()-start))
        print(json.dumps(stages[-1]),flush=True)
    _,_,_,prior,_=example
    run=m.RunConfiguration(**{field.name:getattr(prior,field.name) for field in fields(m.RunConfiguration)})
    profile=m.symbolic.build(m.symbolic.StaticProfile(**run.declared_profile()))
    path=tmp_path/'bootstrap6_profile.json';path.write_bytes(profile.raw)
    selector=configuration(tuple(uid for kind,uid in run.stage_order if kind=='generation'),run.network_sha256)
    archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(path),
        sha256(profile.raw).hexdigest(),'training_ub',0,12,65536,run,selector_configuration=selector,phase_archive=archive)
    callbacks=[]
    def retain(*args):callbacks.append(args);raise AssertionError('empty header must not retain a head')
    trace('declaration_prepared')
    with closing(m.BootstrapOwner(declaration,create=True,create_study=True,
            retain_global_head=retain,retain_bootstrap_head=retain)) as owner:
        trace('Bootstrap6_created')
        view=owner.inspect();trace('Bootstrap6_inspected')
        assert type(owner) is m.BootstrapOwner and view['state']=='new'
        assert not Path(owner.roots['controller']).exists() and owner._controller is None
        assert all(view[name] is False for name in m.FLAGS)
        assert not view['N0_numerical_evidence_audited'] and not view['retry_authorized']
        assert owner._operation_nonce is None and not owner._operation.locked()
        assert m.historical_verifier.registry_validation_scope(owner) is None
        for invalid in (1,None,'true'):
            with pytest.raises(ValueError,match='exact registered development flag'):
                owner.bootstrap(registered_development=invalid)
        assert owner.phase_validation_receipt()['segments_opened']==2 and not owner.poisoned
        assert owner._operation.acquire(False)
        try:
            with pytest.raises(ValueError,match='bootstrap operation active'):owner.inspect()
        finally:owner._operation.release()
        errors=[]
        def foreign():
            try:owner.inspect()
            except ValueError as error:errors.append(str(error))
        thread=Thread(target=foreign);thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and len(errors)==1
        assert not owner._operation.locked() and owner._operation_nonce is None and not owner.poisoned
        heads=dict(global_head=owner._global.head,bootstrap_head=owner._bootstrap.head)
        for root in (owner._bootstrap.root,owner._global.root):assert not list(root.glob('[0-9]*.json'))
    trace('original_owner_closed')
    with closing(m.BootstrapOwner(declaration,create=False,create_study=False,
            retain_global_head=retain,retain_bootstrap_head=retain,**heads)) as reopened:
        trace('Bootstrap6_reopened')
        assert reopened.inspect()==view;trace('Bootstrap6_reopen_inspected')
        assert reopened._operation_nonce is None and not reopened._operation.locked()
        assert m.historical_verifier.registry_validation_scope(reopened) is None
    trace('reopened_owner_closed')
    cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    assert owner.closed and reopened.closed and not any(calls.values()) and not callbacks
    receipts=[];read_receipts=[]
    for current in (owner,reopened):
        phase_receipt=current.phase_validation_receipt();receipts.append(phase_receipt)
        assert phase_receipt['lifecycle_complete'] and phase_receipt['all_segments_closed']
        assert phase_receipt['segments_opened']==2 and phase_receipt['pending_cleanup_windows']==0
        assert not phase_receipt['consumer_bound'] and not phase_receipt['dynamic_evidence_cached']
        assert phase_receipt['implementation_observation']=='segment_entry_exit'
        for row in phase_receipt['segments']:
            observation=row['implementation_observation']
            assert observation['entry_raw_attempts']==observation['exit_raw_attempts']==1
            assert observation['entry_exit_equal'] and observation['cached_calls']>0
            assert row['receipt']['lifecycle_complete']
            assert row['receipt']['phase_kernel_receipt']['all_handles_closed']
        reads=current.registry_read_validation_receipt();read_receipts.append(reads)
        assert reads['successful_reads']==2 and not reads['cached_numerical_proofs_retained']
        assert not reads['detached_consumer_credential']
        assert [row['mode'] for row in reads['reads']]==['constructor','inspect']
        assert len({row['registry_execution']['session_identity'] for row in reads['reads']})==2
        for row in reads['reads']:
            proof=row['registry_execution']
            assert row['metadata_read_complete'] and row['numerical_roots']==0
            assert proof['closed'] and not proof['complete'] and proof['first_failure'] is None
            assert not proof['root_receipts'] and not proof['builds'] and proof['confirmed_builds']==0
            assert proof['full_numerical_hour_replays']==proof['fresh_byte_context_revalidations']==proof['context_observations']==0
            assert not row['producer_nonce_borrowed'] and not row['detached_consumer_credential']
    (tmp_path/'bootstrap6_live_header_observation.json').write_bytes(m.encode(dict(
        stages=stages,phase_receipts=receipts,registry_read_observations=read_receipts,
        inspection=view,cleanup=cleanup,execution_denial_calls=calls,
        real_header_classes=True,real_phase_dependency_inventory=True,
        predefinition_execution_denial_seams=True,unmodified_execution_dispatch_verified=False,
        numerical_registry_read_verified=False,completed_N0=0,new_N0_Jobs=0,real_native_calls=0,
        full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)))
