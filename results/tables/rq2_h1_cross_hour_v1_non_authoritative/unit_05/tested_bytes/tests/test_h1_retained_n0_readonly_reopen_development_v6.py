"""Read current Bootstrap6 state using174 external heads; never rerun its Job."""
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


def test_saved174_reopens_only_externally_retained_heads(prepared,tmp_path,monkeypatch):
    _,prior,_,final=prepared;assert not final
    candidate_path=D/'bootstrap6_retained_n0_bounded_result_174.json'
    assert sha256(candidate_path.read_bytes()).hexdigest()=='4068fd99c0fce79a9a2c061917ca3690985fbf82a164fbb92a747d038bee177e'
    candidate=json.loads(candidate_path.read_bytes())
    assert candidate['terminal']['observed_owned_processes_absent']
    records=candidate['externally_persisted_retention_records'];assert len(records)==8
    assert not candidate['saved_journal_suffix_adopted']
    assert all(not row['unretained_suffix_present'] for row in candidate['journal_suffix_observations'])
    base=Path('D:/h1_bootstrap6_retained_174_non_authoritative')
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
    names=('experiments.h1_bootstrap_integration_development_v6',
           'experiments.h1_owned_bootstrap_controller_development_v6')
    assert all(name not in sys.modules for name in names)
    monkeypatch.setattr(source_fixture.m.symbolic,'inspect',ORIGINAL_SYMBOLIC_INSPECT)
    resolver=[None]
    def open_manifest():
        if resolver[0] is None:raise ValueError('saved symbolic resolver not installed')
        return resolver[0]
    monkeypatch.setattr(source_fixture.m.owned.binding,'open_manifest',open_manifest)
    from experiments import h1_bootstrap_integration_development_v6 as m
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
        (tmp_path/'saved174_readonly_inspection.json').write_bytes(m.encode(observed))
    finally:owner.close()
    trace('saved_owner_closed')
    reads=owner.registry_read_validation_receipt()
    assert reads['successful_reads']==2 and reads['failed_read_count']==0 and reads['pending_registry_records']==0
    assert not reads['cached_numerical_proofs_retained'] and not reads['detached_consumer_credential']
    assert [row['mode'] for row in reads['reads']]==['constructor','inspect']
    assert len({row['registry_execution']['session_identity'] for row in reads['reads']})==2
    for row in reads['reads']:
        proof=row['registry_execution']
        assert row['purpose']=='consumer_read' and not row['producer_nonce_borrowed']
        assert proof['complete'] and proof['closed'] and proof['confirmed_builds']==2
        assert (proof['full_numerical_hour_replays'],proof['fresh_byte_context_revalidations'],proof['context_observations'])==(4,12,32)
        assert all(item['proof_cleared'] and item['closed'] for item in proof['root_receipts'])
        assert [item['execution']['proof_role'] for item in proof['builds']]==['produced','consumed']
    assert m.historical_verifier.registry_validation_scope(owner) is None
    assert owner._operation_nonce is None and not owner._original_operation.locked()
    (tmp_path/'saved174_consumer_read_observations.json').write_bytes(m.encode(reads))
    receipt=owner.phase_validation_receipt();cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert receipt['all_segments_closed'] and receipt['lifecycle_complete']
    assert receipt['pending_cleanup_windows']==0 and cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    (tmp_path/'saved174_readonly_reopen.json').write_bytes(m.encode(dict(
        externally_retained_heads_used=True,saved_journal_suffix_adopted=False,inspection=observed,
        receipt=receipt,cleanup=cleanup,measurements=measurements,new_N0_Jobs=0,real_native_calls=0,
        read_only_reopen_state_verified=True,new_read_only_owner_closed=True,
        prior_public_bootstrap_return_verified=candidate['public_return_observed'],
        prior_operation_graceful_cleanup_proven=candidate['internal_graceful_cleanup_proven'],
        producer_plan_metadata_mismatch_preserved=True,
        full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)))
