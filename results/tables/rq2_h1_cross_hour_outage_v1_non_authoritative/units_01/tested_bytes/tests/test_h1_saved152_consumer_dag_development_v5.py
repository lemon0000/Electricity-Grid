"""Saved-data baseline versus two consumer-sized proof lifetimes, no public owner.

One fixed-order unprofiled diagnostic compares the verifier DAG. It does not
reopen a successor owner under a predecessor header or rerun the saved Job.
"""
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

from tests.test_h1_registry_validation_fresh_n0_development_v2 import (
    prepared,example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained)


ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/whole_workflow_optimization_01_non_authoritative'


def test_saved152_same_science_across_fallback_and_two_read_sized_operations(prepared,tmp_path):
    _,_,_,final=prepared;assert not final
    from experiments import h1_historical_n0_verifier_development_v5 as verifier
    source=D/'saved152_numerical_postcheck_result_153.json'
    assert sha256(source.read_bytes()).hexdigest()=='b9b995041a7104098ad157c5b097ce40da3558374b307d3db366f098360acec7'
    oracle=json.loads(source.read_bytes());local=Path(oracle['profile']['local_candidate_path'])
    assert sha256(local.read_bytes()).hexdigest()==oracle['profile']['local_candidate_sha256']
    body=json.loads(local.read_bytes())['body'];root=Path(body['controller_root'])
    audit_path=D/'saved152_oracle_153_preserved_non_authoritative/saved152_numerical_audit.json'
    expected_audit=audit_path.read_bytes()
    assert sha256(expected_audit).hexdigest()==body['audit_payload_sha256']==oracle['profile']['predecessor_audit_sha256']
    audits=[];decisions=[];rows=[];receipts=[];total=perf_counter()
    def trace(stage,**extra):
        value=dict(stage=stage,seconds=perf_counter()-total,**extra)
        with (tmp_path/'saved152_consumer_dag_timing.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(value)+'\n')
        print(json.dumps(value),flush=True)
    def operation(reuse,label,count):
        value=verifier.N0ValidationOperation(root,arm_id='consumer_dag_diagnostic',
            expected_binding_sha256=body['controller_binding_sha256'],
            expected_terminal_sha256=body['controller_terminal_sha256'],completed_hours=1,
            reuse_numerical_proof=reuse,diagnostic_only=reuse,maximum_prepares=count)
        started=perf_counter()
        try:
            with value:
                for ordinal in range(1,count+1):
                    trace('prepare_start',label=label,ordinal=ordinal)
                    start=perf_counter()
                    ticket=value.begin_build(None,f'build_{ordinal:03d}') if reuse else None
                    result=value.prepare()
                    if reuse:
                        diagnostic_body=dict(body,historical_verifier_schema=verifier.VERIFIER_SCHEMA,
                            historical_validation_contract=verifier.VERIFIER_SCHEMA,
                            historical_verifier_identity=result.verifier_identity,
                            audit_payload_sha256=sha256(result.audit_payload).hexdigest())
                        value.confirm_build(ticket,diagnostic_body)
                    elapsed=perf_counter()-start
                    assert result.audit_payload==expected_audit
                    audits.append(result.audit_payload);decisions.append(result.decision.decision_bytes)
                    execution=json.loads(result.execution_receipt)
                    assert not execution['bootstrap_operation_bound']
                    assert execution['diagnostic_only'] is reuse
                    expected=(4,4) if ordinal==1 else (0,8)
                    assert (result.full_numerical_hour_replays,result.fresh_byte_context_revalidations)==expected
                    rows.append(dict(label=label,ordinal=ordinal,seconds=elapsed,execution=execution))
                    trace('prepare_complete',label=label,ordinal=ordinal,elapsed_seconds=elapsed)
            proof=value.receipt()
            assert proof['closed'] and proof['proof_cleared'] and proof['first_failure'] is None
            assert proof['completed_prepares']==count and proof['context_observations']==16*count
            assert proof['complete']
            receipts.append(dict(label=label,seconds=perf_counter()-started,receipt=proof))
        finally:
            verifier._retire_operation(value)
    with verifier.hour.prior.guard.solver_calls_forbidden():
        baseline_start=perf_counter()
        for i in range(4):operation(False,'fallback_'+str(i+1),1)
        baseline_seconds=perf_counter()-baseline_start
        reuse_start=perf_counter()
        for i in range(2):operation(True,'consumer_sized_'+str(i+1),2)
        reuse_seconds=perf_counter()-reuse_start
    assert len(audits)==len(decisions)==8 and all(v==decisions[0] for v in decisions)
    def counts(prefix):
        selected=[row['execution'] for row in rows if row['label'].startswith(prefix)]
        return dict(full=sum(v['full_numerical_hour_replays'] for v in selected),
            fresh=sum(v['reused_numerical_inspections_total'] for v in selected),contexts=16*len(selected))
    assert counts('fallback_')==dict(full=16,fresh=16,contexts=64)
    assert counts('consumer_sized_')==dict(full=8,fresh=24,contexts=64)
    (tmp_path/'saved152_consumer_dag_observation.json').write_bytes(verifier.io.encode(dict(
        baseline_seconds=baseline_seconds,consumer_dag_seconds=reuse_seconds,rows=rows,receipts=receipts,
        baseline_counts=counts('fallback_'),consumer_counts=counts('consumer_sized_'),
        audit_sha256=sha256(audits[0]).hexdigest(),decision_sha256=sha256(decisions[0]).hexdigest(),
        exact_saved_predecessor_audit_equal=True,all_decision_bytes_equal=True,
        unprofiled=True,fixed_order_single_observation=True,repeated_benchmark=False,
        genuine_consumer_owner_authenticated=False,public_constructor_or_inspect_measured=False,
        diagnostic_operation_retirement_verified=True,new_N0_Jobs=0,real_native_calls=0,
        original152_public_return_verified=False,full_optimized_workflow_accepted=False,
        whole_workflow_runtime_estimate=False,formal_result=False,resource_admission=False)))
