"""Finite stdlib-only admission checks, never a saved F actor."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_owner_binding_completion_v1_non_authoritative/checks_01'


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def save(name, value):
    path = OUT/name; assert not path.exists(), name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def main():
    label, script, cap = sys.argv[1:]; cap = float(cap)
    spent = sum(json.loads(p.read_bytes())['capture_seconds'] for p in OUT.glob('*.exit.json'))
    assert 0 < cap <= 15 and spent+cap <= 90
    assert not (OUT/(label+'.exit.json')).exists()
    start = time.monotonic()
    selected = json.loads((PRIOR/'admission.json').read_bytes())['source_pins']
    assert all(pin((ROOT/n).read_bytes()) == expected for n, expected in selected.items())
    target = PRIOR/'saved_checks.py' if script == ':previous' else OUT/script
    image = target.read_bytes(); snapshot = OUT/(label+'.script.snapshot'); snapshot.write_bytes(image)
    folder = OUT/(label+'_source'); folder.mkdir(); images = {}
    for name in ('src/staged_rts24_saved_fresh_adoption_v1.py', 'experiments/staged_rts24_saved_fresh_adoption_v1.py',
            'tests/test_staged_rts24_saved_fresh_adoption_v1.py'):
        raw = (ROOT/name).read_bytes(); path = folder/(Path(name).parent.name+'_'+Path(name).name+'.snapshot')
        path.write_bytes(raw); images[name] = dict(snapshot=path.relative_to(ROOT).as_posix(), pin=pin(raw))
    save(label+'.snapshot.json', dict(sources=images))
    argv = [r'D:\Miniconda3\envs\compute\python.exe', '-B', str(target)]
    launch = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=max(.01, cap-(launch-start)))
        code, stdout, stderr, timed_out = result.returncode, result.stdout, result.stderr, False
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr, timed_out = None, error.stdout or b'', error.stderr or b'', True
    process_seconds = time.monotonic()-launch
    same = all(pin((ROOT/n).read_bytes()) == expected for n, expected in selected.items())
    for suffix, raw in [('stdout.log', stdout), ('stderr.log', stderr)]: (OUT/(label+'.'+suffix)).write_bytes(raw)
    elapsed = time.monotonic()-start
    save(label+'.exit.json', dict(authority='DRAFT_NONAUTHORITATIVE', argv=argv, exit_code=code, timed_out=timed_out,
        capture_seconds=elapsed, process_seconds=process_seconds, timeout_seconds=cap, source_pins=selected,
        source_pins_unchanged=same, script_snapshot=snapshot.relative_to(ROOT).as_posix(), script_pin=pin(image),
        source_snapshot=label+'.snapshot.json', actual_saved_F_execution=False, F_launch_admitted=False))
    files = [p for p in OUT.rglob('*') if p.is_file()]
    assert len(files) <= 128 and sum(p.stat().st_size for p in files) <= 8*1024**2
    print(json.dumps(dict(exit_code=code, timed_out=timed_out, capture_seconds=elapsed, source_pins_unchanged=same)))
    if code: sys.stderr.buffer.write(stderr[-1500:])
    raise SystemExit(0 if code == 0 and same and not timed_out and elapsed <= cap else 1)


if __name__ == '__main__': main()
