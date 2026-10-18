"""Verify exact attempted bytes, saved science and the preregistered local adoption rule."""
from hashlib import sha256
import json
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE/'negative_handoff_performance_postcheck_01_non_authoritative'
OUT.mkdir(exist_ok=False)
rows = []
result = dict(exit_code=1, formal_result=False, resource_admission=False,
    full_hour0_chain_passed=False, native_execution_authorized=False)
try:
    for number in (3, 4, 5):
        plan_path = HERE/f'negative_handoff_alias_plan_{number:02d}.json'
        plan = json.loads(plan_path.read_bytes())
        outer = Path(plan['outer_output'])
        inner = Path(plan['inner_output'])
        terminal = json.loads((outer/'terminal.json').read_bytes())
        assert terminal['exit_code'] == terminal['child_exit_code'] == terminal['inner_exit_code'] == 0
        assert terminal['source_unchanged'] and terminal['old_chain_unchanged']
        assert terminal['observed_owned_processes_absent'] and not terminal['errors']
        for name, pin in plan['source_sha256'].items():
            path = Path(name)
            relative = path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
            tested = outer/'tested_bytes'/relative
            assert sha256(tested.read_bytes()).hexdigest() == pin
        if number == 5:
            assert all(sha256(Path(name).read_bytes()).hexdigest() == pin
                for name, pin in plan['source_sha256'].items())
        assert all(sha256(Path(name).read_bytes()).hexdigest() == pin
            for name, pin in plan['old_chain_sha256'].items())
        read_closed = json.loads((inner/'bounded_closed_receipt.json').read_bytes())
        assert read_closed['code_owner_closed'] and read_closed['path_open_restored'] and read_closed['path_read_bytes_restored']
        assert not read_closed['remaining_code_handles'] and not read_closed['remaining_streams'] and not read_closed['cleanup_errors']
        science, = Path(plan['basetemp']).rglob('science_sequence_non_authoritative/terminal.json')
        science_root = science.parent
        scientific = json.loads(science.read_bytes())
        records = [(science_root/'stages'/f'{index:04d}'/'selector_record.json').read_bytes()
            for index in range(len(scientific['record_sha256']))]
        assert [sha256(raw).hexdigest() for raw in records] == scientific['record_sha256']
        assert sha256((science_root/'binding.json').read_bytes()).hexdigest() == scientific['binding_sha256']
        assert sha256((science_root/'commits'/f'{len(records)-1:04d}.json').read_bytes()).hexdigest() == scientific['last_commit_sha256']
        times = []
        for line in (outer/'stdout.log').read_text(encoding='utf-8').splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if 'reference_seconds' in value:
                times.append(value)
        timing, = times
        assert timing['common_replays_during_rejection'] == timing['actuals_created'] == 0
        scientific_projection = {key:value for key,value in scientific.items()
            if key not in ('binding_sha256', 'last_commit_sha256')}
        saved = {str(path.relative_to(Path(plan['basetemp']))):sha256(path.read_bytes()).hexdigest()
            for path in Path(plan['basetemp']).rglob('*') if path.is_file()}
        with (OUT/f'saved_{number:02d}_sha256.json').open('x', encoding='utf-8') as stream:
            json.dump(saved, stream, indent=2)
        pure = json.loads((inner/'pure_digest_closed_receipt.json').read_bytes()) if number > 3 else None
        if pure:
            assert pure['remaining_keys'] == 0 and pure['failure'] is None
            assert pure['restored_aliases'] == ['experiments.h1_origin_grid_step_development_v1._digest']
            assert not pure['source_bytes_cached'] and not pure['numerical_audit_cached']
        rows.append(dict(number=number, plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
            outer_seconds=terminal['elapsed_seconds'], timing=timing, source_snapshots=len(plan['source_sha256']),
            code_paths_reopened=json.loads((inner/'terminal.json').read_bytes())['code_paths_reopened_for_write_without_writing'],
            lock_count=len(terminal['saved_locks_reacquired_and_released']), saved_files=len(saved),
            scientific_projection=scientific_projection, selector_record_sha256=scientific['record_sha256'],
            pure_receipt=pure))
    assert all(row['scientific_projection'] == rows[0]['scientific_projection'] for row in rows[1:])
    assert all(row['selector_record_sha256'] == rows[0]['selector_record_sha256'] for row in rows[1:])
    savings = 1-rows[-1]['outer_seconds']/rows[0]['outer_seconds']
    threshold = json.loads((HERE/'negative_handoff_alias_plan_05.json').read_bytes())['adoption_minimum_whole_entry_savings_fraction']
    result.update(exit_code=0, rows=rows, whole_entry_savings_fraction=savings,
        minimum_adoption_savings_fraction=threshold, representative_path_gain_established=savings >= threshold,
        pure_memo_decision='eligible_for_next_bounded_validation' if savings >= threshold else 'not_adopted_stop_this_branch',
        same_saved_scientific_projection=True, all_selector_records_exact_bytes=True,
        archive_identifiers_checked_per_root=True, pure_memo_full_positive_handoff_validated=False,
        sample_design='one fixed historical baseline and two changed candidates; old chain concurrent; no repeated timing statistics')
except BaseException:
    result['error'] = traceback.format_exc()
with (OUT/'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({key:value for key,value in result.items() if key != 'rows'}))
raise SystemExit(result['exit_code'])
