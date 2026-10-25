"""Mechanical-only wrapper; freeze execution files and share the original time ledger."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;MAIN=OUT.parent/'checks_01'
EXE=Path('D:/Miniconda3/envs/compute/python.exe')
action_started=time.monotonic()
TAIL_RESERVE_SECONDS=.5
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(path):return json.loads(path.read_bytes())
def save(name,value):
    target=OUT/name;assert not target.exists(),name
    target.write_bytes((json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
def files():return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in MAIN.rglob('*') if p.is_file()}

label,target_name,cap=sys.argv[1:];cap=float(cap)
assert (label,target_name) in (('finalizer_20','finalize_evidence.py'),('saved_21','saved_checks.py'),('terminal_22','saved_checks.py'))
assert 0<cap<=12 and not (OUT/(label+'.exit.json')).exists()
plan=read(MAIN/'group_admission_03.json')
for group,nodes in plan['groups'].items():
    r=read(MAIN/(group+'.exit.json'));assert r['exit_code']==0 and not r['timed_out'] and r['nodes']==nodes and r['source_pins']==plan['source_pins']
current={n:pin((ROOT/n).read_bytes()) for n in plan['source_pins']};assert current==plan['source_pins']
inventory=files();size=sum(p['bytes'] for p in inventory.values())
assert len(inventory)<=224 and size<=16*1024**2
freeze=dict(files=inventory,count=len(inventory),bytes=size,inventory_root_sha256=sha256(canonical(inventory)).hexdigest())
if (OUT/'execution_freeze.json').exists():assert read(OUT/'execution_freeze.json')==freeze
else:save('execution_freeze.json',freeze)
spent=sum(read(p)['wall_seconds'] for d in (MAIN,OUT) for p in d.glob('*.exit.json') if read(p)['kind']=='static')
assert spent+cap+TAIL_RESERVE_SECONDS<=80
helpers={}
for name in ('package_capture.py','finalize_evidence.py','saved_checks.py'):
    raw=(OUT/name).read_bytes();where=OUT/('helper_'+sha256(raw).hexdigest()+'.snapshot')
    if where.exists():assert where.read_bytes()==raw
    else:where.write_bytes(raw)
    helpers[name]=dict(pin=pin(raw),snapshot=where.relative_to(ROOT).as_posix())
support_pin=None
prior_labels=[] if label=='finalizer_20' else ['finalizer_20'] if label=='saved_21' else ['finalizer_20','saved_21']
prior_mechanical_pins={(OUT/(prior+'.'+suffix)).relative_to(ROOT).as_posix():pin((OUT/(prior+'.'+suffix)).read_bytes())
    for prior in prior_labels for suffix in ('snapshot.json','stdout.log','stderr.log','exit.json')}
if label!='finalizer_20':
    support_pin=pin((OUT/'support_pins.json').read_bytes())
    assert support_pin==read(OUT/'finalizer_20.exit.json')['support_pin']
save(label+'.snapshot.json',dict(helpers=helpers,source_pins=current,execution_inventory_root_sha256=freeze['inventory_root_sha256'],
    support_pin=support_pin,prior_mechanical_pins=prior_mechanical_pins))
remaining=cap-(time.monotonic()-action_started);assert remaining>0
stdout=stderr=b'';code=None;timeout=False
try:
    value=subprocess.run([str(EXE),'-B',str(OUT/target_name)],cwd=ROOT,capture_output=True,timeout=remaining,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    stdout,stderr,code=value.stdout,value.stderr,value.returncode
except subprocess.TimeoutExpired as error:stdout,stderr,timeout=error.stdout or b'',error.stderr or b'',True
for suffix,raw in (('stdout.log',stdout),('stderr.log',stderr)):(OUT/(label+'.'+suffix)).write_bytes(raw)
source_after={n:pin((ROOT/n).read_bytes()) for n in current}
inventory_unchanged=files()==inventory
helpers_unchanged=all(pin((OUT/n).read_bytes())==item['pin'] for n,item in helpers.items())
if code==0:
    current_support=pin((OUT/'support_pins.json').read_bytes())
    if label=='finalizer_20':assert json.loads(stdout)['support_pin']==current_support
    else:assert current_support==support_pin
    support_pin=current_support
measured=time.monotonic()-action_started;seconds=measured+TAIL_RESERVE_SECONDS
record=dict(authority='DRAFT_NONAUTHORITATIVE',kind='static',wall_seconds=seconds,measured_action_seconds=measured,
    tail_reserve_seconds=TAIL_RESERVE_SECONDS,timeout_seconds=cap,timed_out=timeout,exit_code=code,
    source_pins=current,source_pins_unchanged=source_after==current,execution_inventory_unchanged=inventory_unchanged,
    helper_pins_unchanged=helpers_unchanged,support_pin=support_pin,
    snapshot_manifest=label+'.snapshot.json',actual_saved_F_execution=False,F_launch_admitted=False)
save(label+'.exit.json',record)
package=[p for p in OUT.rglob('*') if p.is_file()]
assert len(package)<=32 and sum(p.stat().st_size for p in package)<=2*1024**2
print(json.dumps({k:record[k] for k in ('exit_code','timed_out','wall_seconds','source_pins_unchanged','execution_inventory_unchanged','helper_pins_unchanged')}))
assert code==0 and not timeout and record['source_pins_unchanged'] and record['execution_inventory_unchanged'] and record['helper_pins_unchanged']
assert measured<=cap
