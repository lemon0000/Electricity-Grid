"""Resolve exact executed/prior bytes and clarify generator provenance."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = HERE.parent / 'rq2_h1_constructor_inspection_v2_non_authoritative'


def load(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def resolve(mapping, snapshots):
    answer = {}
    for name, expected in mapping.items():
        path = Path(name)
        choices = [path]
        try:
            relative = path.relative_to(REPO)
        except ValueError:
            relative = None
        if relative is not None:
            choices += [root / relative for root in snapshots]
        found = next((p for p in choices if p.is_file() and pin(p) == expected), None)
        if found is None:
            raise ValueError('unresolved exact evidence: '+name)
        answer[name] = dict(sha256=expected, resolved_path=str(found), live=found == path)
    return answer


def main():
    attempts = {}
    snapshots = [HERE / 'before_edit', HERE / 'canonical_before', PRIOR / 'canonical_before']
    labels = ('probe_01', 'model_units_01', 'model_units_02', 'probe_02',
              'oracle_01', 'short_comparison_01', 'runtime_probe_01')
    for label in labels:
        root = HERE / label
        terminal, request = load(root / 'terminal.json'), load(root / 'request.json')
        assert terminal['exit_code'] == 0 and terminal['reason'] is None
        assert not terminal['changed_sources'] and not terminal['observed_processes_remaining']
        assert terminal['new_normal_jobs'] == terminal['real_native_calls'] == 0
        found = resolve(request['sources_sha256'], [root / 'tested_bytes', *snapshots])
        attempts[label] = dict(request_sha256=pin(root / 'request.json'),
            terminal_sha256=pin(root / 'terminal.json'), executed_after_source_pins_unchanged=True,
            verified_pins=len(found), current_live_pins=sum(v['live'] for v in found.values()),
            preserved_snapshot_pins=sum(not v['live'] for v in found.values()), resolved=found)
    prior_final_path = PRIOR / 'final_verification.json'
    prior_final = load(prior_final_path)
    assert pin(prior_final_path) == 'f6680d1110a9525e3727ccad49a3b0bdf131763923bd1b49d21ad6d8c564e0e7'
    assert pin(prior_final['latest_core']) == prior_final['latest_core_sha256']
    prior_core = load(prior_final['latest_core'])
    prior_resolved = {key: resolve(value['bindings'], snapshots)
                      for key, value in (('core', prior_core), ('final', prior_final))}
    assert len(prior_resolved['core']) == 157 and len(prior_resolved['final']) == 164
    # The immediately earlier scope already resolved the older source-cost
    # core/final through its own exact canonical snapshots. Recheck that receipt
    # and those complete top-level binding maps, without rerunning old bodies.
    source_final_path = HERE.parent / 'rq2_h1_source_replay_cost_v1_non_authoritative/final_verification.json'
    source_final = load(source_final_path)
    assert pin(source_final['latest_core']) == source_final['latest_core_sha256']
    source_core = load(source_final['latest_core'])
    source_resolved = {key: resolve(value['bindings'], snapshots)
                       for key, value in (('core', source_core), ('final', source_final))}
    assert len(source_resolved['core']) == 56 and len(source_resolved['final']) == 59
    post = load(REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    case = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    expected_case = post['diagnostic_case_files_sha256']
    assert {str(p): pin(p) for p in case.rglob('*') if p.is_file()} == expected_case
    owned = load(case / 'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(expected_case) == 465 and len(owned) == 444
    assert all(pin(name) == expected for name, expected in owned.items())
    for row in load(HERE / 'canonical_doc_updates.json')['updates']:
        current, before = Path(row['path']).read_bytes(), Path(row['before_snapshot']).read_bytes()
        offset, length = row['insertion_offset'], row['insertion_length']
        assert current[:offset]+current[offset+length:] == before
        assert sha256(before).hexdigest() == row['before_sha256']
        assert sha256(current).hexdigest() == row['after_sha256']
    preparation = load(HERE / 'short_harness_preparation.json')
    original = Path(preparation['original_harness'])
    target = Path(preparation['target'])
    assert pin(original) == preparation['original_harness_sha256']
    assert pin(target) == preparation['target_sha256']
    expected = original.read_text(encoding='utf-8')
    before = "    assert fixture.pin(HERE / 'oracle_01/oracle_terminal.json') == 'a6850603e74592f486d5e427c9d5ea3f8c204ef91bee37fa5c61b1169376da91'"
    after = "    assert fixture.pin(HERE / 'oracle_01/oracle_terminal.json') == '"+preparation['oracle_sha256']+"'"
    assert expected.count(before) == 1
    expected = expected.replace(before, after)
    before = "            assert batch.observations[0]['observation_token'] != batch.observations[1]['observation_token']"
    after = before+"\n            if name == 'new':\n                assert all(m['normal_model_dependency_bookends_verified'] is True for m in batch.observations)"
    assert expected.count(before) == 1
    expected = expected.replace(before, after)
    assert expected.encode('utf-8') == target.read_bytes()
    assert ast.dump(ast.parse(expected)) == ast.dump(ast.parse(target.read_text(encoding='utf-8')))
    provenance_sources = [HERE / 'prepare_short_comparison_v1.py', HERE / 'short_harness_preparation.json', original]
    short_request = load(HERE / 'short_comparison_01/request.json')['sources_sha256']
    short_correction = dict(status='DRAFT_NONAUTHORITATIVE', original_record=preparation,
        complete_byte_change_description=['two declared semantic substitutions', 'CRLF normalized to LF throughout generated worker'],
        original_CRLF_count=original.read_bytes().count(b'\r\n'), target_CRLF_count=target.read_bytes().count(b'\r\n'),
        exact_generated_worker_reproduced=True, AST_changes_match_declared_substitutions=True,
        missing_from_execution_request=[str(p) for p in provenance_sources if str(p) not in short_request],
        independently_bound_provenance={str(p): pin(p) for p in provenance_sources},
        execution_request_already_bound_actual_worker=True, execution_receipts_modified=False,
        correction_scope='outer provenance clarification; execution remains unchanged', formal_result=False)
    save('short_harness_provenance_correction_v1.json', short_correction)
    runtime = load(HERE / 'runtime_harness_preparation.json')
    generated = Path(runtime['runner_source']).read_bytes().replace(b'probe_saved_v1.py', b'probe_runtime_saved_v1.py')
    generated = generated.replace(b'two_saved_one_hour_historical_readers_constructor_window_dependency_alias_fault',
        b'two_saved_H1_historical_readers_constructor_return_external_metadata_version_fault')
    assert sha256(generated).hexdigest() == runtime['runner_target_sha256']
    generated_path = HERE / 'runtime_runner_generated_before_pin.py'
    with generated_path.open('xb') as stream:
        stream.write(generated)
    before = "new = [Path(__file__), HERE / 'design_and_budget.md', HERE / 'probe_runtime_saved_v1.py',"
    after = before+"\n       HERE / 'prepare_runtime_probe_v1.py', HERE / 'runtime_harness_preparation.json',\n       HERE / 'probe_saved_v1.py', HERE / 'run_probe_v1.py',"
    expected = generated.decode('utf-8').replace('\r\n', '\n')
    assert expected.count(before) == 1
    expected = expected.replace(before, after)
    actual = Path(runtime['runner_target'])
    assert expected == actual.read_text(encoding='utf-8')
    runtime_request = load(HERE / 'runtime_probe_01/request.json')
    assert runtime_request['sources_sha256'][str(actual)] == pin(actual)
    runtime_correction = dict(status='DRAFT_NONAUTHORITATIVE',
        generator_output_runner=str(generated_path), generator_output_sha256=pin(generated_path),
        original_record_runner_hash_describes_generator_output_only=True,
        actual_executed_runner=str(actual), actual_executed_runner_sha256=pin(actual),
        added_before_launch=['prepare_runtime_probe_v1.py', 'runtime_harness_preparation.json', 'probe_saved_v1.py', 'run_probe_v1.py'],
        normalized_program_diff_exactly_reproduced=True,
        generated_CRLF_count=generated.count(b'\r\n'), actual_CRLF_count=actual.read_bytes().count(b'\r\n'),
        execution_request_and_tested_bytes_match_actual_runner=True,
        original_record_and_execution_receipts_modified=False, formal_result=False)
    save('runtime_harness_provenance_correction_v1.json', runtime_correction)
    result = dict(status='DRAFT_NONAUTHORITATIVE', attempts=attempts,
        saved_case_files=465, saved_owned_files=444, saved_case_and_owned_sha256_unchanged=True,
        previous_constructor_final_sha256=pin(prior_final_path), previous_constructor_resolved=prior_resolved,
        previous_source_cost_resolved=source_resolved,
        two_prior_dirty_canonical_documents_exact_bytes_preserved=True,
        whole_dirty_worktree_preservation_claimed=False,
        short_provenance_correction_sha256=pin(HERE / 'short_harness_provenance_correction_v1.json'),
        runtime_provenance_correction_sha256=pin(HERE / 'runtime_harness_provenance_correction_v1.json'),
        source_map_reuse_does_not_rerun_prior_bodies=True, full_nested_preregistration_source_reaudit_performed=False,
        new_normal_jobs=0, real_native_calls=0, formal_result=False)
    save('postcheck_v1.json', result)
    print(json.dumps(dict(attempts={k:{q:v[q] for q in ('verified_pins','preserved_snapshot_pins')} for k,v in attempts.items()},
        prior_constructor_core_final=[157,164], prior_source_core_final=[56,59],
        saved_files=465, owned_files=444, provenance_clarifications=2)))


if __name__ == '__main__':
    main()
