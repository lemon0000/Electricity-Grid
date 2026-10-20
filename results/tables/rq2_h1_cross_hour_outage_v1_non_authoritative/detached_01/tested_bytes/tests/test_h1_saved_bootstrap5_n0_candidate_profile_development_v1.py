"""Inspect the saved137 numerical candidate without opening an owner or Job."""
import cProfile
from hashlib import sha256
import json
from pathlib import Path
import pstats
from time import perf_counter

from tests.test_h1_registry_validation_fresh_n0_development_v2 import (
    prepared,example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained)


def test_saved137_candidate_numerical_oracle_and_cost(prepared,tmp_path):
    s,prior,_,final=prepared;assert not final
    base=Path('D:/h1_bootstrap5_n0_137_non_authoritative')
    candidates=[]
    for path in base.glob('nt_non_authoritative/episodes/*/bootstrap_non_authoritative/[0-9]*.json'):
        value=json.loads(path.read_bytes())
        if value['body'].get('kind')=='normal_terminal':candidates.append((path,value['body']))
    assert len(candidates)==1
    local_path,body=candidates[0];root=local_path.parent.parent/'controller_non_authoritative'
    assert Path(body['controller_root'])==root
    # These hashes are candidate data, never externally retained owner heads.
    from experiments import h1_historical_n0_verifier_development_v1 as oracle
    profile=cProfile.Profile();start=perf_counter()
    with oracle.witness.hour.prior.guard.solver_calls_forbidden():
        result=profile.runcall(oracle.prepare,root,
            expected_binding_sha256=body['controller_binding_sha256'],
            expected_terminal_sha256=body['controller_terminal_sha256'],completed_hours=1)
    elapsed=perf_counter()-start
    assert sha256(result.audit_payload).hexdigest()==body['audit_payload_sha256']
    stats=pstats.Stats(profile)
    top=sorted(stats.stats.items(),key=lambda row:row[1][3],reverse=True)[:40]
    rows=[dict(file=key[0],line=key[1],function=key[2],primitive_calls=value[0],
        calls=value[1],self_seconds=value[2],cumulative_seconds=value[3]) for key,value in top]
    profile.dump_stats(str(tmp_path/'saved137_numerical_oracle.prof'))
    (tmp_path/'saved137_numerical_audit.json').write_bytes(result.audit_payload)
    observation=dict(schema='h1_saved137_numerical_candidate_profile_v1',
        local_candidate_path=str(local_path),local_candidate_sha256=sha256(local_path.read_bytes()).hexdigest(),
        controller_root=str(root),oracle_seconds=elapsed,top_cumulative=rows,
        predecessor_audit_sha256=sha256(result.audit_payload).hexdigest(),
        numerical_candidate_equal_to_local_record=True,
        candidate_data_only=True,externally_retained_owner_heads_verified=False,
        public_bootstrap_return_verified=False,registered_N0_owner_authenticated=False,
        new_N0_Jobs=0,real_native_calls=0,full_optimized_workflow_accepted=False,
        profiler_enabled=True,matched_unprofiled_runtime_comparison=False,
        formal_result=False,resource_admission=False)
    (tmp_path/'saved137_candidate_oracle_profile.json').write_text(json.dumps(observation,indent=2),encoding='utf-8')
    print(json.dumps(dict(saved137_numerical_candidate_equal=True,oracle_seconds=elapsed,
        public_bootstrap_return_verified=False,new_N0_Jobs=0)),flush=True)
