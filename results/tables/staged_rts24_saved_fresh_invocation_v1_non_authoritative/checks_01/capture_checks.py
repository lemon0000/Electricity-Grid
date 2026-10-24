"""Bounded ordinary invocation checks; preserve every raw attempt/source epoch."""
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
    target = OUT/name
    assert not target.exists(), name
    target.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


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
        scope='ordinary external invocation and affected regressions only', F_launch_admitted=False, new_F_workflow_executed=False)
    save(label+'.exit.json', result)
    return result, stdout


def collect():
    result, stdout = capture('collection_01', ['--collect-only', '-q', TARGET, GUARD], 15)
    assert result['exit_code'] == 0
    nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
    graph_names = {'test_invocation_real_external_host_holds_context_and_observes_complete_graph',
        'test_invocation_native_wait_in_constructor_or_publication_is_stopped_by_external_job',
        'test_invocation_ready_expires_and_cannot_be_reused_or_serialized',
        'test_invocation_host_resource_failure_never_reads_return', 'test_invocation_unknown_actual_quiet_blocks_return_consumption'}
    prior = json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01/group_admission_03.json').read_bytes())
    groups = dict(invocation_units_01=[n for n in nodes if n.startswith(TARGET+'::test_invocation_') and n.split('::')[1].split('[')[0] not in graph_names],
        invocation_graph_02=[n for n in nodes if n.split('::')[1].split('[')[0] in graph_names],
        roles_03=[n for n in nodes if n.startswith(TARGET+'::test_role_')],
        stages_04=[n for n in nodes if n.startswith(TARGET+'::test_stage_') or n.startswith(GUARD+'::')],
        adapter_05=prior['groups']['adapter_06'])
    flat = [n for group in groups.values() for n in group]
    assert len(flat) == len(set(flat)) and all(groups.values()) and set(flat) <= set(nodes)
    save('group_admission_01.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups,
        caps=dict(invocation_units_01=30, invocation_graph_02=60, roles_03=60, stages_04=30, adapter_05=60),
        pytest_total_seconds=240, static_collection_seconds=60, successor_total_seconds=300,
        automatic_retries=0, F_launch_admitted=False))
    print(json.dumps(dict(groups={name: len(group) for name, group in groups.items()})))


if __name__ == '__main__':
    if sys.argv[1:] == ['collect']: collect()
    elif sys.argv[1:] == ['collect_final']:
        result, stdout = capture('collection_02', ['--collect-only', '-q', TARGET, GUARD], 15)
        assert result['exit_code'] == 0
        nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
        graph_names = {'test_invocation_real_external_host_holds_context_and_observes_complete_graph',
            'test_invocation_native_wait_in_constructor_or_publication_is_stopped_by_external_job',
            'test_invocation_wrong_host_ack_is_diagnosed_before_controller_construct'}
        edge_names = {'test_invocation_ready_expires_and_cannot_be_reused_or_serialized',
            'test_invocation_host_resource_failure_never_reads_return', 'test_invocation_unknown_actual_quiet_blocks_return_consumption'}
        invocation = [n for n in nodes if n.startswith(TARGET+'::test_invocation_')]
        groups = dict(invocation_units_04=[n for n in invocation if n.split('::')[1].split('[')[0] not in graph_names|edge_names],
            invocation_graph_05=[n for n in invocation if n.split('::')[1].split('[')[0] in graph_names],
            invocation_edges_06=[n for n in invocation if n.split('::')[1].split('[')[0] in edge_names])
        used = sum(json.loads((OUT/(label+'.exit.json')).read_bytes())['wall_seconds']
            for label in ('invocation_units_01', 'invocation_graph_02', 'affected_diagnostic_03'))
        save('group_admission_03.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups,
            caps=dict(invocation_units_04=30, invocation_graph_05=30, invocation_edges_06=20), previous_pytest_seconds=used,
            remaining_pytest_seconds=240-used, automatic_retries=0,
            scope='fixed bounded writer lock, continuous terminal prefix, kernel ready identities, actual constructor wait marker'))
        print(json.dumps({name: len(group) for name, group in groups.items()}))
    else:
        admission = json.loads((OUT/sys.argv[1]).read_bytes()); label = sys.argv[2]
        result, _ = capture(label, ['-q', '-s', '--durations=10', *admission['groups'][label]],
            admission['caps'][label], admission['groups'][label])
        print(json.dumps({key: result[key] for key in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
        raise SystemExit(0 if result['exit_code'] == 0 and result['source_pins_unchanged'] else 1)
