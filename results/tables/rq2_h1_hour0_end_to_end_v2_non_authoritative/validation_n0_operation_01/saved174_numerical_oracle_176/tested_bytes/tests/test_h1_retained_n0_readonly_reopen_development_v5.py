"""Read current Bootstrap5 state using152 external heads; never rerun its Job."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

from tests import test_h1_hour0_end_to_end_development_v2 as source_fixture
from tests.test_h1_registry_validation_fresh_n0_development_v2 import (
    prepared,example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained,
    ORIGINAL_SYMBOLIC_INSPECT)

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/whole_workflow_optimization_01_non_authoritative'


def test_saved152_reopens_only_externally_retained_heads(prepared,tmp_path,monkeypatch):
    _,prior,_,final=prepared;assert not final
    candidate_path=D/'bootstrap5_retained_n0_bounded_result_152.json'
    assert sha256(candidate_path.read_bytes()).hexdigest()=='4c031ae2f63e223d6184fb59821f3cd8a34fbfd122a83bb8746d1b74ac10467a'
    candidate=json.loads(candidate_path.read_bytes())
    assert candidate['terminal']['observed_owned_processes_absent']
    records=candidate['externally_persisted_retention_records'];assert len(records)==8
    assert not candidate['saved_journal_suffix_adopted']
    assert all(not row['unretained_suffix_present'] for row in candidate['journal_suffix_observations'])
    base=Path('D:/h1_bootstrap5_retained_152_non_authoritative')
    directory,=base.glob('*/external_retention_non_authoritative')
    previous=None
    for index,record in enumerate(records,1):
        raw=(directory/f'{index:04d}.json').read_bytes()
        assert sha256(raw).hexdigest()==record['sha256']
        assert json.loads(raw)==record['record'] and record['record']['previous_retention_sha256']==previous
        previous=record['sha256']
    raw_declaration=json.loads((directory/'declaration.json').read_bytes())
    assert records[-1]['record']['retained_heads']==candidate['retained_heads']
    heads=candidate['retained_heads']
    local,=[root for root in heads if Path(root).name=='bootstrap_non_authoritative']
    global_root,=[root for root in heads if Path(root).name=='global_claims_non_authoritative']
    start=perf_counter();measurements=[]
    def trace(stage):
        value=dict(stage=stage,seconds=perf_counter()-start);measurements.append(value)
        with (tmp_path/'saved_reopen_timing.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value)+'\n')
        print(json.dumps(value),flush=True)
    names=('experiments.h1_bootstrap_integration_development_v5',
           'experiments.h1_owned_bootstrap_controller_development_v5')
    assert all(name not in sys.modules for name in names)
    monkeypatch.setattr(source_fixture.m.symbolic,'inspect',ORIGINAL_SYMBOLIC_INSPECT)
    resolver=[None]
    def open_manifest():
        if resolver[0] is None:raise ValueError('saved symbolic resolver not installed')
        return resolver[0]
    monkeypatch.setattr(source_fixture.m.owned.binding,'open_manifest',open_manifest)
    from experiments import h1_bootstrap_integration_development_v5 as m
    snapshot=m.symbolic.inspect(raw_declaration['symbolic_path'],expected_sha256=raw_declaration['symbolic_sha256'])
    resolver[0]=m.symbolic.proof._resolver(snapshot._proof_raw)
    configuration=dict(raw_declaration['run_configuration'])
    configuration.update(specification=m.Rq2SolverSpec(**configuration['specification']),
        limits=m.phase.base.old.replay.H1HourReplayLimits(**configuration['limits']),
        budget=m.phase.base.old.process.TaskProcessBudget(**configuration['budget']),
        stage_order=tuple(tuple(row) for row in configuration['stage_order']))
    assert m.encode(asdict(prior.selector_configuration))==m.encode(raw_declaration['selector_configuration'])
    declaration=m.BootstrapDeclaration(**dict(raw_declaration,
        run_configuration=m.RunConfiguration(**configuration),
        registry_binding=m.RegistryBinding(**raw_declaration['registry_binding']),
        selector_configuration=prior.selector_configuration,
        phase_archive=m.phase_manifest.ArchiveCapacityDeclaration(**raw_declaration['phase_archive'])))
    assert m.encode(asdict(declaration))==m.encode(raw_declaration)
    trace('saved_declaration_and_heads_ready')
    callbacks=[]
    def no_retention(*args):
        callbacks.append(args)
        raise AssertionError('read-only saved reopen must not publish or retain a new head')
    owner=m.BootstrapOwner(declaration,create=False,create_study=False,
        global_head=heads[global_root],bootstrap_head=heads[local],
        retain_global_head=no_retention,retain_bootstrap_head=no_retention)
    trace('saved_owner_open')
    try:
        observed=owner.inspect();trace('saved_owner_inspected')
        assert observed['state']=='pending_post_N' and observed['N0_numerical_evidence_audited']
        assert observed['global_head']==heads[global_root] and observed['bootstrap_head']==heads[local]
        assert observed['retry_authorized'] is False and all(observed[key] is False for key in m.FLAGS)
        assert owner._controller is None and not callbacks
        (tmp_path/'saved152_readonly_inspection.json').write_bytes(m.encode(observed))
    finally:owner.close()
    trace('saved_owner_closed')
    receipt=owner.phase_validation_receipt();cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert receipt['all_segments_closed'] and receipt['lifecycle_complete']
    assert receipt['pending_cleanup_windows']==0 and cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    (tmp_path/'saved152_readonly_reopen.json').write_bytes(m.encode(dict(
        externally_retained_heads_used=True,saved_journal_suffix_adopted=False,inspection=observed,
        receipt=receipt,cleanup=cleanup,measurements=measurements,new_N0_Jobs=0,real_native_calls=0,
        read_only_reopen_state_verified=True,new_read_only_owner_closed=True,
        original_public_bootstrap_return_verified=False,original_operation_graceful_cleanup_proven=False,
        full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)))
