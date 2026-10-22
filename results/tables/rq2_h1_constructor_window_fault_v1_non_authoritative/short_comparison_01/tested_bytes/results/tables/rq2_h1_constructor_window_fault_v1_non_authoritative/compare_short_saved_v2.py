"""Fixed two-call one-hour, read-only saved-prefix comparison. Zero Job/native."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import traceback
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO / 'tests'))
import pytest

spec = importlib.util.spec_from_file_location('saved_profile_fixture',
    HERE.parent / 'rq2_h1_source_replay_cost_v1_non_authoritative/profile_saved_v1.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from experiments import h1_phase_exact_source_batch_development_v1 as old
from experiments import h1_cross_hour_owner_development_v2 as old_owner

CASE = fixture.CASE
ALLOWED_PATHS = (
    ('schema',), ('implementation_identity',), ('replay_contract',), ('normal_audit_identity',),
    ('historical_controller', 'replay_contract'),
    ('normal_audit_payload', 'historical_controller', 'replay_contract'))


def save(root, name, value):
    with (root / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def normalized(audit):
    result = deepcopy(audit)
    for path in ALLOWED_PATHS:
        item = result
        for key in path[:-1]:
            item = item[key]
        item[path[-1]] = '<declared-validation-provenance>'
    return old.io.encode(result)


def summary(current):
    prepared = current.prepared_current
    return dict(scientific_sha256=sha256(current.exogenous_scientific_payload).hexdigest(),
        decision_sha256=sha256(prepared.decision.decision_bytes).hexdigest(),
        frame=old.physical._digest(prepared.frame), origin=old.physical._digest(prepared.source_origin),
        action=old.physical._digest(prepared.source_action),
        workload_exact=old.prior._ratio(current.workload_exact),
        cfe_exact=old.prior._ratio(current.source_cfe_at_alpha_one_exact),
        normalized_audit_sha256=sha256(normalized(json.loads(current.source_projection_audit_payload))).hexdigest())


def main():
    out = Path(sys.argv[1]).resolve()
    assert out.parent == HERE and out.is_dir()
    started = time.perf_counter()
    before = fixture.inventory(CASE)
    postcheck = fixture.load(REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    assert before == postcheck['diagnostic_case_files_sha256'] and len(before) == 465
    checkpoint = fixture.load(CASE / 'external_preclose_checkpoint.json')
    assert len(checkpoint['saved_files_sha256']) == 444
    assert all(fixture.pin(path) == value for path, value in checkpoint['saved_files_sha256'].items())
    with closing(sqlite3.connect((CASE / 'owner_non_authoritative/owner.sqlite').as_uri()+'?mode=ro', uri=True)) as db:
        intents = [json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='intent' ORDER BY seq")]
    assert [row['hour'] for row in intents] == [0, 1, 2]
    root = CASE / 'normal_non_authoritative'
    terminals = {h: fixture.pin(root / f'obligation_non_authoritative/{h:03d}.terminal.json') for h in range(1)}
    binding = SimpleNamespace(binding_sha256=fixture.pin(root / 'obligation_non_authoritative/binding.json'),
        registry_identity=intents[0]['source_audit']['registry_identity'])
    args = dict(expected_binding_sha256=binding.binding_sha256, expected_terminals=terminals,
                selected_hours=(0,), expected_registry_identity=binding.registry_identity)
    assert fixture.pin(HERE / 'oracle_01/oracle_terminal.json') == '87f83f0c0f47e220ddf054766116f07fe2c43fa5c4c67d70ae752244919d903e'
    save(out, 'comparison_request.json', dict(root=str(root), arguments=args,
        order=['old', 'new'], full_source_batches=2, independent_readers=4,
        permitted_provenance_paths=[list(p) for p in ALLOWED_PATHS], synthetic_saved_fixture=True,
        manifest_pin_reused_without_real_source_reaudit=True, identity_fixture_targets=0,
        dynamic_source_or_history_cached=False, owner_integrated=False, formal_result=False))
    case_prefix = os.path.normcase(str(CASE))+os.sep
    audits = dict(old_case_read_opens=0, rejected_mutations=0)
    last_activity = [0.0]
    def within(value):
        return (isinstance(value, (str, bytes, os.PathLike)) and
                (os.path.normcase(os.path.abspath(os.fsdecode(value)))+os.sep).startswith(case_prefix))
    def audit(event, values):
        mutation = False
        if event == 'open' and within(values[0]):
            _, mode, flags = values
            mutation = ((isinstance(mode, str) and any(c in mode for c in 'wax+')) or
                (isinstance(flags, int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC))))
            audits['old_case_read_opens'] += not mutation
            now = time.monotonic()
            if not mutation and now-last_activity[0] >= 15:
                last_activity[0] = now
                (out / 'source_read_activity.json').write_text(json.dumps(dict(read_opens=audits['old_case_read_opens'], evidence='read_open_activity_only')), encoding='utf-8')
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime', 'os.truncate'):
            mutation = within(values[0])
        elif event in ('os.rename', 'os.link', 'os.symlink'):
            mutation = any(within(p) for p in values[:2])
        if mutation:
            audits['rejected_mutations'] += 1
            raise RuntimeError('saved-case filesystem mutation denied')
    sys.addaudithook(audit)
    patch = pytest.MonkeyPatch()
    rows, oracle, fault_checks, error = [], None, [], None
    result = {}
    try:
        fixture.install_saved_fixture(patch)
        # No static-identity memo: both paths pay their original identity cost.
        from experiments import h1_phase_exact_source_batch_development_v2 as new
        from experiments import h1_constructor_source_batch_validation_development_v1 as validator
        identity = new.implementation_identity()
        for ordinal, name in enumerate(('old', 'new')):
            module = old if name == 'old' else new
            began = time.perf_counter()
            batch = module.prepare_many(root, **args)
            elapsed = time.perf_counter()-began
            if name == 'new':
                validator.validate_detached_batch(batch, binding, terminals, (0,), identity)
            else:
                old_owner._validate_batch(batch, binding, terminals, (0,), old.implementation_identity())
            values = {}
            for h, current in batch.currents.items():
                raw = current.source_projection_audit_payload
                audit_value = json.loads(raw)
                assert old.io.encode(audit_value) == raw
                assert audit_value['schema'] == module.SCHEMA and audit_value['replay_contract'] == module.SCHEMA
                assert audit_value['implementation_identity'] == module.implementation_identity()
                assert audit_value['historical_controller']['replay_contract'] == module.historical.SCHEMA
                assert audit_value['normal_audit_payload']['historical_controller'] == audit_value['historical_controller']
                assert audit_value['normal_audit_identity'] == old.io.digest(old.io.encode(audit_value['normal_audit_payload']))
                assert normalized(audit_value) == normalized(intents[h]['source_audit'])
                assert current.exogenous_scientific_identity == intents[h]['source_audit']['exogenous_scientific_identity']
                if name == 'old':
                    assert raw == old.io.encode(intents[h]['source_audit'])
                values[h] = summary(current)
                with (out / f'call_{ordinal}_{name}_hour_{h}_audit.json').open('xb') as stream:
                    stream.write(raw)
            if oracle is None:
                oracle = values
            assert values == oracle
            expected = 2 if name == 'old' else 1
            assert len(batch.observations) == 2
            assert all(m['parent_inspect_traversals'] == expected for m in batch.observations)
            assert batch.observations[0]['observation_token'] != batch.observations[1]['observation_token']
            if name == 'new':
                assert all(m['normal_model_dependency_bookends_verified'] is True for m in batch.observations)
            row = dict(ordinal=ordinal, implementation=name, elapsed_seconds=elapsed,
                observations=batch.observations, scientific_summaries=values, equal_to_old_oracle=True)
            rows.append(row)
            with (out / 'progress.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row)+'\n')
            print(json.dumps(dict(call=ordinal, implementation=name, elapsed_seconds=elapsed)), flush=True)
            batch.currents.clear()
        result['new_implementation_identity'] = identity
    except BaseException:
        error = traceback.format_exc()
        (out / 'error.txt').write_text(error, encoding='utf-8')
    finally:
        patch.undo()
    after = fixture.inventory(CASE)
    accepted = error is None and len(rows) == 2 and before == after
    result.update(status='DRAFT_NONAUTHORITATIVE', exit_code=0 if accepted else 1,
        error=error, elapsed_seconds=time.perf_counter()-started, calls=rows,
        data_validator_fault_checks=[], malformed_evidence_reused_from='oracle_01/oracle_terminal.json', saved_case_files=len(before), saved_owned_files=444,
        saved_case_bytes_unchanged=before == after, audit=audits,
        fixed_old_then_new_order=True, repetitions_per_implementation=1, production_speedup_established=False, complete_dynamic_closure_proved=False, unobserved_ABA_covered=False,
        constructor_window_real_file_faults_complete=False, owner_integrated=False,
        full_192_hour_execution_verified=False, overall_performance_review_complete=False,
        resource_admission=False, formal_execution_ready=False, Jobs=0, real_native_calls=0, formal_result=False)
    save(out, 'comparison_terminal.json', result)
    print(json.dumps(dict(exit_code=result['exit_code'], full_batches=len(rows),
        data_fault_checks=len(fault_checks), saved_case_bytes_unchanged=before == after)), flush=True)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
