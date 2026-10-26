"""Create-only remaining-group budget; no scientific implementation import."""
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
plan=read(OUT/'admission.json');failed=read(OUT/'role_1.exit.json')
assert failed['accepted'] is False and failed['error']=='timeout' and failed['source_pins']==plan['source_pins']
assert not (OUT/'role_1.harness.json').exists()
assert all(pin((ROOT/n).read_bytes())==p for n,p in plan['source_pins'].items())
completed={n for n in plan['groups'] if n not in ('role_1','role_2','role_3','role_4')}
for n in completed:
    r=read(OUT/(n+'.exit.json'));h=read(OUT/(n+'.harness.json'))
    assert r['accepted'] and r['source_pins']==plan['source_pins'] and h['pytest_exit_code']==0
    assert set(h['passed_call_nodes'])==set(plan['groups'][n]) and not h['failed_phases'] and not h['skipped_phases']
spent={k:sum(read(p)['charged_seconds'] for p in OUT.glob('*.exit.json') if read(p)['kind']==k) for k in ('static','pytest')}
groups={('role_1_retry' if n=='role_1' else n):plan['groups'][n] for n in ('role_1','role_2','role_3','role_4')}
assert spent['pytest']+140<=360 and spent['static']+66<=120
value=dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps={n:35 for n in groups},run_order=list(groups),
    original_admission_pin=pin((OUT/'admission.json').read_bytes()),historical_timeout_pin=pin((OUT/'role_1.exit.json').read_bytes()),
    source_pins=plan['source_pins'],source_epoch=plan['source_epoch'],completed_labels=sorted(completed),previous_charged_seconds=spent,
    target_union_unchanged=True,pytest_cap_seconds=360,static_cap_seconds=120,total_cap_seconds=480,
    helper_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.glob('*.py')},
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
data=raw(value);assert len(data)<=256*1024
with (OUT/'admission_revision_08.json').open('xb') as f:f.write(data)
print(json.dumps(dict(remaining_nodes=sum(map(len,groups.values())),caps=140,pytest_spent=spent['pytest'],source_epoch=plan['source_epoch']),sort_keys=True))
