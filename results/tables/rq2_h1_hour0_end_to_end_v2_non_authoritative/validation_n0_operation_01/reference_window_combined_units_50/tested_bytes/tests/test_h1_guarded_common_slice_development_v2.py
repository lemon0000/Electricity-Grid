"""Bounded fresh 3 N0 -> live synthetic Rref -> two full guarded common calls.

Original-source Parent/Handoff aliases are explicit synthetic seams. No native,
Actual, paired consumption, production Handoff integration or formal claim.
"""
from dataclasses import asdict,replace
import faulthandler
import json
from pathlib import Path
import sys
from time import perf_counter

import pytest
from tests.h1_gil_stack_observer_development_v1 import observe_owner_stack
import experiments
from tests import test_h1_hour0_end_to_end_development_v2 as source_fixture
from tests.test_h1_hour0_end_to_end_development_v2 import (
    example,setup,numerical,environment,synthetic_reports,supplied,
    no_solver,saved,retained,roster,genesis,m,trace)
from tests.h1_guarded_common_slice_helpers_development_v1 import (
    live_reference,fresh_identity_bookends,assert_initial_imports)


@pytest.fixture(scope='session',autouse=True)
def diagnostic_stack_observer(tmp_path_factory,request):
    assert_initial_imports()
    assert not request.config.pluginmanager.has_plugin('faulthandler')
    assert not faulthandler.is_enabled()
    root=tmp_path_factory.getbasetemp()
    with observe_owner_stack(root/'stack_samples.jsonl') as receipt:
        yield
    receipt.update(pytest_faulthandler_plugin_loaded=False,
        fatal_handler_enabled_at_setup=False)
    with (root/'stack_observer_receipt.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)


@pytest.fixture
def complete_group(numerical,environment,synthetic_reports,tmp_path,monkeypatch):
    monkeypatch.setattr(source_fixture,'identity_bookends',fresh_identity_bookends)
    yield from source_fixture.complete_group.__wrapped__(numerical,environment,synthetic_reports,tmp_path,monkeypatch)


def assert_science_equal(candidate,original):
    for key in ('phase_manifest_candidate','canonical_arm','canonical_source_binding',
            'common_scientific_payload','common_scientific_identity'):
        assert m.encode(candidate[key])==m.encode(original[key]),key
    assert set(candidate['arm_audits'])==set(original['arm_audits'])
    for arm,audit in candidate['arm_audits'].items():
        prior=original['arm_audits'][arm]
        assert set(audit)==set(prior)-{'verification_execution'}
        for key in audit:
            if key=='exact_current_audit':
                assert m.encode(audit[key]['predecessor_compatibility']['payload'])==m.encode(prior[key])
            else:assert m.encode(audit[key])==m.encode(prior[key]),(arm,key)


def test_fresh_three_arm_live_reference_two_complete_common_calls(complete_group,tmp_path,monkeypatch):
    s,declaration,captured,final=complete_group
    assert not final  # The inherited full-chain teardown is outside this slice.
    heads=group_head=ordinals=None;records=[];measurements=[];receipt=None
    names=('experiments.h1_common_validation_operation_development_v1',
        'experiments.h1_operation_historical_witness_development_v2',
        'experiments.h1_phase_exact_source_current_development_v3',
        'experiments.h1_group_n0_common_input_binding_development_v3')
    assert all(name not in sys.modules and name.rsplit('.',1)[1] not in vars(experiments) for name in names)
    for index in range(3):
        current=declaration if index==0 else replace(declaration,ordinal=ordinals[index])
        args={} if heads is None else dict(create_study=False,global_head=heads['global_head'])
        owner=s.open(declaration=current,**args);group=None
        trace('slice_arm_'+str(index)+'_open')
        try:
            assert owner.bootstrap()['state']=='pending_post_N'
            trace('slice_arm_'+str(index)+'_N0')
            group=roster(owner,s,create=index==0,expected_head=group_head)
            view=group.inspect()
            if index==0:
                ordinals=sorted(e['sibling']['ordinal'] for e in view['entries']
                    if e['classification']=='direct_shared_lane')
                assert len(ordinals)==3 and ordinals[0]==declaration.ordinal
            arm=next(e['sibling']['arm_id'] for e in view['entries'] if e['sibling']['ordinal']==current.ordinal)
            group_head=group.attach(arm,expected_head=view['head'])
            records.append(owner._bootstrap.rows()[-1][1])
            trace('slice_arm_'+str(index)+'_attached')
            if index<2:heads=retained(owner,s)
            else:
                with genesis.CommonOwnerGenesis(group,create=True,retain_binder_head=s.retain,
                        retain_holder_receipt=lambda value:value,retain_owner_receipt=lambda value:value,
                        max_record_bytes=1024**2) as common_owner:
                    trace('slice_common_genesis_constructed')
                    original=json.loads(common_owner._initial_report)
                    with live_reference(common_owner,current.selector_configuration,monkeypatch,tmp_path,trace) as live:
                        consumer,pair,scoped=live
                        def never_retain(*args):raise AssertionError('diagnostic must not publish paired retention')
                        options=dict(retain_head=never_retain,max_packet_bytes=64*1024**2,
                            max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
                        lanes=tuple(c.lane_id for c in common_owner._manifest.lanes)
                        with consumer.Handoff(common_owner,pair,dict.fromkeys(lanes),**options) as handoff:
                            trace('slice_original_source_alias_handoff_registered')
                            from tests.h1_hour0_synthetic_harness_v2 import load
                            path=Path(__file__).resolve().parents[1]/'experiments/h1_common_validation_operation_development_v1.py'
                            bridge=load(str(path),names[0],scoped,
                                {'h1_selector_phase_handoff_development_v2':consumer})
                            scoped.setattr(experiments,names[0].rsplit('.',1)[1],bridge,raising=False)
                            with bridge.GuardedCommonOperation(handoff) as operation:
                                trace('slice_guarded_operation_entered')
                                first=None
                                for ordinal in (1,2):
                                    begin=perf_counter();result=operation.prepare_common();elapsed=perf_counter()-begin
                                    trace('slice_complete_common_'+str(ordinal))
                                    report=json.loads(result.scientific_report_payload)
                                    assert_science_equal(report,original)
                                    assert m.encode(asdict(result.manifest))==m.encode(asdict(common_owner._manifest))
                                    assert m.encode(asdict(result.source_binding))==m.encode(asdict(common_owner._binding))
                                    if first is not None:assert result.scientific_report_payload==first
                                    first=result.scientific_report_payload
                                    execution=json.loads(result.execution_receipt)
                                    expected=(24,24,0) if ordinal==1 else (0,0,48)
                                    assert tuple(execution[key] for key in ('full_numerical_hour_replays',
                                        'within_prefix_revalidations','cross_common_numerical_proof_reuses'))==expected
                                    assert execution['context_evaluations']==96
                                    assert sum(r['execution']['registry_preparations'] for r in execution['source_preparations'])==12
                                    measurements.append(dict(common_call=ordinal,elapsed_seconds=elapsed,execution=execution))
                                    (tmp_path/('common_'+str(ordinal)+'_scientific.json')).write_bytes(result.scientific_report_payload)
                            receipt=operation.receipt()
                            assert receipt['complete'] and receipt['closed'] and receipt['first_failure'] is None
                            assert all(value['proof_cleared'] for value in receipt['arm_receipts'].values())
                            assert not handoff.root.exists() and not pair[0]._guard.locked()
                            assert not common_owner._original_operation.locked()
                            assert not group._original_operation.locked() and not owner._original_operation.locked()
                            trace('slice_operation_closed_all_guards_released')
                            alias=dict(module=consumer.__name__,source_file=consumer.__file__,
                                implementation_identity=consumer.implementation_identity())
        finally:
            if group is not None:group.close()
            owner.close()
            trace('slice_arm_'+str(index)+'_closed')
    assert len(captured)==len(records)==3
    for controller,record in zip(captured,records):
        assert all(lease.stream is None for lease in controller._owned_original_cleanup)
        observed=json.loads((Path(record['controller_root'])/'job_000_non_authoritative/observation.json').read_bytes())
        assert observed['exit_code']==0 and observed['whole_job_quiescent'] is True
    (tmp_path/'guarded_common_slice_report.json').write_bytes(m.encode(dict(
        status='SYNTHETIC_ORIGINAL_SOURCE_ALIAS_SLICE_ONLY',measurements=measurements,
        operation_receipt=receipt,handoff_alias=alias,N0_records=records,
        shared_scientific_fields_and_predecessor_compatibility_payloads_equal=True,
        shared_scientific_fields=['phase_manifest_candidate','canonical_arm','canonical_source_binding',
            'common_scientific_payload','common_scientific_identity'],
        per_arm_equal_fields='all old arm audit fields except verification_execution; exact_current_audit compared through full predecessor_compatibility.payload',
        execution_only_differences=['new schema/implementation identities','separate actual execution receipts'],
        bootstrap_solver_and_selector_static_identity_caches_installed=False,
        numerical_context_evaluations=192,registry_preparations=24,
        real_native_calls=0,Actual_jobs=0,paired_commits=0,
        production_handoff_integrated=False,full_chain_passed=False,
        formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)))
    trace('slice_report_saved')
