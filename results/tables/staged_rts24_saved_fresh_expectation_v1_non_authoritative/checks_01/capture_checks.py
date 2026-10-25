"""Bounded ordinary expectation checks; source epochs and all failures retained."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_supervisor_budget_v1_non_authoritative/checks_01'
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_saved_fresh_adoption_v1 as entry


def save(name, value):
    path = OUT/name; assert not path.exists(), name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def capture(label, kind, argv, cap, nodes=None):
    assert kind in ('pytest', 'static') and 0 < cap <= 40
    spent = sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
        if json.loads(p.read_bytes())['kind'] == kind)
    assert spent+cap <= (160 if kind == 'pytest' else 40)
    assert not (OUT/(label+'.exit.json')).exists()
    source = entry.source_pins(); names = entry.NEW_SOURCES[:3]
    epoch = sha256(entry.canonical({n:source[n] for n in names})).hexdigest()
    folder = OUT/'source_epochs'/epoch; folder.mkdir(parents=True, exist_ok=True); images = {}
    for name in names:
        raw = (ROOT/name).read_bytes(); path = folder/(Path(name).parent.name+'_'+Path(name).name+'.snapshot')
        if path.exists(): assert path.read_bytes() == raw
        else: path.write_bytes(raw)
        images[name] = dict(snapshot=path.relative_to(ROOT).as_posix(), pin=entry.pin(raw))
    save(label+'.snapshot.json', dict(sources=images))
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, timeout=cap)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b'', error.stderr or b'', None, True
    elapsed = time.monotonic()-start
    for suffix, raw in [('stdout.log', stdout), ('stderr.log', stderr)]: (OUT/(label+'.'+suffix)).write_bytes(raw)
    value = dict(authority='DRAFT_NONAUTHORITATIVE', kind=kind, argv=argv, nodes=nodes, exit_code=code,
        timed_out=timed_out, wall_seconds=elapsed, timeout_seconds=cap, source_pins=source,
        source_pins_unchanged=source == entry.source_pins(), source_epoch=epoch,
        snapshot_manifest=label+'.snapshot.json', actual_saved_F_execution=False, F_launch_admitted=False)
    save(label+'.exit.json', value)
    print(json.dumps({k:value[k] for k in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
    assert code == 0 and not timed_out and value['source_pins_unchanged']
    return value


if __name__ == '__main__':
    if sys.argv[1:] == ['baseline']:
        capture('baseline_01', 'static', [str(entry.EXE), '-B', str(PRIOR/'saved_checks.py')], 8)
    elif sys.argv[1] == 'static':
        label, script, cap = sys.argv[2:]
        capture(label, 'static', [str(entry.EXE), '-B', str(OUT/script)], float(cap))
    else:
        plan = json.loads((OUT/sys.argv[1]).read_bytes()); label = sys.argv[2]; nodes = plan['groups'][label]
        capture(label, 'pytest', [str(entry.EXE), '-B', '-m', 'pytest', '-q', '-s', '--durations=10', *nodes,
            '-p', 'no:cacheprovider', '-o', 'tmp_path_retention_count=100000', '-o', 'tmp_path_retention_policy=all'],
            plan['caps'][label], nodes)
