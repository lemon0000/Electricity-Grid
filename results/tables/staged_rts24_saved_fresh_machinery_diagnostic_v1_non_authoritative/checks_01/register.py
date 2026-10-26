"""Register one diagnostic and its preparation cost; no project/library import."""
import time
STARTED=time.perf_counter()
from hashlib import sha256
import json
from pathlib import Path
import subprocess
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
output=OUT/'admission.json';assert not output.exists()
try:
    old=ROOT/'results/tables';wire=old/'staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
    roots=[old/n for n in ('staged_rts24_saved_fresh_import_policy_v1_non_authoritative','staged_rts24_saved_fresh_import_policy_v2_non_authoritative','staged_rts24_saved_fresh_import_policy_cold_v1_non_authoritative')]
    previous=roots[2]/'checks_01/wip_checkpoint.exit.json';checkpoint=read(previous)
    assert checkpoint['accepted'] is False and checkpoint['failed_check']=='resource_caps_and_binding'
    plan_path=roots[2]/'checks_01/regression_admission.json';plan=read(plan_path);source=names(ROOT/n for n in plan['source_pins'])
    assert source==plan['source_pins'] and len(source)==49
    policy_path=roots[1]/'checks_01/import_policy.json';policy=read(policy_path)
    helpers=names(OUT/n for n in ('register.py','probe.py','capture.py','archive.py'))
    for name in helpers:compile((ROOT/name).read_bytes(),name,'exec',dont_inherit=True)
    directories=[wire/'checks_01',wire/'final_package_01',wire/'checks_02',wire/'final_package_02',roots[0]/'checks_01',roots[1]/'checks_01',roots[1]/'final_package_01',roots[2]/'checks_01',roots[2]/'final_package_01']
    failed=[p for d in directories for p in d.glob('*.exit.json') if not read(p)['accepted']];assert len(failed)==9
    drain=wire/'checks_01/run.py';scope=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_machinery_diagnostic_scope_v1.md'
    references=names(failed+[plan_path,policy_path,drain,scope,roots[2]/'checks_01/pytest_regression.exit.json',roots[2]/'checks_01/pytest_regression.harness.json'])
    external={policy['executable_path']:policy['executable_pin'],**policy['external_sources']}
    env=Path(policy['executable_path']).parent
    external.update({str(env/'Lib/site-packages/pyomo/common'/n):pin((env/'Lib/site-packages/pyomo/common'/n).read_bytes()) for n in ('deprecation.py','dependencies.py')})
    assert all(pin(Path(n).read_bytes())==p for n,p in external.items())
    usage=[]
    for root in roots:
        files=[p for p in root.rglob('*') if p.is_file()];usage.append(dict(path=root.relative_to(ROOT).as_posix(),files=len(files),bytes=sum(p.stat().st_size for p in files)))
    assert sum(r['files'] for r in usage)==127 and sum(r['bytes'] for r in usage)==8462120
    parent='c7a930a57fecbe1b33bc9e3f055a56184128563c'
    git_argv=['git','rev-parse','HEAD',*[parent+':'+r.relative_to(ROOT).as_posix() for r in roots]]
    git_stdout=subprocess.check_output(git_argv,cwd=ROOT);git_refs=git_stdout.decode('ascii').splitlines();assert git_refs[0]==parent
    git_query=dict(argv=git_argv,returncode=0,stdout_pin=pin(git_stdout))
    value=dict(authority='DRAFT_NONAUTHORITATIVE',schema='single_machinery_difference_diagnostic_v1',caps=dict(registration=2,probe=12,archive=4,total_static=18,pytest=0),
        parent_commit=parent,predecessor_policy_git_trees={r.relative_to(ROOT).as_posix():v for r,v in zip(roots,git_refs[1:])},registration_git_query=git_query,
        predecessor_checkpoint_path=previous.relative_to(ROOT).as_posix(),predecessor_charged_seconds=checkpoint['cumulative_charged_seconds'],
        predecessor_resource_observation=usage,predecessor_filesystem_full_rescan_performed=False,
        source_pins=source,source_epoch=plan['source_epoch'],helper_pins=helpers,reference_pins=references,external_pins=external,
        failed_record_pins=names(failed),entry_path='experiments/staged_rts24_saved_fresh_adoption_v1.py',
        policy_path=policy_path.relative_to(ROOT).as_posix(),policy_pin=pin(policy_path.read_bytes()),executable=policy['executable_path'],python=policy['python'],
        scope_path=scope.relative_to(ROOT).as_posix(),drain_helper_path=drain.relative_to(ROOT).as_posix(),drain_helper_pin=pin(drain.read_bytes()),
        predecessor_combined_resource_admission=False,policy_resource_admission=False,cold_acceptance=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
    charged=time.perf_counter()-STARTED+.1
    registration=dict(authority='DRAFT_NONAUTHORITATIVE',label='machinery_diagnostic_registration',kind='static',cap_seconds=2,
        charged_seconds=charged,tail_reserve_seconds=.1,accepted=charged<=2,prepared_controls_pin=pin(raw(value)),git_query=git_query,
        actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
    with (OUT/'registration.json').open('xb') as stream:stream.write(raw(registration))
    value['registration_charged_seconds']=charged;value['registration_tail_reserve_seconds']=.1
    value['registration_accepted']=charged<=2;value['registration_pin']=pin((OUT/'registration.json').read_bytes())
    with output.open('xb') as stream:stream.write(raw(value))
    print(json.dumps(dict(registration_accepted=value['registration_accepted'],charged_seconds=value['registration_charged_seconds'],source_epoch=value['source_epoch']),sort_keys=True))
    if not value['registration_accepted']:raise SystemExit(1)
except BaseException as error:
    if not output.exists():
        value=dict(authority='DRAFT_NONAUTHORITATIVE',accepted=False,error_type=type(error).__name__,charged_seconds=time.perf_counter()-STARTED+.1,cap_seconds=2,actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
        with (OUT/'registration_failed.json').open('xb') as stream:stream.write(raw(value))
    raise
