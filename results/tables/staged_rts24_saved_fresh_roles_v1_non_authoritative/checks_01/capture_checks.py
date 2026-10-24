"""Capture successor ordinary checks, keeping every attempt and source epoch."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_saved_fresh_adoption_v1 as entry
TARGET = 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'
GUARD = 'tests/test_staged_rts24_process_guard_v1.py'


def save(name, value):
    (OUT/name).write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode('utf-8'))


def capture(label, args, limit, nodes=None):
    assert not (OUT/(label+'.exit.json')).exists()
    selected = entry.source_pins(); snapshots = {}; directory = OUT/(label+'_snapshot'); directory.mkdir()
    for name in entry.NEW_SOURCES[:3]:
        raw = (ROOT/name).read_bytes(); path = directory/(Path(name).parent.name+'_'+Path(name).name+'.snapshot')
        path.write_bytes(raw); snapshots[name] = dict(snapshot=path.relative_to(ROOT).as_posix(), pin=entry.pin(raw))
    save(label+'.snapshot.json', dict(sources=snapshots))
    argv = [str(entry.EXE), '-B', '-m', 'pytest', *args, '-p', 'no:cacheprovider',
        '-o', 'tmp_path_retention_count=100000', '-o', 'tmp_path_retention_policy=all']
    started = time.monotonic()
    try:
        run = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, timeout=limit)
        stdout, stderr, code, timed_out = run.stdout, run.stderr, run.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b'', error.stderr or b'', None, True
    elapsed = time.monotonic()-started
    (OUT/(label+'.stdout.log')).write_bytes(stdout); (OUT/(label+'.stderr.log')).write_bytes(stderr)
    result = dict(authority='DRAFT_NONAUTHORITATIVE', argv=argv, timeout_seconds=limit, wall_seconds=elapsed,
        exit_code=code, timed_out=timed_out, nodes=nodes, source_pins=selected,
        source_pins_unchanged=entry.source_pins() == selected, snapshot_manifest=label+'.snapshot.json',
        scope='successor ordinary role graph and regression checks', F_launch_admitted=False, new_F_workflow_executed=False)
    save(label+'.exit.json', result)
    return result, stdout


def collect():
    result, stdout = capture('collection_01', ['--collect-only', '-q', TARGET, GUARD], 15)
    assert result['exit_code'] == 0
    nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
    selected = {'test_complete_metrics_comparison_retains_missing_input_and_closed_gates',
        'test_one_saved_parent_adapter_matches_all_original_metrics_without_effects',
        'test_context_binds_actual_compute_executable_inputs_sources_and_budget',
        'test_unknown_quiet_safety_accounting_reads_metadata_only',
        'test_safety_accounting_rejects_unbounded_or_unexpected_outputs',
        'test_record_pending_consumes_one_slot_without_double_charging',
        'test_context_cannot_extend_deadline_by_rehashing',
        'test_actual_entry_and_expanded_arguments_are_bound',
        'test_actual_test_argv_cannot_enter_F_execution_or_adoption',
        'test_entry_import_bootstrap_does_not_load_project_or_scientific_modules',
        'test_bootstrap_environment_matches_the_bound_original_without_importing_it',
        'test_scientific_failure_always_checks_final_inputs_and_preserves_both_errors'}
    groups = dict(roles_01=[n for n in nodes if n.startswith(TARGET+'::test_role_')],
        stages_02=[n for n in nodes if n.startswith(TARGET+'::test_stage_') or n.startswith(GUARD+'::')],
        adapter_03=[n for n in nodes if n.startswith(TARGET+'::') and n.split('::')[1].split('[')[0] in selected])
    flat = [n for group in groups.values() for n in group]
    assert len(flat) == len(set(flat)) and all(groups.values())
    save('group_admission_01.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups,
        caps=dict(roles_01=60, stages_02=60, adapter_03=90), pytest_total_seconds=240,
        static_collection_seconds=60, successor_total_seconds=300, automatic_retries=0,
        historical_stage_owner_groups_reused_as_budget=False, F_launch_admitted=False))
    print(json.dumps(dict(groups={name: len(group) for name, group in groups.items()})))


if __name__ == '__main__':
    if sys.argv[1:] == ['collect']: collect()
    else:
        admission = json.loads((OUT/'group_admission_03.json').read_bytes()); label = sys.argv[1]
        result, _ = capture(label, ['-q', '-s', '--durations=12', *admission['groups'][label]],
            admission['caps'][label], admission['groups'][label])
        print(json.dumps({key: result[key] for key in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
        raise SystemExit(0 if result['exit_code'] == 0 and result['source_pins_unchanged'] else 1)
