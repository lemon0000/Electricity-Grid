"""Stdlib-only saved development-evidence checks; no worker/scientific replay."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def stamp(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&0x400,'nonordinary file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    checks=BASE/'development_checks_01';units=read(checks/'units_04.exit.json')
    require(units['exit_code']==0 and units['source_pins_unchanged'] is True,'targeted check terminal')
    require(re.search(rb'\b73 passed in\b',(checks/'units_04.stdout.log').read_bytes())
        and (checks/'units_04.stderr.log').read_bytes()==b'','targeted check summary')
    require(all(stamp(ROOT/n)==v for n,v in units['source_pins'].items()),'four development inputs drifted')
    related=read(POST/'related_check_summary.json')
    for item in related['checks']:
        name=item['name'];record=read(checks/(name+'.exit.json'))
        require(record['exit_code']==0 and record['source_pins_unchanged'] is True,'related check terminal')
        require(re.search(rb'\b'+str(item['passed']).encode()+rb' passed',
            (checks/(name+'.stdout.log')).read_bytes()) and (checks/(name+'.stderr.log')).read_bytes()==b'','related check summary')
        require(record['source_pins']==units['source_pins'],'related check input set')
    dependencies=read(POST/'related_dependency_pins.json')
    require(all(stamp(ROOT/n)==v for n,v in dependencies.items()),'frozen dependency drift')
    preservation=read(POST/'prior_preservation_inventory.json')
    require(len(preservation)==400 and all(stamp(ROOT/n)==v for n,v in preservation.items()),'prior publication drift')
    pre=read(checks/'prereview_01.json')
    require(pre['remaining_high_medium']==[] and pre['source_pins']==units['source_pins']
        and pre['official_verdict'] is pre['receipt'] is pre['seal'] is None,'development review state')
    # Preserve the first fixture failure; it is not relabelled as a final pass.
    failed=read(checks/'units_01.exit.json')
    require(failed['exit_code']!=0 and re.search(rb'\b5 failed, 45 passed in\b',
        (checks/'units_01.stdout.log').read_bytes()),'historical failed fixture evidence')
    stopped=read(checks/'related_01.exit.json')
    require(stopped['exit_code'] is None and stopped['stop_reason']=='wrapper_timeout'
        and stopped['timeout_seconds']==120 and stopped['terminal_pass_observed'] is False,'historical stopped regression')
    for label,anchor in (
        ('P1_and_prior','results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck_03.stdout.json'),
        ('workflow_accounting','results/tables/staged_rts24_p2_workflow_accounting_v1_non_authoritative/postcheck_01/accounting_01.stdout.json')):
        record=read(POST/(label+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is True
            and stamp(POST/(label+'.stdout.json'))==stamp(ROOT/anchor)
            and (POST/(label+'.stderr.log')).read_bytes()==b'','prior independent postcheck reproduction')
    for name in units['source_pins']:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
    # This component was exercised only in pytest tmp, never a public attempt.
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    require(not (native/'p2_01').exists() and not (native/'registration_v1.json').exists(),'public P2 state exists')
    require(not list(BASE.rglob('parent_observation.json')),'unexpected persistent process observation')
    require(all(stamp(ROOT/n)==v for n,v in preservation.items())
        and all(stamp(ROOT/n)==v for n,v in units['source_pins'].items()),'final preservation bookend')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),targeted_passed=73,
        related_passed=related['distinct_passed'],prior_published_paths_unchanged=400,
        P1_files_unchanged=683,B1_B3_saved_files_unchanged=118,prior_checkpoint_paths_unchanged=685,
        prior_postcheck_stdout_exact_reproductions=2,new_scientific_calls_by_postcheck=0,new_native_calls=0,
        public_P2_registered=False,public_P2_executed=False,actual_outer_launcher_implemented=False,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False,
        C_overall_performance_review_complete=False,
        scope='saved ordinary control tests and byte preservation only; no public 10-hour or 139 scientific evidence')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
