"""Independent stdlib archive check for the bounded root-repair checkpoint."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
PACKAGE=Path(__file__).resolve().parent;OUT=PACKAGE.parent/'checks_01';ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def verify():
    freeze=read(PACKAGE/'checkpoint_freeze.json');baseline=read(OUT/'baseline.json');plan=read(OUT/'admission_r3.json')
    assert freeze['authority']=='DRAFT_NONAUTHORITATIVE' and freeze['production_seal'] is False
    assert names(ROOT/n for n in freeze['bound_files'])==freeze['bound_files']
    assert len(baseline['preserved'])==4333 and names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert names(ROOT/n for n in plan['source_pins'])==plan['source_pins']==freeze['source_pins']
    assert len(plan['source_pins'])==49 and plan['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    changed={n for n,p in plan['source_pins'].items() if p!=baseline['sources'][n]}
    assert changed=={'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}
    for n,before in baseline['old_nodes'].items():
        tree=ast.parse((ROOT/n).read_bytes());compile(tree,n,'exec',dont_inherit=True)
        after=[sha256(ast.dump(node,include_attributes=False).encode()).hexdigest() for node in tree.body]
        if n.startswith('experiments/'):assert after[:len(before)-1]==before[:-1] and after[-1]==before[-1]
        elif n.startswith('tests/'):assert after[:len(before)]==before
        else:assert after==before
    expected=[n for group in plan['groups'].values() for n in group]
    assert len(expected)==len(set(expected))==531 and plan['new_nodes']==51 and plan['regression_nodes']==480
    observed=[]
    for original_label,group in plan['groups'].items():
        label='r4_old_expectation_a_12' if original_label=='r3_old_expectation_a_12' else original_label
        record=read(OUT/(label+'.exit.json'));harness_path=OUT/(label+'.harness.json');harness=read(harness_path)
        assert record['accepted'] and record['returncode']==0 and record['error'] is None
        assert record['source_pins']==plan['source_pins'] and record['source_epoch']==plan['source_epoch']
        assert record['cap_seconds']==plan['caps'][original_label] and record['charged_seconds']<=plan['caps'][original_label]
        assert harness['pytest_exit_code']==0 and harness['requested_nodes']==group
        assert set(harness['collected_nodes'])==set(harness['passed_call_nodes'])==set(group)
        assert len(harness['passed_call_nodes'])==len(set(harness['passed_call_nodes']))==len(group)
        assert not harness['failed_phases'] and not harness['skipped_phases']
        assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,
            native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
        assert harness['guards_installed_before_repository_import'] and harness['native_constructor_original_restored']
        assert harness['actual_saved_F_execution'] is False and harness['production_policy_decided'] is False
        # stdout independently supplies the terminal call count, not just the harness summary.
        stdout=(OUT/(label+'.stdout.log')).read_text(encoding='utf-8')
        assert re.search(r'\b'+str(len(group))+r' passed in ',stdout)
        observed.extend(harness['passed_call_nodes'])
    assert len(observed)==len(set(observed))==len(expected) and set(observed)==set(expected)
    records={p.relative_to(ROOT).as_posix():(p,read(p)) for directory in (OUT,PACKAGE) for p in directory.glob('*.exit.json')}
    spent=dict(static=0.,pytest=0.);ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']));failures=[]
    for index,name in enumerate(ordered):
        path,record=records[name]
        prior={n:pin(records[n][0].read_bytes()) for n in ordered[:index]}
        assert record['prior_record_pins']==prior
        assert all(abs(record['previous_charged_seconds'][k]-spent[k])<1e-7 for k in spent)
        assert record['fixed_before']==record['fixed_after']==pin(raw(baseline['preserved']))
        for suffix in ('stdout','stderr'):assert pin(path.with_name(record['label']+'.'+suffix+'.log').read_bytes())==record[suffix+'_pin']
        assert record['source_epoch']==sha256(raw(record['source_pins'])).hexdigest()
        for n,p in {**record['source_pins'],**record['helper_pins']}.items():
            snapshot=OUT/('code_'+p['sha256']+'.snapshot')
            if not snapshot.exists():snapshot=ROOT/baseline['source_snapshots'][n]
            assert pin(snapshot.read_bytes())==p
        state=record['bounded_drain']
        assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        assert state['stdout_observed_bytes']<=262144 and state['stderr_observed_bytes']<=32768
        assert record['package_postcheck_verified'] and record['charged_seconds']<=record['cap_seconds']
        assert all(record[k] is False for k in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
        if not record['accepted']:failures.append(record['label'])
        spent[record['kind']]+=record['charged_seconds']
    assert set(failures)=={'wip_static_02','r1_new_smoke','r3_old_expectation_a_12'}
    drift=read(OUT/'r3_old_expectation_a_12.exit.json')
    assert drift['returncode']==0 and drift['source_pins']==plan['source_pins'] and drift['error'] is None
    retry=read(OUT/'admission_retry.json')
    assert retry['source_pins']==plan['source_pins'] and retry['caps']=={'r4_old_expectation_a_12':32}
    assert retry['groups']['r4_old_expectation_a_12']==plan['groups']['r3_old_expectation_a_12']
    reconciliation=read(OUT/'retry_archive_reconciliation.json')
    assert reconciliation['used_retry_plan_pin']==pin((OUT/'admission_retry.json').read_bytes())
    assert reconciliation['actual_r3_plan_pin']==pin((OUT/'admission_r3.json').read_bytes())
    assert reconciliation['failed_capture_pin']==pin((OUT/'r3_old_expectation_a_12.exit.json').read_bytes())
    assert reconciliation['retry_capture_pin']==pin((OUT/'r4_old_expectation_a_12.exit.json').read_bytes())
    assert reconciliation['retry_harness_pin']==pin((OUT/'r4_old_expectation_a_12.harness.json').read_bytes())
    assert reconciliation['actual_retry_helper_pins']==read(OUT/'r4_old_expectation_a_12.exit.json')['helper_pins']
    assert reconciliation['source_pins']==plan['source_pins']
    assert reconciliation['after_helper_map_recorded'] is False
    assert reconciliation['stale_inherited_fields']=={k:retry[k] for k in ('previous_plan_pin','preserved_failure_pin','helper_pins')}
    assert pin((OUT/reconciliation['used_retry_plan_snapshot']).read_bytes())==reconciliation['used_retry_plan_pin']
    drift_harness=read(OUT/'r3_old_expectation_a_12.harness.json');group=plan['groups']['r3_old_expectation_a_12']
    assert drift_harness['pytest_exit_code']==0 and drift_harness['requested_nodes']==group
    assert set(drift_harness['collected_nodes'])==set(drift_harness['passed_call_nodes'])==set(group)
    assert not drift_harness['failed_phases'] and not drift_harness['skipped_phases']
    assert spent['static']<=120 and spent['pytest']<=420 and sum(spent.values())<=540
    # All failure records and their exact code bytes remain inside the bound history.
    assert all(pin(p.read_bytes())['sha256']==p.stem.removeprefix('code_') for p in OUT.glob('code_*.snapshot'))
    review=read(OUT/'pre_seal_review.json')
    assert review['source_epoch']==plan['source_epoch'] and review['remaining_must_fix_findings']==[]
    assert review['official_verdict'] is None and review['review_receipt_issued'] is False
    for n,row in freeze['navigation'].items():
        data=(ROOT/row['checkpoint_snapshot']).read_bytes();prefix=row['prefix'].encode('utf-8')
        assert pin(data)==row['checkpoint_pin']
        assert pin((ROOT/n).read_bytes()) in (row['checkpoint_pin'],row['published_pin'])
        header,body=data.split(b'\n\n',1);assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    for directory,files_cap,bytes_cap in ((OUT,180,14*1024**2),(PACKAGE,24,2*1024**2)):
        files=[p for p in directory.rglob('*') if p.is_file()]
        assert len(files)<=files_cap and sum(p.stat().st_size for p in files)<=bytes_cap
    return dict(authority='DRAFT_NONAUTHORITATIVE',production_seal=False,source_epoch=plan['source_epoch'],
        current_Source_nodes=531,new_nodes=51,regression_nodes=480,preserved_paths=4333,preserved_failures=failures,
        charged_seconds_before_this_capture=spent,old_AST_and_CLI_preserved=True,navigation_body_preserved=True,
        production_module_imported_by_oracle=False,two_root_risks_closed_in_declared_data_scope=True,
        actual_F=False,actual_fresh=False,final_parent_adoption=False,scientific_evidence_adopted=False,
        resource_admission=False,formal_result=False,run_authority=False)
if __name__=='__main__':
    report=verify();target=PACKAGE/('saved_report.json' if sys.argv[1]=='saved' else 'terminal_report.json')
    with target.open('xb') as stream:stream.write(raw(report))
    print(json.dumps(report,sort_keys=True))
