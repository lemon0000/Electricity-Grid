"""One successor 3h batch against saved predecessor science. No old Reader rerun."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import traceback
from types import SimpleNamespace

import compare_saved_v1 as core
import pytest

HERE, REPO, CASE, old, fixture = core.HERE, core.REPO, core.CASE, core.old, core.fixture


def saved_scientific_oracle(current, saved, hour):
    """Rebuild original join/projection from saved normal audit and fresh source.

    The packet projection field is taken from the accepted saved audit. This is
    an explicit one-field data stand-in, not a reconstructed H1 packet or lease.
    """
    prior = old.prior
    raw = old.io.encode(saved['normal_audit_payload'])
    assert old.io.digest(raw) == saved['normal_audit_identity']
    envelope = prior.normal._owned(prior.normal.H1NormalAuditEnvelope,
        decision=current.prepared_current.decision.normal, audit_payload=raw)
    _, declaration, origin, current_declaration = prior.origin_join.predecessor._coordinates(envelope, hour+1)
    prefix = old.registry.prepare(split=origin.split, raw_start=origin.power_raw_hour, hours=hour+1,
        outage_seed=origin.outage_seed, expected_registry_identity=saved['registry_identity'])
    observation = old.source.load_pinned_current(current_declaration, declaration['upstream_root'],
        config_path=declaration['config_path'])
    assert observation.identity == saved['source_observation_identity']
    assert json.loads(observation.audit_payload) == saved['source_observation_audit_payload']
    assert prefix.audit == saved['registry_audit_payload']
    decision, frame, action = prior.origin_join._join(envelope, prefix, observation, completed_hours=hour+1)
    projected_packet_field = SimpleNamespace(workload_projection_payload=old.io.encode(saved['workload_projection']))
    workload, cfe, projection = prior._project(observation, frame, projected_packet_field)
    scientific = old.io.encode(dict(schema=prior.SCHEMA, relative_hour=hour,
        current_decision_identity=decision.decision_identity, workload_exact=prior._ratio(workload),
        source_cfe_at_alpha_one_exact=prior._ratio(cfe), projection_rule=projection['projection_rule'],
        power_rule=projection['power_rule'], decimal_places=12, normalized_unit_mw='250', cfe_source_mapping_rule=prior.CFE_RULE))
    assert scientific == current.exogenous_scientific_payload
    assert old.io.digest(scientific) == saved['exogenous_scientific_identity']
    prepared = current.prepared_current
    assert decision.decision_bytes == prepared.decision.decision_bytes
    assert old.physical._digest(frame) == old.physical._digest(prepared.frame)
    assert old.physical._digest(prefix.origin) == old.physical._digest(prepared.source_origin)
    assert old.physical._digest(action) == old.physical._digest(prepared.source_action) == saved['source_action_audit_identity']
    assert workload == current.workload_exact and cfe == current.source_cfe_at_alpha_one_exact
    assert core.normalized(json.loads(current.source_projection_audit_payload)) == core.normalized(saved)
    return core.summary(current)


def main():
    out = Path(sys.argv[1]).resolve()
    assert out.parent == HERE and out.is_dir()
    started = time.perf_counter()
    before = fixture.inventory(CASE)
    previous = fixture.load(REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    assert before == previous['diagnostic_case_files_sha256'] and len(before) == 465
    checkpoint = fixture.load(CASE / 'external_preclose_checkpoint.json')
    assert len(checkpoint['saved_files_sha256']) == 444
    assert all(fixture.pin(path) == value for path, value in checkpoint['saved_files_sha256'].items())
    with closing(sqlite3.connect((CASE / 'owner_non_authoritative/owner.sqlite').as_uri()+'?mode=ro', uri=True)) as db:
        intents = [json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='intent' ORDER BY seq")]
    root = CASE / 'normal_non_authoritative'
    terminals = {h: fixture.pin(root / f'obligation_non_authoritative/{h:03d}.terminal.json') for h in range(3)}
    binding = SimpleNamespace(binding_sha256=fixture.pin(root / 'obligation_non_authoritative/binding.json'),
        registry_identity=intents[0]['source_audit']['registry_identity'])
    args = dict(expected_binding_sha256=binding.binding_sha256, expected_terminals=terminals,
        selected_hours=(0, 1, 2), expected_registry_identity=binding.registry_identity)
    core.save(out, 'oracle_request.json', dict(arguments=args, full_successor_batches=1,
        independent_readers=2, parent_traversals=2, old_readers_rerun=0,
        static_identity_memo=False, saved_case_reused=True, one_field_packet_projection_standin=True,
        permitted_provenance_paths=[list(p) for p in core.ALLOWED_PATHS],
        oracle_scope='saved_raw_science_plus_original_join_projection_and_fresh_synthetic_source',
        actual_RTS_or_complete_192h=False, Jobs=0, native=0, formal_result=False))
    prefix = os.path.normcase(str(CASE))+os.sep
    activity = dict(case_read_opens=0, rejected_mutations=0)
    last_activity = [0.0]
    def within(value):
        return (isinstance(value, (str, bytes, os.PathLike)) and
            (os.path.normcase(os.path.abspath(os.fsdecode(value)))+os.sep).startswith(prefix))
    def audit(event, values):
        mutation = False
        if event == 'open' and within(values[0]):
            _, mode, flags = values
            mutation = ((isinstance(mode, str) and any(c in mode for c in 'wax+')) or
                (isinstance(flags, int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC))))
            activity['case_read_opens'] += not mutation
            now = time.monotonic()
            if not mutation and now-last_activity[0] >= 15:
                last_activity[0] = now
                (out / 'source_read_activity.json').write_text(json.dumps(dict(
                    case_read_opens=activity['case_read_opens'], monotonic_seconds=now,
                    evidence='read_open_activity_only_not_scientific_progress')), encoding='utf-8')
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime', 'os.truncate'):
            mutation = within(values[0])
        elif event in ('os.rename', 'os.link', 'os.symlink'):
            mutation = any(within(p) for p in values[:2])
        if mutation:
            activity['rejected_mutations'] += 1
            raise RuntimeError('saved-case filesystem mutation denied')
    sys.addaudithook(audit)
    patch, batch = pytest.MonkeyPatch(), None
    result, error = {}, None
    try:
        fixture.install_saved_fixture(patch)
        from experiments import h1_phase_exact_source_batch_development_v2 as new
        from experiments import h1_constructor_source_batch_validation_development_v1 as validator
        identity = new.implementation_identity()
        began = time.perf_counter()
        batch = new.prepare_many(root, **args)
        result['successor_batch_seconds'] = time.perf_counter()-began
        validator.validate_detached_batch(batch, binding, terminals, (0, 1, 2), identity)
        summaries = {}
        for h, current in batch.currents.items():
            summaries[h] = saved_scientific_oracle(current, intents[h]['source_audit'], h)
            with (out / f'new_hour_{h}_audit.json').open('xb') as stream:
                stream.write(current.source_projection_audit_payload)
        result.update(scientific_summaries=summaries, old_saved_science_bytes_equal=True,
            observations=batch.observations, new_implementation_identity=identity,
            validator_faults=core.audit_faults(new, validator, batch, binding, terminals, identity))
        assert len(result['validator_faults']) == 21
        assert all(m['parent_inspect_traversals'] == 1 for m in batch.observations)
        assert batch.observations[0]['observation_token'] != batch.observations[1]['observation_token']
    except BaseException:
        error = traceback.format_exc()
        (out / 'error.txt').write_text(error, encoding='utf-8')
    finally:
        if batch is not None:
            batch.currents.clear()
        patch.undo()
    after = fixture.inventory(CASE)
    accepted = error is None and before == after
    result.update(status='DRAFT_NONAUTHORITATIVE', exit_code=0 if accepted else 1, error=error,
        elapsed_seconds=time.perf_counter()-started, saved_case_files=465, owned_files=444,
        saved_case_sha256_equal=before == after, source_activity=activity,
        performance_comparison_completed=False, speedup_claim_supported=False,
        complete_dynamic_closure_proved=False, unobserved_ABA_covered=False,
        constructor_window_real_file_faults_complete=False, owner_integrated=False,
        full_192_hour_execution_verified=False, resource_admission=False,
        formal_execution_ready=False, Jobs=0, real_native_calls=0, formal_result=False)
    core.save(out, 'oracle_terminal.json', result)
    print(json.dumps(dict(exit_code=result['exit_code'], successor_batch_seconds=result.get('successor_batch_seconds'),
        science_equal=result.get('old_saved_science_bytes_equal'), data_faults=len(result.get('validator_faults', [])))), flush=True)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
