"""Measure the existing verifier4 reuse DAG on saved137 data, with no owner/Job."""
import cProfile
from hashlib import sha256
import json
from pathlib import Path
import pstats
from time import perf_counter

from tests.test_h1_registry_validation_fresh_n0_development_v2 import (
    prepared, example, setup, numerical, environment, synthetic_reports,
    supplied, no_solver, saved, retained)


def test_saved137_four_prepare_operation_cost_and_science(prepared, tmp_path):
    _, _, _, final = prepared
    assert not final
    base = Path('D:/h1_bootstrap5_n0_137_non_authoritative/nt_non_authoritative')
    candidates = []
    for path in base.glob('episodes/*/bootstrap_non_authoritative/[0-9]*.json'):
        body = json.loads(path.read_bytes())['body']
        if body.get('kind') == 'normal_terminal':
            candidates.append((path, body))
    assert len(candidates) == 1
    local_path, body = candidates[0]
    root = local_path.parent.parent / 'controller_non_authoritative'
    assert Path(body['controller_root']) == root
    from experiments import h1_historical_n0_verifier_development_v4 as verifier
    operation = verifier.N0ValidationOperation(root, arm_id='saved_candidate_diagnostic',
        expected_binding_sha256=body['controller_binding_sha256'],
        expected_terminal_sha256=body['controller_terminal_sha256'], completed_hours=1,
        reuse_numerical_proof=True, diagnostic_only=True, maximum_prepares=4)
    rows = []
    total = perf_counter()
    with verifier.hour.prior.guard.solver_calls_forbidden(), operation:
        for ordinal in range(1, 5):
            print(json.dumps(dict(stage='prepare_start', ordinal=ordinal,
                                  seconds=perf_counter()-total)), flush=True)
            profile = cProfile.Profile()
            start = perf_counter()
            def build():
                ticket = operation.begin_build(None, f'build_{ordinal:03d}')
                result = operation.prepare()
                diagnostic_body = dict(body,
                    historical_verifier_schema=verifier.VERIFIER_SCHEMA,
                    historical_validation_contract=verifier.VERIFIER_SCHEMA,
                    historical_verifier_identity=result.verifier_identity,
                    audit_payload_sha256=sha256(result.audit_payload).hexdigest())
                operation.confirm_build(ticket, diagnostic_body)
                return result
            try:
                result = profile.runcall(build)
            finally:
                profile.dump_stats(str(tmp_path/f'prepare_{ordinal}.prof'))
            elapsed = perf_counter()-start
            assert sha256(result.audit_payload).hexdigest() == body['audit_payload_sha256']
            execution = json.loads(result.execution_receipt)
            assert execution['bootstrap_operation_bound'] is False
            assert execution['diagnostic_only'] is True
            assert (result.full_numerical_hour_replays, result.fresh_byte_context_revalidations) == (
                (4, 4) if ordinal == 1 else (0, 8))
            stats = pstats.Stats(profile)
            def records(items):
                return [dict(file=key[0], line=key[1], function=key[2], primitive_calls=v[0],
                    calls=v[1], self_seconds=v[2], cumulative_seconds=v[3]) for key, v in items]
            cumulative = sorted(stats.stats.items(), key=lambda row:row[1][3], reverse=True)[:35]
            own = sorted(stats.stats.items(), key=lambda row:row[1][2], reverse=True)[:25]
            row = dict(prepare=ordinal, seconds=elapsed, execution=execution,
                       top_cumulative=records(cumulative), top_self=records(own))
            rows.append(row)
            (tmp_path/f'prepare_{ordinal}_profile.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
            print(json.dumps(dict(stage='prepare_complete', ordinal=ordinal, seconds=elapsed,
                full=result.full_numerical_hour_replays, fresh=result.fresh_byte_context_revalidations)), flush=True)
    receipt = operation.receipt()
    assert receipt['closed'] and receipt['proof_cleared'] and receipt['first_failure'] is None
    assert receipt['completed_prepares'] == len(receipt['confirmed_builds']) == 4
    assert receipt['complete'] is True and receipt['diagnostic_only'] is True
    observation = dict(schema='h1_saved137_n0_operation_profile_v4',
        local_candidate_path=str(local_path), candidate_data_only=True,
        candidate_sha256=sha256(local_path.read_bytes()).hexdigest(),
        controller_root=str(root), elapsed_seconds=perf_counter()-total, prepares=rows,
        operation_receipt=receipt, public_owner_opened=False, new_N0_Jobs=0, real_native_calls=0,
        registered_N0_owner_authenticated=False, public_bootstrap_return_verified=False,
        profiler_enabled=True, matched_unprofiled_runtime_comparison=False,
        formal_result=False, resource_admission=False)
    (tmp_path/'saved137_operation_profile.json').write_text(json.dumps(observation, indent=2), encoding='utf-8')
