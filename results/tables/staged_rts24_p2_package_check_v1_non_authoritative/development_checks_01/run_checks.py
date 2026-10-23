"""Ordinary saved-metadata tests with retained terminal records; no native run."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SOURCES=('src/staged_rts24_p2_package_check_v1.py','tests/test_staged_rts24_p2_package_check_v1.py',
    'docs/plan/staged_deliverability_c_p2_package_check_contract_v1.md')

def pins():
    return {n:dict(bytes=len(b),sha256=sha256(b).hexdigest()) for n in SOURCES for b in [(ROOT/n).read_bytes()]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');parser.add_argument('selection');args=parser.parse_args()
    prefix=OUT/args.label
    assert args.label.isidentifier() and not prefix.with_suffix('.exit.json').exists()
    cmd=[sys.executable,'-B','-m','pytest','tests/test_staged_rts24_p2_package_check_v1.py','-k',args.selection,
        '-x','-q','-rP','--tb=short','--durations=5','-p','no:cacheprovider','-o','tmp_path_retention_count=100000','-o','tmp_path_retention_policy=all']
    record=dict(argv=cmd,scope='ordinary synthetic saved-metadata tests; no native/scientific execution',source_pins=pins(),timeout_seconds=120)
    start=time.perf_counter()
    with prefix.with_suffix('.stdout.log').open('xb') as stdout,prefix.with_suffix('.stderr.log').open('xb') as stderr:
        try:record.update(exit_code=subprocess.run(cmd,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=120).returncode,timed_out=False)
        except subprocess.TimeoutExpired:record.update(exit_code=None,timed_out=True)
    record.update(wall_seconds=time.perf_counter()-start,source_pins_unchanged=record['source_pins']==pins())
    prefix.with_suffix('.exit.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('exit_code','timed_out','wall_seconds','source_pins_unchanged')}))
    print(prefix.with_suffix('.stdout.log').read_text(encoding='utf-8',errors='replace'))
    print(prefix.with_suffix('.stderr.log').read_text(encoding='utf-8',errors='replace'))
