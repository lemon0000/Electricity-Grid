"""Independent stdlib saved check; no current production/test/fixture import."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
PACKAGE=Path(__file__).resolve().parent;BASE=PACKAGE.parent;OUT=BASE/'checks_02';ROOT=BASE.parents[2]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def snapshot(p,n=None):
    for d in (OUT,BASE/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01'):
        path=d/('code_'+p['sha256']+'.snapshot')
        if path.exists():data=path.read_bytes();assert pin(data)==p;return data
    old=read(BASE/'checks_01/baseline.json');path=ROOT/old['source_snapshots'][n]
    data=path.read_bytes();assert pin(data)==p;return data
def verify():
    baseline=read(OUT/'continuation_baseline.json');plan=read(OUT/'admission.json')
    preserved={**baseline['predecessor_preserved'],**baseline['preserved']}
    assert names(ROOT/n for n in preserved)==preserved
    assert len(baseline['predecessor_preserved'])==4333 and len(baseline['preserved'])==162
    assert names(ROOT/n for n in plan['source_pins'])==plan['source_pins']
    assert len(plan['source_pins'])==49 and plan['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    mutable={'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}
    assert all(p==baseline['sources'][n] for n,p in plan['source_pins'].items() if n not in mutable)
    for n,p in plan['source_pins'].items():assert snapshot(p,n)==(ROOT/n).read_bytes()
    entry='experiments/staged_rts24_saved_fresh_adoption_v1.py';tests='tests/test_staged_rts24_saved_fresh_adoption_v1.py'
    before=ast.parse(snapshot(baseline['sources'][entry],entry));after=ast.parse(snapshot(plan['source_pins'][entry],entry))
    compile(after,entry,'exec',dont_inherit=True)
    by_name={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    for node in before.body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name!='_saved_wire_layout':assert ast.dump(node)==ast.dump(by_name[node.name]),node.name
    def other_nodes(tree):
        return [ast.dump(n) for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef)) and not (
            isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_SAVED_WIRE_TYPES' for t in n.targets))]
    assert other_nodes(before)==other_nodes(after)
    before_layout=next(n for n in before.body if isinstance(n,ast.FunctionDef) and n.name=='_saved_wire_layout')
    expected_layout=deepcopy(before_layout)
    layout_assignment=next(n for n in expected_layout.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='layouts' for t in n.targets))
    layout_assignment.value.keys.append(ast.Name(id='SavedWireFailureEventData',ctx=ast.Load()))
    layout_assignment.value.values.append(ast.parse('(contracts,SavedWireFailureData)',mode='eval').body)
    broker_branch=next(n for n in expected_layout.body if isinstance(n,ast.If))
    broker_branch.body=ast.parse("facts=parse(value._facts)\nrequire(type(facts['has_controller_return']) is type(facts['has_failure']) is bool,'broker return dependency flags')\nexpected=(ctx,contracts,SavedMailboxHeaderData)+((SavedControllerReturnData,) if facts['has_controller_return'] else ())+((SavedWireFailureData,) if facts['has_failure'] else ())").body
    assert ast.dump(expected_layout)==ast.dump(by_name['_saved_wire_layout']),'only the declared layout extensions are permitted'
    def type_assignment(tree):
        return next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_SAVED_WIRE_TYPES' for t in n.targets))
    expected_types=deepcopy(type_assignment(before));expected_types.value.elts.append(ast.Name(id='SavedWireFailureEventData',ctx=ast.Load()))
    assert ast.dump(expected_types)==ast.dump(type_assignment(after))
    assert ast.dump(before.body[-1])==ast.dump(after.body[-1])
    required=('validate_saved_stage_transcript_data','validate_saved_stage_failure_data','validate_saved_wire_failure_data',
        'compose_saved_failure_event_data','validate_saved_controller_binding_data','validate_saved_controller_return_data',
        'validate_saved_broker_return_data','validate_saved_constructor_diagnostic_data')
    assert set(required)<=set(by_name)
    before_tests=ast.parse(snapshot(baseline['sources'][tests],tests));after_tests=ast.parse(snapshot(plan['source_pins'][tests],tests))
    assert [ast.dump(n) for n in after_tests.body[:len(before_tests.body)]]==[ast.dump(n) for n in before_tests.body]
    selected=[]
    for label,group in plan['groups'].items():
        capture=read(OUT/(label+'.exit.json'));harness=read(OUT/(label+'.harness.json'))
        assert capture['accepted'] and capture['returncode']==0 and capture['error'] is None
        assert capture['source_pins']==plan['source_pins'] and capture['source_epoch']==plan['source_epoch']
        assert capture['cap_seconds']==plan['caps'][label] and capture['charged_seconds']<=plan['caps'][label]
        assert harness['pytest_exit_code']==0 and harness['requested_nodes']==group
        assert set(harness['collected_nodes'])==set(harness['passed_call_nodes'])==set(group)
        assert len(harness['passed_call_nodes'])==len(set(harness['passed_call_nodes']))==len(group)
        assert not harness['failed_phases'] and not harness['skipped_phases']
        assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
        assert harness['guards_installed_before_repository_import'] and harness['native_constructor_original_restored']
        assert re.search(r'\b'+str(len(group))+r' passed in ',(OUT/(label+'.stdout.log')).read_text(encoding='utf-8'))
        selected.extend(group)
    assert len(selected)==len(set(selected))==plan['current_targeted_nodes']
    old_plan=read(BASE/'checks_01/admission_r3.json')
    prior_wire={n for g in old_plan['groups'].values() for n in g if '::test_saved_wire_' in n}
    assert len(prior_wire)==51 and prior_wire<=set(selected)
    assert plan['new_nodes']==len(selected)-51 and plan['historical_only_nodes']==480
    review=read(OUT/'pre_seal_review.json')
    assert review['source_epoch']==plan['source_epoch'] and not review['remaining_must_fix_findings']
    assert review['official_verdict'] is None and review['production_seal'] is False
    records={p.relative_to(ROOT).as_posix():(p,read(p)) for d in (BASE/'checks_01',BASE/'final_package_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']));spent=dict(static=0.,pytest=0.)
    for i,n in enumerate(ordered):
        path,r=records[n];assert r['prior_record_pins']=={k:pin(records[k][0].read_bytes()) for k in ordered[:i]}
        assert all(abs(r['previous_charged_seconds'][k]-spent[k])<1e-7 for k in spent)
        assert r['fixed_before']==r['fixed_after'] and r['charged_seconds']<=r['cap_seconds']
        if path.parent in (OUT,PACKAGE):
            assert r['fixed_before']==pin(raw(preserved)) and r['postcheck_pins_match']
            assert r['source_pins']==r['after_source_pins']==plan['source_pins'] and r['helper_pins']==r['after_helper_pins']
        for suffix in ('stdout','stderr'):assert pin(path.with_name(r['label']+'.'+suffix+'.log').read_bytes())==r[suffix+'_pin']
        for name,p in {**r['source_pins'],**r['helper_pins']}.items():snapshot(p,name)
        state=r['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        assert state['stdout_observed_bytes']<=262144 and state['stderr_observed_bytes']<=32768
        assert all(r[k] is False for k in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
        spent[r['kind']]+=r['charged_seconds']
    assert spent['static']<=120 and spent['pytest']<=420 and sum(spent.values())<=540
    assert {r['label'] for _,r in records.values() if not r['accepted']}=={'wip_static_02','r1_new_smoke','r3_old_expectation_a_12'}
    navigation=read(OUT/'navigation_changes.json')
    for n,row in navigation.items():
        data=(ROOT/row['checkpoint_snapshot']).read_bytes();assert pin(data)==row['checkpoint_pin']
        assert pin((ROOT/n).read_bytes()) in (row['checkpoint_pin'],row['published_pin'])
        header,body=data.split(b'\n\n',1);prefix=row['prefix'].encode();assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    main=[p for d in (BASE/'checks_01',OUT) for p in d.rglob('*') if p.is_file()]
    packages=[p for d in (BASE/'final_package_01',PACKAGE) for p in d.rglob('*') if p.is_file()]
    assert len(main)<=180 and sum(p.stat().st_size for p in main)<=14*1024**2
    assert len(packages)<=24 and sum(p.stat().st_size for p in packages)<=2*1024**2
    all_files=[p for p in BASE.rglob('*') if p.is_file()]
    assert len(all_files)<=204 and sum(p.stat().st_size for p in all_files)<=16*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],current_targeted_nodes=len(selected),
        prior_wire_nodes=51,new_nodes=plan['new_nodes'],historical_only_regression_nodes=480,preserved_paths=len(preserved),
        all_eight_data_APIs_present=True,old_scientific_API_and_CLI_AST_preserved=True,
        old_wire_layout_extended=True,production_seal=False,charged_before_capture=spent,
        production_module_imported_by_oracle=False,actual_F=False,actual_fresh=False,run_authority=False,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
if __name__=='__main__':
    mode=sys.argv[1];freeze_path=PACKAGE/'checkpoint_freeze.json'
    if mode=='saved':
        navigation=read(OUT/'navigation_changes.json')
        paths=[p for p in OUT.rglob('*') if p.is_file()]+[Path(__file__).resolve()]
        paths.append(ROOT/'docs/plan/continuation_handoff_20261026_saved_fresh_wire_completion.md')
        freeze=dict(authority='DRAFT_NONAUTHORITATIVE',production_seal=False,bound_files=names(paths))
        with freeze_path.open('xb') as stream:stream.write(raw(freeze))
    freeze=read(freeze_path);assert names(ROOT/n for n in freeze['bound_files'])==freeze['bound_files']
    report=verify()
    with (PACKAGE/(mode+'_report.json')).open('xb') as stream:stream.write(raw(report))
    print(json.dumps(report,sort_keys=True))
