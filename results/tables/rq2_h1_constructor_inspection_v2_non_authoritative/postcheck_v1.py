"""Resolve preserved attempt bytes, saved case and prior exact evidence."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def resolve(bindings, snapshots=()):
    resolved = {}
    for name, expected in bindings.items():
        path = Path(name)
        choices = [path]
        try:
            relative = path.relative_to(REPO)
        except ValueError:
            relative = None
        if relative is not None:
            choices.extend(Path(root)/relative for root in snapshots)
        found = next((candidate for candidate in choices if candidate.is_file() and pin(candidate) == expected), None)
        if found is None:
            raise ValueError('unresolved exact evidence bytes: '+name)
        resolved[name] = dict(sha256=expected, resolved_path=str(found), live=found == path)
    return resolved


def main():
    attempts = {}
    for label in ('unit_01', 'unit_02', 'unit_03', 'unit_04', 'comparison_01', 'oracle_01', 'short_comparison_01'):
        root = HERE/label
        terminal, request = load(root/'terminal.json'), load(root/'request.json')
        assert not terminal['changed_sources'] and not terminal['observed_processes_remaining']
        assert terminal['new_normal_jobs'] == terminal['real_native_calls'] == 0
        resolved = resolve(request['sources_sha256'], (root/'tested_bytes', HERE/'canonical_before'))
        attempts[label] = dict(exit_code=terminal['exit_code'], reason=terminal['reason'],
            request_sha256=pin(root/'request.json'), terminal_sha256=pin(root/'terminal.json'),
            verified_pins=len(resolved), live_bindings=sum(v['live'] for v in resolved.values()),
            snapshot_bindings=sum(not v['live'] for v in resolved.values()), resolved=resolved)
    assert load(HERE/'unit_04/terminal.json')['junit'] == dict(tests=110, failures=0, errors=0, skipped=0, accepted=True)
    assert attempts['comparison_01']['exit_code'] == 15 and attempts['comparison_01']['reason'] == 'no_progress_limit'
    assert not (HERE/'comparison_01/comparison_terminal.json').exists()
    for label in ('oracle_01', 'short_comparison_01'):
        assert attempts[label]['exit_code'] == 0
    old_post = REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json'
    saved = load(old_post)['diagnostic_case_files_sha256']
    case = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    assert {str(p):pin(p) for p in case.rglob('*') if p.is_file()} == saved and len(saved) == 465
    owned = load(case/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(owned) == 444 and all(pin(path) == expected for path, expected in owned.items())
    before = HERE/'canonical_before'
    source_scope = REPO/'results/tables/rq2_h1_source_replay_cost_v1_non_authoritative'
    prior_final = load(source_scope/'final_verification.json')
    assert pin(prior_final['latest_core']) == prior_final['latest_core_sha256']
    prior_core = load(prior_final['latest_core'])
    prior_checks = {name: resolve(value['bindings'], (before,))
        for name, value in (('core',prior_core), ('final',prior_final))}
    preparation = {}
    for version in (1, 2, 3):
        path = HERE/f'formal_preparation_state_v{version}.json'
        value = load(path)
        bindings = dict(value['bindings'])
        source_name = str(HERE/'build_preparation_state_v1.py')
        source_binding = bindings.pop(source_name)
        source = HERE/(f'preparation_state_v{version}_source_before_review.py' if version < 3 else 'build_preparation_state_v1.py')
        assert pin(source) == source_binding
        checks = resolve(bindings, (before,))
        preparation[str(version)] = dict(path=str(path), sha256=pin(path),
            verified_bindings=len(checks)+1, historical_source=str(source), historical_source_sha256=source_binding,
            resolved=checks)
    assert load(HERE/'oracle_01_interpretation.json')['original_sha256'] == pin(HERE/'oracle_01/oracle_terminal.json')
    updates = load(HERE/'canonical_doc_updates.json')['updates']
    for row in updates:
        current, original = Path(row['path']).read_bytes(), Path(row['before_snapshot']).read_bytes()
        offset, length = row['insertion_offset'], row['insertion_length']
        assert current[:offset]+current[offset+length:] == original
        assert sha256(original).hexdigest() == row['before_sha256'] and sha256(current).hexdigest() == row['after_sha256']
    result = dict(status='DRAFT_NONAUTHORITATIVE', attempts=attempts,
        saved_case_files=465, saved_owned_files=444, saved_case_and_owned_sha256_unchanged=True,
        prior_source_cost_core_sha256=prior_final['latest_core_sha256'],
        prior_source_cost_core_bindings=len(prior_checks['core']), prior_source_cost_final_bindings=len(prior_checks['final']),
        prior_source_cost_resolved=prior_checks, preparation_inventory_resolution=preparation,
        all_preexisting_dirty_document_bytes_preserved=True,
        source_map_reuse_does_not_rerun_old_tests_or_proofs=True,
        full_nested_preregistration_source_reaudit_performed=False,
        real_native_calls=0, new_normal_jobs=0, formal_result=False)
    with (HERE/'postcheck_v1.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(attempts={k:{q:v[q] for q in ('exit_code','verified_pins','snapshot_bindings')} for k,v in attempts.items()},
        saved_files=465, owned_files=444, prior_core_bindings=len(prior_checks['core']), prior_final_bindings=len(prior_checks['final']),
        inventory_bindings={k:v['verified_bindings'] for k,v in preparation.items()})))


if __name__ == '__main__':
    main()
