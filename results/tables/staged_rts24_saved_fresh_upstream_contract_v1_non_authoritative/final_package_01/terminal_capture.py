"""Sixth and final ordinary static command; preserves the typed saved_05 failure."""
import time
STARTED = time.perf_counter()
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE.parent/'checks_01'
ROOT = HERE.parents[3]

def raw(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')

def pin(data): return dict(bytes=len(data),sha256=sha256(data).hexdigest())
def read(path): return json.loads(path.read_bytes())
def pins(paths): return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}

def main():
    assert not sys.argv[1:]
    records = {p.relative_to(ROOT).as_posix():read(p) for directory in (MAIN,HERE) for p in directory.glob('*.exit.json')}
    assert len(records) == 5 and {Path(n).name for n in records} == {n+'.exit.json' for n in ('baseline_01','design_02','design_03','finalizer_04','saved_05')}
    assert sum(r['returncode'] != 0 for r in records.values()) == 1
    spent = sum(r['charged_seconds'] for r in records.values()); assert spent+12 <= 90
    migration_path = HERE/'document_migration.json'; migration_raw = migration_path.read_bytes(); migration = json.loads(migration_raw)
    revision_path = MAIN/'draft_revision_02.json'; revision = read(revision_path)
    baseline_path = MAIN/'baseline.json'; baseline = read(baseline_path)
    capture_path = MAIN/'capture_static.py'; expected_capture = revision['helpers_after'][capture_path.relative_to(ROOT).as_posix()]
    assert pin(capture_path.read_bytes()) == expected_capture
    loader = importlib.util.spec_from_file_location('frozen_upstream_capture_for_fixed_pins',capture_path)
    module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
    checker = HERE/'terminal_checks.py'; capture = HERE/'terminal_capture.py'
    assert pin(checker.read_bytes()) == migration['terminal_helper_pin']
    assert pin(capture.read_bytes()) == migration['terminal_capture_pin']
    for path, target in ((checker,HERE/'terminal_checks.snapshot'),(capture,HERE/'terminal_capture.snapshot')):
        data = path.read_bytes(); ast.parse(data)
        with target.open('xb') as stream: stream.write(data)
    def bookend():
        source = module.fixed(baseline)
        assert pin(migration_path.read_bytes()) == pin(migration_raw)
        assert pin(checker.read_bytes()) == migration['terminal_helper_pin']
        assert pin(capture.read_bytes()) == migration['terminal_capture_pin']
        assert pin(capture_path.read_bytes()) == expected_capture
        for n, item in migration['documents'].items(): assert pin((ROOT/n).read_bytes()) == item['after_pin']
        assert pin((ROOT/migration['supplement_path']).read_bytes()) == migration['supplement_pin']
        for n, expected in migration['original_package_files'].items(): assert pin((ROOT/n).read_bytes()) == expected
        freeze = read(HERE/'execution_freeze.json')
        actual = pins(p for p in MAIN.rglob('*') if p.is_file()); assert actual == freeze['files']
        return source
    before = bookend()
    argv = [sys.executable,'-B',str(checker)]
    timeout = max(.01,min(11.,11.5-(time.perf_counter()-STARTED)))
    error = None; target_started=time.perf_counter()
    try:
        child = subprocess.run(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
        code, stdout, stderr = child.returncode, child.stdout, child.stderr
    except subprocess.TimeoutExpired as caught:
        code, stdout, stderr, error = -2,caught.stdout or b'',caught.stderr or b'','timeout'
    target_seconds=time.perf_counter()-target_started
    after=bookend(); assert before == after
    for suffix,data in (('stdout.log',stdout),('stderr.log',stderr)):
        with (HERE/('terminal_06.'+suffix)).open('xb') as stream: stream.write(data)
    observed=time.perf_counter()-STARTED; charged=observed+.25
    record=dict(authority='DRAFT_NONAUTHORITATIVE',label='terminal_06',argv=argv,returncode=code,error=error,
        accepted=code==0 and not stderr and len(stdout)<=32768 and charged<=12,
        helper_epoch='mechanical_successor_02',revision_pin=pin(revision_path.read_bytes()),
        migration_pin=pin(migration_raw),script_pin=migration['terminal_helper_pin'],
        baseline_pin=pin(baseline_path.read_bytes()),fixed_before=before,fixed_after=after,
        design_output_pins=pins(MAIN/n for n in ('fixed_templates.json','protocol_domains.json','protocol_dag.json','verification_matrix.json')),
        stdout_pin=pin(stdout),stderr_pin=pin(stderr),support_pin=pin((HERE/'support_pins.json').read_bytes()),
        observed_capture_seconds=observed,target_seconds=target_seconds,tail_reserve_seconds=.25,charged_seconds=charged,
        previous_charged_seconds=spent,target_timeout_seconds=timeout,per_capture_cap_seconds=12,cumulative_cap_seconds=90,
        prior_records={n:pin((ROOT/n).read_bytes()) for n in records},capture_python_startup_included=False,
        whole_workflow_wall_budget_verified=False,actual_F=False,resource_admission=False,scientific_evidence_adopted=False,formal_result=False)
    members=[p for p in HERE.rglob('*') if p.is_file()]
    record['package_postcheck_verified']=False
    upper_payload=raw({**record,'accepted':False})
    prospective_bytes=sum(p.stat().st_size for p in members)+len(upper_payload)
    package_ok=({p.name for p in members} == set(migration['expected_package_members'])-{'terminal_06.exit.json'}
                and len(members)+1<=16 and prospective_bytes<=1024**2)
    record['package_postcheck_verified']=package_ok
    record['accepted']=record['accepted'] and package_ok
    payload=raw(record)
    with (HERE/'terminal_06.exit.json').open('xb') as stream: stream.write(payload)
    assert (HERE/'terminal_06.exit.json').read_bytes() == payload
    print(json.dumps(dict(label='terminal_06',returncode=code,accepted=record['accepted'],charged_seconds=charged,
        cumulative_charged_seconds=spent+charged,execution_files=31,package_files=len(members)+1,
        package_bytes=prospective_bytes-len(upper_payload)+len(payload),historical_saved_05_exit=1),sort_keys=True))
    if not record['accepted']: raise SystemExit(1)

if __name__ == '__main__': main()
