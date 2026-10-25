"""Source-bound, finite ordinary direct-file checks; retain every attempt."""
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
    path = OUT/name; assert not path.exists(), name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def capture(label, args, limit, nodes=None):
    assert not (OUT/(label+'.exit.json')).exists()
    selected = entry.source_pins(); folder = OUT/(label+'_snapshot'); folder.mkdir(); images = {}
    for name in entry.NEW_SOURCES[:3]:
        raw = (ROOT/name).read_bytes(); target = folder/(Path(name).parent.name+'_'+Path(name).name+'.snapshot')
        target.write_bytes(raw); images[name] = dict(snapshot=target.relative_to(ROOT).as_posix(), pin=entry.pin(raw))
    save(label+'.snapshot.json', dict(sources=images))
    argv = [str(entry.EXE), '-B', '-m', 'pytest', *args, '-p', 'no:cacheprovider',
        '-o', 'tmp_path_retention_count=100000', '-o', 'tmp_path_retention_policy=all']
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, timeout=limit)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b'', error.stderr or b'', None, True
    elapsed = time.monotonic()-start
    (OUT/(label+'.stdout.log')).write_bytes(stdout); (OUT/(label+'.stderr.log')).write_bytes(stderr)
    value = dict(authority='DRAFT_NONAUTHORITATIVE', scope='ordinary file-entry development only', argv=argv,
        nodes=nodes, exit_code=code, timed_out=timed_out, wall_seconds=elapsed, timeout_seconds=limit,
        source_pins=selected, source_pins_unchanged=selected == entry.source_pins(), snapshot_manifest=label+'.snapshot.json',
        actual_saved_F_execution=False, F_launch_admitted=False)
    save(label+'.exit.json', value)
    return value, stdout


def collect():
    result, stdout = capture('collection_01', ['--collect-only', '-q', TARGET, GUARD], 15)
    assert result['exit_code'] == 0
    nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
    save('collected_nodes.json', nodes)
    groups = dict(file_units_01=[n for n in nodes if n.startswith(TARGET+'::test_file_entry_')],
        file_smoke_02=[TARGET+'::test_invocation_real_external_host_holds_context_and_observes_complete_graph'])
    save('group_admission_01.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups,
        caps=dict(file_units_01=30, file_smoke_02=15), pytest_total_seconds=240, static_total_seconds=60,
        whole_development_seconds=300, automatic_actor_retries=0, actual_saved_F_execution=False))
    print(json.dumps({key: len(value) for key, value in groups.items()}))


if __name__ == '__main__':
    if sys.argv[1:] == ['collect']: collect()
    else:
        plan = json.loads((OUT/sys.argv[1]).read_bytes()); label = sys.argv[2]
        result, _ = capture(label, ['-q', '-s', '--durations=10', *plan['groups'][label]], plan['caps'][label], plan['groups'][label])
        print(json.dumps({key: result[key] for key in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
        raise SystemExit(0 if result['exit_code'] == 0 and result['source_pins_unchanged'] else 1)
