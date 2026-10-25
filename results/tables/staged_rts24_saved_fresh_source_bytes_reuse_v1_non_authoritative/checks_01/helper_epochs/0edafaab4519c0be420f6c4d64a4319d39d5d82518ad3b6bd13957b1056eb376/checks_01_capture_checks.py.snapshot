"""Bounded ordinary checks with source and executed-helper byte snapshots."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_expectation_v1_non_authoritative/checks_01'
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_saved_fresh_adoption_v1 as entry


def read(name):
    return json.loads((OUT/name).read_bytes())


def save(name, value):
    path = OUT/name
    assert not path.exists(), name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def snapshot(path, folder):
    raw = path.read_bytes()
    target = OUT/folder/sha256(raw).hexdigest()/(path.parent.name+'_'+path.name+'.snapshot')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)
    return dict(snapshot=target.relative_to(ROOT).as_posix(), pin=entry.pin(raw))


def capture(label, kind, argv, cap, nodes=None):
    assert kind in ('pytest','static') and 0 < cap <= 40
    spent = sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
        if json.loads(p.read_bytes())['kind'] == kind)
    assert spent+cap <= (160 if kind == 'pytest' else 40)
    assert not (OUT/(label+'.exit.json')).exists()
    source = entry.source_pins()
    images = {name:snapshot(ROOT/name, 'source_epochs') for name in entry.NEW_SOURCES[:3]}
    helpers = {Path(__file__).resolve()}
    if len(argv) > 2 and argv[2].endswith('.py'):
        helpers.add(Path(argv[2]).absolute())
    helper_images = {p.relative_to(ROOT).as_posix():snapshot(p,'helper_epochs') for p in helpers}
    save(label+'.snapshot.json', dict(sources=images, helpers=helper_images))
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, timeout=cap)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b'', error.stderr or b'', None, True
    elapsed = time.monotonic()-start
    for suffix, raw in [('stdout.log',stdout),('stderr.log',stderr)]:
        (OUT/(label+'.'+suffix)).write_bytes(raw)
    value = dict(authority='DRAFT_NONAUTHORITATIVE', kind=kind, argv=argv, nodes=nodes,
        exit_code=code, timed_out=timed_out, wall_seconds=elapsed, timeout_seconds=cap,
        source_pins=source, source_raw_bytes=sum(p['bytes'] for p in source.values()),
        source_pins_unchanged=source==entry.source_pins(),
        source_epoch=sha256(entry.canonical({n:source[n] for n in entry.NEW_SOURCES[:3]})).hexdigest(),
        snapshot_manifest=label+'.snapshot.json', helper_pins={n:i['pin'] for n,i in helper_images.items()},
        helper_pins_unchanged=all(entry.pin((ROOT/n).read_bytes())==i['pin'] for n,i in helper_images.items()),
        actual_saved_F_execution=False,F_launch_admitted=False)
    save(label+'.exit.json',value)
    print(json.dumps({k:value[k] for k in ('exit_code','timed_out','wall_seconds','source_pins_unchanged','helper_pins_unchanged')}))
    assert code == 0 and not timed_out and value['source_pins_unchanged'] and value['helper_pins_unchanged']


if __name__ == '__main__':
    if sys.argv[1:] == ['baseline']:
        capture('baseline_01','static',[str(entry.EXE),'-B',str(PRIOR/'saved_checks.py')],8)
    elif sys.argv[1] == 'static':
        label, script, cap = sys.argv[2:]
        capture(label,'static',[str(entry.EXE),'-B',str(OUT/script)],float(cap))
    else:
        plan = read(sys.argv[1]); label = sys.argv[2]
        capture(label,'pytest',[str(entry.EXE),'-B','-m','pytest','-q','-s','--durations=10',*plan['groups'][label],
            '-p','no:cacheprovider','-o','tmp_path_retention_count=100000','-o','tmp_path_retention_policy=all'],
            plan['caps'][label],plan['groups'][label])
