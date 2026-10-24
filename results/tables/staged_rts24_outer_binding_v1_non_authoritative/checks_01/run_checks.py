"""Retained ordinary unit-test terminals, no experiment or native invocation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCES = ('src/staged_rts24_p2_outer_v1.py', 'src/staged_rts24_p2_package_check_v2.py',
    'tests/test_staged_rts24_p2_outer_v1.py', 'docs/plan/staged_deliverability_c_p2_outer_binding_contract_v1.md')


def pins():
    return {name: dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) for name in SOURCES for raw in [(ROOT/name).read_bytes()]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('label'); parser.add_argument('files', nargs='+')
    args = parser.parse_args(); assert args.label.isidentifier()
    prefix = OUT/args.label
    assert not prefix.with_suffix('.exit.json').exists()
    argv = [sys.executable, '-B', '-m', 'pytest', *args.files, '-x', '-q', '-rP', '--tb=short', '--durations=5',
        '-p', 'no:cacheprovider', '-o', 'tmp_path_retention_count=100000', '-o', 'tmp_path_retention_policy=all']
    record = dict(argv=argv, scope='ordinary bounded unit checks; no solver/native/scientific execution',
        source_pins=pins(), timeout_seconds=90)
    start = time.perf_counter()
    with prefix.with_suffix('.stdout.log').open('xb') as out, prefix.with_suffix('.stderr.log').open('xb') as err:
        try: record.update(exit_code=subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=90).returncode, timed_out=False)
        except subprocess.TimeoutExpired: record.update(exit_code=None, timed_out=True)
    record.update(wall_seconds=time.perf_counter()-start, source_pins_unchanged=record['source_pins'] == pins())
    prefix.with_suffix('.exit.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('exit_code', 'timed_out', 'wall_seconds', 'source_pins_unchanged')}))
    print(prefix.with_suffix('.stdout.log').read_text(encoding='utf-8', errors='replace'))
    print(prefix.with_suffix('.stderr.log').read_text(encoding='utf-8', errors='replace'))
