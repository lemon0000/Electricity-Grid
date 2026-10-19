"""Create fresh saved-data postchecks; preserve all prior tested sources."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
result=D/'bootstrap6_retained_n0_bounded_result_174.json';pin=sha256(result.read_bytes()).hexdigest()
v=json.loads(result.read_bytes());assert v['public_development_N0_return_and_close_verified']
assert v['terminal']['observed_owned_processes_absent'] and not v['terminal']['cleanup_errors']
prior=R/'tests/test_h1_saved_retained_n0_candidate_profile_development_v1.py'
s=prior.read_text(encoding='utf-8').replace('152','174').replace('bootstrap5','bootstrap6')
numeric=R/'tests/test_h1_saved_bootstrap6_n0_candidate_profile_development_v1.py'
with numeric.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
prior=R/'tests/test_h1_retained_n0_readonly_reopen_development_v5.py'
s=prior.read_text(encoding='utf-8').replace('152','174').replace('Bootstrap5','Bootstrap6').replace('bootstrap5','bootstrap6')
s=s.replace('h1_bootstrap_integration_development_v5','h1_bootstrap_integration_development_v6').replace(
    'h1_owned_bootstrap_controller_development_v5','h1_owned_bootstrap_controller_development_v6')
s=s.replace('4c031ae2f63e223d6184fb59821f3cd8a34fbfd122a83bb8746d1b74ac10467a',pin)
marker='    receipt=owner.phase_validation_receipt();cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()\n'
assert s.count(marker)==1
s=s.replace(marker,'''    reads=owner.registry_read_validation_receipt()
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
'''+marker)
s=s.replace('original_public_bootstrap_return_verified=False,original_operation_graceful_cleanup_proven=False,',
    "prior_public_bootstrap_return_verified=candidate['public_return_observed'],\n        prior_operation_graceful_cleanup_proven=candidate['internal_graceful_cleanup_proven'],\n        producer_plan_metadata_mismatch_preserved=True,")
target=R/'tests/test_h1_retained_n0_readonly_reopen_development_v6.py'
with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print(json.dumps(dict(result_sha256=pin,created=[str(numeric),str(target)])))
