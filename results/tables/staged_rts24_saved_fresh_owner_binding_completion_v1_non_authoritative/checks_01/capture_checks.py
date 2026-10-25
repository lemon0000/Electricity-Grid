"""One source-frozen binding verification packet, never a saved F actor."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNER = ROOT/'results/tables/staged_rts24_saved_fresh_owner_v1_non_authoritative/checks_01'
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_saved_fresh_adoption_v1 as entry


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def save(name, value):
    path = OUT/name; assert not path.exists(), name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def capture(label, argv, limit, nodes=None):
    assert not (OUT/(label+'.exit.json')).exists()
    selected = entry.source_pins(); images = {}; folder = OUT/(label+'_snapshot'); folder.mkdir()
    for name in entry.NEW_SOURCES[:3]:
        raw = (ROOT/name).read_bytes(); snapshot = folder/(Path(name).parent.name+'_'+Path(name).name+'.snapshot')
        snapshot.write_bytes(raw); images[name] = dict(snapshot=snapshot.relative_to(ROOT).as_posix(), pin=pin(raw))
    save(label+'.snapshot.json', dict(sources=images))
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, timeout=limit)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b'', error.stderr or b'', None, True
    elapsed = time.monotonic()-start
    for suffix, raw in [('stdout.log', stdout), ('stderr.log', stderr)]: (OUT/(label+'.'+suffix)).write_bytes(raw)
    value = dict(authority='DRAFT_NONAUTHORITATIVE', argv=argv, exit_code=code, timed_out=timed_out,
        wall_seconds=elapsed, timeout_seconds=limit, nodes=nodes, source_pins=selected,
        source_pins_unchanged=selected == entry.source_pins(), snapshot_manifest=label+'.snapshot.json',
        actual_saved_F_execution=False, F_launch_admitted=False)
    save(label+'.exit.json', value)
    print(json.dumps({k:value[k] for k in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
    assert code == 0 and not timed_out and value['source_pins_unchanged']
    return value


def prepare():
    current = entry.source_pins(); previous = json.loads((OWNER/'development_summary.json').read_bytes())
    assert current == previous['source_pins'] and previous['current_epoch_terminal_nodes'] == 143
    nodes = json.loads((OWNER/'group_admission_06.json').read_bytes())['groups']['binding_affected_01']
    assert len(nodes) == len(set(nodes)) == 18 and not set(nodes)&set(previous['final_nodeids'])
    assert set(nodes) <= set(json.loads((OWNER/'collected_nodes_03.json').read_bytes()))
    preserved = json.loads((OWNER/'preservation_inventory.json').read_bytes())
    for path in OWNER.parent.rglob('*'):
        if path.is_file(): preserved[path.relative_to(ROOT).as_posix()] = pin(path.read_bytes())
    for name in json.loads((OWNER/'document_checks.json').read_bytes())['document_pins']:
        preserved[name] = pin((ROOT/name).read_bytes())
    save('preservation_inventory.json', preserved)
    navigation = {}
    for name in json.loads((OWNER/'navigation_before.json').read_bytes()):
        head, _, body = (ROOT/name).read_bytes().partition(b'\n\n')
        navigation[name] = dict(header=head.decode(), body=pin(body))
    save('navigation_before.json', navigation)
    save('admission.json', dict(authority='DRAFT_NONAUTHORITATIVE', nodes=nodes, source_pins=current,
        pytest_cap_seconds=45, static_cap_seconds=15, whole_cap_seconds=60,
        predecessor_terminal_nodes=143, automatic_actor_retries=0, actual_saved_F_execution=False, F_launch_admitted=False))
    capture('baseline_owner_01', [str(entry.EXE), '-B', str(OWNER/'saved_checks.py')], 5)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']: prepare()
    elif sys.argv[1:] == ['run']:
        plan = json.loads((OUT/'admission.json').read_bytes())
        assert entry.source_pins() == plan['source_pins']
        capture('binding_completion_01', [str(entry.EXE), '-B', '-m', 'pytest', '-q', '-s', '--durations=10',
            *plan['nodes'], '-p', 'no:cacheprovider', '-o', 'tmp_path_retention_count=100000',
            '-o', 'tmp_path_retention_policy=all'], 45, plan['nodes'])
    else: raise SystemExit('prepare or run required')
