"""Bounded ordinary static archive checks with exact before/after pins."""
import time
STARTED = time.perf_counter()
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_upstream_contract_v1_non_authoritative'
CONTRACT='docs/plan/staged_deliverability_c_saved_fresh_upstream_archive_scope_budget_v1.md'
HANDOFF='docs/plan/continuation_handoff_20261025_saved_fresh_upstream_archive.md'
REPORT=(OUT.parent/'validation_report.md').relative_to(ROOT).as_posix()
HELPERS=(OUT/'capture.py',OUT/'saved_checks.py')

def raw(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def pin(data):return dict(bytes=len(data),sha256=sha256(data).hexdigest())
def read(path):return json.loads(path.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def save(path,value):
    with path.open('xb') as stream:stream.write(raw(value))

def initial():
    assert sys.executable.lower()==r'D:\Miniconda3\envs\compute\python.exe'.lower()
    assert not (OUT/'baseline.json').exists()
    previous=read(OLD/'checks_01/baseline.json')
    preserved=dict(previous['preserved'])
    old_files=names(p for p in OLD.rglob('*') if p.is_file())
    assert len(old_files)==47
    preserved.update(old_files)
    assert len(preserved)==4105
    source=names(ROOT/n for n in previous['sources'])
    assert source==previous['sources'] and len(source)==49
    current_documents=[CONTRACT,HANDOFF,REPORT]
    support_paths=[*HELPERS,*(OUT/(p.stem+'.snapshot') for p in HELPERS),
                   OUT/'baseline.json',OUT/'navigation_migration.json',
                   *(OUT/('check_01.'+suffix) for suffix in ('stdout.log','stderr.log','exit.json')),
                   *(ROOT/n for n in current_documents)]
    baseline=dict(authority='DRAFT_NONAUTHORITATIVE',base_head='d458c35cfe6b537853d3ff7aee3314f4fd5d5147',
        sources=source,preserved=preserved,helpers=names(HELPERS),fixed_documents=names([ROOT/CONTRACT]),
        current_documents=current_documents,support_member_names=sorted(p.relative_to(ROOT).as_posix() for p in support_paths),
        source_epoch=previous['source_epoch'],actual_F=False,resource_admission=False,formal_result=False)
    save(OUT/'baseline.json',baseline)
    for path in HELPERS:
        data=path.read_bytes();ast.parse(data)
        with (OUT/(path.stem+'.snapshot')).open('xb') as stream:stream.write(data)

def fixed(baseline):
    expected={**baseline['sources'],**baseline['preserved'],**baseline['helpers'],**baseline['fixed_documents']}
    actual=names(ROOT/n for n in expected)
    assert actual==expected,'Source/history/helper drift'
    nav=read(OUT/'navigation_migration.json')
    for n,item in nav.items():assert pin((ROOT/n).read_bytes())==item['after_full_pin'],n
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    return pin(raw(actual))

def main(action):
    assert action in ('check','saved','terminal','reserve')
    labels=dict(check='check_01',saved='saved_02',terminal='terminal_03',reserve='reserve_04')
    label=labels[action]
    records={p.name.removesuffix('.exit.json'):read(p) for p in OUT.glob('*.exit.json')}
    assert len(records)<4 and set(records)<=set(labels.values())
    order=('check_01','saved_02','terminal_03','reserve_04')
    assert label==order[len(records)] and set(records)==set(order[:len(records)])
    spent=sum(r['charged_seconds'] for r in records.values());assert spent+30<=120
    assert all(r['returncode']==0 and r['accepted'] for r in records.values())
    if action=='check':
        assert not records
        initial()
    baseline=read(OUT/'baseline.json')
    before=fixed(baseline)
    if action=='saved':
        assert set(records)=={'check_01'}
        save(OUT/'support_pins.json',names(ROOT/n for n in baseline['support_member_names']))
    if action=='terminal':assert {'check_01','saved_02'}<=set(records)
    target=OUT/'saved_checks.py'
    argv=[sys.executable,'-B',str(target)]+(['--draft'] if not (OUT/'support_pins.json').exists() else [])
    for suffix in ('stdout.log','stderr.log','exit.json'):assert not (OUT/(label+'.'+suffix)).exists()
    baseline_pin=pin((OUT/'baseline.json').read_bytes());navigation_pin=pin((OUT/'navigation_migration.json').read_bytes())
    support_pin=pin((OUT/'support_pins.json').read_bytes()) if (OUT/'support_pins.json').exists() else None
    target_pin=pin(target.read_bytes());capture_pin=pin(Path(__file__).read_bytes())
    timeout=max(.01,min(25.,29.-(time.perf_counter()-STARTED)))
    target_started=time.perf_counter();error=None
    try:
        child=subprocess.run(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
        code,stdout,stderr=child.returncode,child.stdout,child.stderr
    except subprocess.TimeoutExpired as caught:
        code,stdout,stderr,error=-2,caught.stdout or b'',caught.stderr or b'','timeout'
    target_seconds=time.perf_counter()-target_started
    after=fixed(baseline)
    post_ok=(before==after and pin(target.read_bytes())==target_pin
        and pin(Path(__file__).read_bytes())==capture_pin
        and pin((OUT/'baseline.json').read_bytes())==baseline_pin
        and pin((OUT/'navigation_migration.json').read_bytes())==navigation_pin)
    if support_pin is not None:post_ok &= pin((OUT/'support_pins.json').read_bytes())==support_pin
    for suffix,data in (('stdout.log',stdout),('stderr.log',stderr)):
        with (OUT/(label+'.'+suffix)).open('xb') as stream:stream.write(data)
    observed=time.perf_counter()-STARTED;charged=observed+.5
    record=dict(authority='DRAFT_NONAUTHORITATIVE',label=label,argv=argv,returncode=code,error=error,
        accepted=code==0 and not stderr and len(stdout)<=32768 and post_ok and charged<=30,
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),script_pin=target_pin,capture_pin=capture_pin,
        baseline_pin=baseline_pin,navigation_pin=navigation_pin,support_pin=support_pin,
        fixed_before=before,fixed_after=after,observed_capture_seconds=observed,tail_reserve_seconds=.5,
        target_seconds=target_seconds,target_timeout_seconds=timeout,charged_seconds=charged,
        previous_charged_seconds=spent,prior_records={k:pin((OUT/(k+'.exit.json')).read_bytes()) for k in records},
        capture_python_startup_included=False,whole_workflow_wall_budget_verified=False,
        actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False,
        package_postcheck_verified=False)
    existing=[p for p in OUT.rglob('*') if p.is_file()]
    upper=raw({**record,'accepted':False})
    package_ok=len(existing)+1<=24 and sum(p.stat().st_size for p in existing)+len(upper)<=4*1024**2
    record['accepted'] &= package_ok;record['package_postcheck_verified']=package_ok
    payload=raw(record)
    with (OUT/(label+'.exit.json')).open('xb') as stream:stream.write(payload)
    assert (OUT/(label+'.exit.json')).read_bytes()==payload
    print(json.dumps(dict(label=label,returncode=code,accepted=record['accepted'],charged_seconds=charged,
        cumulative_charged_seconds=spent+charged,files=len(existing)+1,
        bytes=sum(p.stat().st_size for p in existing)+len(payload)),sort_keys=True))
    if not record['accepted']:raise SystemExit(1)

if __name__=='__main__':
    assert len(sys.argv)==2
    main(sys.argv[1])
