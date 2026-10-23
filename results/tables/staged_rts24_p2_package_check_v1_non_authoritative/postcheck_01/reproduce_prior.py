"""Reproduce two immutable stdlib postchecks; exact stdout, no science replay."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
CHECKS=(
    ('P1_and_prior','results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck.py',
        '161b69a7f39ed5981cf755596cf1465438d335b41a1198826fa0f7be06bd3d88',
        'results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck_03.stdout.json'),
    ('failure_outer','results/tables/staged_rts24_p2_failure_outer_v1_non_authoritative/postcheck_01/postcheck.py',
        '5e9539bca6ecd17cc367babc87689637e610713eb5ca4b62a21dc66b64f57dfb',
        'results/tables/staged_rts24_p2_failure_outer_v1_non_authoritative/postcheck_01/saved_01.stdout.json'),
)

def run(item):
    label,name,expected,target=item;raw=(ROOT/name).read_bytes();assert sha256(raw).hexdigest()==expected
    start=time.perf_counter();cmd=[sys.executable,'-B','-s',str(ROOT/name)]
    with (OUT/(label+'.stdout.json')).open('xb') as out,(OUT/(label+'.stderr.log')).open('xb') as err:
        record=dict(argv=cmd,timeout_seconds=30,script_sha256=expected)
        try:record.update(exit_code=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=err,timeout=30).returncode,timed_out=False)
        except subprocess.TimeoutExpired:record.update(exit_code=None,timed_out=True)
    record.update(wall_seconds=time.perf_counter()-start,exact_prior_stdout=(OUT/(label+'.stdout.json')).read_bytes()==(ROOT/target).read_bytes(),
        script_unchanged=(ROOT/name).read_bytes()==raw)
    with (OUT/(label+'.exit.json')).open('x',encoding='utf-8') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    return dict(check=label,**record)

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CHECKS))
    for result in results:
        print(json.dumps(result));assert result['exit_code']==0 and result['exact_prior_stdout'] and result['script_unchanged']
