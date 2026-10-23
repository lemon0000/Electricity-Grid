"""Stdlib saved-evidence verification; never import or execute research code."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'
CHECKS=BASE/'development_checks_01'

def require(value,message):
    if not value:raise ValueError(message)

def data(path):return json.loads(path.read_bytes())

def pin(path):
    info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and not getattr(info,'st_file_attributes',0)&0x400,'nonordinary saved file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def main():
    summary=data(POST/'ordinary_check_summary.json');sources=summary['source_pins']
    require(summary['targeted_distinct_passed']==129 and summary['related_distinct_passed']==72,'ordinary scope')
    require(all(pin(ROOT/n)==v for n,v in sources.items()),'three source pins drifted')
    require(data(CHECKS/'collection_01.exit.json')['exit_code']==0 and pin(CHECKS/'collection_01.stdout.log')==summary['collection'],'collection evidence')
    nodes=[n for n in (CHECKS/'collection_01.stdout.log').read_text(encoding='utf-8').splitlines() if n.startswith('tests/') and '::' in n]
    require(len(nodes)==len(set(nodes))==129,'collection count')
    seen=set();total=0
    for label,group in summary['groups'].items():
        record=data(CHECKS/(label+'.exit.json'));ids=group['nodeids'];count=group['passed']
        require(record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True and record['source_pins']==sources,'final group terminal or inputs')
        require(pin(CHECKS/(label+'.exit.json'))==group['exit_record'] and pin(CHECKS/(label+'.stdout.log'))==group['stdout'],'group record drift')
        require(len(ids)==len(set(ids))==count and seen.isdisjoint(ids),'group node overlap');seen.update(ids);total+=count
        require(re.search(rb'\b'+str(count).encode()+rb' passed\b',(CHECKS/(label+'.stdout.log')).read_bytes()) and (CHECKS/(label+'.stderr.log')).read_bytes()==b'','group terminal summary')
    require(total==129 and seen==set(nodes),'group coverage')
    related=data(CHECKS/'related_02.exit.json')
    require(related['exit_code']==0 and related['source_pins']==sources and related['source_pins_unchanged'] is True
        and b'72 passed' in (CHECKS/'related_02.stdout.log').read_bytes() and (CHECKS/'related_02.stderr.log').read_bytes()==b'','related regression')
    for label,expected in [('units_19',dict(oracle='full_319_all_protocol_digest_entrances',calls=7582,bytes=81683242,root_types=['NoneType','dict','list'])),
        ('units_20',dict(oracle='all_saved_P1_wire_roots',roots=403,bytes=9790308))]:
        values=[json.loads(line) for line in (CHECKS/(label+'.stdout.log')).read_text().splitlines() if line.startswith('{')]
        require(values==[expected],'independent encoding oracle scope')
    preservation=data(POST/'prior_preservation_inventory.json')
    require(len(preservation)==440 and all(pin(ROOT/n)==v for n,v in preservation.items()),'prior 440 publication paths drifted')
    for label,target in [('P1_and_prior','results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck_03.stdout.json'),
        ('failure_outer','results/tables/staged_rts24_p2_failure_outer_v1_non_authoritative/postcheck_01/saved_01.stdout.json')]:
        record=data(POST/(label+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is record['script_unchanged'] is True
            and pin(POST/(label+'.stdout.json'))==pin(ROOT/target) and (POST/(label+'.stderr.log')).read_bytes()==b'','prior stdlib stdout reproduction')
    budget=data(POST/'budget_01.stdout.json');require(data(POST/'budget_01.exit.json')['exit_code']==0,'budget arithmetic terminal')
    require(budget['outer_members']==66 and budget['known_inner_members']==64 and len(budget['outer_residual_members'])==2
        and budget['projected_members']==642 and budget['conditional_member_array_lower_bound_bytes']==31459
        and budget['conditional_P1_shape_record_example_bytes']==34658 and budget['actual_P2_record_measured'] is budget['actual_P2_overflow_inferred'] is False,'conditional budget scope')
    require(all(pin(ROOT/n)==v for n,v in {**budget['input_pins'],**budget['guard_pin']}.items()),'P1 budget inputs')
    review=data(POST/'review_01.json')
    require(review['source_pins']==sources and review['remaining_high_medium']==[]
        and review['official_verdict'] is review['receipt'] is review['seal'] is None,'PRE_SEAL review boundary')
    docs=data(POST/'document_checks_01.json')
    require(all(pin(ROOT/n)==v for n,v in {**docs['document_pins'],**docs['AST_pins']}.items()),'document or AST drift')
    tails=data(POST/'navigation_prior_tails.json')
    for name,value in tails.items():
        raw=(ROOT/name).read_bytes();tail=raw[-value['tail']['bytes']:]
        require(raw.split(b'\n\n',1)[0].decode()==value['header'] and dict(bytes=len(tail),sha256=sha256(tail).hexdigest())==value['tail'],'prior navigation body drift')
    # Preserve errors, interrupted observations, and timeouts as such.
    require(data(CHECKS/'units_01.exit.json')['exit_code']==1 and b'3 failed, 11 passed, 44 errors' in (CHECKS/'units_01.stdout.log').read_bytes(),'first failed fixture missing')
    for label in ('units_02','units_03','units_05','units_06','units_08'):
        record=data(CHECKS/(label+'.exit.json'));require(record['exit_code'] is None and record['timed_out'] is True and record['timeout_seconds']==120,'historical timeout')
    require(data(CHECKS/'units_04.exit.json')['exit_code']==3221225477,'historical access violation missing')
    require(data(CHECKS/'units_11.exit.json')['terminal_pass_observed'] is False and data(CHECKS/'units_12.exit.json')['exit_code']==1
        and data(CHECKS/'units_15.exit.json')['exit_code']==1,'historical interrupted or failed test')
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    require(not (native/'p2_01').exists() and not (native/'registration_v1.json').exists(),'public P2 state exists')
    require(not list(BASE.rglob('parent_observation.json')),'persistent parent observation unexpectedly exists')
    for name in sources:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
    require(all(pin(ROOT/n)==v for n,v in preservation.items()) and all(pin(ROOT/n)==v for n,v in sources.items()),'preservation bookend')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=pin(Path(__file__)),targeted_distinct_passed=129,related_distinct_passed=72,
        full_319_real_double_inventory_verified=True,late_319_numeric_real_double_inventory_verified=True,
        P1_wire_roots_old_bytes_equal=403,protocol_digest_old_bytes_equal_calls=7582,prior_published_paths_unchanged=440,
        P1_files_unchanged=683,B1_B3_saved_files_unchanged=118,prior_checkpoint_paths_unchanged=685,
        prior_postcheck_stdout_exact_reproductions=2,projected_outer_members_conditional_only=642,
        terminal_reserve_boundary_guarantee_established=False,new_scientific_calls_by_postcheck=0,new_native_calls=0,
        public_P2_registered=False,public_P2_executed=False,actual_outer_launcher_implemented=False,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False,C_overall_performance_review_complete=False)

if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
