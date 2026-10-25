"""Finite static capture; never launches an F actor or changes old evidence."""
import json
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def main():
    label, limit, script, *args = sys.argv[1:]
    limit = float(limit)
    assert 0 < limit <= 20
    assert not (OUT/(label+'.exit.json')).exists()
    argv = [r'D:\Miniconda3\envs\compute\python.exe', '-B', str(OUT/script), *args]
    image = (OUT/script).read_bytes()
    snapshot = OUT/(label+'.script.snapshot'); assert not snapshot.exists(); snapshot.write_bytes(image)
    started = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=limit)
        code, stdout, stderr, timed_out = result.returncode, result.stdout, result.stderr, False
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr, timed_out = None, error.stdout or b'', error.stderr or b'', True
    elapsed = time.monotonic()-started
    for suffix, raw in [('stdout.log', stdout), ('stderr.log', stderr)]:
        (OUT/(label+'.'+suffix)).write_bytes(raw)
    value = dict(argv=argv, exit_code=code, timed_out=timed_out, wall_seconds=elapsed,
        timeout_seconds=limit, scope='static saved evidence only', actual_saved_F_execution=False,
        script_snapshot=snapshot.relative_to(ROOT).as_posix(), script_pin=dict(bytes=len(image), sha256=sha256(image).hexdigest()))
    (OUT/(label+'.exit.json')).write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
    print(json.dumps(value))
    if code != 0: sys.stderr.buffer.write(stderr[-2000:])
    raise SystemExit(0 if code == 0 else 1)


if __name__ == '__main__': main()
