"""Finite static packet captures, with a separate 15-second cumulative cap."""
import json
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def main():
    label, script = sys.argv[1:]
    spent = json.loads((OUT/'preparation_timing.json').read_bytes())['external_tool_wall_seconds']
    spent += sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
        if not json.loads(p.read_bytes()).get('nodes'))
    assert spent+5 <= 15 and not (OUT/(label+'.exit.json')).exists()
    raw = (OUT/script).read_bytes(); snapshot = OUT/(label+'.script.snapshot')
    snapshot.write_bytes(raw)
    argv = [r'D:\Miniconda3\envs\compute\python.exe', '-B', str(OUT/script)]
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=5)
        code, stdout, stderr, timed_out = result.returncode, result.stdout, result.stderr, False
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr, timed_out = None, error.stdout or b'', error.stderr or b'', True
    elapsed = time.monotonic()-start
    for suffix, image in [('stdout.log', stdout), ('stderr.log', stderr)]: (OUT/(label+'.'+suffix)).write_bytes(image)
    value = dict(exit_code=code, timed_out=timed_out, argv=argv, wall_seconds=elapsed, timeout_seconds=5,
        script_snapshot=snapshot.relative_to(ROOT).as_posix(), script_pin=dict(bytes=len(raw), sha256=sha256(raw).hexdigest()),
        actual_saved_F_execution=False)
    (OUT/(label+'.exit.json')).write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
    print(json.dumps(value))
    if code: sys.stderr.buffer.write(stderr[-1500:])
    raise SystemExit(0 if code == 0 else 1)


if __name__ == '__main__': main()
