"""Capture bounded scripts and all direct local helper/source bytes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import ROOT,OUT,PRIOR,EXE,SOURCE_PATHS,FROZEN_EPOCH,pin,selected,save,snapshot

label,script,cap=sys.argv[1:];cap=float(cap)
assert 0<cap<=15 and not (OUT/(label+'.exit.json')).exists()
spent=sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json'))
assert spent+cap<=90
source=selected();target=Path(script).absolute()
helpers={Path(__file__).resolve(),OUT/'common.py',target}
images={p.relative_to(ROOT).as_posix():snapshot(p) for p in helpers}
source_images={n:snapshot(ROOT/n) for n in SOURCE_PATHS}
save(label+'.snapshot.json',dict(sources=source_images,helpers=images))
start=time.monotonic()
try:
    result=subprocess.run([str(EXE),'-B',str(target)],cwd=ROOT,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=cap)
    stdout,stderr,code,timed_out=result.stdout,result.stderr,result.returncode,False
except subprocess.TimeoutExpired as error:
    stdout,stderr,code,timed_out=error.stdout or b'',error.stderr or b'',None,True
elapsed=time.monotonic()-start
for suffix,raw in [('stdout.log',stdout),('stderr.log',stderr)]: (OUT/(label+'.'+suffix)).write_bytes(raw)
value=dict(authority='DRAFT_NONAUTHORITATIVE',exit_code=code,timed_out=timed_out,wall_seconds=elapsed,
    timeout_seconds=cap,source_pins=source,source_epoch=FROZEN_EPOCH,source_pins_unchanged=selected()==source,
    helper_pins={n:i['pin'] for n,i in images.items()},
    helper_pins_unchanged=all(pin((ROOT/n).read_bytes())==i['pin'] for n,i in images.items()),
    snapshot_manifest=label+'.snapshot.json',argv=[str(EXE),'-B',str(target)],
    actual_saved_F_execution=False,F_launch_admitted=False)
save(label+'.exit.json',value)
print(json.dumps({k:value[k] for k in ('exit_code','timed_out','wall_seconds','source_pins_unchanged','helper_pins_unchanged')}))
files=[p for p in OUT.rglob('*') if p.is_file()]
assert len(files)<=128 and sum(p.stat().st_size for p in files)<=8*1024**2
assert code==0 and not timed_out and value['source_pins_unchanged'] and value['helper_pins_unchanged']
