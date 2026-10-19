"""Real public header lifecycle with pre-definition execution-denial seams.

Zero N0/source/Job/native work is allowed. All phase dependencies and journals
are real; the execution-denial seams are explicit diagnostic limitations.
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


def test_exact_bootstrap5_roster4_headers_create_inspect_close_and_reopen(example,tmp_path,monkeypatch):
    assert 'experiments.h1_bootstrap_integration_development_v5' not in sys.modules
    from experiments import h1_owned_bootstrap_controller_development_v5 as owned
    from experiments import h1_selector_configuration_development_v1 as selectors
    phase=owned.phase;capture=selectors.inspector.bridge.capture
    calls={}
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
    # New runtimes capture the denial routes at definition, not after arming.
    from experiments import h1_group_execution_roster_development_v4 as roster
    m=roster.bootstrap
    start=perf_counter();stages=[]
    def trace(stage):
        stages.append(dict(stage=stage,elapsed_seconds=perf_counter()-start))
        print(json.dumps(stages[-1]),flush=True)
    _,_,_,prior,_=example
    run=m.RunConfiguration(**{field.name:getattr(prior,field.name) for field in fields(m.RunConfiguration)})
    profile=m.symbolic.build(m.symbolic.StaticProfile(**run.declared_profile()))
    path=tmp_path/'bootstrap5_profile.json';path.write_bytes(profile.raw)
    selector=configuration(tuple(uid for kind,uid in run.stage_order if kind=='generation'),run.network_sha256)
    archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(path),
        sha256(profile.raw).hexdigest(),'training_ub',0,12,65536,run,selector_configuration=selector,phase_archive=archive)
    retained={}
    def retain(root,before,after):
        assert m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()['active_operations']==0
        assert retained.get(str(root),before)==before
        retained[str(root)]=after;return after
    trace('declaration_prepared')
    with closing(m.BootstrapOwner(declaration,create=True,create_study=True,
            retain_global_head=retain,retain_bootstrap_head=retain)) as owner:
        trace('Bootstrap5_created')
        assert type(owner) is m.BootstrapOwner and not Path(owner.roots['controller']).exists()
        with closing(roster.GroupRoster(owner,create=True,retain_head=retain,max_record_bytes=65536)) as group:
            trace('Roster4_created')
            view=group.inspect();trace('Roster4_inspected')
            assert view['schema']==roster.SCHEMA and len(view['entries'])==4
            assert not view['independent_N0_mapping_complete']
            assert all(row['attachment'] is None and not row['independent_N0_available'] for row in view['entries'])
            assert all(view[name] is False for name in roster.FLAGS)
            assert owner._operation.acquire(False)
            try:
                with pytest.raises(ValueError,match='bootstrap operation active'):group.inspect()
            finally:owner._operation.release()
            errors=[]
            def foreign():
                try:group.inspect()
                except ValueError as error:errors.append(str(error))
            thread=Thread(target=foreign);thread.start();thread.join(timeout=5)
            assert not thread.is_alive() and len(errors)==1
            assert not group._operation.locked() and not owner._operation.locked() and not owner.poisoned
            heads=dict(global_head=owner._global.head,bootstrap_head=owner._bootstrap.head)
            group_head=group._journal.head;group_root=group.root
            for root in (owner._bootstrap.root,owner._global.root,group.root):assert not list(root.glob('[0-9]*.json'))
            trace('guards_checked')
        original_receipt=owner.phase_validation_receipt()
        assert original_receipt['lifecycle_complete'] and original_receipt['all_segments_closed']
        assert original_receipt['segments_opened']==3 and not original_receipt['consumer_bound']
    trace('original_headers_closed')
    with closing(m.BootstrapOwner(declaration=declaration,create=False,create_study=False,
            retain_global_head=retain,retain_bootstrap_head=retain,**heads)) as reopened:
        trace('Bootstrap5_reopened')
        with closing(roster.GroupRoster(owner=reopened,create=False,expected_head=group_head,
                retain_head=retain,max_record_bytes=65536)) as re_group:
            trace('Roster4_reopened')
            assert re_group.root==group_root and re_group.inspect()==view
            trace('Roster4_reopen_inspected')
        reopened_receipt=reopened.phase_validation_receipt()
        assert reopened_receipt['lifecycle_complete'] and reopened_receipt['segments_opened']==3
    trace('reopened_headers_closed')
    assert owner.closed and group.closed and reopened.closed and re_group.closed
    cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    assert not any(calls.values()) and not retained
    for receipt in (original_receipt,reopened_receipt):
        assert receipt['pending_cleanup_windows']==0 and not receipt['dynamic_evidence_cached']
        for segment in receipt['segments']:
            phase_receipt=segment['receipt'];kernel=phase_receipt['phase_kernel_receipt']
            assert phase_receipt['lifecycle_complete'] and phase_receipt['cached_science_cleared']
            assert kernel['all_handles_closed'] and kernel['completed_prepares']==1
    (tmp_path/'roster4_live_header_observation.json').write_bytes(m.encode(dict(
        stages=stages,original_receipt=original_receipt,reopened_receipt=reopened_receipt,
        execution_denial_calls=calls,real_header_classes=True,real_phase_dependency_inventory=True,
        predefinition_execution_denial_seams=True,unmodified_execution_dispatch_verified=False,
        completed_N0=0,new_N0_Jobs=0,real_native_calls=0,group_mapping_complete=False,
        full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)))
